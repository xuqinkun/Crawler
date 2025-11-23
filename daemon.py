import sys
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, QObject


# 工作线程类
class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    data_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def do_work(self):
        """模拟耗时任务"""
        for i in range(1, 101):
            if not self._is_running:
                break

            # 模拟工作
            time.sleep(0.1)

            # 发送进度信号
            self.progress.emit(i)
            self.message.emit(f"正在处理项目 {i}/100")

            # 发送数据信号
            data = {"progress": i, "message": f"已完成 {i}%", "timestamp": time.time()}
            self.data_ready.emit(data)

        self.finished.emit()

    def stop_work(self):
        self._is_running = False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_thread()

    def init_ui(self):
        layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.status_label = QLabel("准备开始...")
        self.result_label = QLabel("")

        self.start_btn = QPushButton("开始任务")
        self.stop_btn = QPushButton("停止任务")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_worker)
        self.stop_btn.clicked.connect(self.stop_worker)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.result_label)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)
        self.setWindowTitle("多线程通信示例")
        self.setGeometry(300, 300, 400, 200)

    def setup_thread(self):
        # 创建线程和工作对象
        self.thread = QThread()
        self.worker = Worker()

        # 将工作对象移动到线程
        self.worker.moveToThread(self.thread)

        # 连接信号
        self.worker.progress.connect(self.update_progress)
        self.worker.message.connect(self.update_status)
        self.worker.data_ready.connect(self.handle_data)
        self.worker.finished.connect(self.work_finished)

        self.thread.started.connect(self.worker.do_work)
        self.thread.finished.connect(self.thread.deleteLater)

    def start_worker(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("任务进行中...")
        self.thread.start()

    def stop_worker(self):
        self.worker.stop_work()
        self.thread.quit()
        self.thread.wait()
        self.status_label.setText("任务已停止")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)

    def handle_data(self, data):
        self.result_label.setText(
            f"进度: {data['progress']}% | 消息: {data['message']}"
        )

    def work_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("任务完成!")
        self.thread.quit()

    def closeEvent(self, event):
        """窗口关闭时确保线程安全退出"""
        if self.thread.isRunning():
            self.worker.stop_work()
            self.thread.quit()
            self.thread.wait()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())