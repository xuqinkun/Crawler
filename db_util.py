import sqlite3
from pathlib import Path
from typing import List
from constant import DATETIME_PATTERN
from bean import *
from util import ensure_dir_exists


class AmazonDatabase:
    def __init__(self, db_name=".cache/db/amazon_products.db"):
        ensure_dir_exists(Path(db_name).parent)
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"数据库连接错误: {e}")

    def create_product_table(self):
        """创建数据表"""
        try:
            # 用户表
            self.cursor.execute ("""
            CREATE TABLE IF NOT EXISTS account (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            );
            """)

            # 商品信息表
            self.cursor.execute('''                
                CREATE TABLE IF NOT EXISTS product (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE NOT NULL,
                    asin TEXT,
                    title TEXT,
                    price REAL DEFAULT -1,
                    black_list INTEGER DEFAULT -1,
                    currency TEXT,
                    url TEXT,
                    used INTEGER DEFAULT 0,
                    invalid INTEGER DEFAULT 0,
                    availability INTEGER DEFAULT 0,                                        
                    completed INTEGER DEFAULT 0,
                    shipping_from_amazon TEXT,
                    shipping_cost TEXT,
                    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    owner TEXT,
                    FOREIGN KEY (owner) REFERENCES accounts (username)
                );
            ''')

            self.conn.commit()
        except sqlite3.Error as e:
            print(f"创建表错误: {e}")

    def create_device_table(self):
        """创建数据表"""
        try:
            # 商品信息表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS device (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT UNIQUE NOT NULL,
                    device_code TEXT UNIQUE NOT NULL,
                    secrete_key TEXT,
                    activated INTEGER DEFAULT 0,
                    expired INTEGER DEFAULT 0,
                    valid_days INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activated_at TIMESTAMP DEFAULT NULL
                );
            ''')

            self.conn.commit()
        except sqlite3.Error as e:
            print(f"创建表错误: {e}")

    def drop(self):
        """创建数据表"""
        try:
            # 商品信息表
            self.cursor.execute('DROP TABLE IF EXISTS product;')
            self.cursor.execute('DROP TABLE IF EXISTS account;')
            self.conn.commit()
            print("删除表成功！")
        except sqlite3.Error as e:
            print(f"删除表错误: {e}")

    def upsert_product(self, product: Product):
        """插入或更新商品信息"""
        try:
            self.cursor.execute('''
            INSERT INTO product 
            (product_id, asin, url, price, used,shipping_from_amazon, shipping_cost, 
            availability, owner, completed, invalid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                asin = COALESCE(excluded.asin, asin),
                url = COALESCE(excluded.url, url),
                price = COALESCE(excluded.price, price),
                used = COALESCE(excluded.used, used),
                shipping_from_amazon = COALESCE(excluded.shipping_from_amazon, shipping_from_amazon),
                shipping_cost = COALESCE(excluded.shipping_cost, shipping_cost),
                availability = COALESCE(excluded.availability, availability),
                owner = COALESCE(excluded.owner, owner),
                completed = COALESCE(excluded.completed, completed),
                invalid = COALESCE(excluded.invalid, invalid),
                updated_at = CURRENT_TIMESTAMP
                ''', (
                product.product_id,
                product.asin,
                product.url,
                product.price,
                product.used,
                product.shipping_from_amazon,
                product.shipping_cost,
                product.availability,
                product.owner,
                product.completed,
                product.invalid,
            ))
            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"插入商品错误: {e}")
            return False

    def upsert_device(self, device: Device):
        """插入或更新设备信息"""
        try:
            self.cursor.execute('''
            INSERT INTO device 
            (device_name, device_code, secrete_key, activated, expired, 
             valid_days, created_at, activated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_code) DO UPDATE SET
                device_name = COALESCE(excluded.device_name, device_name),
                secrete_key = COALESCE(excluded.secrete_key, secrete_key),
                activated = COALESCE(excluded.activated, activated),
                expired = COALESCE(excluded.expired, expired),
                valid_days = COALESCE(excluded.valid_days, valid_days),
                created_at = COALESCE(excluded.created_at, created_at),
                activated_at = COALESCE(excluded.activated_at, activated_at)
                ''', (
                device.device_name,
                device.device_code,
                device.secrete_key,
                device.activated,
                device.expired,
                device.valid_days,
                device.created_at,
                device.activated_at
            ))
            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"插入设备信息错误: {e}")
            return False

    def batch_delete_products_by_ids(self, product_ids: List[str]):
        """批量删除商品信息"""
        try:
            self.cursor.executemany('''
            DELETE FROM product WHERE product_id = ?
            ''', [(product_id,) for product_id in product_ids])
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"批量删除商品错误: {e}")
            return False

    def batch_upsert_products_chunked(self, products: list[Product], chunk_size=500):
        """分块批量插入或更新商品信息"""
        if not products:
            return True

        total_count = len(products)
        success_count = 0

        for i in range(0, total_count, chunk_size):
            chunk = products[i:i + chunk_size]
            if self._batch_upsert_chunk(chunk):
                success_count += len(chunk)
            else:
                return False
        return True

    def _batch_upsert_chunk(self, products: list[Product]):
        """处理单个数据块"""
        try:
            product_data = []
            for product in products:
                product_data.append((
                    product.product_id,
                    product.asin,
                    product.url,
                    product.title,
                    product.price,
                    product.used,
                    product.shipping_from_amazon,
                    product.shipping_cost,
                    product.availability,
                    product.owner,
                    product.completed,
                    product.invalid,
                ))

            self.cursor.executemany('''
            INSERT INTO product 
            (product_id, asin, url, title, price, used, shipping_from_amazon, shipping_cost, 
             availability, owner, completed, invalid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                asin = COALESCE(excluded.asin, asin),
                url = COALESCE(excluded.url, url),
                title = COALESCE(excluded.title, title),
                price = COALESCE(excluded.price, price),
                used = COALESCE(excluded.used, used),
                shipping_from_amazon = COALESCE(excluded.shipping_from_amazon, shipping_from_amazon),
                shipping_cost = COALESCE(excluded.shipping_cost, shipping_cost),
                availability = COALESCE(excluded.availability, availability),
                owner = COALESCE(excluded.owner, owner),
                completed = COALESCE(excluded.completed, completed),
                invalid = COALESCE(excluded.invalid, invalid),
                updated_at = CURRENT_TIMESTAMP
            ''', product_data)

            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"批量插入数据块错误: {e}")
            self.conn.rollback()
            return False

    def update_product_dynamic(self, product):
        """动态构建UPDATE语句，只更新有值的字段"""
        update_fields = []
        update_values = []

        # 检查每个字段是否有值（None、空字符串等不算有值）
        if product.asin is not None and product.asin != '':
            update_fields.append("asin = ?")
            update_values.append(product.asin)

        if product.price is not None:
            update_fields.append("price = ?")
            update_values.append(product.price)

        if product.black_list is not None:
            update_fields.append("black_list = ?")
            update_values.append(product.black_list)

        if product.used is not None:
            update_fields.append("used = ?")
            update_values.append(product.used)

        if product.availability is not None and product.availability != '':
            update_fields.append("availability = ?")
            update_values.append(product.availability)

        if product.completed is not None:
            update_fields.append("completed = ?")
            update_values.append(product.completed)

        if product.shipping_from_amazon is not None:
            update_fields.append("shipping_from_amazon = ?")
            update_values.append(product.shipping_from_amazon)

        # 总是更新updated_at
        update_fields.append("updated_at = ?")
        update_values.append(datetime.now())

        # 如果没有要更新的字段（除了updated_at），直接返回
        if len(update_fields) <= 1:
            print("没有需要更新的字段")
            return False

        # 添加WHERE条件
        update_values.append(product.product_id)

        # 构建SQL语句
        sql = f'''
            UPDATE product 
            SET {', '.join(update_fields)}
            WHERE product_id = ?
        '''

        try:
            self.cursor.execute(sql, update_values)
            self.conn.commit()
            print(f"成功更新商品 {product.product_id}")
            return True
        except Exception as e:
            print(f"更新商品失败: {e}")
            return False

    def get_product_status(self):
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT id, product_id, url, completed FROM product
            ''')
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取爬取状态错误: {e}")

    def get_product_uncompleted(self, owner: str):
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT id, product_id, url FROM product
                where completed = 0 and owner=?;
            ''', (owner,))
            rows = self.cursor.fetchall()
            products = []
            for row in rows:
                product = Product(
                    product_id=row['product_id'],
                    url=row['url'],
                )
                products.append(product)
            return products
        except sqlite3.Error as e:
            print(f"获取爬取状态错误: {e}")

    def get_device_by_name(self, device_name: str):
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT * from device
                where device_name = ?;
            ''', (device_name,))
            row = self.cursor.fetchone()
            if not row:
                return None
            return Device(
                    device_name=row['device_name'],
                    device_code=row['device_code'],
                    secrete_key=row['secrete_key'],
                    activated=row['activated'] == 1,
                    expired=row['expired'] == 1,
                    valid_days=row['valid_days'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                )
        except Exception as e:
            print(f"获取爬取状态错误: {e}")
            return None

    def get_device_by_code(self, device_code: str):
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT * from device
                where device_code =?;
            ''', (device_code,))
            row = self.cursor.fetchone()
            if not row:
                return None
            return Device(
                    device_name=row['device_name'],
                    device_code=row['device_code'],
                    secrete_key=row['secrete_key'],
                    activated=row['activated'] == 1,
                    expired=row['expired'] == 1,
                    valid_days=row['valid_days'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                )
        except sqlite3.Error as e:
            print(f"获取爬取状态错误: {e}")

    def get_all_devices(self):
        try:
            self.cursor.execute("SELECT * FROM device")
            rows = self.cursor.fetchall()
            devices = []
            for row in rows:
                device = Device(
                    device_name=row['device_name'],
                    device_code=row['device_code'],
                    secrete_key=row['secrete_key'],
                    activated=row['activated'] == 1,
                    expired=row['expired'] == 1,
                    valid_days=row['valid_days'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                )
                devices.append(device)
            return devices
        except Exception as e:
            print(f"获取所有设备信息错误: {e}")
            return []

    def get_all_products(self, owner: str) -> List[Product]:
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT * FROM product
                where owner = ?
            ''', (owner,))
            rows = self.cursor.fetchall()
            products = []
            for row in rows:
                product = Product(
                    product_id=row['product_id'],
                    asin=row['asin'],
                    title=row['title'],
                    url=row['url'],
                    price=row['price'],
                    invalid=row['invalid'],
                    availability=row['availability'],
                    completed=row['completed'] == 1,
                    shipping_cost=row['shipping_cost'],
                    shipping_from_amazon=row['shipping_from_amazon'] == '1',
                )
                products.append(product)
            return products
        except sqlite3.Error as e:
            print(f"获取爬取状态错误: {e}")
            return []

    def get_product_by_id(self, product_id):
        """根据ASIN获取商品信息"""
        try:
            self.cursor.execute('''
                SELECT * FROM product WHERE product_id = ?
            ''', (product_id,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"获取商品错误: {e}")

    def upsert_account(self, username, password):
        """插入或更新账户信息"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO account (username, password)
                VALUES (?, ?)
            ''', (username, password))
            self.conn.commit()
            print(f"账户 {username} 保存成功")
            return True
        except sqlite3.Error as e:
            print(f"插入账户错误: {e}")
            return False

    def get_all_accounts(self):
        """获取账户信息"""
        try:
            self.cursor.execute('''
                SELECT * FROM account
            ''')
            ret = self.cursor.fetchall()
            if ret:
                return ret
            else:
                return []
        except sqlite3.Error as e:
            print(f"获取账户错误: {e}")
            return []

    def get_account_by_username(self, username):
        """根据用户名获取账户信息"""
        try:
            self.cursor.execute('''
                SELECT * FROM accounts WHERE username = ?
            ''', (username,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"获取账户错误: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("数据库连接已关闭")

    def delete_product_by_owner(self, username):
        """删除账户"""
        try:
            self.cursor.execute('''
                DELETE FROM product WHERE owner = ?
            ''', (username,))
            self.conn.commit()
            print(f"成功删除{username}的{self.cursor.rowcount}个产品")
            return True
        except sqlite3.Error as e:
            print(f"删除{username}的产品错误: {e}")
            return  False

    def delete_device_by_name(self, device_name):
        """删除账户"""
        try:
            self.cursor.execute('''
                DELETE FROM device WHERE device_name = ?
            ''', (device_name,))
            self.conn.commit()
            print(f"成功删除设备{device_name}")
            return True
        except sqlite3.Error as e:
            print(f"删除设备{device_name}错误: {e}")
            return  False

    def delete_device_by_code(self, device_code):
        """删除账户"""
        try:
            self.cursor.execute('''
                DELETE FROM device WHERE device_code = ?
            ''', (device_code,))
            self.conn.commit()
            print(f"成功删除设备{device_code}")
            return True
        except sqlite3.Error as e:
            print(f"删除设备{device_code}错误: {e}")
            return  False

    def delete_account(self, username):
        """删除账户"""
        try:
            self.cursor.execute('''
                DELETE FROM account WHERE username = ?
            ''', (username,))
            print(f"删除账户{username}成功!")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"删除账户错误: {e}")
            return  False

    def extend_device_life(self, device_code, extra_days):
        """续期：增加有效天数"""
        try:
            self.cursor.execute('''
                UPDATE device SET valid_days = valid_days + ? WHERE device_code = ?
            ''', (extra_days, device_code))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"续期错误: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    db = AmazonDatabase()
    db.connect()
    db.create_device_table()
    d = Device(device_name='d', device_code='d')
    d.secrete_key = 'xxxx'
    d.activated = True
    d.valid_days = 7
    db.upsert_device(d)
    devices = db.get_all_devices()
    print(devices)
    db.delete_device_by_name('d')
    db.upsert_device(Device(device_name='a',
                            device_code='a',
                            valid_days=7))
    print(db.get_all_devices())