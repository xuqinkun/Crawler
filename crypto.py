import base64
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

def base64_encode(s: str):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')

def get_encrypt_by_str(text: str, timestamp: int) -> str:
    """
    重写 JavaScript 的 getEncryptByStr 函数
    参数:
        s: 要加密的字符串
        time: 时间参数
    返回:
        Base64 编码的加密结果
    """
    # 密钥 - 注意：JavaScript 中的密钥是 Base64 编码的 'dianxiaomi202412'
    key = 'ZGlhbnhpYW9taTIwMjQxMg=='.encode('utf-8')

    
    # 构造待加密数据，用 '±DXM±' 连接两个参数
    plaintext = f"{text}±DXM±{timestamp}"
    
    # 创建 AES ECB 密码器
    cipher = AES.new(key, AES.MODE_ECB)
    
    # 对数据进行 PKCS7 填充并加密
    padded = pad(plaintext.encode('utf-8'), AES.block_size, style='pkcs7')
    encrypted_data = cipher.encrypt(padded)
    
    # 返回 Base64 编码的加密结果
    return base64.b64encode(encrypted_data).decode('utf-8')

# 测试函数
if __name__ == "__main__":
    d = {"deviceId":"708e8b72-0a46-49c0-beb9-fe5a77efb999","userId":"","parentId":"","sessionId":1763689374075,"optOut":False,"lastEventId":0}
    s = json.dumps(d)
