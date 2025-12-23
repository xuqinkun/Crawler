from dataclasses import dataclass
from datetime import time


@dataclass
class Product:
    """
    爬取的是  正常价格+运费，不能有二手，是否是亚马逊发货，有无库存，价格，品牌黑名单，ASIN黑名单，这是爬取到的数据用EXECL表格展示

    """
    product_id: str = None
    asin: str = None
    url: str = None
    title: str = None
    used: bool = None
    price: float = None
    shipping_cost: str = None
    black_list: bool = False
    shipping_from_amazon: bool = None
    availability: bool = False
    completed: bool = False
    owner: str = None
    created_at: time = None
    updated_at: time = None
    invalid: bool = False

@dataclass
class Device:
    device_name: str=None
    device_code: str=None
    secrete_key: str=None
    activated: bool=None
    expired: bool=None
    valid_days: int=None
    created_at: time=None
    activated_at: time=None
