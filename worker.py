import time

from PyQt5.QtCore import QObject, pyqtSignal


class CrawlWorker(QObject):
    """爬取工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(str, str, int)  # 用户名,状态, 进度
    status_updated = pyqtSignal(str, str)  # 用户名, 状态
    log_updated = pyqtSignal(str, str)  # 用户名, 日志
    finished = pyqtSignal(str)  # 用户名
    error_occurred = pyqtSignal(str, str)  # 用户名, 错误信息

    def __init__(self, username, agent):
        super().__init__()
        self.username = username
        self.agent = agent
        self.is_running = True

    def run(self):
        """执行爬取任务"""
        try:
            self.status_updated.emit(self.username, "爬取中")
            self.log_updated.emit(self.username, f"[开始] {self.username} 开始执行爬取任务")

            # 模拟爬取过程 - 实际使用时替换为真实的爬取逻辑
            for progress in range(0, 101, 5):
                if not self.is_running:
                    self.log_updated.emit(self.username, f"[中断] {self.username} 爬取任务被中断")
                    return

                # 更新进度
                self.progress_updated.emit(self.username, '爬取中', progress)

                # 模拟工作
                time.sleep(0.1)

                # 添加日志
                if progress % 20 == 0:
                    self.log_updated.emit(self.username, f"[进度] {self.username} 已完成 {progress}%")

            # 完成任务
            self.progress_updated.emit(self.username, '已完成', 100)
            self.status_updated.emit(self.username, "已完成")
            self.log_updated.emit(self.username, f"[完成] {self.username} 爬取任务已完成")
            self.finished.emit(self.username)

        except Exception as e:
            error_msg = f"爬取过程中发生错误: {str(e)}"
            self.error_occurred.emit(self.username, error_msg)

    def stop(self):
        """停止爬取任务"""
        self.is_running = False