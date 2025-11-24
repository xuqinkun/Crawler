from dataclasses import dataclass
from datetime import time


@dataclass
class Product():
    """
    爬取的是  正常价格+运费，不能有二手，是否是亚马逊发货，有无库存，价格，品牌黑名单，ASIN黑名单，这是爬取到的数据用EXECL表格展示

    """
    product_id: int = 0
    asin: str = ''
    url: str = ''
    used: bool = None
    price: float = None
    shipping_cost: str = None
    black_list: bool = False
    shipping_from_amazon: bool = None
    availability: bool = False
    completed: bool = False
    owner: str = ''
    created_at: time = None
    updated_at: time = None
