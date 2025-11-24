from datetime import datetime

import requests
from db_util import AmazonDatabase
from constant import amazon_cookies
from PyQt5.QtCore import QObject, pyqtSignal


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
        self.is_running = True
        self.completed_num = 0
        self.total_num = 0

    def get_progress(self) -> float:
        if self.total_num == 0:
            return 0
        else:
            return (100 * self.completed_num) / self.total_num

    def run(self):
        """执行爬取任务"""
        db = AmazonDatabase()
        db.connect()
        db.init()

        self.status_updated.emit(self.username, "获取产品链接")
        self.log_updated.emit(self.username, f"[开始] {self.username} 开始获取产品链接")

        all_saved_products = db.get_all_products()
        ids = set([p.product_id for p in all_saved_products])
        new_products, total_items = self.agent.parse_product_list(ids=ids)

        for p in new_products:
            p.owner = self.username
            db.upsert_product(p)
        self.status_updated.emit(self.username, f"共获取{total_items}个链接")
        self.log_updated.emit(self.username, f"[开始] {self.username} 共获取{total_items}个链接")

        self.status_updated.emit(self.username, "爬取中")
        self.log_updated.emit(self.username, f"[开始] {self.username} 开始执行爬取任务")
        self.total_num = total_items
        product_uncompleted = db.get_product_uncompleted()
        self.completed_num = self.total_num - len(product_uncompleted)
        session = requests.Session()
        session.cookies.update(amazon_cookies)
        for product in product_uncompleted:
            if not self.is_running:
                self.log_updated.emit(self.username, f"[中断] {self.username} 爬取任务被中断")
                return
            data = self.agent.start_craw(url=product.url, session=session)
            self.completed_num += 1
            self.log_updated.emit(self.username, f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {product.url} 解析完成")
            # 更新进度
            self.progress_updated.emit(self.username, '爬取中', self.get_progress())
            db.upsert_product(data)

        # 完成任务
        self.progress_updated.emit(self.username, '已完成', 100)
        self.status_updated.emit(self.username, "已完成")
        self.log_updated.emit(self.username, f"[完成] {self.username} 爬取任务已完成")
        self.finished.emit(self.username)

        # except Exception as e:
        #     error_msg = f"爬取过程中发生错误: {str(e)}"
        #     self.error_occurred.emit(self.username, error_msg)

    def stop(self):
        """停止爬取任务"""
        self.is_running = False