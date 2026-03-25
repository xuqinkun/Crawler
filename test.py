from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # 自带铬内核，无需驱动
    page = browser.new_page()
    page.goto("https://www.baidu.com")
    print(page.content())
    browser.close()
