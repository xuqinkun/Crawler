import json
import os
import platform
import subprocess
import sys
from datetime import datetime
import pandas as pd
import requests

from PyQt5.QtCore import Qt, QByteArray, QTimer, QSize, QThread
from PyQt5.QtGui import QPixmap, QCursor, QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QToolTip,
                             QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QListWidget, QListWidgetItem,
                             QFileDialog, QFrame, QProgressBar, QTextEdit)
from pathlib import Path
from agent import Agent
from worker import CrawlWorker
from constant import *
from util import curr_milliseconds, ensure_dir_exists
from db_util import AmazonDatabase

db = AmazonDatabase()
db.connect()
db.init()
user_home = Path(os.path.expanduser('~'))

class ClickableLabel(QLabel):
    """可点击的QLabel，用于验证码图片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_tooltip_immediately)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.parent().refresh_captcha()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """鼠标进入事件"""
        self.tooltip_timer.start(50)  # 50毫秒后显示提示，几乎无延迟
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.tooltip_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def show_tooltip_immediately(self):
        """立即显示工具提示"""
        pos = self.mapToGlobal(self.rect().topRight())
        QToolTip.showText(pos, "点击刷新验证码", self)


class DownloadButton(QPushButton):
    """自定义下载按钮，支持开始/暂停状态切换"""

    def __init__(self, username, callback, parent=None):
        super().__init__(parent)
        self.username = username
        self.callback = callback
        self.is_running = False
        self.is_finished = False
        self.init_ui()

    def init_ui(self):
        """初始化按钮UI"""
        self.setText('开始')
        self.setFixedSize(80, 32)
        self.update_style()

        # 连接点击事件
        self.clicked.connect(self.on_clicked)

    def update_style(self):
        """根据状态更新按钮样式"""
        if self.is_finished:
            # 运行状态 - 橙色暂停按钮
            self.setStyleSheet("""
                   QPushButton {
                       background-color: #a8a8a8;
                       color: #e0e0e0;
                       border: none;
                       border-radius: 6px;
                       font-size: 12px;
                       font-weight: bold;
                       padding: 6px 12px;
                   }
                   QPushButton:hover {
                       background-color: #e96a00;
                   }
                   QPushButton:pressed {
                       background-color: #d45a00;
                   }
            """)
            self.setText('开始')
        elif self.is_running:
            # 运行状态 - 橙色暂停按钮
            self.setStyleSheet("""
                QPushButton {
                    background-color: #fd7e14;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #e96a00;
                }
                QPushButton:pressed {
                    background-color: #d45a00;
                }
            """)
            self.setText('暂停')
        else:
            # 停止状态 - 绿色开始按钮
            self.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)
            self.setText('开始')

    def on_clicked(self):
        """按钮点击事件"""
        self.is_running = not self.is_running
        self.update_style()

        # 执行回调函数
        if self.callback:
            self.callback(self.username, self.is_running)

    def set_running(self, running):
        """设置运行状态"""
        self.is_running = running
        self.update_style()


class ButtonSwitch(QWidget):
    def __init__(self, normal_icon: str, pressed_icon: str, callback: callable):
        super().__init__()
        self.is_pressed = False
        self.normal_icon = QIcon(normal_icon)
        self.pressed_icon = QIcon(pressed_icon)
        self.callback = callback
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 创建按钮
        self.button = QPushButton('', self)
        self.button.setFixedSize(40, 60)
        self.button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                }
            """)
        # 设置图标


        # 设置图标大小
        self.button.setIconSize(QSize(40, 40))
        self.button.setIcon(self.normal_icon)

        # 连接信号
        self.button.clicked.connect(self.on_button_clicked)

        layout.addWidget(self.button)
        self.setLayout(layout)
        self.setWindowTitle('图标按钮示例')
        self.setGeometry(0, 0, 100, 100)

    def on_button_clicked(self):
        # 切换图标
        if self.is_pressed:
            self.button.setIcon(self.normal_icon)
            self.is_pressed = False
        else:
            self.button.setIcon(self.pressed_icon)
            self.is_pressed = True
            self.callback()


class Button(QWidget):
    def __init__(self, icon: str, callback: callable, *args, **kwargs):
        super().__init__()
        self.icon = icon
        self.is_pressed = False
        self.init_ui()
        self.callback = lambda: callback(*args, **kwargs)  # 将参数包装到回调函数中

    def init_ui(self):
        layout = QVBoxLayout()

        # 创建按钮
        self.button = QPushButton('', self)
        self.button.setFixedSize(30, 40)
        self.button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                }
            """)
        # 设置图标
        self.normal_icon = QIcon(self.icon)

        # 设置图标大小
        self.button.setIconSize(QSize(30, 30))
        self.button.setIcon(self.normal_icon)

        # 连接信号
        self.button.clicked.connect(self.on_button_clicked)

        layout.addWidget(self.button)
        self.setLayout(layout)
        self.setWindowTitle('图标按钮示例')
        self.setGeometry(0, 0, 100, 100)

    def on_button_clicked(self):
        self.callback()

class LoginWindow(QWidget):
    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent
        self.captcha_url = f"{ROOT}/{VERIFY_PAGE}?t={curr_milliseconds()}"
        self.accounts = {}
        self.cache_dir = Path('.cache')
        self.login_success_callback = None  # 添加回调函数属性
        ensure_dir_exists(self.cache_dir)
        self.init_ui()
        self.refresh_captcha()

    def init_ui(self):
        self.setWindowTitle('用户登录')
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: 'Microsoft YaHei';
            }
            QLabel {
                color: #333;
                font-size: 14px;
                margin-bottom: 2px;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 12px 15px;
                font-size: 14px;
                background-color: white;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
                border-width: 2px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#refresh {
                background-color: #2196F3;
                margin-top: 10px;
                font-size: 14px;
            }
            QPushButton#refresh:hover {
                background-color: #1976D2;
            }
        """)

        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(40, 5, 40, 5)

        # 标题
        title_label = QLabel('用户登录')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 0px;
        """)

        # 用户名输入
        username_layout = QVBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入账号')
        self.username_input.setMinimumHeight(40)
        username_layout.addWidget(self.username_input)

        # 密码输入
        password_layout = QVBoxLayout()

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('请输入密码')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        password_layout.setContentsMargins(0,5,0,5)
        password_layout.addWidget(self.password_input)

        # 验证码区域
        captcha_layout = QVBoxLayout()

        # 验证码输入行
        captcha_input_layout = QHBoxLayout()
        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText('请输入验证码')
        self.captcha_input.setMaximumWidth(150)
        self.captcha_input.setMinimumHeight(40)

        # 验证码图片显示
        self.captcha_label = ClickableLabel(self)
        self.captcha_label.setFixedSize(120, 40)
        self.captcha_label.setStyleSheet("""
            border: 1px solid #ddd;
            background-color: white;
        """)
        self.captcha_label.setAlignment(Qt.AlignCenter)

        captcha_input_layout.addWidget(self.captcha_input)
        captcha_input_layout.addSpacing(10)
        captcha_input_layout.addWidget(self.captcha_label)
        captcha_input_layout.addStretch()

        captcha_layout.addLayout(captcha_input_layout)

        # 登录按钮
        self.login_btn = QPushButton('登录')
        self.login_btn.clicked.connect(self.login)

        # 添加到主布局
        main_layout.addWidget(title_label)
        main_layout.addLayout(username_layout)
        main_layout.addLayout(password_layout)
        main_layout.addLayout(captcha_layout)
        main_layout.addWidget(self.login_btn)

        self.setLayout(main_layout)

    def refresh_captcha(self):
        """从指定URL获取验证码图片"""
        try:
            # 将图片数据转换为QPixmap
            image_data = QByteArray(self.agent.get_captcha())
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            # 缩放图片以适应标签大小
            scaled_pixmap = pixmap.scaled(120, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.captcha_label.setPixmap(scaled_pixmap)
        except requests.exceptions.RequestException as e:
            QMessageBox.warning(self, '错误', f'获取验证码失败: {str(e)}')
            # 显示默认的错误图片
            self.captcha_label.setText('加载失败')
        except Exception as e:
            QMessageBox.warning(self, '错误', f'处理验证码时发生错误: {str(e)}')

    def login(self):
        """处理登录逻辑"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        captcha = self.captcha_input.text().strip()

        # 基本验证
        if not username:
            QMessageBox.warning(self, '输入错误', '请输入用户名')
            return
        if not password:
            QMessageBox.warning(self, '输入错误', '请输入密码')
            return
        if not captcha:
            QMessageBox.warning(self, '输入错误', '请输入验证码')
            return

        # 这里添加实际的登录验证逻辑
        if self.validate_login(username, password, captcha):
            # QMessageBox.information(self, '成功', '登录成功！')
            # 登录成功后保存账号信息
            db.upsert_account(username, password)
            if self.login_success_callback:
                self.login_success_callback(username, self.agent)
            self.close()
        else:
            QMessageBox.warning(self, '失败', '登录失败，请检查用户名、密码和验证码')
            # 登录失败后刷新验证码
            self.refresh_captcha()
            self.captcha_input.clear()

    def validate_login(self, username, password, captcha):
        """
        验证登录信息
        这里需要根据实际情况实现具体的验证逻辑
        """
        try:
            if self.agent.login(username, password, captcha):
               self.save_account(username, password)
               return True
        except Exception as e:
            print(f"登录验证错误: {e}")
            return False

    def save_account(self, username: str, password: str):
        account_save_dir = self.cache_dir / 'accounts'
        ensure_dir_exists(account_save_dir)
        account_save_file = account_save_dir / f'{username}.json'
        account = {
            'username': username,
            'password': password,
        }
        try:
            with account_save_file.open('w', encoding=DEFAULT_ENCODING) as f:
                json.dump(account, fp=f)
        except Exception as e:
            print(f'保存cookie失败[account={username}]:{e}')


class ConsoleWindow(QWidget):
    """控制台窗口，用于显示实时日志"""

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'{self.username} - 控制台日志')
        self.setGeometry(100, 100, 700, 500)  # 设置合适的位置和大小

        # 设置窗口标志，使其成为独立窗口
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(f'{self.username} 的爬取日志')
        title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 5px;
        """)

        # 状态信息栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")

        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("color: #007bff;")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_label)

        # 日志显示区域 - 使用 QTextEdit 代替 QLabel 以支持滚动
        self.log_display = QTextEdit()
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.log_display.setReadOnly(True)
        self.log_display.setPlainText(f"{self.username} 的控制台已启动...\n")

        # 控制按钮
        button_layout = QHBoxLayout()
        clear_btn = QPushButton("清空日志")
        close_btn = QPushButton("关闭")

        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)

        clear_btn.clicked.connect(self.clear_logs)
        close_btn.clicked.connect(self.close)

        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addWidget(title_label)
        layout.addLayout(status_layout)
        layout.addWidget(self.log_display, 1)  # 设置伸缩因子为1，让日志区域占据更多空间
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def clear_logs(self):
        """清空日志"""
        self.log_display.setPlainText(f"{self.username} 的日志已清空\n{'-' * 50}")
        self.status_label.setText("就绪")
        self.status_label.setStyleSheet("color: #6c757d; font-weight: bold;")

    def update_logs(self, log_text):
        """更新日志内容（供外部调用）"""
        current_text = self.log_display.toPlainText()
        self.log_display.setPlainText(current_text + log_text + '\n')

        # 自动滚动到底部
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """关闭事件处理"""
        super().closeEvent(event)


class MainWindow(QWidget):
    """重新设计的主窗口"""

    def __init__(self):
        super().__init__()
        self.cache_dir = Path('.cache')
        self.cookie_dir = self.cache_dir / 'cookies'
        self.accounts = {}
        self.login_window = None
        self.is_closing = False
        self.is_running = False
        self.console_windows = {}  # 存储控制台窗口
        self.crawl_workers = {}  # 存储爬取工作线程
        self.crawl_threads = {}  # 存储线程对象
        self.agents = {}
        self.account_list = {}
        self.start_buttons = {}
        self.delete_buttons = {}
        self.clear_buttons = {}
        self.export_path = user_home / 'Documents' / 'amazon'  # 全局导出目录
        ensure_dir_exists(self.export_path)
        self.init_ui()
        self.load_accounts()
        # 加载保存的导出路径
        self.load_export_path()

    def init_ui(self):
        self.setWindowTitle('爬虫管理工具')
        self.setFixedSize(900, 650)

        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', 'Segoe UI';
            }
            QLabel {
                color: #333;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
                alternate-background-color: #f8f9fa;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                background-color: #e9ecef;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 顶部标题区域
        header_layout = QHBoxLayout()

        title_label = QLabel('账号管理')
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin: 0;
        """)

        # 全局导出目录设置
        export_section = QHBoxLayout()
        export_label = QLabel('导出目录:')
        export_label.setStyleSheet("font-weight: bold;")

        self.export_path_label = QLabel()
        self.export_path_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 6px 10px;
                color: #495057;
                min-width: 300px;
            }
        """)

        change_export_btn = QPushButton('更改')
        change_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        change_export_btn.clicked.connect(self.change_export_path)

        # 浏览目录按钮
        browse_export_btn = QPushButton('浏览')
        browse_export_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #17a2b8;
                        color: white;
                        padding: 6px 12px;
                    }
                    QPushButton:hover {
                        background-color: #138496;
                    }
                """)
        browse_export_btn.clicked.connect(self.browse_export_path)
        browse_export_btn.setToolTip("在文件管理器中打开导出目录")

        export_section.addWidget(export_label)
        export_section.addWidget(self.export_path_label)
        export_section.addWidget(change_export_btn)
        export_section.addWidget(browse_export_btn)
        export_section.addStretch()

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(export_section)

        # 账号列表区域
        list_frame = QFrame()
        list_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
        """)

        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(15, 15, 15, 15)
        list_layout.setSpacing(10)

        # 列表标题
        list_header = QHBoxLayout()
        list_title = QLabel('账号列表')
        list_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")

        list_header.addWidget(list_title)
        list_header.addStretch()

        # 添加账号按钮
        self.add_btn = QPushButton('+ 添加账号')
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.add_btn.clicked.connect(self.add_account)

        list_header.addWidget(self.add_btn)
        list_layout.addLayout(list_header)

        # 账号列表
        self.account_list = QListWidget()
        self.account_list.setAlternatingRowColors(True)
        self.account_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        list_layout.addWidget(self.account_list)

        # 添加到主布局
        main_layout.addLayout(header_layout)
        main_layout.addWidget(list_frame)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel('就绪')
        self.status_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        main_layout.addLayout(status_layout)
        self.setLayout(main_layout)

        # 更新导出路径显示
        self.update_export_path_display()

    def browse_export_path(self):
        """在文件管理器中打开导出目录"""
        try:
            # 确保目录存在
            if not self.export_path.exists():
                self.export_path.mkdir(parents=True, exist_ok=True)
                self.status_label.setText(f"已创建导出目录: {self.export_path}")

            # 根据不同操作系统打开文件管理器
            system = platform.system()

            if system == "Windows":
                # Windows
                os.startfile(str(self.export_path))
            elif system == "Darwin":
                # macOS
                subprocess.run(["open", str(self.export_path)])
            else:
                # Linux 和其他类Unix系统
                subprocess.run(["xdg-open", str(self.export_path)])

            self.status_label.setText(f"已打开导出目录: {self.export_path}")
            print(f"打开导出目录: {self.export_path}")

        except Exception as e:
            error_msg = f"无法打开导出目录: {str(e)}"
            QMessageBox.warning(self, "打开目录失败", error_msg)
            self.status_label.setText("打开目录失败")
            print(f"打开目录错误: {e}")

    def closeEvent(self, event):
        """重写关闭事件，确保资源正确释放"""
        if self.is_closing:
            event.accept()
            return

        if self.is_running:
            # 询问用户是否确认退出
            reply = QMessageBox.question(
                self,
                '确认退出',
                '确定要退出程序吗？\n这将停止所有正在进行的爬取任务。',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        else:
            print('没用后台任务，直接退出')
            reply = QMessageBox.Yes
        if reply == QMessageBox.Yes:
            self.is_closing = True

            # 停止所有后台线程
            # self.stop_background_threads()

            # 停止所有Agent的爬取任务
            self.stop_all_agents()

            # 关闭所有控制台窗口
            self.close_all_consoles()

            # 关闭数据库连接
            self.close_database()

            # 保存配置
            self.save_before_exit()

            # 接受关闭事件
            event.accept()
            print("程序已安全退出")
        else:
            # 忽略关闭事件
            event.ignore()

    def stop_all_agents(self):
        """停止所有Agent的爬取任务"""
        print("正在停止所有爬取任务...")
        for username, agent in self.agents.items():
            try:
                if hasattr(agent, 'stop'):
                    agent.stop()
                    print(f"已停止 {username} 的爬取任务")
                elif hasattr(agent, 'is_running') and agent.is_running:
                    # 如果agent有运行状态但没有stop方法，尝试其他方式停止
                    print(f"警告: {username} 的Agent没有stop方法")
            except Exception as e:
                print(f"停止 {username} 的Agent时出错: {e}")

    def close_all_consoles(self):
        """关闭所有控制台窗口"""
        print("正在关闭所有控制台窗口...")
        for username, console in list(self.console_windows.items()):
            try:
                console.close()
                console.deleteLater()  # 确保Qt对象被删除
            except Exception as e:
                print(f"关闭 {username} 的控制台时出错: {e}")
        self.console_windows.clear()

    def close_database(self):
        """关闭数据库连接"""
        print("正在关闭数据库连接...")
        try:
            if hasattr(db, 'close'):
                db.close()
                print("数据库连接已关闭")
        except Exception as e:
            print(f"关闭数据库连接时出错: {e}")

    def save_before_exit(self):
        """退出前保存配置"""
        print("正在保存配置...")
        try:
            # 保存导出路径
            self.save_export_path()

            # 保存其他需要持久化的配置
            config_file = self.cache_dir / 'app_config.json'
            config = {
                'last_export_path': str(self.export_path),
                'window_geometry': {
                    'width': self.width(),
                    'height': self.height()
                }
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            print("配置已保存")
        except Exception as e:
            print(f"保存配置时出错: {e}")

    def update_export_path_display(self):
        """更新导出路径显示"""
        display_path = str(self.export_path)
        if len(display_path) > 50:
            display_path = "..." + display_path[-47:]
        self.export_path_label.setText(display_path)
        self.export_path_label.setToolTip(str(self.export_path))

    def change_export_path(self):
        """更改全局导出目录"""
        new_path = QFileDialog.getExistingDirectory(
            self,
            '选择导出目录',
            str(self.export_path)
        )
        if new_path:
            self.export_path = Path(new_path)
            self.update_export_path_display()
            self.save_export_path()

    def save_export_path(self):
        """保存导出路径到配置文件"""
        config_file = self.cache_dir / 'export_path.json'
        try:
            config = {'export_path': str(self.export_path)}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存导出路径失败: {e}")

    def load_export_path(self):
        """从配置文件加载导出路径"""
        config_file = self.cache_dir / 'export_path.json'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.export_path = Path(config.get('export_path', user_home / 'Downloads'))
            except Exception as e:
                print(f"加载导出路径失败: {e}")

    def add_account(self):
        """添加新账号"""
        agent = Agent()
        self.login_window = LoginWindow(agent)
        self.login_window.login_success_callback = self.on_login_success
        self.login_window.setWindowModality(Qt.ApplicationModal)
        self.login_window.show()

    def on_login_success(self, username, agent: Agent):
        """登录成功回调"""
        self.agents[username] = agent
        if username in self.accounts:
            QMessageBox.information(self, '提示', f'账号 {username} 已存在')
            return False

        self.accounts[username] = True
        self.create_account_item(username)
        self.status_label.setText(f'账号 {username} 添加成功')
        return True

    def load_accounts(self):
        """加载已保存的账号"""
        self.accounts = {}
        self.account_list.clear()
        try:
            self.accounts_data = db.get_all_accounts()
            for (username, password) in self.accounts_data:
                agent = Agent()
                agent.login(username)
                self.agents[username] = agent
                self.accounts[username] = True
                self.create_account_item(username)
        except Exception as e:
            print(f"加载账号失败: {e}")

    def create_account_item(self, username):
        """创建账号列表项"""
        item = QListWidgetItem()
        widget = QWidget()

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15, 10, 15, 10)

        # 顶部行：账号信息和主要操作按钮
        top_layout = QHBoxLayout()

        # 账号信息
        top_layout.setSpacing(10)

        # 账号信息区域 - 设置固定宽度
        account_info_widget = QWidget()
        account_info_widget.setFixedWidth(300)  # 固定宽度确保账号名显示完整
        account_info_layout = QHBoxLayout(account_info_widget)
        account_info_layout.setContentsMargins(0, 0, 0, 0)
        account_info_layout.setSpacing(4)

        account_name = QLabel(username)
        account_name.setStyleSheet("""
                    font-size: 16px; 
                    font-weight: bold; 
                    color: #2c3e50;
                    background-color: transparent;
                    min-height: 40px;
                """)
        account_name.setAlignment(Qt.AlignVCenter)
        account_name.setWordWrap(False)

        account_name.setMaximumWidth(180)  # 限制最大宽度

        status_label = QLabel('就绪')
        status_label.setStyleSheet("font-size: 12px; color: #28a745; font-weight: bold;")
        status_label.setProperty("username", username)

        account_info_layout.addWidget(account_name)
        account_info_layout.addWidget(status_label)

        top_layout.addWidget(account_info_widget)
        top_layout.addStretch()

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # 控制台按钮
        console_btn = QPushButton('日志')
        console_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        console_btn.clicked.connect(lambda: self.show_console(username))

        # 导出按钮
        export_btn = QPushButton('导出')
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        export_btn.clicked.connect(lambda: self.export_data(username))

        # 下载/暂停按钮
        start_btn = DownloadButton(username, self.on_start_toggle)
        self.start_buttons[username] = start_btn  # 存储按钮引用

        # 删除按钮
        delete_btn = QPushButton('删除')
        self.delete_buttons[username] = delete_btn
        delete_btn.setFixedSize(60, 32)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #c82333;
                background-repeat: no-repeat;
                background-position: center;
            }
            QPushButton:pressed {
                background-color: #a71e2a;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_account(username))

        # 复位按钮样式
        clear_btn = QPushButton('清除')
        self.clear_buttons[username] = clear_btn
        restart_btn_style = """
        QPushButton {
            background-color: #6f42c1;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            padding: 6px 12px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #5a32a3;
        }
        QPushButton:pressed {
            background-color: #4c2b8a;
        }
        QPushButton:disabled {
            background-color: #a8a8a8;
            color: #e0e0e0;
        }
        """
        clear_btn.setStyleSheet(restart_btn_style)
        clear_btn.setDisabled(True)
        clear_btn.clicked.connect(lambda: self.clear(username))

        button_layout.addWidget(start_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(console_btn)
        button_layout.addWidget(delete_btn)

        top_layout.addLayout(button_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_label = QLabel('进度:')
        progress_label.setStyleSheet("font-size: 12px; color: #6c757d;")

        progress_bar = QProgressBar()
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)

        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(progress_bar)
        progress_layout.addStretch()

        # 添加到主布局
        main_layout.addLayout(top_layout)

        widget.setLayout(main_layout)
        widget.setProperty("username", username)

        item.setSizeHint(widget.sizeHint())
        self.account_list.addItem(item)
        self.account_list.setItemWidget(item, widget)

    def on_start_toggle(self, username, is_running):
        """启动按钮状态切换回调"""
        try:
            if is_running:
                # 开始爬取
                self.status_label.setText(f'{username} 开始爬取...')
                # 更新状态标签
                self.update_account_status(username, '初始化...', '#17a2b8')

                self.start_worker(username)

                # 更新控制台日志
                if username in self.console_windows:
                    self.console_windows[username].update_logs(f"[开始爬取] {username} 开始执行爬取任务")
            else:
                # 暂停爬取
                self.pause_worker(username)
                self.status_label.setText(f'{username} 已暂停')

                # 更新状态标签
                self.update_account_status(
                    username=username,
                    status='已暂停',
                    progress=self.crawl_workers[username].get_progress(),
                    color='#ffc107')

                # 更新控制台日志
                if username in self.console_windows:
                    self.console_windows[username].update_logs(f"[暂停] {username} 爬取任务已暂停")
        except Exception as e:
            QMessageBox.warning(self, '错误', f'操作失败: {str(e)}')
            # 发生错误时恢复按钮状态
            if username in self.start_buttons:
                self.start_buttons[username].set_running(not is_running)

    def resume_worker(self, username):
        """恢复工作线程"""
        try:
            if username in self.crawl_workers:
                worker = self.crawl_workers[username]
                worker.resume()
                print(f"已恢复 {username} 的爬取任务")

        except Exception as e:
            print(f"恢复爬取任务时出错: {e}")

    def start_worker(self, username):
        """开始爬取任务"""
        try:
            agent = self.agents[username]

            # 如果
            if username in self.crawl_workers and self.crawl_workers[username].is_paused:
                self.resume_worker(username)

            # 创建工作线程和QThread
            self.crawl_workers[username] = CrawlWorker(username=username, agent=agent)
            self.crawl_threads[username] = QThread()

            # 将工作线程移动到新线程
            self.crawl_workers[username].moveToThread(self.crawl_threads[username])

            # 连接信号槽
            worker = self.crawl_workers[username]
            thread = self.crawl_threads[username]

            worker.progress_updated.connect(self.on_progress_updated)
            worker.status_updated.connect(self.on_status_updated)
            worker.log_updated.connect(self.on_log_updated)
            worker.finished.connect(self.on_crawl_finished)
            worker.error_occurred.connect(self.on_crawl_error)

            # 连接线程开始和结束信号
            thread.started.connect(worker.run)
            thread.finished.connect(thread.deleteLater)

            # 启动线程
            thread.start()

            # 更新界面状态
            self.status_label.setText(f'{username} 开始爬取...')
            self.update_account_status(username, '爬取中', '#17a2b8')

            # 标记有任务在运行
            self.is_running = True

        except Exception as e:
            error_msg = f'启动爬取任务失败: {str(e)}'
            QMessageBox.warning(self, '错误', error_msg)
            if username in self.start_buttons:
                self.start_buttons[username].set_running(False)

    def pause_worker(self, username):
        """暂停工作线程"""
        try:
            if username in self.crawl_workers:
                worker = self.crawl_workers[username]
                worker.pause()
                print(f"已暂停 {username} 的爬取任务")

        except Exception as e:
            print(f"暂停爬取任务时出错: {e}")

    def stop_worker(self, username):
        """停止爬取任务"""
        try:
            if username in self.crawl_workers:
                # 停止工作线程
                self.crawl_workers[username].stop()

                # 停止QThread
                if username in self.crawl_threads:
                    self.crawl_threads[username].quit()

                    # 清理资源
                    del self.crawl_workers[username]
                    del self.crawl_threads[username]

                # 更新界面状态
                self.status_label.setText(f'{username} 就绪')
                self.update_account_status(username, '就绪', '#ffc107')

                # 更新按钮状态
                if username in self.start_buttons:
                    self.start_buttons[username].set_running(False)

        except Exception as e:
            print(f"停止爬取任务时出错: {e}")

    def on_progress_updated(self, username, status, progress):
        """处理进度更新信号"""
        # 确保在主线程中更新UI
        QTimer.singleShot(0, lambda: self.on_status_updated(username=username,
                                                            status=status,
                                                            progress=progress))

    def update_progress_bar(self, username, progress):
        """更新进度条"""
        for i in range(self.account_list.count()):
            item = self.account_list.item(i)
            widget = self.account_list.itemWidget(item)

            if widget and widget.property("username") == username:
                progress_bar = None
                for child in widget.findChildren(QProgressBar):
                    if child.property("username") == username:
                        progress_bar = child
                        break

                if progress_bar:
                    progress_bar.setValue(progress)
                break

    def on_status_updated(self, username: str, status: str = '', progress: float=0):
        """处理状态更新信号"""
        QTimer.singleShot(0, lambda: self.update_account_status(username=username,
                                                                status=status,
                                                                color=self.get_status_color(status),
                                                                progress=progress))

    def get_status_color(self, status):
        """根据状态获取颜色"""
        color_map = {
            '就绪': '#28a745',
            '初始化': '#17a2b8',
            '爬取中': '#17a2b8',
            '已停止': '#ffc107',
            '已完成': '#28a745',
            '错误': '#dc3545'
        }
        return color_map.get(status, '#6c757d')

    def on_log_updated(self, username, log_message):
        """处理日志更新信号"""
        QTimer.singleShot(0, lambda: self.update_console_logs(username, log_message))

    def update_console_logs(self, username, log_message):
        """更新控制台日志"""
        if username in self.console_windows:
            self.console_windows[username].update_logs(log_message)

    def on_crawl_finished(self, username):
        """处理爬取完成信号"""
        QTimer.singleShot(0, lambda: self.handle_crawl_finished(username))

    def handle_crawl_finished(self, username):
        """处理爬取完成"""
        # 清理线程资源
        self.start_buttons[username].is_finished = True
        self.start_buttons[username].is_running = False
        if username in self.crawl_workers:
            del self.crawl_workers[username]
        # if username in self.crawl_threads:
        #     del self.crawl_threads[username]

        # 更新按钮状态
        if username in self.start_buttons:
            self.start_buttons[username].set_running(False)

        # 更新状态
        self.status_label.setText(f'{username} 爬取完成')
        self.update_account_status(username=username, status='已完成', color='#28a745', progress=100)


    def check_all_tasks_finished(self):
        """检查是否所有爬取任务都已完成"""
        if not self.crawl_workers:  # 如果没有正在运行的爬取任务
            self.is_running = False

    def on_crawl_error(self, username, error_message):
        """处理爬取错误信号"""
        QTimer.singleShot(0, lambda: self.handle_crawl_error(username, error_message))

    def handle_crawl_error(self, username, error_message):
        """处理爬取错误"""
        # 清理线程资源
        if username in self.crawl_workers:
            del self.crawl_workers[username]
        if username in self.crawl_threads:
            del self.crawl_threads[username]

        # 更新按钮状态
        if username in self.start_buttons:
            self.start_buttons[username].set_running(False)

        # 更新状态
        self.status_label.setText(f'{username} 爬取出错')
        self.update_account_status(username, '错误', '#dc3545')

        # 显示错误消息
        QMessageBox.warning(self, '爬取错误', f'{username} 爬取过程中发生错误:\n{error_message}')

        # 更新控制台日志
        self.update_console_logs(username, f"[错误] {error_message}")

        # 检查是否所有任务都完成了
        self.check_all_tasks_finished()

    def update_account_status(self, username, status, color, progress: float=0):
        """更新账号状态标签"""
        if progress > 0:
            self.clear_buttons[username].setDisabled(False)
        if progress == 100.0:
            self.start_buttons[username].setDisabled(True)

        for i in range(self.account_list.count()):
            item = self.account_list.item(i)
            widget = self.account_list.itemWidget(item)

            if widget and widget.property("username") == username:
                # 查找状态标签
                status_label = None
                for child in widget.findChildren(QLabel):
                    if child.property("username") == username:
                        status_label = child
                        break

                if status_label:
                    if progress > 0:
                        status_label.setText(f'{status} {progress:.2f}%')
                    else:
                        status_label.setText(f'{status}')
                    status_label.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: bold;")
                break

    def show_console(self, username):
        """显示控制台窗口"""
        if username not in self.console_windows:
            self.console_windows[username] = ConsoleWindow(username)

        console_window = self.console_windows[username]
        console_window.show()
        console_window.raise_()  # 置于顶层
        console_window.activateWindow()  # 激活窗口

        # 确保控制台窗口不会完全覆盖主窗口
        main_geometry = self.geometry()

        # 设置控制台窗口位置，避免完全重叠
        new_x = main_geometry.x() + 50
        new_y = main_geometry.y() + 50
        console_window.move(new_x, new_y)

    def export_data(self, username, filename=None):
        """将用户的产品数据导出到CSV文件"""
        try:
            # 获取产品数据
            products = db.get_all_products(username)

            if not products:
                print(f"用户 {username} 没有产品数据")
                return False

            # 如果没有指定文件名，生成默认文件名
            if filename is None:
                timestamp = datetime.now().strftime("%Y年%m月%d日_%H时%M分%S秒")
                filename = self.export_path/username / f"products_{timestamp}.csv"
                ensure_dir_exists(filename.parent)

            # 将产品对象转换为字典列表
            products_data = []
            for n, product in enumerate(products):
                if product.completed:
                    product_dict = {
                        '序号': n + 1,
                        '产品ID': str(product.product_id),
                        'asin': product.asin,
                        '链接': product.url,
                        '有无库存': '有' if product.availability else '无',
                        '价格': 'N/A',
                        '运费': 'N/A',
                        '是否二手': 'N/A',
                        '从亚马逊发货': 'N/A',
                    }
                    if product.availability:
                        product_dict['价格'] = product.price
                        product_dict['运费'] = product.shipping_cost
                        product_dict['是否二手'] = '是' if product.used else '否'
                        product_dict['从亚马逊发货'] = '是' if product.shipping_from_amazon else '否'
                    products_data.append(product_dict)

            # 创建DataFrame并导出到CSV
            df = pd.DataFrame(products_data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')

            print(f"成功导出 {len(products)} 条产品数据到 {filename}")
            self.status_label.setText(f"成功导出 {len(products)} 条产品数据到 {filename}")
            return True

        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False

    def clear(self, username):
        # 确认重启对话框
        if username in self.crawl_workers and self.crawl_workers[username].is_running:
            QMessageBox.warning(
                self,
                '操作被禁止',
                f'账号 {username} 正在下载过程中，不可以清除数据！\n请先暂停下载任务。',
                QMessageBox.Ok
            )
            return False
        reply = QMessageBox.question(
            self,
            '确认清除',
            f'确定要清除下载进度吗？\n此操作将删除所有相关数据且不可恢复。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            print(f'清理爬取进度 {username}')
            self.update_account_status(username, '清理爬取进度', self.get_status_color(''))
            self.start_buttons[username].is_running = False
            self.start_buttons[username].is_finished = False
            self.start_buttons[username].update_style()
            self.stop_worker(username)
            db.delete_product_by_owner(username)
            self.update_account_status(username, '就绪', self.get_status_color('就绪'))

    def delete_account(self, username):
        # 确认删除对话框
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除账号 {username} 吗？\n此操作将删除所有相关数据且不可恢复。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            print(f'清空用户{username}的下载记录')

        if reply == QMessageBox.Yes:
            try:
                # 停止该账号的下载任务
                if username in self.start_buttons:
                    self.start_buttons[username].set_running(False)

                # 删除cookie文件
                cookie_file = self.cookie_dir / f'{username}.json'
                if cookie_file.exists():
                    cookie_file.unlink()
                    print(f"已删除cookie文件: {cookie_file}")

                # 删除数据库记录
                db.delete_account(username)
                print(f"已删除数据库记录: {username}")

                # 关闭控制台窗口
                if username in self.console_windows:
                    self.console_windows[username].close()
                    del self.console_windows[username]
                    print(f"已关闭控制台窗口: {username}")

                # 从内存中移除相关引用
                if username in self.accounts:
                    del self.accounts[username]
                if username in self.agents:
                    del self.agents[username]
                if username in self.start_buttons:
                    del self.start_buttons[username]
                if username in self.delete_buttons:
                    del self.delete_buttons[username]

                # 从界面中移除对应的列表项
                self.remove_account_item(username)

                self.status_label.setText(f'账号 {username} 已删除')
                self.load_accounts()
            except Exception as e:
                error_msg = f'删除账号时发生错误: {str(e)}'
                QMessageBox.warning(self, '删除失败', error_msg)
                self.status_label.setText("删除失败")
                print(f"删除账号错误: {e}")

    def remove_account_item(self, username):
        """从列表中移除账号项"""
        for i in range(self.account_list.count()):
            item = self.account_list.item(i)
            widget = self.account_list.itemWidget(item)

            if widget and widget.property("username") == username:
                # 移除列表项
                self.account_list.takeItem(i)

                # 删除widget和item
                widget.deleteLater()
                del item

                print(f"已从界面移除账号项: {username}")
                break


def excepthook(exctype, value, traceback):
    """全局异常处理"""
    print(f"未捕获的异常: {exctype.__name__}: {value}")
    sys.__excepthook__(exctype, value, traceback)


# 在主函数中设置
if __name__ == '__main__':
    # 设置全局异常处理
    sys.excepthook = excepthook

    app = QApplication(sys.argv)

    try:
        window = MainWindow()
        window.show()

        # 确保应用程序正确退出
        result = app.exec_()
        print(f"应用程序退出，代码: {result}")
        sys.exit(result)

    except Exception as e:
        print(f"应用程序启动失败: {e}")
        sys.exit(1)