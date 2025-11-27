import threading
from datetime import datetime

import pandas as pd

from db_util import AmazonDatabase
from util import ensure_dir_exists


class ExportWorker:
    """导出工作器（使用标准threading）"""

    def __init__(self, username, filename, export_path, callback=None):
        self.username = username
        self.filename = filename
        self.export_path = export_path
        self.callback = callback  # 完成回调函数
        self.thread = None

    def start(self):
        """启动导出线程"""
        self.thread = threading.Thread(target=self._export_data)
        self.thread.daemon = True  # 设置为守护线程
        self.thread.start()

    def _export_data(self):
        """在后台线程中执行导出操作"""
        try:
            # 获取产品数据
            db = AmazonDatabase()
            db.connect()
            products = db.get_all_products(self.username)

            if not products:
                if self.callback:
                    self.callback(False, f"用户 {self.username} 没有产品数据")
                return

            # 如果没有指定文件名，生成默认文件名
            if self.filename is None:
                timestamp = datetime.now().strftime("%Y年%m月%d日_%H时%M分%S秒")
                self.filename = self.export_path / self.username / f"products_{timestamp}.csv"
                ensure_dir_exists(self.filename.parent)

            # 将产品对象转换为字典列表
            products_data = []
            for n, product in enumerate(products):
                if product.completed:
                    product_dict = {
                        '序号': n + 1,
                        '产品ID': str(product.product_id),
                        'asin': product.asin,
                        '链接': product.url,
                        '有无库存': '有' if product.availability else '无',
                        '价格': 'N/A',
                        '运费': 'N/A',
                        '是否二手': 'N/A',
                        '从亚马逊发货': 'N/A',
                        '备注': '',
                    }
                    if product.invalid:
                        product_dict['备注'] = '异常'
                    elif product.availability:
                        product_dict['价格'] = product.price
                        product_dict['运费'] = product.shipping_cost
                        product_dict['是否二手'] = '是' if product.used else '否'
                        product_dict['从亚马逊发货'] = '是' if product.shipping_from_amazon else '否'
                    products_data.append(product_dict)

            # 创建DataFrame并导出到CSV
            df = pd.DataFrame(products_data)
            df.to_csv(self.filename, index=False, encoding='utf-8-sig')

            success_msg = f"成功导出 {len(products_data)} 条产品数据到 {self.filename}"
            if self.callback:
                self.callback(True, success_msg, self.filename)

        except Exception as e:
            error_msg = f"导出数据时出错: {str(e)}"
            if self.callback:
                self.callback(False, error_msg)