import time
import requests
from PyQt5.QtCore import QObject, pyqtSignal, QWaitCondition, QMutex
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from constant import amazon_cookies
from db_util import AmazonDatabase


# 批量处理大小和并发数配置
BATCH_SIZE = 100
MAX_WORKERS = 1  # 并发线程数，可根据网络状况调整

class CrawlWorker(QObject):
    """爬取工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(str, str, float)  # 用户名,状态, 进度
    status_updated = pyqtSignal(str, str)  # 用户名, 状态
    log_updated = pyqtSignal(str, str)  # 用户名, 日志
    finished = pyqtSignal(str)  # 用户名
    error_occurred = pyqtSignal(str, str)  # 用户名, 错误信息

    def __init__(self, username, agent, logger):
        super().__init__()
        self.username = username
        self.logger = logger
        self.agent = agent
        self.completed_num = 0
        self.total_num = 0
        self.is_running = True
        self.is_paused = False
        self.is_stopped = False
        self.first_running = True
        # 添加暂停/恢复相关的同步对象
        self.mutex = QMutex()
        self.condition = QWaitCondition()

    def get_progress(self) -> float:
        if self.total_num == 0:
            return 0
        else:
            return (100 * self.completed_num) / self.total_num

    def pause(self):
        """暂停工作线程"""
        self.mutex.lock()
        self.is_paused = True
        self.is_running = False
        self.mutex.unlock()

    def resume(self):
        """恢复工作线程"""
        self.mutex.lock()
        self.is_running = True
        self.is_paused = False
        self.condition.wakeAll()  # 唤醒所有等待的线程
        self.mutex.unlock()

    def wait_if_paused(self):
        """检查是否暂停，如果暂停则等待"""
        self.mutex.lock()
        while self.is_paused and not self.is_stopped:
            # 在等待时发送暂停状态
            self.condition.wait(self.mutex)  # 等待恢复信号
        self.mutex.unlock()

    def run(self):
        """执行爬取任务"""
        db = AmazonDatabase()
        db.connect()
        db.init()

        if self.first_running:
            self.first_running = False
            self.status_updated.emit(self.username, "开始爬取产品链接...")
        else:
            self.status_updated.emit(self.username, "恢复爬取进度...")

        self.log_updated.emit(self.username, f"[开始] {self.username} 开始获取产品链接")

        # 检查是否被暂停
        self.wait_if_paused()
        if not self.is_running:
            return

        all_saved_products = db.get_all_products(self.username)
        print(f'已保存产品数:{len(all_saved_products)}')
        ids = set([p.product_id for p in all_saved_products])
        expired_product_ids, new_products, total_items = self.agent.parse_product_list(ids=ids)

        if expired_product_ids:
            print(f'{len(expired_product_ids)}个商品已经失效')
            self.log_updated.emit(self.username, f"[开始] {self.username} 删除失效商品")
            db.batch_delete_products_by_ids(expired_product_ids)

        self.status_updated.emit(self.username, f"共获取{total_items}个链接")
        if total_items <= 0:
            self.status_updated.emit(self.username, "无法获取产品链接")
            return

        # 检查是否被暂停
        self.wait_if_paused()
        if self.is_stopped:
            return

        if new_products:
            print(f'新增加{len(new_products)} 个商品')
            db.batch_upsert_products_chunked(new_products)

        self.log_updated.emit(self.username, f"[开始] {self.username} 开始执行爬取任务")
        self.total_num = total_items
        print(f'商品总数:{total_items}')

        product_uncompleted = db.get_product_uncompleted(self.username)
        print(f'未解析完成的商品数:{len(product_uncompleted)}')
        self.completed_num = self.total_num - len(product_uncompleted)

        if self.get_progress() > 0 and self.is_running:
            self.progress_updated.emit(self.username, '爬取中', self.get_progress())

        failed_products = self.do_craw_concurrent(db, product_uncompleted)

        # 将失败的商品重新放入待处理队列（可选）
        # 这里可以根据需求决定是否重试失败的商品
        if failed_products and not self.is_stopped:
            print(f"有 {len(failed_products)} 个商品爬取失败")
            self.log_updated.emit(self.username, f"[警告] {len(failed_products)} 个商品爬取失败")
            self.do_craw_concurrent(db, product_uncompleted)

        # 完成任务
        self.progress_updated.emit(self.username, '结束', self.get_progress())

    def do_craw_concurrent(self, db, product_uncompleted):
        def crawl_single_product(product):
            """单个产品的爬取任务"""
            try:
                if self.is_stopped:
                    return None, product, "stopped"

                self.wait_if_paused()
                if self.is_stopped:
                    return None, product, "stopped"

                # 创建Session的副本，避免线程间竞争
                data = self.agent.start_craw(url=product.url)
                data.product_id = product.product_id

                if data.completed:
                    return data, product, "success"
                else:
                    return None, product, "failed"

            except Exception as e:
                return None, product, str(e)

        # 使用线程池并发执行
        completed_products = []
        failed_products = []
        # 计算需要处理的批次
        total_to_process = len(product_uncompleted)
        processed_count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while processed_count < total_to_process and not self.is_stopped:
                # 检查是否暂停
                self.wait_if_paused()

                # 获取当前批次的产品
                batch_size = min(BATCH_SIZE, total_to_process - processed_count)
                current_batch = []
                for _ in range(batch_size):
                    if product_uncompleted:
                        product = product_uncompleted.pop()
                        current_batch.append(product)
                        processed_count += 1

                if not current_batch:
                    break

                # 为每个任务创建独立的session副本
                futures = []
                for product in current_batch:
                    # 为每个线程创建独立的Session
                    future = executor.submit(crawl_single_product, product)
                    futures.append(future)

                # 收集当前批次的结果
                for future in concurrent.futures.as_completed(futures):
                    try:
                        data, product, status = future.result(timeout=10)  # 3s超时
                        if self.is_stopped:
                            break
                        if status == "success" and data:
                            completed_products.append(data)
                            self.completed_num += 1
                        elif status == "failed":
                            print(f'链接{product.url} 解析失败')
                            failed_products.append(product)
                        elif isinstance(status, str) and status != "stopped":
                            # 发生异常
                            error_msg = f"爬取过程中发生错误: {product.url} {status}"
                            self.log_updated.emit(self.username, error_msg)
                            print(error_msg)
                            self.logger.error(error_msg)
                            failed_products.append(product)

                        # 更新进度
                        if self.is_running:
                            self.progress_updated.emit(self.username, '爬取中', self.get_progress())

                    except concurrent.futures.TimeoutError:
                        error_msg = f"爬取超时: {product.url}"
                        self.log_updated.emit(self.username, error_msg)
                        print(error_msg)
                        self.logger.error(error_msg)
                        failed_products.append(product)
                    except Exception as e:
                        error_msg = f"处理结果时发生错误: {str(e)}"
                        self.log_updated.emit(self.username, error_msg)
                        print(error_msg)
                        self.logger.error(error_msg)

                # 批量保存已完成的商品
                if len(completed_products) >= BATCH_SIZE:
                    db.batch_upsert_products_chunked(completed_products)
                    completed_products.clear()

                    # 短暂暂停，避免对数据库造成过大压力
                    time.sleep(0.1)
        # 处理剩余的成功商品
        if completed_products:
            db.batch_upsert_products_chunked(completed_products)
        return failed_products

    def stop(self):
        """停止爬取任务"""
        # 加锁，确保状态修改的原子性
        self.mutex.lock()
        self.is_running = False
        self.is_stopped = True
        self.completed_num = 0
        self.finished = False
        self.first_running = True
        # 这一步确保在 wait_if_paused() 中阻塞的线程能够跳出等待
        self.condition.wakeAll()
        self.agent.stop()
        self.mutex.unlock()
