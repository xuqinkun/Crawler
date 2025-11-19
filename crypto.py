import time
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

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
    key_base64 = 'ZGlhbnhpYW9taTIwMjQxMg=='
    key = base64.b64decode(key_base64)  # 解码得到 16 字节密钥
    
    # 构造待加密数据，用 '±DXM±' 连接两个参数
    plaintext = f"{text}±DXM±{timestamp}"
    
    # 创建 AES ECB 密码器
    cipher = AES.new(key, AES.MODE_ECB)
    
    # 对数据进行 PKCS7 填充并加密
    padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    
    # 返回 Base64 编码的加密结果
    return base64.b64encode(encrypted_data).decode('utf-8')

# 测试函数
if __name__ == "__main__":    
    test_s = "111"
    test_time = int(time.time() * 1000)        
    result = get_encrypt_by_str(test_s, test_time)
    print(f"加密结果: {result}")