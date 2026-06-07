# 台中交通小幫手 Line Bot

使用 Python 3.12、Flask、line-bot-sdk、requests、gunicorn 開發，可部署到 Render。

## 功能

- 公車即時查詢：輸入 `300公車`
- YouBike 查詢：輸入 `YouBike 台中車站`
- 停車場查詢：輸入 `停車場`
- Flex Message 主選單：輸入 `主選單`
- 公車訂閱：輸入 `訂閱 300`
- 取消訂閱：輸入 `取消訂閱 300`
- 查看訂閱：輸入 `我的訂閱`

## 專案架構

```text
traffic_bot/
├── app.py
├── config.py
├── services/
│   ├── __init__.py
│   ├── tdx_client.py
│   ├── bus_service.py
│   ├── bike_service.py
│   └── parking_service.py
├── flex/
│   ├── __init__.py
│   └── menu.py
├── data/
├── requirements.txt
├── Procfile
├── runtime.txt
├── .env.example
└── README.md
```

## 本機執行

```bash
cd traffic_bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

編輯 `.env`：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
TDX_CLIENT_ID=你的_TDX_Client_Id
TDX_CLIENT_SECRET=你的_TDX_Client_Secret
PUSH_TIMEZONE=Asia/Taipei
PUSH_HOUR=8
PUSH_MINUTE=0
```

啟動：

```bash
python app.py
```

本機預設網址：

```text
http://127.0.0.1:5050/
```

Webhook URL：

```text
https://你的網域/callback
```

## Render 部署步驟

### 方法一：使用 Blueprint

1. 將 `traffic_bot` 推到 GitHub。
2. 到 Render 建立 `New Blueprint Instance`。
3. 選擇 GitHub repository。
4. Render 會讀取 `render.yaml` 並建立 Web Service。
5. 在 Environment Variables 補上以下四個 Secret：

```text
LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET
TDX_CLIENT_ID
TDX_CLIENT_SECRET
```

### 方法二：手動建立 Web Service

1. 將 `traffic_bot` 推到 GitHub。
2. 到 Render 建立 `New Web Service`。
3. 選擇 GitHub repository。
4. Root Directory 設為 `traffic_bot`。
5. Runtime 選 Python。
6. Build Command：

```bash
pip install -r requirements.txt
```

7. Start Command：

```bash
gunicorn app:app --workers 1 --threads 2 --timeout 120
```

8. 在 Render Environment Variables 設定：

```text
LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET
TDX_CLIENT_ID
TDX_CLIENT_SECRET
PUSH_TIMEZONE=Asia/Taipei
PUSH_HOUR=8
PUSH_MINUTE=0
```

9. 部署完成後，到 LINE Developers 後台設定 Webhook URL：

```text
https://你的-render-service.onrender.com/callback
```

10. 啟用 `Use webhook`，並關閉不需要的 Auto-reply。

## API 說明

- 公車：TDX `v2/Bus/EstimatedTimeOfArrival/City/Taichung/{RouteName}`
- YouBike：TDX `v2/Bike/Availability/City/Taichung`
- 停車場：優先使用 TDX `v1/Parking/OffStreet/ParkingAvailability/City/Taichung`，若未設定 TDX 金鑰則 fallback 至台中市路外剩餘車位 OpenData。

## 訂閱推播注意事項

訂閱資料會存放於 `data/subscriptions.json`。Render 免費方案可能會休眠，休眠期間無法準時推播；正式環境建議使用付費 Web Service 或外部排程服務固定喚醒。
