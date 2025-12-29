import sys
import PyInstaller.__main__
import os
import argparse
import platform
import subprocess

# 1. 获取certifi包的安装位置，并找到cacert.pem文件
import certifi

cert_path = certifi.where()  # 例如: C:\...\crawler\Lib\site-packages\certifi\cacert.pem
certifi_dir = os.path.dirname(cert_path)


def open_folder(path):
    """打开文件夹"""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
        print(f"已打开文件夹: {path}")
    except Exception as e:
        print(f"打开文件夹失败: {e}")


def build_app(app_type):
    """编译指定的应用程序"""

    if app_type == "app":
        entry_file = "app.py"
        app_name = "AmazonCrawler"
        dist_dir_name = "AmazonCrawler"
    elif app_type == "admin":
        entry_file = "admin.py"
        app_name = "Admin"
        dist_dir_name = "Admin"
    else:
        print(f"错误: 不支持的应用类型: {app_type}")
        return False

    print(f"开始编译 {app_name}...")
    print(f"入口文件: {entry_file}")

    # 构建参数列表
    args = [
        entry_file,
        f'--name={app_name}',
        '--onefile',
        '--windowed',

        # 指定输出目录
        '--distpath', f'./dist/{dist_dir_name}',
        '--workpath', f'./build/{dist_dir_name}',
        '--specpath', f'./build/{dist_dir_name}',

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
        '--hidden-import=ssl',
        '--hidden-import=cryptography',
        '--hidden-import=pycryptodome',
        '--hidden-import=OpenSSL',
        '--hidden-import=bs4',
        '--hidden-import=hashlib',
        '--hidden-import=hmac',
        '--hidden-import=urllib',
        '--hidden-import=urllib3',
        '--hidden-import=email',
        '--hidden-import=http',
        '--hidden-import=html',
        '--hidden-import=selenium',

        # 添加证书文件
        '--add-data', f'{certifi_dir}{os.pathsep}certifi',

        # 优化选项
        '--noupx',  # 禁用UPX（有时会更小）
    ]

    try:
        # 运行PyInstaller
        PyInstaller.__main__.run(args)

        # 编译成功后打开输出文件夹
        output_dir = f"./dist/{dist_dir_name}"
        if os.path.exists(output_dir):
            print(f"\n编译完成! 输出目录: {output_dir}")
            open_folder(output_dir)
        else:
            print(f"\n警告: 输出目录不存在: {output_dir}")

        return True
    except Exception as e:
        print(f"编译失败: {e}")
        return False


def build_all():
    """编译所有应用"""
    print("开始编译所有应用...")
    success_count = 0

    if build_app("app"):
        success_count += 1
    print("-" * 50)

    if build_app("admin"):
        success_count += 1

    print(f"\n编译完成! 成功编译 {success_count}/2 个应用")
    return success_count == 2


def main():
    parser = argparse.ArgumentParser(description='编译应用程序')
    parser.add_argument('target', nargs='?', default='all',
                        choices=['app', 'admin', 'all'],
                        help='要编译的目标: app, admin 或 all (默认: all)')

    args = parser.parse_args()

    print(f"编译目标: {args.target}")
    print(f"当前工作目录: {os.getcwd()}")
    print("-" * 50)

    if args.target == 'all':
        build_all()
    else:
        build_app(args.target)


if __name__ == "__main__":
    main()