from io import BytesIO

import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (ApiClient, Configuration, MessagingApi,
                                  MessagingApiBlob, ReplyMessageRequest,
                                  TextMessage)
from linebot.v3.webhooks import (ImageMessageContent, MessageEvent,
                                 TextMessageContent)
from PIL import Image
from pyzbar import pyzbar

app = Flask(__name__)
configuration = Configuration(access_token="YOUR_CHANNEL_ACCESS_TOKEN")
handler = WebhookHandler("YOUR_CHANNEL_SECRET")


@app.route("/")
def index():
    return "Hello World"


@app.post("/callback")
def callback():
    # 獲取簽章
    signature: str = request.headers["X-Line-Signature"]

    # 獲取請求內容
    body: str = request.get_data(as_text=True)
    print(body)

    # 處理事件
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 若請求內的簽章與計算結果不符則報錯
        return "Invalid signature.", 400

    return "OK"


# 處理文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    # 建立 ApiClient 實例
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 獲取使用者發送的訊息
        msg: str = event.message.text

        # 回覆原訊息
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=msg),
                ],
            )
        )

        return "OK"


# 接收圖片訊息
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event: MessageEvent):
    # 建立 ApiClient 實例
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        api_blob = MessagingApiBlob(api_client)

        # 獲取圖片內容
        image_content = api_blob.get_message_content(event.message.id)
        image = Image.open(BytesIO(image_content))

        # 解碼圖片中的 QR Code
        barcodes = pyzbar.decode(image)

        print(barcodes)
        if len(barcodes) > 0:
            code = barcodes[0].data.decode("utf-8")

            print("QR Code:", code)

            print(signin("D1234567", "password", code))


def get_viewstate(soup: BeautifulSoup):
    event_target = soup.select_one("#__EVENTTARGET")["value"]
    event_argument = soup.select_one("#__EVENTARGUMENT")["value"]
    viewstate = soup.select_one("#__VIEWSTATE")["value"]
    viewstate_generator = soup.select_one("#__VIEWSTATEGENERATOR")["value"]
    event_validation = soup.select_one("#__EVENTVALIDATION")["value"]

    return {
        "__EVENTTARGET": event_target,
        "__EVENTARGUMENT": event_argument,
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_generator,
        "__EVENTVALIDATION": event_validation,
    }


def signin(username: str, password: str, code: str):
    # ASP.NET 會驗證 session cookie, Session() 可以於多請求中共享 cookie
    session = requests.Session()

    # 先獲取 /login.aspx 頁面的 view state
    res = session.get("https://ccu.0xian.dev/clockin/login.aspx")
    soup = BeautifulSoup(res.text, "html.parser")
    data = get_viewstate(soup)

    # 加上登入用到的資料
    data["LoginLdap$UserName"] = username
    data["LoginLdap$Password"] = password
    data["LoginLdap$LoginButton"] = "登入"

    # 連同 view state 一起發送回去
    res = session.post("https://ccu.0xian.dev/clockin/login.aspx", data=data)

    # 登入成功會被導到 /Student.aspx
    if not res.url.endswith("/Student.aspx"):
        return "登入失敗"

    # 打卡
    res = session.get(f"https://ccu.0xian.dev/clockin/ClassClockin.aspx?param={code}")
    soup = BeautifulSoup(res.text, "html.parser")

    # 若 LabelNote 是空的則代表成功
    return soup.select_one("#LabelNote").text or "打卡成功"


if __name__ == "__main__":
    app.run("0.0.0.0", port=8080)
