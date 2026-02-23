import json
import re
import time
from pathlib import Path
from time import sleep
from typing import Set
from urllib.parse import quote

import requests
from PyQt5.QtCore import QObject
from bs4 import BeautifulSoup
from selenium.common import TimeoutException

from constant import *
from cookies import CookieManager
from crypto import get_encrypt_by_str, base64_encode
from extractor import AmazonASINExtractor
from logger import setup_concurrent_logging
from bean import Product
import concurrent.futures
from util import curr_milliseconds, ensure_dir_exists
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver

ZIP_CODE = '61110'

DRIVER_EXE = r'C:\Users\xqk\AppData\Local\Programs\bitbrowser\比特浏览器.exe'
# 使用示例
extractor = AmazonASINExtractor()
logger = setup_concurrent_logging()
chrome_options = Options()
chrome_options.binary_location = DRIVER_EXE
service = Service(executable_path=DRIVER_EXE)

def shipping_from_amazon(ships_from, sold_by):
    return 'amazon' in ships_from.lower() or 'amazon' in sold_by.lower()

class any_of_elements_located:
    def __init__(self, locators):
        self.locators = locators
    def __call__(self, driver: WebDriver):
        for locator in self.locators:
            try:
                element = driver.find_element(*locator)
                if element.is_displayed():
                    return element
            except:
                continue
        return False


# 关键元素定位器列表，用于判断页面是否成功加载
KEY_SUCCESS_SELECTORS_LIST = [
    (By.CSS_SELECTOR, "span.a-price > span.a-offscreen"), # 价格
    (By.ID, "productTitle"), # 标题
    (By.ID, "dp"), # 主体容器
]

class Agent(QObject):

    def __init__(self, cache_dir: str = CACHE_DIR):
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.cookie_dir = self.cache_dir / 'cookies'
        self.url_dir = self.cache_dir / 'urls'
        ensure_dir_exists(self.cache_dir)
        ensure_dir_exists(self.url_dir)
        self.cookie_manager = CookieManager()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Origin': 'https://www.dianxiaomi.com',
            'Referer': 'https://www.dianxiaomi.com/index.htm',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-HK;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Ch-Ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=1, i'
        }
        self.shopping_sys_session = requests.Session()
        self.online = False
        self.username = None

    def load_cookies(self, account: str):
        if account is None:
            return None
        cookie_file = self.cookie_dir / f'{account}.json'
        try:
            with cookie_file.open('r', encoding=DEFAULT_ENCODING) as f:
                cookies = json.load(f)
            return cookies
        except Exception as e:
            print(f'读取cookie错误[account={account}]: {e}')
            logger.error(f'读取cookie错误[account={account}]: {e}')
            return {}

    def get_captcha(self):
        ts = curr_milliseconds()
        verify_code_url = f'{ROOT}/{VERIFY_PAGE}?t={ts}'
        response = self.shopping_sys_session.get(verify_code_url)
        image = response.content
        return image

    def login(self, username: str, password: str = '', captcha: str = ''):
        self.username = username
        valid = self.cookie_manager.load_cookies_json(self.shopping_sys_session, username)
        if valid:
            product_page = f'{ROOT}/{PRODUCT_PAGE}'
            resp = self.shopping_sys_session.post(product_page, headers=self.headers)
            data = json.loads(resp.text)
            self.online = data['msg'] == 'Successful'
            if self.online:
                return self.online
            else:
                print(data['msg'])
        print(f'{ username}加载cookie失败，重新登录')
        self.shopping_sys_session.cookies.set('_dxm_ad_client_id', 'EF5ED1455E6745E01606AB28D81ACD6D7')
        self.shopping_sys_session.cookies.set('MYJ_MKTG_fapsc5t4tc', 'JTdCJTdE')
        self.shopping_sys_session.cookies.set('Hm_lvt_f8001a3f3d9bf5923f780580eb550c0b', '1763520089')
        self.shopping_sys_session.cookies.set('Hm_lpvt_f8001a3f3d9bf5923f780580eb550c0b', '1763520789')
        self.shopping_sys_session.cookies.set('tfstk',
        'g69ibNvtcC5syNy_smXssb8KNHcK6O6f7EeAktQqTw7QWPe90iDDkeUvXf69nxbHlNCOQReciw8CDKn1MeXDRe8cGc_AuZYv0CnKeYK6ft6qn4H-ew9J1yd0QZPZ0vScnGRo2uJBft6qJkeqwYx6W1iWANWqx9ScjZWV_skFTwsY_Z8V76zFqg6VuE8VTwSRVrzaQZrUYwsV3Z8V3DxFRiXVuEWqxHllHR7y3p9Elv2jyqWZdQjGsa-N7hKpLJ141nb33-JHt_Qrow243pjw0MGGM8cAzQ_Owa8EpRXDYiYOJUkzK95kNnIDSA2NBBRBCOpKru1Mowfyp64a_gXGS_JNOly2AsRHKOpZl7tpxN5lpBhIWsBMSQ_5_XgBoHb9udfUS2QvwHpNtUuLKE1DNnIDSA2wzgWuT7uoC-sEDpPbG1SCxapyAdO5PQkrhDm3Nt1NAG3-xDVbG1SCxannx7Of_Msty')

        myj = {"deviceId": "708e8b72-0a46-49c0-beb9-fe5a77efb999",
               "userId": "",
               "parentId": "",
               "sessionId": curr_milliseconds(),
               "optOut": False,
               "lastEventId": 0}
        myj_text = json.dumps(myj)
        self.shopping_sys_session.cookies.set('MYJ_fapsc5t4tc', base64_encode(quote(myj_text)))
        ts = curr_milliseconds()
        payload = {
            'account': get_encrypt_by_str(username, ts),
            'password': get_encrypt_by_str(password, ts),
            'dxmVerify': captcha,
            'loginVerifyCode': None,
            "loginRedUrl": "",
            "remeber": "remeber",
            "url": ""
        }
        login_url = f'{ROOT}/{LOGIN_PAGE}'
        resp = self.shopping_sys_session.post(login_url, data=payload, headers=self.headers)
        data = json.loads(resp.text)
        self.cookie_manager.save_cookies_json(self.shopping_sys_session, account=username)
        self.online = 'error' not in data
        if not self.online:
            print(f'登录失败[username={username}]: {data}')
            logger.error(f'登录失败[username={username}]: {data}')
        return self.online

    def post(self, url, payload):
        resp = self.shopping_sys_session.post(url, data=payload, headers=self.headers)
        return resp.text


    def parse_product_list(self, ids: Set[int]):
        if not self.online:
            print(f'当前用户{self.username}未登录')
            return [], [], 0

        page_url = f'{ROOT}/{PRODUCT_PAGE}'
        payload = {
            'pageNo': 1,
            'pageSize': 100,
            'total': 0,
            'searchType': 0,
            'searchValue': None,
            'shopId': -1,
            'dxmState': 'online',
            'dxmOfflineState': None,
            'productStatusType': 'onSelling',
            'sortValue': 2,
            'sortName': 13,
        }

        # 先获取第一页，得到总页数信息
        response = self.post(page_url, payload)
        pages = json.loads(response)
        page = pages['data']['page']
        total_pages = page['totalPage']
        total_items = page['totalSize']

        # 准备多线程获取所有页面的数据
        def fetch_page(page_no: int):
            """获取单页数据的函数"""
            try:
                page_payload = payload.copy()
                page_payload['pageNo'] = page_no
                response = self.post(page_url, page_payload)
                pages_data = json.loads(response)
                if pages_data['code'] != 0:
                    print(f'爬取第{page_no}页数据时出错: {pages_data["msg"]}')
                    return
                page_data = pages_data['data']['page']
                return page_no, page_data['list']
            except Exception as e:
                print(f"获取第 {page_no} 页数据失败: {e}")
                return page_no, []

        # 使用线程池并行获取所有页面
        products_in_web = []

        # 设置合适的线程数，可根据实际情况调整
        max_workers = min(1, total_pages)  # 最多10个线程
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有页面获取任务
            future_to_page = {
                executor.submit(fetch_page, page_no): page_no
                for page_no in range(1, total_pages + 1)
            }

            # 按完成顺序处理结果
            for future in concurrent.futures.as_completed(future_to_page):
                page_no = future_to_page[future]
                try:
                    page_no, items = future.result()
                    for item in items:
                        product_id = item['productId']
                        product = Product(product_id=product_id, url=item['sourceUrl'])
                        product.title = item['subject']
                        product.owner = self.username
                        products_in_web.append(product)
                except Exception as e:
                    print(f"处理第 {page_no} 页数据时出错: {e}")

        # 处理结果
        new_products = [p for p in products_in_web if p.product_id not in ids]
        realtime_product_ids = [p.product_id for p in products_in_web]
        expired_product_ids = [pid for pid in ids if pid not in realtime_product_ids]

        return expired_product_ids, new_products, total_items


class AmazonAgent(QObject):
    def __init__(self, driver: WebDriver):
        super().__init__()
        # driver 对象启动 Chrome 浏览器
        self.amazon_session = requests.Session()
        self.amazon_driver = driver
        time.sleep(1.5)
        self.amazon_driver.maximize_window()
        self.wait = WebDriverWait(self.amazon_driver, 10)  # 最大等待 15 秒
        self.shopping_sys_session = requests.Session()
        self.amazon_driver.get("https://www.amazon.com/dp/B0F2DTDDFV?language=en_US")

        try:
            time.sleep(1)
            self.amazon_driver.find_element(By.CSS_SELECTOR, 'body > div > div.a-row.a-spacing-double-large > div.a-section > div > div > form > div > div > span > span > button').click()
            print(f'Click continue')
        except Exception:
            pass

        address_span = self.wait.until(EC.presence_of_element_located((By.ID, "glow-ingress-line2")))
        if ZIP_CODE not in address_span.text.strip():
            address_span.click()
            address_input = self.wait.until(EC.presence_of_element_located((By.ID, "GLUXZipUpdateInput")))
            address_input.send_keys(ZIP_CODE)
            self.amazon_driver.find_element(By.CSS_SELECTOR, '#GLUXZipUpdate > span > input').click()

        for cookie in self.amazon_driver.get_cookies():
            self.amazon_session.cookies.update(cookie)

    def start_craw(self, product: Product) -> Product:
        """
        使用 Selenium 获取页面内容并进行解析。

        :param url: 目标商品 URL
        :param product: 包含商品数据的对象
        :param logger: 日志对象
        :return: 更新后的 product 对象
        """
        # 1. 导航到目标 URL
        url = product.url
        if url is None:
            product.invalid = True
            product.completed = True
            print(f'产品{product.product_id} 没有找到链接')
            return product
        try:
            self.amazon_driver.get(url)  # 假设 self.amazon_driver 已初始化
        except Exception as e:
            # 如果导航本身失败（例如，网络中断）
            print(f'{url} 导航失败: {e}')
            logger.error(f'{url} 导航失败: {e}')
            product.completed = False
            return product

        # 2. 显式等待关键元素出现，判断页面是否加载成功
        # 替代了 if status_code != 200: 的检查

        main_page_source = None
        try:
            # 等待任何一个关键元素出现 (使用自定义的 OR 条件)
            self.wait.until(
                any_of_elements_located(KEY_SUCCESS_SELECTORS_LIST),
                message=f"等待页面关键元素超时 ({url})。"
            )
            # 如果成功找到元素，说明页面加载成功
            main_page_source = self.amazon_driver.page_source

        except TimeoutException:
            # 3. 超时或加载失败，检查是否为 404/反爬页面
            main_page_source = self.amazon_driver.page_source

            # 检查是否为 Amazon 的 404/商品不存在页面
            if "Sorry! We couldn't find that page" in main_page_source or "The requested URL was not found" in main_page_source:
                # 替代了 if status_code == 404: 的检查
                print(f'{url} 链接失效, 疑似404页面。')
                logger.warning(f'{url} 链接失效, 疑似404页面。')
                product.completed = True
                product.invalid = True
                return product

            elif "Type the characters" in main_page_source or "Sorry, we just need to make sure you're not a robot" in main_page_source:
                # 遇到验证码/反爬，标记为未完成，下次重试
                print(f'{url} 遇到亚马逊验证码/机器人检查页面，爬取失败。')
                logger.warning(f'{url} 遇到亚马逊验证码/机器人检查页面。')
                product.completed = False
                return product

            else:
                # 可能是页面加载慢，但不是明确的404或验证码，继续尝试用 BS 解析已有的源码
                resp = self.amazon_session.get(url)
                code = resp.status_code
                if code == 404:
                    print(f'{url} 链接失效, 404页面。')
                    product.completed = True
                    product.invalid = True
                    return product
                elif code != 200:
                    print(f'{url} 链接失效, 状态码: {code}')
                    logger.warning(f'{url} 链接失效, 状态码: {code}')
                    product.completed = True
                    product.invalid = True
                    return product
                main_page_source = resp.text

                # 4. 使用 BeautifulSoup 解析页面的最终 HTML 源代码
        # 替代了 main_soup = BeautifulSoup(main_page.text, 'html.parser')
        if not isinstance(main_page_source, (str, bytes)):
            logger.error(f"resp.text 返回了意外的类型: {main_page_source}")
            return product
        main_soup = BeautifulSoup(main_page_source, 'html.parser')

        # --- 以下是您原有的 Beautiful Soup 解析逻辑 (无需修改) ---

        # 无商品信息检查
        learn_more_span = main_soup.select_one('#fod-cx-message-with-learn-more > span:nth-child(1)')
        out_of_stock_div = main_soup.select_one('#outOfStock')
        if learn_more_span or out_of_stock_div:
            print(f'{url} 无商品信息')
            logger.warning(f'{url} 无商品信息')
            product.completed = True
            product.invalid = True
            return product

        used_only_buy_box = main_soup.select_one('#usedOnlyBuybox')
        if used_only_buy_box:
            print(f'{url} 是二手商品')
            product.used = True
            product.completed = True
            return product
        used_div = main_soup.select_one('div#usedAccordionRow')
        if used_div:
            if main_soup.select_one('div[id^="newAccordionRow_"]') is None:
                product.used = True
                product.completed = True
                return product
        partial_state_box = main_soup.select_one('div#partialStateBuybox')
        if partial_state_box:
            product.completed = True
            product.invalid = True
            return product
        new_product_div = main_soup.select_one('div[id^="newAccordionRow_"]')
        shipping_from = ''
        sold_by = ''
        availability = False
        if new_product_div is None:
            buy_box_div = main_soup.select_one('#buybox')
            if buy_box_div:
                availability_span = buy_box_div.select_one('#availability > span')
            else:
                availability_span = None
            if availability_span is None:
                product.availability = False
                product.completed = True
                # 有价格显示考虑是有货的
                core_price_feature_div = buy_box_div.select_one('#corePrice_feature_div')
                if core_price_feature_div:
                    availability = True
            else:
                availability_text = availability_span.text.lower()
                availability = 'in stock' in availability_text or 'available to ship' in availability_text
            if availability:
                core_price_feature_div = buy_box_div.select_one('#corePrice_feature_div')
                if core_price_feature_div:
                    price_span = core_price_feature_div.select_one('span.a-offscreen')
                else:
                    price_span = None
                if price_span:
                    product.price = self.extract_price(price_span.text)
                delivery_tag = buy_box_div.select_one(
                    '#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE > span')
                if delivery_tag is None:
                    delivery_tag = buy_box_div.select_one(
                        '#mir-layout-DELIVERY_BLOCK-slot-NO_PROMISE_UPSELL_MESSAGE > a')
                if delivery_tag:
                    product.shipping_cost = delivery_tag.text.strip().split(' ')[0]
                else:
                    delivery_tag = buy_box_div.select_one(
                        '#mir-layout-DELIVERY_BLOCK-slot-NO_PROMISE_UPSELL_MESSAGE')
                    if delivery_tag:
                        product.shipping_cost = delivery_tag.text.strip().split(' ')[0]
                    else:
                        print(f'{url} 无法获取运费信息')
                ships_from_span = buy_box_div.select_one(
                    '#fulfillerInfoFeature_feature_div > div.offer-display-feature-text.a-size-small > div.offer-display-feature-text.a-spacing-none.odf-truncation-popover > span')
                if ships_from_span:
                    shipping_from = ships_from_span.text.strip()
                else:
                    ships_from_new_span = main_soup.select_one('#sellerProfileTriggerId')
                    if ships_from_new_span:
                        shipping_from = ships_from_new_span.text.strip()
                    else:
                        ships_from_span = main_soup.select_one(
                            '#merchantInfoFeature_feature_div > div.offer-display-feature-text.a-size-small > div.offer-display-feature-text.a-spacing-none.odf-truncation-popover > span')
                        if ships_from_span:
                            shipping_from = ships_from_span.text.strip()
                        else:
                            shipping_from = ''
                            print(f'{url} 获取货源地信息失败')
                sold_by_span = buy_box_div.select_one(
                    '#merchantInfoFeature_feature_div > div.offer-display-feature-text.a-size-small > div.offer-display-feature-text.a-spacing-none.odf-truncation-popover.aok-inline-block')
                if sold_by_span:
                    sold_by = sold_by_span.text.strip()
                else:
                    sold_by_span = buy_box_div.select_one(
                        '#merchantInfoFeature_feature_div > div.offer-display-feature-text.a-size-small > div.offer-display-feature-text.a-spacing-none.odf-truncation-popover > span')
                    if sold_by_span:
                        sold_by = sold_by_span.text.strip()
                    else:
                        sold_by = ''
                        print(f'{url} 无法获取卖方信息')
                product.shipping_from_amazon = shipping_from_amazon(shipping_from, sold_by)
            else:
                price_feature_div = main_soup.select_one('#corePrice_feature_div')
                if price_feature_div:
                    availability = True
                    price_span = price_feature_div.select_one('span.a-offscreen')
                    if price_span:
                        product.price = self.extract_price(price_span.text)
                    delivery_tag = main_soup.select_one(
                        '#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE > span')
                    if delivery_tag:
                        product.shipping_cost = delivery_tag.text.strip().split(' ')[0]
                    shipping_from_span = main_soup.select_one('#fulfillerInfoFeature_feature_div > '
                                                              'div.offer-display-feature-text.a-size-small > div.offer-display-feature-text.a-spacing-none.odf-truncation-popover > span')
                    if shipping_from_span:
                        shipping_from = shipping_from_span.text.strip()
                    else:
                        shipping_from = ''
                    sold_by_span = main_soup.select_one('#sellerProfileTriggerId')
                    if sold_by_span:
                        sold_by = sold_by_span.text.strip()
                    else:
                        sold_by = ''
                    product.shipping_from_amazon = shipping_from_amazon(shipping_from, sold_by)
                availability = availability
                product.completed = True
        else:
            availability_span = new_product_div.select_one('#availability > span')
            if availability_span is None:
                select_quantity = new_product_div.select_one('#selectQuantity')
                availability = select_quantity is not None
            else:
                availability = 'in stock' in availability_span.text.lower()
                availability = availability or 'available to ship' in availability_span.text.lower()
            price_span = new_product_div.select_one(
                '#corePrice_feature_div > div > div > div > div > span.a-price.a-text-normal.aok-align-center.reinventPriceAccordionT2 > span.a-offscreen')
            if price_span is None:
                product.invalid = True
                product.completed = True
                return product
            product.price = self.extract_price(price_span.text)
            shipping_info = new_product_div.select_one(
                '#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_MEDIUM')
            if shipping_info is None:
                shipping_info = new_product_div.select_one('#mir-layout-DELIVERY_BLOCK-slot-NO_PROMISE_UPSELL_MESSAGE')
            if shipping_info:
                product.shipping_cost = shipping_info.text.strip().split(' ')[0]
            else:
                print(f'{url} 获取运费信息失败')
            shipping_from_span = new_product_div.select_one(
                '#sfsb_accordion_head > div:nth-child(1) > div > span:nth-child(2)')
            if shipping_from_span:
                shipping_from = shipping_from_span.text.strip()
            else:
                shipping_from = ''
                print(f'{url} 获取货源地信息失败')
            sold_by_span = new_product_div.select_one(
                '#sfsb_accordion_head > div:nth-child(2) > div > span:nth-child(2)')
            if sold_by_span:
                sold_by = sold_by_span.text.strip()
            else:
                sold_by = ''
                print(f'{url} 获取卖方信息失败')
        product.shipping_from_amazon = shipping_from_amazon(shipping_from, sold_by)
        product.completed = True
        product.availability = availability
        return product

    @staticmethod
    def extract_price(price_text):
        logger.debug(f"price_span 类型: {type(price_text)}, 值: {price_text}")
        match = re.search(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', price_text)
        if match:
            price = match.group()
            return float(price.replace(',', ''))
        else:
            return 0

    def stop(self):
        try:
            self.amazon_driver.close()
        except Exception as e:
            pass


if __name__ == '__main__':
    from bit_browser import *
    # ids = get_all_browser_ids()
    driver = get_chrome_driver()
    agent = AmazonAgent(driver=driver)
    with open('urls.text', 'r') as f:
        urls = f.readlines()
    for url in urls:
        p = Product(url=url.strip())
        p = agent.start_craw(p)
        if p.availability:
            print(p.url, ' ', p.price)
