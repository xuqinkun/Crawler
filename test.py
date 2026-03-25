from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.byhy.net/cdn2/files/selenium/stock1.html")
    print(page.title())
    page.locator('#kw').fill('通讯\n')
    page.locator('#go').click()
    # 打印所有搜索内容
    lcs = page.locator(".result-item").all()
    for lc in lcs:
        print(lc.inner_text())
    browser.close()