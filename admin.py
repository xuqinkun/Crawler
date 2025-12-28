import logging
import sys
from datetime import datetime, timedelta

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import cert_util
from constant import  DATETIME_PATTERN
from bean import Device
from db_util import AmazonDatabase


class DeviceKeyManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.all_devices = []  # 存储从数据库加载的所有数据
        self.display_devices = []  # 存储当前过滤后显示的数据

        self.db = AmazonDatabase()
        self.db.connect()
        self.db.create_device_table()

        self.load_data()
        self.init_ui()
        self.refresh_table()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timers)
        self.timer.start(1000)

    def load_data(self):
        """加载保存的数据"""
        try:
            self.all_devices = self.db.get_all_devices()
        except:
            logging.info("加载设备列表失败")
            self.all_devices = []

    def save_data(self):
        """保存数据到文件"""
        for device in self.all_devices:
            self.db.upsert_device(device)

    def update_devices(self, devices):
        """保存数据到文件"""
        for device in devices:
            self.db.upsert_device(device)

    def delete_devices(self, devices):
        """保存数据到文件"""
        for device_code in devices:
            self.db.delete_device_by_code(device_code)

    def insert_device(self, device):
        """保存数据到文件"""
        self.db.upsert_device(device)

    def init_ui(self):
        self.setWindowTitle("设备授权管理系统 (增强版)")
        self.resize(1000, 700)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # --- 顶部功能按钮区域 (保留原功能) ---
        top_layout = QHBoxLayout()
        self.add_btn = QPushButton('添加新设备')
        self.add_btn.clicked.connect(self.add_device)
        self.renew_btn = QPushButton('批量续期选中')
        self.renew_btn.clicked.connect(self.renew_selected)
        self.delete_btn = QPushButton('批量删除选中')
        self.delete_btn.clicked.connect(self.delete_selected)

        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.renew_btn)
        top_layout.addWidget(self.delete_btn)

        # --- 1. 搜索区域 ---

        self.search_name = QLineEdit()
        self.search_name.setPlaceholderText("按设备名称搜索...")
        self.search_name.textChanged.connect(self.perform_search)

        self.search_code = QLineEdit()
        self.search_code.setPlaceholderText("按设备码搜索...")
        self.search_code.textChanged.connect(self.perform_search)

        self.search_days = QSpinBox()
        self.search_days.setRange(0, 9999)
        self.search_days.setPrefix("到期天数 <= ")
        self.search_days.setSpecialValueText("到期天数 (全部)")
        self.search_days.valueChanged.connect(self.perform_search)

        btn_refresh = QPushButton("重置搜索")
        btn_refresh.clicked.connect(self.reset_search)

        top_layout.addWidget(QLabel("名称:"))
        top_layout.addWidget(self.search_name)
        top_layout.addWidget(QLabel("设备码:"))
        top_layout.addWidget(self.search_code)
        top_layout.addWidget(self.search_days)
        top_layout.addWidget(btn_refresh)

        layout.addLayout(top_layout)


        # --- 2. 表格区域 ---
        self.table = QTableWidget()
        # 增加一列：操作
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["设备名称", "设备码", "密钥", "创建日期", "剩余时间", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 220)
        self.table.cellClicked.connect(self.copy_key_to_clipboard)
        layout.addWidget(self.table)

    def perform_search(self):
        """执行模糊搜索和到期天数过滤"""
        name_query = self.search_name.text().lower()
        code_query = self.search_code.text().lower()
        days_limit = self.search_days.value()

        self.display_devices = []
        for d in self.all_devices:
            # 模糊匹配名称
            if name_query and name_query not in d.device_name.lower():
                continue
            # 模糊匹配设备码
            if code_query and code_query not in d.device_code.lower():
                continue
            # 搜索到期日期
            if days_limit > 0:
                remaining = d.created_at - datetime.now() + timedelta(days=d.valid_days)
                if remaining.days > days_limit:
                    continue

            self.display_devices.append(d)

        self.update_table_display()

    def reset_search(self):
        self.search_name.clear()
        self.search_code.clear()
        self.search_days.setValue(0)
        self.perform_search()

    def update_table_display(self):
        """渲染表格内容"""
        self.table.setRowCount(0)
        for i, device in enumerate(self.display_devices):
            self.table.insertRow(i)

            # 基本数据列
            self.table.setItem(i, 0, QTableWidgetItem(device.device_name))
            self.table.setItem(i, 1, QTableWidgetItem(device.device_code))
            self.table.setItem(i, 2, QTableWidgetItem(device.secrete_key))
            self.table.setItem(i, 3, QTableWidgetItem(device.created_at.strftime(DATETIME_PATTERN)))

            # 剩余时间列 (由定时器更新)
            remaining_item = QTableWidgetItem()
            self.table.setItem(i, 4, remaining_item)

            action_widget = self.build_action_widget(device)
            self.table.setCellWidget(i, 5, action_widget)

        self.update_timers()  # 立即填充倒计时

    def build_action_widget(self, device):
        # --- 操作功能键 ---
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        action_layout.setSpacing(5)
        btn_edit = QPushButton("修改")
        btn_edit.setStyleSheet("background-color: #e1f5fe;")
        btn_edit.clicked.connect(lambda _, d=device: self.handle_edit(d))
        btn_renew = QPushButton("续期")
        btn_renew.setStyleSheet("background-color: #e8f5e9;")
        btn_renew.clicked.connect(lambda _, d=device: self.handle_renew(d))
        btn_del = QPushButton("删除")
        btn_del.setStyleSheet("background-color: #ffebee; color: red;")
        btn_del.clicked.connect(lambda _, d=device: self.handle_delete(d))
        action_layout.addWidget(btn_edit)
        action_layout.addWidget(btn_renew)
        action_layout.addWidget(btn_del)
        return action_widget

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

        # 设备名称输入
        device_layout = QHBoxLayout()
        device_label = QLabel('设备代码:')
        device_input = QLineEdit()
        device_input.setPlaceholderText('请输入设备代码')
        device_layout.addWidget(device_label)
        device_layout.addWidget(device_input)

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
        layout.addLayout(device_layout)
        layout.addLayout(duration_layout)
        layout.addStretch()
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)

        def on_ok():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, '警告', '请输入设备名称！')
                return
            device_code = device_input.text().strip()
            if not device_code:
                QMessageBox.warning(self, '警告', '请输入设备代码！')
                return
            # 设置有效期
            duration_text = duration_combo.currentText()
            valid_days = int(duration_text.replace('天', ''))
            now = datetime.now()
            secret_key = cert_util.generate_key_from_device(name, device_code, now, valid_days)
            device = Device(device_name=name,
                            device_code=device_code,
                            secrete_key=secret_key,
                            created_at=now,
                            valid_days=valid_days)

            self.all_devices.append(device)
            self.insert_device(device)
            self.refresh_table()
            self.statusBar().showMessage(f'已添加设备: {name}')
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()

    # --- 功能操作逻辑 ---

    def handle_edit(self, device):
        new_name, ok = QInputDialog.getText(self, "修改信息", "请输入新的设备名称:", QLineEdit.Normal,
                                            device.device_name)
        if ok and new_name:
            device.device_name = new_name
            if self.db.upsert_device(device):
                QMessageBox.information(self, "成功", "设备名称已更新")
                self.load_data()

    def handle_renew(self, device):
        days, ok = QInputDialog.getInt(self, "设备续期", "请输入增加的天数:", 30, 1, 3650)
        if ok:
            if self.db.extend_device_life(device.device_code, days):
                # 同步更新本地内存数据，避免重新加载全量数据闪烁
                device.valid_days += days
                QMessageBox.information(self, "成功", f"设备已成功续期 {days} 天")
                self.update_table_display()

    def handle_delete(self, device):
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除设备 [{device.device_name}] 吗？\n该操作不可撤销。",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_device_by_code(device.device_code):
                self.delete_device(device)
                QMessageBox.information(self, "成功", "设备已删除")

    def delete_device(self, device):
        self.all_devices.remove(device)
        self.display_devices.remove(device)

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
            devices = []
            for row in selected_rows:
                index = row.row()
                device = self.all_devices[index]

                # 更新过期时间
                device.valid_days = device.valid_days + days
                devices.append(device)

            self.update_devices(devices)
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
            devices = []
            for row in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                index = row.row()
                d = self.all_devices.pop(index)
                devices.append(d.device_code)

            self.delete_devices(devices)
            self.refresh_table()
            self.statusBar().showMessage(f'已删除 {len(selected_rows)} 台设备')

    def refresh_table(self):
        """刷新表格数据"""
        self.table.setRowCount(len(self.all_devices))

        for i, device in enumerate(self.all_devices):
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
            issue_item = QTableWidgetItem(device.created_at.strftime(DATETIME_PATTERN))
            issue_item.setFlags(issue_item.flags() & ~Qt.ItemIsEditable)

            # 计算剩余时间
            remaining = device.created_at - datetime.now() + timedelta(days=device.valid_days)

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
            self.table.setCellWidget(i, 5, self.build_action_widget(device))

            # 设置行高
            self.table.setRowHeight(i, 30)

    def copy_key_to_clipboard(self, row, column):
        """点击密钥列时自动复制到剪贴板"""
        if column == 2:  # 密钥列在表格中的索引为 2
            item = self.table.item(row, column)
            if item:
                key_text = item.text()
                # 获取系统剪贴板并设置文本内容
                clipboard = QApplication.clipboard()
                clipboard.setText(key_text)

                # 在状态栏给予提示，增强用户体验
                self.statusBar().showMessage(f'密钥已复制到剪贴板: {key_text}', 3000)

    def update_timers(self):
        """更新倒计时显示"""
        for i in range(self.table.rowCount()):
            device = self.all_devices[i]
            remaining = device.created_at - datetime.now() + timedelta(days=device.valid_days)

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