import json
import os
import sys
import requests

from PyQt5.QtCore import Qt, QByteArray, QTimer, QSize
from PyQt5.QtGui import QPixmap, QCursor, QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QToolTip,
                             QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QListWidget, QListWidgetItem)
from pathlib import Path
from agent import Agent
from constant import *
from util import curr_milliseconds, ensure_dir_exists


home_path = os.path.expanduser('~')

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
    def __init__(self, icon_path: str):
        super().__init__()
        self.is_pressed = False
        self.initUI(icon_path)

    def initUI(self, icon_path: str):
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
        self.normal_icon = QIcon(icon_path)

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
        # 切换图标
        if self.is_pressed:
            self.button.setIcon(self.normal_icon)
            self.is_pressed = False
        else:
            self.button.setIcon(self.pressed_icon)
            self.is_pressed = True

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
            self.username_input.setPlaceholderText('请输入账号')
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


class MainWindow(QWidget):
    """登录成功后的主窗口示例"""

    def __init__(self):
        super().__init__()
        self.cache_dir = Path('.cache')
        self.accounts = {}
        self.login_window = None
        self.init_ui()
        self.agents = {}
        self.load_accounts()

    def init_ui(self):
        self.setWindowTitle('账号管理器')
        self.setFixedSize(500, 400)

        self.normal_style = """
                    QPushButton {
                        border: none;
                        background-image: url('icon/play_fill.png');
                        background-repeat: no-repeat;
                        background-position: center;
                    }
                    QPushButton:hover {
                        # background-image: url('hover.png');
                    }
                """

        # 点击后状态 - 按下背景
        self.pressed_style = """
                    QPushButton {
                        border: none;
                        background-image: url('pressed.png');
                        background-repeat: no-repeat;
                        background-position: center;
                    }
                """
        self.setStyleSheet("""
                    QWidget {
                        background-color: #f5f5f5;
                        font-family: 'Microsoft YaHei';
                    }
                    QLabel {
                        color: #333;
                        font-size: 16px;
                        font-weight: bold;
                        margin-bottom: 10px;
                    }
                    QListWidget {
                        background-color: white;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        padding: 5px;
                        font-size: 14px;
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 15px;
                        font-size: 14px;
                        font-weight: bold;
                        min-height: 20px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton#deleteBtn {
                        background-color: #f44336;
                        padding: 5px 10px;
                        font-size: 12px;
                    }
                    QPushButton#deleteBtn:hover {
                        background-color: #d32f2f;
                    }
                    QPushButton#addBtn {
                        background-color: #2196F3;
                        margin: 10px;
                        padding: 10px;
                    }
                    QPushButton#addBtn:hover {
                        background-color: #1976D2;
                    }
                """)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel('账号管理')
        title_label.setAlignment(Qt.AlignCenter)

        # 账号列表
        self.account_list = QListWidget()

        # 添加账号按钮
        self.add_btn = QPushButton('添加账号')
        self.add_btn.setObjectName("addBtn")
        self.add_btn.clicked.connect(self.add_account)

        # 添加控件到布局
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.account_list)
        main_layout.addWidget(self.add_btn)

        self.setLayout(main_layout)

    def add_account(self):
        """添加新账号"""
        agent = Agent()
        self.login_window = LoginWindow(agent)
        # 重写登录窗口的关闭事件，使其登录成功后通知主窗口
        self.login_window.login_success_callback = self.on_login_success
        self.login_window.show()

    def on_login_success(self, username, agent: Agent):
        """登录成功回调"""
        self.agents[username] = agent
        # 添加账号
        if username in self.accounts:
            print(f"账号已存在: {username}")
            return False
        self.create_account_item(username)
        return True

    def load_accounts(self):
        """加载已保存的账号"""
        self.accounts = {}
        self.account_list.clear()

        accounts_dir = self.cache_dir / 'accounts'
        if not accounts_dir.exists():
            return

        for f in accounts_dir.glob("*.json"):
            try:
                with f.open('r', encoding=DEFAULT_ENCODING) as fp:
                    account = json.load(fp)
                if 'username' in account:
                    username = account['username']
                    self.accounts[username] = account
                    agent = Agent()
                    agent.login(username)
                    self.agents[username] = agent
                    # 添加到列表
                    item = QListWidgetItem()
                    widget = self.create_account_item(username)
                    item.setSizeHint(widget.sizeHint())
                    self.account_list.addItem(item)
                    self.account_list.setItemWidget(item, widget)
            except Exception as e:
                print(f"加载账号失败: {e}")

    def create_account_item(self, username):
        """创建账号列表项"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                # background-color: #f0f0f0;  /* 浅色背景 */
                border: 1px solid #333333;   /* 深色边框 */
            }
        """)
        # 使用垂直布局来排列账号名和下载地址
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)  # 减小间距
        main_layout.setContentsMargins(5, 5, 5, 5)

        top_layout = QHBoxLayout()

        # 账号名标签
        account_name_label = QLabel(username)
        account_name_label.setStyleSheet("font-size: 14px; color: #333;")
        account_name_label.setAlignment(Qt.AlignVCenter)  # 水平和垂直居中对齐

        download_path_label = QLabel(f"下载地址：{home_path}")  # 默认下载路径
        download_path_label.setStyleSheet("font-size: 12px; color: #666;")
        download_path_label.setAlignment(Qt.AlignVCenter)

        # 修改下载地址按钮
        modify_path_btn = Button('icon/folder.png')  # 使用文件夹图标

        # 下载按钮
        agent = self.agents[username]
        download_btn = ButtonSwitch(normal_icon='icon/play_fill.png',
                                    pressed_icon='icon/pause.png',
                                    callback=agent.download)
        download_btn.setObjectName("downloadBtn")
        # download_btn.setFixedSize(30, 30)
        # download_btn.setStyleSheet(self.normal_style)

        # 删除按钮
        delete_btn = Button('icon/delete.png')
        delete_btn.setObjectName("deleteBtn")

        # delete_btn.clicked.connect(lambda _, u=username: self.delete_account(u))

        top_layout.addWidget(account_name_label)
        top_layout.addWidget(download_btn)
        top_layout.addWidget(delete_btn)
        top_layout.addStretch()
        top_layout.setAlignment(Qt.AlignVCenter)

        # 下层水平布局：下载地址和修改按钮
        bottom_layout = QHBoxLayout()

        bottom_layout.addWidget(download_path_label)
        bottom_layout.addWidget(modify_path_btn)
        bottom_layout.addStretch()  # 添加弹性空间
        bottom_layout.setAlignment(Qt.AlignVCenter)

        # 将上下两层布局添加到主布局
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)

        widget.setLayout(main_layout)
        return widget

    def delete_account(self, username):
        """删除账号"""
        reply = QMessageBox.question(self, '确认删除', f'确定要删除账号 {username} 吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 删除账号文件
            account_file = self.cache_dir / 'accounts' / f'{username}.json'
            if account_file.exists():
                account_file.unlink()

            # 如果是当前账号，也删除current_account.txt
            current_account_file = self.cache_dir / 'current_account.txt'
            if current_account_file.exists():
                with current_account_file.open('r', encoding=DEFAULT_ENCODING) as f:
                    current_username = f.read().strip()
                if current_username == username:
                    current_account_file.unlink()

            # 重新加载列表
            self.load_accounts()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # login_window = LoginWindow()
    # login_window.show()
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())