import json
import sys
import requests

from PyQt5.QtCore import Qt, QByteArray, QTimer
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QToolTip,
                             QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox)
from pathlib import Path
from agent import Agent
from constant import *
from util import curr_milliseconds, ensure_dir_exists


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

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.agent = Agent()
        self.captcha_url = f"{ROOT}/{VERIFY_PAGE}?t={curr_milliseconds()}"
        self.accounts = {}
        self.cache_dir = Path('.cache')
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

        account = self.load_current_account()
        username = None
        password = None
        if account and 'username' in account:
            username = account['username']
        if account and 'password' in account:
            password = account['password']
        # 用户名输入
        username_layout = QVBoxLayout()                

        self.username_input = QLineEdit()
        if username:
            self.username_input.setText(username)
        else:
            self.username_input.setPlaceholderText(username)
        self.username_input.setMinimumHeight(40)
        username_layout.addWidget(self.username_input)

        # 密码输入
        password_layout = QVBoxLayout()

        self.password_input = QLineEdit()
        if password:
            self.password_input.setText(password)
        else:
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
        
    def load_current_account(self):
        accounts_dir = self.cache_dir / 'accounts'
        if not accounts_dir.exists():
            return None
        for f in accounts_dir.glob("*.json"):
            with f.open('r', encoding=DEFAULT_ENCODING) as fp:
                account = json.load(fp)
            if 'username' not in account:
                continue
            self.accounts[account['username']] = account
        current_account_file = self.cache_dir / 'current_account.txt'
        with current_account_file.open('r', encoding=DEFAULT_ENCODING) as f:
            username = f.read()
        if username not in self.accounts:
            return None
        return self.accounts[username]

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
            QMessageBox.information(self, '成功', '登录成功！')
            # 登录成功后的操作，比如打开主窗口
            current_account_file =  self.cache_dir / f'current_account.txt'
            with current_account_file.open('w', encoding=DEFAULT_ENCODING) as f:
                f.write(username)
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
            return self.agent.login(username, password, captcha)
        except Exception as e:
            print(f"登录验证错误: {e}")
            return False


class MainWindow(QWidget):
    """登录成功后的主窗口示例"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('主窗口')
        self.setFixedSize(600, 400)

        layout = QVBoxLayout()
        welcome_label = QLabel('欢迎使用系统！')
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; color: #333;")

        layout.addWidget(welcome_label)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    login_window = LoginWindow()
    login_window.show()

    sys.exit(app.exec_())