import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from product import Product
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
            print(f"成功连接到数据库: {self.db_name}")
        except sqlite3.Error as e:
            print(f"数据库连接错误: {e}")

    def init(self):
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
                    availability INTEGER DEFAULT 0,                                        
                    completed INTEGER DEFAULT 0,
                    shipping_from_amazon TEXT,
                    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    owner TEXT,
                    FOREIGN KEY (owner) REFERENCES accounts (username)
                );
            ''')

            self.conn.commit()
            print("数据表创建成功！")
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
            (product_id, asin, url, price, used,
            shipping_from_amazon, availability, owner, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                asin = COALESCE(excluded.asin, asin),
                url = COALESCE(excluded.url, url),
                price = COALESCE(excluded.price, price),
                used = COALESCE(excluded.used, used),
                shipping_from_amazon = COALESCE(excluded.shipping_from_amazon, shipping_from_amazon),
                availability = COALESCE(excluded.availability, availability),
                owner = COALESCE(excluded.owner, owner),
                completed = COALESCE(excluded.completed, completed),
                updated_at = CURRENT_TIMESTAMP
                ''', (
                product.product_id,
                product.asin,
                product.url,
                product.price,
                product.used,
                product.shipping_from_amazon,
                product.availability,
                product.owner,
                product.completed
            ))
            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"插入商品错误: {e}")
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

    def get_product_uncompleted(self):
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT id, product_id, url FROM product
                where completed = 0;
            ''')
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

    def get_all_products(self) -> List[Product]:
        """获取爬取状态"""
        try:
            self.cursor.execute('''
                SELECT * FROM product
            ''')
            rows = self.cursor.fetchall()
            products = []
            for row in rows:
                product = Product(
                    product_id=row['product_id'],
                    asin=row['asin'],
                    url=row['url'],
                    price=row['price'],
                    availability=row['availability'],
                    completed=bool(row['completed']),
                    shipping_from_amazon=bool(row['shipping_from_amazon']),
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
            return True
        except sqlite3.Error as e:
            print(f"删除账户错误: {e}")
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


# 使用示例
if __name__ == "__main__":
    db = AmazonDatabase()
    db.connect()
    db.drop()
    # db.init()
    # # 示例商品数据
    # product = Product(1, 'aaa')
    # db.insert_product(product)
    # prod = db.get_product_detail()
    # print(prod)
    # db.close()