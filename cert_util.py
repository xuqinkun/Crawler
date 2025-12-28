import base64
import hashlib
import json
import subprocess
import uuid
import locale
from datetime import datetime

from bean import Device
from constant import DATETIME_PATTERN

system_encoding = locale.getpreferredencoding()

def get_mac_address():
    """获取计算机的MAC地址"""
    try:
        import platform

        system = platform.system()
        mac = ''

        if system == "Windows":
            # Windows系统
            try:
                output = subprocess.check_output("getmac", shell=True, encoding=system_encoding)
            except UnicodeDecodeError:
                # 如果首选编码失败，尝试UTF-8，并忽略无法解码的字符
                output = subprocess.check_output("getmac", shell=True).decode('utf-8', errors='ignore')
            for line in output.split('\n'):
                if ':' in line or '-' in line:
                    # 取第一个有效的MAC地址
                    parts = line.strip().split()
                    for part in parts:
                        if ':' in part or '-' in part:
                            # 统一格式为用冒号分隔
                            mac = part.replace('-', ':')
                            break
                    if mac:
                        break

        elif system == "Linux":
            # Linux系统
            with open('/sys/class/net/eth0/address', 'r') as f:
                mac = f.read().strip()
        elif system == "Darwin":
            # macOS系统
            output = subprocess.check_output("ifconfig en0 | grep ether", shell=True).decode()
            mac = output.strip().split()[1]

        return mac if mac else "00:00:00:00:00:00"

    except Exception as e:
        print(f"获取MAC地址失败: {e}")
        return "00:00:00:00:00:00"


def generate_device_code(mac_address=None, custom_salt="device_key_system"):
    """
    生成唯一的设备码

    参数:
        mac_address: 设备的MAC地址，如果为None则自动获取当前计算机的MAC地址
        custom_salt: 自定义盐值，增加设备码的复杂性

    返回:
        字符串: 32位的唯一设备码
    """
    try:
        if mac_address is None:
            mac_address = get_mac_address()

        # 获取当前时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # 生成一个随机UUID
        random_uuid = str(uuid.uuid4())

        # 组合所有元素并进行哈希
        combined_string = f"{mac_address}{timestamp}{random_uuid}{custom_salt}"

        # 使用SHA256生成哈希值
        hash_object = hashlib.sha256(combined_string.encode())
        hex_digest = hash_object.hexdigest()

        # 取前32位作为设备码（可以调整长度）
        device_code = hex_digest[:32]

        # 格式化为8-4-4-4-12的格式，便于识别和记忆
        formatted_code = '-'.join([
            device_code[0:8],
            device_code[8:12],
            device_code[12:16],
            device_code[16:20],
            device_code[20:32]
        ])

        return formatted_code.upper()

    except Exception as e:
        print(f"生成设备码失败: {e}")
        # 如果生成失败，返回一个基于UUID的设备码作为后备
        return str(uuid.uuid4()).upper()


def digest(text: str):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def device_code_with_digest():
    """
    基于设备码生成密钥

    参数:
        device_code: 设备码
        custom_salt: 自定义盐值

    返回:
        字符串: 16位密钥
    """
    try:
        # 获取当前时间戳
        mac = get_mac_address()
        return digest(mac)
    except Exception as e:
        print(f"生成密钥失败: {e}")
        # 如果生成失败，返回一个简化的密钥作为后备
        return str(uuid.uuid4()).replace('-', '')[:16].upper()


def generate_key_from_device(device_name: str, device_code: str, created_at: datetime, valid_days: int):
    cert = {"device_name": device_name,
            "device_code": device_code,
            "created_at": created_at.strftime(DATETIME_PATTERN),
            "activated_at": datetime.now().strftime(DATETIME_PATTERN),
            "valid_days": valid_days}
    cert_str = json.dumps(cert)

    cert_str_padded = cert_str + '=' * (4 - len(cert_str) % 4)
    cert_data = base64.b64encode(cert_str_padded.encode('utf-8'))
    return cert_data.decode('utf-8')


def decode_key(encoded_key: str) -> Device:
    plain_text = base64.b64decode(encoded_key).decode('utf-8').rstrip('=')
    device_info = json.loads(plain_text)
    return Device(device_name=device_info['device_name'],
                  device_code=device_info['device_code'],
                  created_at=datetime.strptime(device_info['created_at'], DATETIME_PATTERN),
                  valid_days=device_info['valid_days'],
                  activated_at=datetime.strptime(device_info['activated_at'], DATETIME_PATTERN))


if __name__ == '__main__':
    print(device_code_with_digest())