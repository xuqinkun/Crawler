import concurrent.futures
import time

from PyQt5.QtCore import QObject, pyqtSignal, QWaitCondition, QMutex
from itertools import cycle # 导入循环迭代器
from agent import AmazonAgent
from bit_browser import *
from db_util import AmazonDatabase


class CrawlWorker(QObject):
    """爬取工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(str, str, float)  # 用户名,状态, 进度
    status_updated = pyqtSignal(str, str)  # 用户名, 状态
    log_updated = pyqtSignal(str, str)  # 用户名, 日志
    finished = pyqtSignal(str)  # 用户名
    error_occurred = pyqtSignal(str, str)  # 用户名, 错误信息

    def __init__(self, username, agent, logger, max_workers=5, batch_size=100):
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
        self.agent_pool = []
        # 添加暂停/恢复相关的同步对象
        self.max_workers = max_workers
        self.batch_size = batch_size
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

    def _initialize_agent_pool(self) -> list:
        """初始化并发爬取的 Agent/Driver 实例池"""
        self.status_updated.emit(self.username, "初始化浏览器池...")

        # 1. 获取所有可用的 BitBrowser ID
        browser_ids = get_all_browser_ids()
        if not browser_ids:
            print('"未找到任何比特浏览器窗口ID，请先创建或打开窗口。"')
            self.error_occurred.emit(self.username, "未找到任何比特浏览器窗口ID，请先创建或打开窗口。")
            return []

        # 2. 限制使用的窗口数量为 MAX_WORKERS
        target_ids = browser_ids[:self.max_workers]
        self.log_updated.emit(self.username, f"将使用 {len(target_ids)} 个浏览器窗口进行并发爬取。")

        agent_pool = []
        for i, browser_id in enumerate(target_ids):
            if self.is_stopped:
                print(f'worker已经停止')
                break

            # 3. 启动窗口并获取 Driver
            self.log_updated.emit(self.username, f"正在启动浏览器 #{i + 1}/{len(target_ids)} (ID: {browser_id[:8]}...)")
            driver = get_bitbrowser_driver(browser_id)
            if driver:
                try:
                    # 4. 为每个 Driver 创建一个独立的 Agent 实例
                    temp_agent = AmazonAgent(driver=driver)

                    # 5. 重新加载登录信息 (使用主 Agent 的用户名)
                    # 这一步确保新会话也能继承登录和Cookie状态
                    agent_pool.append(temp_agent)
                except Exception as e:
                    print(f"初始化 Agent 失败: {e}")
                    self.log_updated.emit(self.username, f"初始化 Agent 失败: {e}")
                    try:
                        driver.quit()
                    except:
                        pass

        self.agent_pool = agent_pool
        return agent_pool

    def _crawl_task(self, product, agent: AmazonAgent, db: AmazonDatabase):
        """单个商品的爬取任务，由线程池调用"""
        try:
            self.wait_if_paused()
            if self.is_stopped:
                return product, False

            agent.start_craw(product)

            # 使用互斥锁保护共享变量的更新
            self.mutex.lock()
            try:
                if product.completed:
                    self.completed_num += 1
                    # 更新进度
                    if self.is_running:
                        self.progress_updated.emit(self.username, '爬取中', self.get_progress())
                    return product, True  # Success
                else:
                    # 更新进度（即使失败也算处理了一次，但计数器不加）
                    if self.is_running:
                        self.progress_updated.emit(self.username, '爬取中', self.get_progress())
                    return product, False  # Failed/Captcha
            finally:
                self.mutex.unlock()
        except Exception as e:
            error_msg = f"爬取商品 {product.url} 时发生错误: {str(e)}"
            print(error_msg)
            self.log_updated.emit(self.username, error_msg)
            self.logger.error(error_msg)
            return product, False

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

        # 1. 初始化 Agent Pool
        agent_pool = self._initialize_agent_pool()
        if not agent_pool and not self.is_stopped:
            self.status_updated.emit(self.username, "并发爬取失败，浏览器初始化错误。")
            return
        # 2. 准备任务和 Agent 循环器
        tasks = list(product_uncompleted)
        agent_cycle = cycle(agent_pool)  # 循环使用 Agent 实例
        completed_products = []
        failed_products = []
        # 计算需要处理的批次
        total_to_process = len(product_uncompleted)
        processed_count = 0
        # 3. 使用线程池进行并发爬取
        self.status_updated.emit(self.username, "开始爬取商品")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agent_pool)) as executor:
            # 提交任务
            future_to_product = {}
            for product in tasks:
                self.wait_if_paused()
                if self.is_stopped:
                    break

                # 分配一个 Agent
                agent = next(agent_cycle)
                future = executor.submit(self._crawl_task, product, agent, db)
                future_to_product[future] = product

            # 处理结果
            for future in concurrent.futures.as_completed(future_to_product):
                if self.is_stopped:
                    break

                product, success = future.result()

                if success:
                    completed_products.append(product)
                    # 批量保存已完成的商品
                    if len(completed_products) >= self.batch_size:
                        db.batch_upsert_products_chunked(completed_products)
                        completed_products.clear()
                        time.sleep(0.1)
                # 失败的商品会自动保留在数据库中，等待下次重试

        # 4. 处理剩余的成功商品
        if completed_products:
            db.batch_upsert_products_chunked(completed_products)

        # 5. 关闭所有 Agent/Driver
        self.log_updated.emit(self.username, "爬取结束，正在关闭浏览器窗口...")
        # 完成任务
        self.progress_updated.emit(self.username, '结束', self.get_progress())

    def stop(self):
        """停止爬取任务"""
        # 加锁，确保状态修改的原子性
        self.mutex.lock()
        self.is_running = False
        self.is_stopped = True
        self.completed_num = 0
        self.first_running = True

        # 发送最终进度信号
        if hasattr(self, 'total_num'):
            self.progress_updated.emit(self.username, '已停止', 0)

        # 唤醒所有等待的线程
        self.condition.wakeAll()
        self.mutex.unlock()

        # 关闭所有并发Agent
        for agent in self.agent_pool:
            try:
                agent.stop()
            except Exception as e:
                print(f"关闭agent pool出错: {e}")
                # 继续清理其他agent，不因单个失败而停止

        # 清空agent pool
        self.agent_pool.clear()

        print(f"Worker {self.username} 已完全停止")
