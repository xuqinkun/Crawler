import sys
import json
import uuid
from db_util import AmazonDatabase
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class DeviceKeyManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.devices = []  # 存储设备数据
        self.timer = QTimer()
        self.db = AmazonDatabase()
        self.db.connect()
        self.db.create_device_table()
        self.timer.timeout.connect(self.update_timers)
        self.timer.start(600)  # 每分钟更新一次
        self.load_data()
        self.init_ui()

    def load_data(self):
        """加载保存的数据"""
        try:
            self.devices = self.db.get_all_devices()
        except:
            self.devices = []

    def save_data(self):
        """保存数据到文件"""
        for device in self.devices:
            self.db.upsert_device(device)

    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('设备密钥管理系统')
        self.setGeometry(100, 100, 1000, 600)

        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 顶部按钮区域
        top_layout = QHBoxLayout()

        self.add_btn = QPushButton('添加新设备')
        self.add_btn.clicked.connect(self.add_device)
        self.add_btn.setFixedHeight(40)

        self.renew_btn = QPushButton('续期选中设备')
        self.renew_btn.clicked.connect(self.renew_selected)
        self.renew_btn.setFixedHeight(40)

        self.delete_btn = QPushButton('删除选中设备')
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setFixedHeight(40)

        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.renew_btn)
        top_layout.addWidget(self.delete_btn)
        top_layout.addStretch()

        # 设备表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['设备名称', '设备码', '密钥', '签发时间', '剩余时间'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)

        # 设置列宽
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 150)

        # 状态栏
        self.statusBar().showMessage('就绪')

        layout.addLayout(top_layout)
        layout.addWidget(self.table)

        # 刷新表格数据
        self.refresh_table()

    def add_device(self):
        """添加新设备"""
        dialog = QDialog(self)
        dialog.setWindowTitle('添加新设备')
        dialog.setFixedSize(400, 200)

        layout = QVBoxLayout()

        # 设备名称输入
        name_layout = QHBoxLayout()
        name_label = QLabel('设备名称:')
        name_input = QLineEdit()
        name_input.setPlaceholderText('请输入设备名称')
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input)

        # 有效期选择
        duration_layout = QHBoxLayout()
        duration_label = QLabel('有效期:')
        duration_combo = QComboBox()
        duration_combo.addItems(['7天', '30天', '90天', '180天', '365天'])
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(duration_combo)

        # 按钮区域
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('确定')
        cancel_btn = QPushButton('取消')
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(name_layout)
        layout.addLayout(duration_layout)
        layout.addStretch()
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)

        def on_ok():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, '警告', '请输入设备名称！')
                return

            # 生成唯一设备码和密钥
            device_code = str(uuid.uuid4())
            key = str(uuid.uuid4()).replace('-', '')[:16]

            # 设置有效期
            duration_text = duration_combo.currentText()
            days = int(duration_text.replace('天', ''))
            expire_date = datetime.now() + timedelta(days=days)

            device = {
                'name': name,
                'device_code': device_code,
                'key': key,
                'issue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'expire_time': expire_date.strftime('%Y-%m-%d %H:%M:%S')
            }

            self.devices.append(device)
            self.save_data()
            self.refresh_table()
            self.statusBar().showMessage(f'已添加设备: {name}')
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()

    def renew_selected(self):
        """为选中设备续期"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, '警告', '请先选择要续期的设备！')
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('续期设备')
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout()

        duration_layout = QHBoxLayout()
        duration_label = QLabel('续期时长:')
        duration_combo = QComboBox()
        duration_combo.addItems(['7天', '30天', '90天', '180天', '365天'])
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(duration_combo)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('确定')
        cancel_btn = QPushButton('取消')
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(duration_layout)
        layout.addStretch()
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        def on_ok():
            duration_text = duration_combo.currentText()
            days = int(duration_text.replace('天', ''))

            for row in selected_rows:
                index = row.row()
                device = self.devices[index]

                # 更新过期时间
                old_expire = datetime.strptime(device['expire_time'], '%Y-%m-%d %H:%M:%S')
                new_expire = old_expire + timedelta(days=days)
                device['expire_time'] = new_expire.strftime('%Y-%m-%d %H:%M:%S')

                # 生成新密钥
                device['key'] = str(uuid.uuid4()).replace('-', '')[:16]
                device['issue_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            self.save_data()
            self.refresh_table()
            self.statusBar().showMessage(f'已续期 {len(selected_rows)} 台设备')
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()

    def delete_selected(self):
        """删除选中设备"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, '警告', '请先选择要删除的设备！')
            return

        reply = QMessageBox.question(self, '确认删除',
                                     f'确定要删除这 {len(selected_rows)} 台设备吗？',
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 从后往前删除，避免索引变化
            for row in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                index = row.row()
                self.devices.pop(index)

            self.save_data()
            self.refresh_table()
            self.statusBar().showMessage(f'已删除 {len(selected_rows)} 台设备')

    def refresh_table(self):
        """刷新表格数据"""
        self.table.setRowCount(len(self.devices))

        for i, device in enumerate(self.devices):
            # 设备名称
            name_item = QTableWidgetItem(device.device_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)

            # 设备码
            code_item = QTableWidgetItem(device.device_code)
            code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)

            # 密钥
            key_item = QTableWidgetItem(device.secrete_key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)

            # 签发时间
            issue_item = QTableWidgetItem(device.created_at)
            issue_item.setFlags(issue_item.flags() & ~Qt.ItemIsEditable)

            # 计算剩余时间
            expire_time = (datetime.strptime(device.created_at, '%Y-%m-%d %H:%M:%S')
                           + timedelta(days=device.valid_days))
            remaining = expire_time - datetime.now()

            if remaining.total_seconds() <= 0:
                # 已过期
                remaining_text = "已过期"
                color = QColor(255, 200, 200)  # 浅红色背景
            elif remaining.days < 7:
                # 即将过期（7天内）
                hours = remaining.seconds // 3600
                remaining_text = f"{remaining.days}天{hours}小时"
                color = QColor(255, 255, 200)  # 浅黄色背景
            else:
                # 正常
                hours = remaining.seconds // 3600
                remaining_text = f"{remaining.days}天{hours}小时"
                color = QColor(200, 255, 200)  # 浅绿色背景

            remaining_item = QTableWidgetItem(remaining_text)
            remaining_item.setFlags(remaining_item.flags() & ~Qt.ItemIsEditable)
            remaining_item.setBackground(color)

            # 设置行数据
            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, code_item)
            self.table.setItem(i, 2, key_item)
            self.table.setItem(i, 3, issue_item)
            self.table.setItem(i, 4, remaining_item)

            # 设置行高
            self.table.setRowHeight(i, 30)

    def update_timers(self):
        """更新倒计时显示"""
        print(f'update_timers: {self.devices}')
        for i in range(self.table.rowCount()):
            device = self.devices[i]
            expire_time = datetime.strptime(device.created_at, '%Y-%m-%d %H:%M:%S') + timedelta(days=device.valid_days)
            remaining = expire_time - datetime.now()

            if remaining.total_seconds() <= 0:
                remaining_text = "已过期"
                color = QColor(255, 200, 200)
            elif remaining.days < 7:
                hours = remaining.seconds // 3600
                remaining_text = f"{remaining.days}天{hours}小时"
                color = QColor(255, 255, 200)
            else:
                hours = remaining.seconds // 3600
                remaining_text = f"{remaining.days}天{hours}小时"
                color = QColor(200, 255, 200)

            item = self.table.item(i, 4)
            if item:
                item.setText(remaining_text)
                item.setBackground(color)


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建并显示窗口
    window = DeviceKeyManager()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()