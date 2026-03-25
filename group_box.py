import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QGroupBox, QCheckBox, QPushButton, QLabel)


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("复选框分组示例")
        self.resize(400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 创建分组框：兴趣爱好 ---
        group_hobbies = QGroupBox("")
        layout_hobbies = QVBoxLayout()

        # 创建多个复选框
        self.cb_music = QCheckBox("🎵 听音乐")
        self.cb_reading = QCheckBox("📚 阅读")
        self.cb_sports = QCheckBox("⚽ 运动")
        self.cb_coding = QCheckBox("💻 编程")
        self.cb_travel = QCheckBox("✈️ 旅行")

        # 默认选中两个
        self.cb_music.setChecked(True)
        self.cb_coding.setChecked(True)

        # 将复选框添加到分组框的布局中
        layout_hobbies.addWidget(self.cb_music)
        layout_hobbies.addWidget(self.cb_reading)
        layout_hobbies.addWidget(self.cb_sports)
        layout_hobbies.addWidget(self.cb_coding)
        layout_hobbies.addWidget(self.cb_travel)

        group_hobbies.setLayout(layout_hobbies)

        # --- 操作按钮区域 ---
        btn_layout = QVBoxLayout()

        btn_get = QPushButton("获取已选项目")
        btn_get.clicked.connect(self.get_selected_items)

        btn_select_all = QPushButton("全选")
        btn_select_all.clicked.connect(self.select_all)

        btn_clear = QPushButton("取消全选")
        btn_clear.clicked.connect(self.clear_all)

        btn_layout.addWidget(btn_get)
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_clear)

        # 结果显示标签
        self.result_label = QLabel("当前未选择任何项目")
        self.result_label.setStyleSheet("color: rgb(91, 101, 124); padding: 5px;")

        # 将所有部件加入主布局
        main_layout.addWidget(group_hobbies)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.result_label)

    def get_selected_items(self):
        """获取所有被选中的复选框文本"""
        selected = []
        # 遍历该组下的所有复选框
        checkboxes = [self.cb_music, self.cb_reading, self.cb_sports, self.cb_coding, self.cb_travel]

        for cb in checkboxes:
            if cb.isChecked():
                selected.append(cb.text())

        if selected:
            self.result_label.setText(f"✅ 您选择了: {', '.join(selected)}")
        else:
            self.result_label.setText("❌ 您没有选择任何项目")

    def select_all(self):
        """全选功能"""
        checkboxes = [self.cb_music, self.cb_reading, self.cb_sports, self.cb_coding, self.cb_travel]
        for cb in checkboxes:
            cb.setChecked(True)

    def clear_all(self):
        """取消全选功能"""
        checkboxes = [self.cb_music, self.cb_reading, self.cb_sports, self.cb_coding, self.cb_travel]
        for cb in checkboxes:
            cb.setChecked(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())