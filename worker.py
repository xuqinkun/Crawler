from datetime import datetime

import requests
from db_util import AmazonDatabase
from constant import amazon_cookies
from PyQt5.QtCore import QObject, pyqtSignal, QWaitCondition, QMutex


class CrawlWorker(QObject):
    """爬取工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(str, str, float)  # 用户名,状态, 进度
    status_updated = pyqtSignal(str, str)  # 用户名, 状态
    log_updated = pyqtSignal(str, str)  # 用户名, 日志
    finished = pyqtSignal(str)  # 用户名
    error_occurred = pyqtSignal(str, str)  # 用户名, 错误信息

    def __init__(self, username, agent):
        super().__init__()
        self.username = username
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

        self.log_updated.emit(self.username, f"[开始] {self.username} 共获取{total_items}个链接")

        # 检查是否被暂停
        self.wait_if_paused()
        if self.is_stopped:
            return
        for p in new_products:
            p.owner = self.username
            db.upsert_product(p)
        self.log_updated.emit(self.username, f"[开始] {self.username} 开始执行爬取任务")
        self.total_num = total_items
        product_uncompleted = db.get_product_uncompleted()
        self.completed_num = self.total_num - len(product_uncompleted)
        if self.get_progress() > 0:
            self.progress_updated.emit(self.username, '爬取中', self.get_progress())
        session = requests.Session()
        session.cookies.update(amazon_cookies)
        for product in product_uncompleted:
            try:
                if self.is_stopped:
                    self.log_updated.emit(self.username, f"[中断] {self.username} 爬取任务被中断")
                    return
                # 检查是否暂停
                self.wait_if_paused()
                if self.is_stopped:
                    return
                data = self.agent.start_craw(url=product.url, session=session)
                data.product_id = product.product_id
                # 更新进度
                # 检查是否暂停
                self.wait_if_paused()
                if self.is_stopped:
                    return
                db.upsert_product(data)
                self.completed_num += 1
                self.log_updated.emit(self.username, f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {product.url} 解析完成")
                self.progress_updated.emit(self.username, '爬取中', self.get_progress())
            except Exception as e:
                error_msg = f"爬取过程中发生错误: {str(e)}"
                self.error_occurred.emit(self.username, error_msg)

        # 完成任务
        self.progress_updated.emit(self.username, '已完成', 100)
        self.status_updated.emit(self.username, "已完成")
        self.log_updated.emit(self.username, f"[完成] {self.username} 爬取任务已完成")
        self.finished.emit(self.username)

    def stop(self):
        """停止爬取任务"""
        self.is_running = False
        self.is_stopped = True