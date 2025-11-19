import ddddocr
import requests
import time
import json

from bs4 import BeautifulSoup
from crypto import get_encrypt_by_str

ocr = ddddocr.DdddOcr()

response = requests.get('https://www.dianxiaomi.com/index.htm')
soup = BeautifulSoup(response.text, 'html.parser')
verify_img_code = soup.select_one('#verifyImgCode')
ts = int(time.time() * 1000)
verify_code_url = f'https://www.dianxiaomi.com/verify/code.htm?t={ts}'
response = requests.get(verify_code_url)
image = response.content
with open('code.png', 'wb') as f:
    f.write(image)
verify_code = ocr.classification(image)
print(verify_code)
verify_code = input('请输入验证码: ')
account = '2b13257592627'
password = 'Aa123456'
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
print(payload)
cookies = {
    '_dxm_ad_client_id': 'EF5ED1455E6745E01606AB28D81ACD6D7',
    'tfstk': 'g69ibNvtcC5syNy_smXssb8KNHcK6O6f7EeAktQqTw7QWPe90iDDkeUvXf69nxbHlNCOQReciw8CDKn1MeXDRe8cGc_AuZYv0CnKeYK6ft6qn4H-ew9J1yd0QZPZ0vScnGRo2uJBft6qJkeqwYx6W1iWANWqx9ScjZWV_skFTwsY_Z8V76zFqg6VuE8VTwSRVrzaQZrUYwsV3Z8V3DxFRiXVuEWqxHllHR7y3p9Elv2jyqWZdQjGsa-N7hKpLJ141nb33-JHt_Qrow243pjw0MGGM8cAzQ_Owa8EpRXDYiYOJUkzK95kNnIDSA2NBBRBCOpKru1Mowfyp64a_gXGS_JNOly2AsRHKOpZl7tpxN5lpBhIWsBMSQ_5_XgBoHb9udfUS2QvwHpNtUuLKE1DNnIDSA2wzgWuT7uoC-sEDpPbG1SCxapyAdO5PQkrhDm3Nt1NAG3-xDVbG1SCxannx7Of_Msty',
    'MYJ_MKTG_fapsc5t4tc': 'JTdCJTdE',
    'Hm_lvt_f8001a3f3d9bf5923f780580eb550c0b': '1763520089',
    'HMACCOUNT': '839D2150948F958E',
    'Hm_lpvt_f8001a3f3d9bf5923f780580eb550c0b': '1763520789',
    'MYJ_fapsc5t4tc': 'JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjI3MDhlOGI3Mi0wYTQ2LTQ5YzAtYmViOS1mZTVhNzdlZmI5OTklMjIlMkMlMjJ1c2VySWQlMjIlM0ElMjIlMjIlMkMlMjJwYXJlbnRJZCUyMiUzQSUyMiUyMiUyQyUyMnNlc3Npb25JZCUyMiUzQTE3NjM1MzEwOTE2NTAlMkMlMjJvcHRPdXQlMjIlM0FmYWxzZSUyQyUyMmxhc3RFdmVudElkJTIyJTNBMCU3RA=='
}
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
login_url = 'https://www.dianxiaomi.com/user/userLoginNew2.json'
response = requests.post(login_url, data=payload, headers=headers, cookies=cookies)
print(response.text)
exit(0)
result = json.loads(response.text)
if result.get('code') != 200:
    print('登录失败')
    verify_code = input('请输入验证码: ')
    payload['dxmVerify'] = verify_code
    response = requests.post(login_url, data=payload)
    print(response.text)