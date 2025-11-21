import json
import time
import requests

from constant import *
from bs4 import BeautifulSoup
from cookies import CookieManager
from util import curr_milliseconds, ensure_dir_exists
from urllib.parse import quote
from crypto import get_encrypt_by_str, base64_encode
from pathlib import Path

class Agent():
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        ensure_dir_exists(self.cache_dir)
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

    def load_cookies(self, account: str):
        if account is None:
            return None
        cookie_file = self.cache_dir / f'{account}.json'
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

    def login(self, username: str, password: str, captcha: str):
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
        login_url = f'{ROOT}/{LOGIN_PAGE}'
        resp = self.session.post(login_url, data=payload, headers=self.headers)
        data = json.loads(resp.text)

        account_save_dir = self.cache_dir / 'accounts'
        ensure_dir_exists(account_save_dir)
        cookie_file = account_save_dir / f'{username}.json'
        account = {
            'username': username,
            'password': password,
            'cookies': self.session.cookies.get_dict()
        }
        try:
            with cookie_file.open('w', encoding=DEFAULT_ENCODING) as f:
                json.dump(account, fp=f)
        except Exception as e:
            print(f'保存cookie失败[account={username}]:{e}')
        return 'error' not in data
