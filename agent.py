import json
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

    def __init__(self, db: AmazonDatabase, cache_dir: str = CACHE_DIR):
        super().__init__()
        self.db = db
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
        self.total_url = 0
        self.completed_url = 0

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

    def get_progress(self):
        if self.total_url == 0:
            return 0
        else:
            return (int)(100 * self.completed_url / self.total_url)

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

    def download(self):
        product_mapping = self.get_product_list()
        pass

    def get_product_list(self):
        if not self.online:
            return []
        url_save_path = self.url_dir / f'{self.username}.json'
        if url_save_path.exists():
            try:
                with url_save_path.open('r', encoding=DEFAULT_ENCODING) as f:
                    product_mapping = json.load(f)
                return product_mapping
            except Exception as e:
                print(f'读取URL错误[account={self.username}]: {e}')
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
        product_mapping = {}
        for page_no in range(1, total_pages + 1):
            payload['pageNo'] = page_no
            response = self.post(page_url, payload)
            pages = json.loads(response)
            page = pages['data']['page']
            for item in page['list']:
                id = item['id']
                product_mapping[id] = item['sourceUrl']
        with url_save_path.open('w', encoding=DEFAULT_ENCODING) as f:
            json.dump(product_mapping, f)
        return product_mapping


if __name__ == '__main__':
    db = AmazonDatabase()
    agent = Agent(db)
    agent.login('2b13257592627')
    product_urls = agent.get_product_list()
    session = requests.Session()
    product_uncompleted = agent.db.get_product_uncompleted()
    session.cookies.update(amazon_cookies)
    for id, product in product_urls.items():
        url = product['url']
        product_save = Product(id, url)
        resp = session.get(url, headers=agent.headers, cookies=amazon_cookies)
        start = url.rfind('/')
        end = url.rfind('?')
        if end == -1:
            asin = url[start + 1:]
        else:
            asin = url[start + 1:end]
        product_payload['asinList'] = asin
        product_payload['asin'] = asin
        product_payload['landingAsin'] = asin
        params = urlencode(product_payload)
        detail_url = f'{PRODUCT_DETAIL_PAGE}?{params}'
        resp = session.get(detail_url, headers=agent.headers)

        main_page = session.get(f'https://www.amazon.com/dp/{asin}?th=1', headers=agent.headers)
        soup = BeautifulSoup(main_page.text, 'html.parser')
        no_availability_info = soup.select_one('p.a-text-bold')
        availability = False
        # 缺货
        if no_availability_info and 'No featured offers available' in no_availability_info.text:
            product_save.completed = True
        else:
            availability = soup.select_one('#availability')
            shipping_info = soup.select_one('#sfsb_accordion_head').text.strip()
            r_index = shipping_info.find('Sold')
            left = shipping_info[:r_index].strip()
            right = shipping_info[r_index:].strip()
            shipping_from = left[left.find(':') + 1:].strip()
            sold_by = right[right.find(':') + 1:].strip()
            shipping_from_amazon = False
            if shipping_from == 'Amazon' or sold_by == 'Amazon':
                shipping_from_amazon = True
            delivery_info = soup.select_one('#mir-layout-DELIVERY_BLOCK').text.strip()
            shipping_cost = delivery_info[:delivery_info.find('delivery')]
            content = json.loads(resp.text)['Value']['content']
            info = content['twisterSlotJson']
            div = content['twisterSlotDiv']
            soup = BeautifulSoup(div, 'html.parser')
            soup.select('#twisterAvailability')
            stock_info = soup.select_one('#twisterAvailability')
            if availability and 'In Stock' in availability.text.strip():
                availability = True
            elif 'isAvailable' in info and info['isAvailable']:
                availability = True
            elif stock_info:
                available_text = stock_info.text.strip()
                if 'In Stock' in available_text:
                    availability = True
            else:
                availability = False
        product_save.availability = availability
        agent.db.insert_product(product_save)
    agent.db.close()

