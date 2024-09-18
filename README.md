# 甲甲大學模擬打卡系統

這是一個用來模擬打卡的系統，讓社員練習透過爬蟲及 LINE Bot 來打卡。

> [!WARNING]  
> 此系統頁面取自友校逢甲大學簽到刷卡系統，此系統與逢甲大學無任何關聯，僅供黑客社社員練習使用。

## Getting Started

因為我不會 ASP.NET，所以此系統使用 flask 搭配手刻 cookies 驗證來模擬 VIEWSTATE 邏輯。

```bash
# Install dependencies
pip install -r requirements.txt

# Edit courses.json
# You can get it from coursesearch's API
nano server/courses.json

# Run server
uvicorn server:app
```

## Usage

### 學生

系統啟動後，可以透過`/D(.*)/`(D 開頭的帳號)來登入，密碼皆為`password`。

登入後隨系統指示，掃描 QR Code 即可完成打卡。

`main.py`為一個簡單的 LINE Bot，傳送圖片給它即可完成打卡。

### 老師

可以透過`/qrcode`開啟 QR Code 頁面供學生掃描。

詳細狀態可以透過`/debug`查看。
