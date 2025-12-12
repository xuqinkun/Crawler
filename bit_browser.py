import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# 配置区域
BITBROWSER_API_URL = "http://127.0.0.1:54345"  # 比特浏览器默认 API 地址
CHROMEDRIVER_PATH = r"chromedriver.exe"  # 你的对应版本的驱动路径


def get_bitbrowser_driver(browser_id):
    """
    启动比特浏览器窗口并返回 Selenium Driver 对象
    """
    # 1. 请求比特浏览器接口打开窗口
    open_url = f"{BITBROWSER_API_URL}/browser/open"
    data = {
        "id": browser_id,
        # "args": [],  # 如果需要额外的启动参数
        # "loadExtensions": False # 是否加载插件
    }

    try:
        resp = requests.post(open_url, json=data, timeout=10).json()
    except Exception as e:
        print(f"无法连接比特浏览器 API: {e}")
        return None

    if not resp.get("success"):
        print(f"启动窗口失败: {resp.get('msg')}")
        return None

    # 2. 获取调试地址和驱动路径
    # API 返回示例: {'data': {'http': '127.0.0.1:53868', 'driver': '...'}, ...}
    debug_address = resp["data"]["http"]
    print(f"窗口已启动，调试地址: {debug_address}")

    # 3. 配置 Selenium 接管
    chrome_options = Options()
    # 关键步骤：设置 debuggerAddress
    chrome_options.add_experimental_option("debuggerAddress", debug_address)

    # 可选：手动指定驱动路径（推荐），防止系统 PATH 中的高版本驱动报错
    service = Service(executable_path=CHROMEDRIVER_PATH)

    # 初始化 Driver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


def get_all_browser_ids():
    """
    获取所有窗口的 ID 和 名称
    """
    url = f"{BITBROWSER_API_URL}/browser/list"

    # 分页参数，pageSize 设置大一点以获取所有窗口
    payload = {
        "page": 0,
        "pageSize": 100
    }

    try:
        resp = requests.post(url, json=payload).json()
        if resp.get("success"):
            data_list = resp.get("data", {}).get("list", [])
            print(f"共找到 {len(data_list)} 个窗口：")

            result = []
            for item in data_list:
                bid = item.get("id")  # 窗口ID (这是我们要的)
                # group_name = item.get("groupName")
                result.append(bid)

            return result
        else:
            print(f"获取列表失败: {resp.get('msg')}")
            return []

    except Exception as e:
        print(f"请求接口出错: {e}")
        return []

# --- 使用示例 ---
if __name__ == "__main__":
    # 替换为你比特浏览器里的 窗口ID
    ids = get_all_browser_ids()

    target_browser_id = list(ids.values())[0]

    driver = get_bitbrowser_driver(target_browser_id)

    if driver:
        print("Selenium 连接成功！")
        driver.get("https://www.amazon.com")
        print(driver.title)

        # 注意：使用接管模式时，不要使用 driver.quit()，否则会关闭整个浏览器窗口
        # 如果只想断开连接但保留窗口，可以直接结束脚本或不做任何操作