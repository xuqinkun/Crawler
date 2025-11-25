import re


class AmazonASINExtractor:
    """Amazon ASIN提取器"""

    # 综合正则模式，覆盖各种URL格式
    PATTERNS = [
        r'/gp/product/(B0[A-Z0-9]{8})',  # /gp/product/B0xxx
        r'/dp/(B0[A-Z0-9]{8})',  # /dp/B0xxx
        r'/product/(B0[A-Z0-9]{8})',  # /product/B0xxx
        r'/(B0[A-Z0-9]{8})(?=/|$|\?|&)',  # 直接ASIN
        r'/[^/]*(B0[A-Z0-9]{8})[^/]*/',  # 其他包含ASIN的路径
    ]

    @classmethod
    def extract_asin(cls, url):
        """从URL中提取ASIN"""
        for pattern in cls.PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                asin = match.group(1)
                # 验证ASIN格式
                if cls.is_valid_asin(asin):
                    return asin
        return None

    @staticmethod
    def is_valid_asin(asin):
        """验证ASIN格式"""
        return bool(re.match(r'^B0[A-Z0-9]{8}$', asin, re.IGNORECASE))

    @classmethod
    def extract_all_asins(cls, text):
        """从文本中提取所有ASIN"""
        # 匹配所有B0开头的10位ASIN
        asin_pattern = r'\b(B0[A-Z0-9]{8})\b'
        matches = re.findall(asin_pattern, text, re.IGNORECASE)

        # 过滤有效的ASIN
        valid_asins = [asin for asin in matches if cls.is_valid_asin(asin)]
        return valid_asins

