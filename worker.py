from datetime import datetime

import requests
from PyQt5.QtCore import QObject, pyqtSignal, QWaitCondition, QMutex

from constant import amazon_cookies
from db_util import AmazonDatabase


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
        ids = set([p.product_id for p in all_saved_products])
        new_products, total_items = self.agent.parse_product_list(ids=ids)

        self.status_updated.emit(self.username, f"共获取{total_items}个链接")
        if total_items <= 0:
            self.status_updated.emit(self.username, "无法获取产品链接")
            return

        # 检查是否被暂停
        self.wait_if_paused()
        if self.is_stopped:
            return
        db.batch_upsert_products_chunked(new_products)
        self.log_updated.emit(self.username, f"[开始] {self.username} 开始执行爬取任务")
        self.total_num = total_items
        product_uncompleted = db.get_product_uncompleted(self.username)
        self.completed_num = self.total_num - len(product_uncompleted)
        if self.get_progress() > 0:
            self.progress_updated.emit(self.username, '爬取中', self.get_progress())
        session = requests.Session()
        session.cookies.update(amazon_cookies)
        completed_products = []
        while self.completed_num < self.total_num and len(product_uncompleted) > 0:
            product = product_uncompleted.pop()
            product_id = product.product_id
            try:
                if self.is_stopped:
                    self.log_updated.emit(self.username, f"[中断] {self.username} 爬取任务被中断")
                    return
                # 检查是否暂停
                self.wait_if_paused()
                if self.is_stopped:
                    return
                data = self.agent.start_craw(url=product.url, session=session)
                data.product_id = product_id
                # 更新进度
                # 检查是否暂停
                self.wait_if_paused()
                if self.is_stopped:
                    return

                if data.completed:
                    completed_products.append(data)
                    if len(completed_products) == 50:
                        db.batch_upsert_products_chunked(completed_products)
                        completed_products.clear()
                    self.completed_num += 1
                self.progress_updated.emit(self.username, '爬取中', self.get_progress())
            except Exception as e:
                error_msg = f"爬取过程中发生错误: {product.url} {str(e)}"
                self.log_updated.emit(self.username, error_msg)
                print(error_msg)
                self.logger.error(error_msg)
                product_uncompleted.insert(0, product)
        if len(completed_products) > 0:
            db.batch_upsert_products_chunked(completed_products)
        # 完成任务
        self.progress_updated.emit(self.username, '已完成', self.get_progress())
        self.status_updated.emit(self.username, "已完成")
        self.log_updated.emit(self.username, f"[完成] {self.username} 爬取任务已完成")
        self.finished.emit(self.username)

    def stop(self):
        """停止爬取任务"""
        self.is_running = False
        self.is_stopped = True