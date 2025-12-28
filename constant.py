CACHE_DIR = '.cache'
DEFAULT_ENCODING = 'UTF-8'
VERIFY_PAGE = 'verify/code.htm'
ROOT = 'https://www.dianxiaomi.com'
LOGIN_PAGE = 'user/userLoginNew2.json'
PRODUCT_PAGE = 'api/smtProduct/pageList.json'
PRODUCT_DETAIL_PAGE = 'https://www.amazon.com/gp/product/ajax/twisterDimensionSlotsDefault'

DATETIME_PATTERN = '%Y-%m-%d %H:%M:%S'

amazon_cookies = {
        'csm-hit': 'adb:adblk_yes&t:1763970326341&tb:s-HT7FZ8V6Z70MNFKWQ1BG|1763970324959',
        'i18n-prefs':'USD',
        'lc-main':'en_US',
        'rx':'AQDTSB+aCLPtFMbDq7AJXwnCpag=@AbrZG2k=',
        'rxc':'AAAA',
        'session-id':'130-2679602-3573903',
        'session-id-time':'2082787201l',
        'session-token':'tQgfT23aSu4cd9dYE9ZZGFTdYstsgktMOnNDp5Cg6q7uZHXkc6old8+Sy63cvyJzHqDYT+ZQRYQXqfmGZPpLqH30CPj+gABHPpuGsQRgqoCJbvch5kdWoiANmZXxutRojIA7iCteF65NeZ4y1NQzqRMVWU3TWMTqGKWTtqPoq98v40+/KmB5NsgQjwFE9IeONXpv6z+fkNhJKnfusk1broVvlgkPS+D72xTM8LonMUaA0CMHnQ0hRGB+8yjRKBYjTA0mtdUTYp1S1y+f/BIPjGHdxsIPuL7SioElr5oZsMU+okeuo8GWv4Vtgn9a//DV3zVsBN3V8jfT0Ylbk9G1ofsUhvDJpcd2',
        'ubid-main':'134-4189356-4195409',
    }


product_payload = {
        'isDimensionSlotsAjax': '1',
        'asinList': '',
        'vs': '1',
        'asin': '',
        'productTypeDefinition': 'VACUUM_CLEANER',
        'productGroupId': 'beauty_display_on_website',
        'parentAsin': '',
        'isPrime': '0',
        'deviceOs': 'unrecognized',
        'landingAsin': '',
        'deviceType': 'web',
        'showFancyPrice': 'false',
        'twisterFlavor': 'twisterPlusDesktopConfigurator'
    }