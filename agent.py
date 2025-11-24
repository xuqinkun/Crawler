import json
from typing import Set

import requests
from PyQt5.QtCore import QObject, pyqtSignal
from db_util import AmazonDatabase
from constant import *
from bs4 import BeautifulSoup
from product import Product
from cookies import CookieManager
from util import curr_milliseconds, ensure_dir_exists
from urllib.parse import quote, urlencode
from crypto import get_encrypt_by_str, base64_encode
from pathlib import Path

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
        self.session = requests.Session()
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
            return {}

    def get_captcha(self):
        ts = curr_milliseconds()
        verify_code_url = f'{ROOT}/{VERIFY_PAGE}?t={ts}'
        response = self.session.get(verify_code_url)
        image = response.content
        return image

    def login(self, username: str, password: str = '', captcha: str = ''):
        self.username = username
        valid = self.cookie_manager.load_cookies_json(self.session, username)
        if not valid:
            self.session.cookies.set('_dxm_ad_client_id', 'EF5ED1455E6745E01606AB28D81ACD6D7')
            self.session.cookies.set('MYJ_MKTG_fapsc5t4tc', 'JTdCJTdE')
            self.session.cookies.set('Hm_lvt_f8001a3f3d9bf5923f780580eb550c0b', '1763520089')
            self.session.cookies.set('Hm_lpvt_f8001a3f3d9bf5923f780580eb550c0b', '1763520789')
            self.session.cookies.set('tfstk',
            'g69ibNvtcC5syNy_smXssb8KNHcK6O6f7EeAktQqTw7QWPe90iDDkeUvXf69nxbHlNCOQReciw8CDKn1MeXDRe8cGc_AuZYv0CnKeYK6ft6qn4H-ew9J1yd0QZPZ0vScnGRo2uJBft6qJkeqwYx6W1iWANWqx9ScjZWV_skFTwsY_Z8V76zFqg6VuE8VTwSRVrzaQZrUYwsV3Z8V3DxFRiXVuEWqxHllHR7y3p9Elv2jyqWZdQjGsa-N7hKpLJ141nb33-JHt_Qrow243pjw0MGGM8cAzQ_Owa8EpRXDYiYOJUkzK95kNnIDSA2NBBRBCOpKru1Mowfyp64a_gXGS_JNOly2AsRHKOpZl7tpxN5lpBhIWsBMSQ_5_XgBoHb9udfUS2QvwHpNtUuLKE1DNnIDSA2wzgWuT7uoC-sEDpPbG1SCxapyAdO5PQkrhDm3Nt1NAG3-xDVbG1SCxannx7Of_Msty')

            myj = {"deviceId": "708e8b72-0a46-49c0-beb9-fe5a77efb999",
                   "userId": "",
                   "parentId": "",
                   "sessionId": curr_milliseconds(),
                   "optOut": False,
                   "lastEventId": 0}
            myj_text = json.dumps(myj)
            self.session.cookies.set('MYJ_fapsc5t4tc', base64_encode(quote(myj_text)))
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
            resp = self.session.post(login_url, data=payload, headers=self.headers)
            data = json.loads(resp.text)
            self.cookie_manager.save_cookies_json(self.session, account=username)
            self.online = 'error' not in data
            return self.online
        product_page = f'{ROOT}/{PRODUCT_PAGE}'
        resp = self.session.post(product_page, headers=self.headers)
        self.online = json.loads(resp.text)['msg']=='Successful'
        return self.online

    def post(self, url, payload):
        resp = self.session.post(url, data=payload, headers=self.headers)
        return resp.text

    def start_craw(self, url: str, session: requests.Session):
        try:
            start = url.rfind('/')
            end = url.rfind('?')
            if end == -1:
                asin = url[start + 1:]
            else:
                asin = url[start + 1:end]
            product = Product()
            product.asin = asin
            product_payload['asinList'] = asin
            product_payload['asin'] = asin
            product_payload['landingAsin'] = asin
            params = urlencode(product_payload)
            detail_url = f'{PRODUCT_DETAIL_PAGE}?{params}'
            detail_resp = session.get(detail_url, headers=self.headers, cookies=amazon_cookies)
            detail = json.loads(detail_resp.text)
            product.price = float(detail['Value']['content']['twisterSlotJson']['price'])
            main_page = session.get(f'https://www.amazon.com/dp/{asin}?th=1', headers=self.headers, cookies=amazon_cookies)
            main_soup = BeautifulSoup(main_page.text, 'html.parser')
            # buy_new = main_soup.select_one('#newAccordionCaption_feature_div').text.strip()
            # product.used = 'Buy new' not in buy_new
            availability_info = main_soup.select_one('#availability')
            # 缺货
            if availability_info and 'In Stock' in availability_info.text:
                product.availability = True
                shipping_info = self.extract_amazon_shipping_info(main_page.text)

                if shipping_info['ships_from'] == 'Amazon' or shipping_info['sold_by'] == 'Amazon':
                    product.shipping_from_amazon = True
                else:
                    product.shipping_from_amazon = False
                delivery_info = main_soup.select_one('#mir-layout-DELIVERY_BLOCK').text.strip()
                shipping_cost = float(delivery_info[:delivery_info.find('delivery')])
                product.shipping_cost = shipping_cost
            else:
                product.availability = False
            product.completed = True
            return product
        except Exception as e:
            print(f'解析{url}时发生错误：{e}')

    def extract_amazon_shipping_info(self, html_content):
        """
        从亚马逊商品页面提取Ships from和Sold by信息
        返回字典包含: ships_from, sold_by, seller_link
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result = {'ships_from': None, 'sold_by': None, 'seller_link': None}
            # 查找所有包含运输和销售信息的div
            feature_divs = soup.find_all('div', class_='celwidget', attrs={'data-feature-name': True})

            for div in feature_divs:
                feature_name = div.get('data-feature-name', '')

                # Ships from 信息
                if feature_name == 'fulfillerInfoFeature_feature_div':
                    ships_from_span = div.find('span', class_='a-size-small a-color-tertiary', string='Ships from')
                    if ships_from_span:
                        # 在同一个feature_div中查找商家名称
                        name_span = div.find('span', class_='offer-display-feature-text-message')
                        if name_span:
                            result['ships_from'] = name_span.get_text(strip=True)

                # Sold by 信息
                elif feature_name == 'merchantInfoFeature_feature_div':
                    sold_by_span = div.find('span', class_='a-size-small a-color-tertiary', string='Sold by')
                    if sold_by_span:
                        # 查找商家名称和链接
                        seller_link = div.find('a',
                                               class_='a-size-small a-link-normal offer-display-feature-text-message')
                        if seller_link:
                            result['sold_by'] = seller_link.get_text(strip=True)
                            result['seller_link'] = seller_link.get('href', '')

            # 备用方法：如果上述方法没找到，尝试直接搜索文本
            if not result['ships_from']:
                ships_from_elements = soup.find_all('span', class_='a-size-small a-color-tertiary', string='Ships from')
                for element in ships_from_elements:
                    next_text = element.find_next('span', class_='offer-display-feature-text-message')
                    if next_text:
                        result['ships_from'] = next_text.get_text(strip=True)
                        break

            if not result['sold_by']:
                sold_by_elements = soup.find_all('span', class_='a-size-small a-color-tertiary', string='Sold by')
                for element in sold_by_elements:
                    next_link = element.find_next('a',
                                                  class_='a-size-small a-link-normal offer-display-feature-text-message')
                    if next_link:
                        result['sold_by'] = next_link.get_text(strip=True)
                        result['seller_link'] = next_link.get('href', '')
                        break

        except Exception as e:
            print(f"提取运输信息时出错: {e}")

        return result

    def parse_product_list(self, ids: Set[int]):
        if not self.online:
            return [], 0

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
        response = self.post(page_url, payload)
        pages = json.loads(response)
        page = pages['data']['page']
        total_pages = page['totalPage']
        total_items = page['totalSize']

        products = []
        if len(ids) < total_items:
            for page_no in range(1, total_pages + 1):
                payload['pageNo'] = page_no
                response = self.post(page_url, payload)
                pages = json.loads(response)
                page = pages['data']['page']
                for item in page['list']:
                    product_id = item['id']
                    if product_id in ids:
                        continue
                    product = Product(product_id=product_id, url=item['sourceUrl'])
                    products.append(product)
        return products, total_items


if __name__ == '__main__':
    db = AmazonDatabase()
    db.connect()
    db.init()
    agent = Agent(db)
    agent.login('2b13257592627')

    agent.db.close()

