import json
import time
import ddddocr
import requests


from urllib.parse import quote
from crypto import get_encrypt_by_str, base64_encode

ocr = ddddocr.DdddOcr()
headers = {
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
session = requests.Session()
# response = session.get('https://www.dianxiaomi.com/index.htm', headers=headers)
# soup = BeautifulSoup(response.text, 'html.parser')
# verify_img_code = soup.select_one('#verifyImgCode')
ts = int(time.time() * 1000)
verify_code_url = f'https://www.dianxiaomi.com/verify/code.htm?t={ts}'
response = session.get(verify_code_url)
# dxm_vc = response.cookies.get("dxm_vc")
# for k,v in response.cookies
image = response.content
with open('code.png', 'wb') as f:
    f.write(image)
verify_code = ocr.classification(image)
print(verify_code)
verify_code = input('请输入验证码: ')
account = '2b13257592627'
password = 'Aa123456'
time.sleep(2)
ts = int(time.time() * 1000)
payload = {
    'account': get_encrypt_by_str(account, ts),
    'password': get_encrypt_by_str(password, ts),
    'dxmVerify': verify_code,
    'loginVerifyCode': None,
    "loginRedUrl": "",
    "remeber": "remeber",
    "url": ""
}

cookies = {
    '_dxm_ad_client_id': 'EF5ED1455E6745E01606AB28D81ACD6D7',
    'tfstk': 'g69ibNvtcC5syNy_smXssb8KNHcK6O6f7EeAktQqTw7QWPe90iDDkeUvXf69nxbHlNCOQReciw8CDKn1MeXDRe8cGc_AuZYv0CnKeYK6ft6qn4H-ew9J1yd0QZPZ0vScnGRo2uJBft6qJkeqwYx6W1iWANWqx9ScjZWV_skFTwsY_Z8V76zFqg6VuE8VTwSRVrzaQZrUYwsV3Z8V3DxFRiXVuEWqxHllHR7y3p9Elv2jyqWZdQjGsa-N7hKpLJ141nb33-JHt_Qrow243pjw0MGGM8cAzQ_Owa8EpRXDYiYOJUkzK95kNnIDSA2NBBRBCOpKru1Mowfyp64a_gXGS_JNOly2AsRHKOpZl7tpxN5lpBhIWsBMSQ_5_XgBoHb9udfUS2QvwHpNtUuLKE1DNnIDSA2wzgWuT7uoC-sEDpPbG1SCxapyAdO5PQkrhDm3Nt1NAG3-xDVbG1SCxannx7Of_Msty',
    'MYJ_MKTG_fapsc5t4tc': 'JTdCJTdE',
    'Hm_lvt_f8001a3f3d9bf5923f780580eb550c0b': '1763520089',
    'HMACCOUNT': '839D2150948F958E',
    'Hm_lpvt_f8001a3f3d9bf5923f780580eb550c0b': '1763520789',
    'MYJ_fapsc5t4tc': ''
}
session.cookies.set('_dxm_ad_client_id', 'EF5ED1455E6745E01606AB28D81ACD6D7')
session.cookies.set('MYJ_MKTG_fapsc5t4tc', 'JTdCJTdE')
session.cookies.set('Hm_lvt_f8001a3f3d9bf5923f780580eb550c0b', '1763520089')
session.cookies.set('Hm_lpvt_f8001a3f3d9bf5923f780580eb550c0b', '1763520789')
session.cookies.set('tfstk', 'g69ibNvtcC5syNy_smXssb8KNHcK6O6f7EeAktQqTw7QWPe90iDDkeUvXf69nxbHlNCOQReciw8CDKn1MeXDRe8cGc_AuZYv0CnKeYK6ft6qn4H-ew9J1yd0QZPZ0vScnGRo2uJBft6qJkeqwYx6W1iWANWqx9ScjZWV_skFTwsY_Z8V76zFqg6VuE8VTwSRVrzaQZrUYwsV3Z8V3DxFRiXVuEWqxHllHR7y3p9Elv2jyqWZdQjGsa-N7hKpLJ141nb33-JHt_Qrow243pjw0MGGM8cAzQ_Owa8EpRXDYiYOJUkzK95kNnIDSA2NBBRBCOpKru1Mowfyp64a_gXGS_JNOly2AsRHKOpZl7tpxN5lpBhIWsBMSQ_5_XgBoHb9udfUS2QvwHpNtUuLKE1DNnIDSA2wzgWuT7uoC-sEDpPbG1SCxapyAdO5PQkrhDm3Nt1NAG3-xDVbG1SCxannx7Of_Msty')

myj = {"deviceId":"708e8b72-0a46-49c0-beb9-fe5a77efb999","userId":"","parentId":"","sessionId":1763689374075,"optOut":False,"lastEventId":0}
myj_text = json.dumps(myj)
cookies['MYJ_fapsc5t4tc'] = base64_encode(quote(myj_text))
session.cookies.set('MYJ_fapsc5t4tc', base64_encode(quote(myj_text)))

login_url = 'https://www.dianxiaomi.com/user/userLoginNew2.json'
response = session.post(login_url, data=payload, headers=headers)
print(response.text)
