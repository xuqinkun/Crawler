import json
import logging
import os
import pickle
import requests

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from util import ensure_dir_exists


class CookieManager:
    """
    Cookie管理器 - 支持多个账号的Cookie保存和恢复
    """

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        ensure_dir_exists(self.cache_dir)
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger('CookieManager')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def ensure_storage_dir(self):
        """确保存储目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def save_cookies_json(self, session: requests.Session, account: str, filename: Optional[str] = None):
        """
        将Session的Cookie保存为JSON文件

        Args:
            session: requests.Session对象
            account: 账号标识
            filename: 文件名（可选，默认使用account_id）
        """
        if filename is None:
            filename = f"{account}.json"

        filepath = os.path.join(self.cache_dir, filename)

        try:
            cookies_list = []
            for cookie in session.cookies:
                cookie_dict = {
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'expires': cookie.expires,
                    'secure': cookie.secure,
                    'rest': getattr(cookie, 'rest', None)
                }
                cookies_list.append(cookie_dict)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'account_id': account,
                    'saved_at': datetime.now().isoformat(),
                    'cookies': cookies_list
                }, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Cookie已保存到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"保存Cookie失败: {e}")
            return False

    def load_cookies_json(self, session: requests.Session, account_id: str, filename: Optional[str] = None):
        """
        从JSON文件加载Cookie到Session

        Args:
            session: requests.Session对象
            account_id: 账号标识
            filename: 文件名（可选，默认使用account_id）
        """
        if filename is None:
            filename = f"{account_id}_cookies.json"

        filepath = os.path.join(self.cache_dir, filename)

        if not os.path.exists(filepath):
            self.logger.warning(f"Cookie文件不存在: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 清空现有Cookie
            session.cookies.clear()

            # 添加Cookie
            for cookie_dict in data['cookies']:
                # 处理过期时间
                expires = cookie_dict.get('expires')
                if expires and expires != -1:
                    # 如果Cookie已过期，跳过
                    if datetime.now().timestamp() > expires:
                        continue

                cookie = requests.cookies.create_cookie(
                    name=cookie_dict['name'],
                    value=cookie_dict['value'],
                    domain=cookie_dict['domain'],
                    path=cookie_dict['path'],
                    expires=expires,
                    secure=cookie_dict.get('secure', False)
                )
                session.cookies.set_cookie(cookie)

            self.logger.info(f"Cookie已从 {filepath} 加载")
            return True

        except Exception as e:
            self.logger.error(f"加载Cookie失败: {e}")
            return False

    def save_cookies_pickle(self, session: requests.Session, account_id: str, filename: Optional[str] = None):
        """
        使用pickle保存整个Session（包含Cookie）

        Args:
            session: requests.Session对象
            account_id: 账号标识
            filename: 文件名（可选）
        """
        if filename is None:
            filename = f"{account_id}_session.pkl"

        filepath = os.path.join(self.cache_dir, filename)

        try:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'account_id': account_id,
                    'saved_at': datetime.now(),
                    'session': session
                }, f)

            self.logger.info(f"Session已保存到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"保存Session失败: {e}")
            return False

    def load_cookies_pickle(self, account_id: str, filename: Optional[str] = None) -> Optional[requests.Session]:
        """
        从pickle文件加载整个Session

        Args:
            account_id: 账号标识
            filename: 文件名（可选）

        Returns:
            requests.Session对象或None
        """
        if filename is None:
            filename = f"{account_id}_session.pkl"

        filepath = os.path.join(self.cache_dir, filename)

        if not os.path.exists(filepath):
            self.logger.warning(f"Session文件不存在: {filepath}")
            return None

        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)

            self.logger.info(f"Session已从 {filepath} 加载")
            return data['session']

        except Exception as e:
            self.logger.error(f"加载Session失败: {e}")
            return None

    def save_cookies_simple(self, cookies_dict: dict, account_id: str, filename: Optional[str] = None):
        """
        简单保存Cookie字典（适用于手动获取的Cookie）

        Args:
            cookies_dict: Cookie字典 {name: value}
            account_id: 账号标识
            filename: 文件名（可选）
        """
        if filename is None:
            filename = f"{account_id}_simple_cookies.json"

        filepath = os.path.join(self.cache_dir, filename)

        try:
            data = {
                'account_id': account_id,
                'saved_at': datetime.now().isoformat(),
                'cookies': cookies_dict
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"简单Cookie已保存到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"保存简单Cookie失败: {e}")
            return False

    def load_cookies_simple(self, account_id: str, filename: Optional[str] = None) -> Optional[dict]:
        """
        加载简单Cookie字典

        Args:
            account_id: 账号标识
            filename: 文件名（可选）

        Returns:
            Cookie字典或None
        """
        if filename is None:
            filename = f"{account_id}_simple_cookies.json"

        filepath = os.path.join(self.cache_dir, filename)

        if not os.path.exists(filepath):
            self.logger.warning(f"简单Cookie文件不存在: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.logger.info(f"简单Cookie已从 {filepath} 加载")
            return data['cookies']

        except Exception as e:
            self.logger.error(f"加载简单Cookie失败: {e}")
            return None

    def list_accounts(self) -> List[str]:
        """列出所有已保存的账号"""
        accounts = set()

        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json') or filename.endswith('.pkl'):
                # 从文件名提取account_id
                account_id = filename.split('_')[0]
                accounts.add(account_id)

        return sorted(list(accounts))

    def delete_account_cookies(self, account_id: str):
        """删除指定账号的所有Cookie文件"""
        deleted_count = 0

        for filename in os.listdir(self.cache_dir):
            if filename.startswith(account_id + '_'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    self.logger.info(f"已删除: {filepath}")
                except Exception as e:
                    self.logger.error(f"删除文件失败 {filepath}: {e}")

        return deleted_count


# 使用示例
def demo():
    """演示使用方法"""

    # 创建Cookie管理器
    cookie_mgr = CookieManager()

    # 示例1: 使用JSON方式保存和加载
    print("=== JSON方式演示 ===")
    session1 = requests.Session()

    # 模拟登录获取Cookie（这里需要替换为实际的登录代码）
    # login_response = session1.post('https://example.com/login', data={'user': 'user1', 'pass': 'pass1'})

    # 保存Cookie
    cookie_mgr.save_cookies_json(session1, "user1")

    # 创建新Session并加载Cookie
    new_session1 = requests.Session()
    cookie_mgr.load_cookies_json(new_session1, "user1")

    # 示例2: 使用pickle方式保存和加载整个Session
    print("\n=== Pickle方式演示 ===")
    session2 = requests.Session()
    cookie_mgr.save_cookies_pickle(session2, "user2")

    loaded_session = cookie_mgr.load_cookies_pickle("user2")
    if loaded_session:
        print("Session加载成功")

    # 示例3: 简单Cookie字典方式
    print("\n=== 简单Cookie方式演示 ===")
    cookies_dict = {
        'session_id': 'abc123',
        'user_token': 'xyz789',
        'csrf_token': 'def456'
    }
    cookie_mgr.save_cookies_simple(cookies_dict, "user3")

    loaded_cookies = cookie_mgr.load_cookies_simple("user3")
    print(f"加载的Cookie: {loaded_cookies}")

    # 示例4: 列出所有账号
    print("\n=== 账号列表 ===")
    accounts = cookie_mgr.list_accounts()
    print(f"已保存的账号: {accounts}")


# 实际应用场景示例
class MultiAccountManager:
    """多账号管理器"""

    def __init__(self, cookie_dir=".cache"):
        self.cookie_mgr = CookieManager(cookie_dir)
        self.sessions = {}

    def login_and_save(self, account: str, login_url: str, payload: dict, headers: dict):
        """登录并保存Cookie"""
        session = requests.Session()

        try:
            # 执行登录
            response = session.post(login_url, data=payload, headers=headers)
            response.raise_for_status()

            # 检查登录是否成功（根据实际API调整）
            if self.check_login_success(response):
                # 保存Cookie
                self.cookie_mgr.save_cookies_json(session, account)
                self.sessions[account] = session
                print(f"账号 {account} 登录成功并保存Cookie")
                return True
            else:
                print(f"账号 {account} 登录失败")
                return False

        except Exception as e:
            print(f"账号 {account} 登录异常: {e}")
            return False

    def load_account(self, account_id: str) -> bool:
        """加载已保存的账号"""
        session = requests.Session()

        if self.cookie_mgr.load_cookies_json(session, account_id):
            # 验证Cookie是否仍然有效
            if self.validate_session(session):
                self.sessions[account_id] = session
                print(f"账号 {account_id} 加载成功")
                return True
            else:
                print(f"账号 {account_id} 的Cookie已失效")
                return False
        else:
            print(f"账号 {account_id} 的Cookie文件不存在")
            return False

    def check_login_success(self, response):
        """检查登录是否成功（需要根据实际情况实现）"""
        # 示例：检查响应中是否包含成功标识
        return 'login_success' in response.text or response.status_code == 200

    def validate_session(self, session):
        """验证Session是否有效（需要根据实际情况实现）"""
        try:
            # 示例：访问需要登录的页面验证
            test_url = "https://example.com/user/profile"
            response = session.get(test_url, timeout=10)
            return response.status_code == 200
        except:
            return False

    def get_session(self, account_id: str) -> Optional[requests.Session]:
        """获取账号的Session"""
        return self.sessions.get(account_id)

    def list_available_accounts(self):
        """列出所有可用的账号"""
        return self.cookie_mgr.list_accounts()


if __name__ == "__main__":
    # # 运行演示
    # demo()
    #
    # # 多账号管理器示例
    # print("\n" + "=" * 50)
    # print("多账号管理器示例")

    account_manager = MultiAccountManager()

    # 假设的登录信息
    accounts_info = [
        {"id": "alice", "url": "https://www.dianxiaomi.com", "data": {"user": "alice", "pass": "pass123"}},
        {"id": "bob", "url": "https://www.dianxiaomi.com", "data": {"user": "bob", "pass": "pass456"}},
    ]

    # 登录并保存（实际使用时取消注释）
    for acc_info in accounts_info:
        account_manager.login_and_save(acc_info["id"], acc_info["url"], acc_info["data"])

    # 加载已保存的账号
    available_accounts = account_manager.list_available_accounts()
    print(f"可用的账号: {available_accounts}")

    for account_id in available_accounts:
        if account_manager.load_account(account_id):
            session = account_manager.get_session(account_id)
            # 使用session进行后续请求...