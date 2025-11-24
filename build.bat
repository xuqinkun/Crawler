@echo off
echo Building Amazon Crawler with crypto support...

REM 清理
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 打包命令
pyinstaller --onefile --windowed --name=AmazonCrawler --clean ^
    --hidden-import=email ^
    --hidden-import=urllib3 ^
    --hidden-import=requests ^
    --hidden-import=cryptography ^
    --hidden-import=ssl ^
    --hidden-import=numpy ^
    --hidden-import=hashlib ^
    --hidden-import=hmac ^
    --hidden-import=binascii ^
    --hidden-import=base64 ^
    --exclude-module=matplotlib ^
    --exclude-module=scipy ^
    --exclude-module=pytest ^
    --exclude-module=tkinter ^
    app.py

echo Build completed!
explore dist

pause