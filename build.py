import sys

import PyInstaller.__main__
import os


def build_optimized():
    args = [
        'app.py',
        '--name=AmazonCrawler',
        '--onefile',
        '--windowed',

        # 关键优化选项
        '--clean',  # 清理临时文件
        '--noconfirm',  # 覆盖现有文件不提示

        # 排除不必要的包
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=pytest',
        '--exclude-module=tkinter',
        '--exclude-module=unittest',
        '--exclude-module=lib2to3',

        # 只包含必要的隐藏导入
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=requests',
        '--hidden-import=sqlite3',
        '--hidden-import=cryptography',
        '--hidden-import=OpenSSL',
        '--hidden-import=bs4',
        '--hidden-import=urllib',  # 明确添加urllib3
        '--hidden-import=urllib3',  # 明确添加urllib3
        '--hidden-import=email',  # 明确添加email模块
        '--hidden-import=http',  # 明确添加email模块
        '--hidden-import=html',  # 明确添加email模块
        # 添加证书文件
        '--add-data={};certifi'.format(
            os.path.join(os.path.dirname(sys.executable), '../Lib/site-packages/certifi/cacert.pem')
        ),
        # 优化选项
        '--strip',  # 剥离符号（减小大小）
        '--noupx',  # 禁用UPX（有时会更小）
    ]

    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    build_optimized()