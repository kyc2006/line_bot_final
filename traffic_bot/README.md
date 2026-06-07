# 台中交通小幫手 LINE Bot

台中交通小幫手是一個 Flask LINE Bot，串接 LINE Messaging API v3 與 TDX API，提供台中公車、YouBike、停車場與公車訂閱推播查詢。專案以 Render 部署為目標，保留輕量 Flask 架構，並把訊息呈現升級為正式產品感的 LINE Flex Message。

## 功能

- 主選單 Flex Message
- 公車即時到站查詢，支援自然語句如 `300`、`公車300`、`查詢300到站`、`幫我查 300 多久到`
- YouBike 站點查詢，支援 `YouBike 台中車站`、`ubike台中車站`、`腳踏車 台中車站`，並依站名與地址做模糊搜尋
- 停車場剩餘車位查詢，支援 `西屯停車場`、`台中車站停車場` 等地點或區域查詢；輸入 `查停車場` 會先顯示引導卡片
- 公車訂閱、取消訂閱、我的訂閱
- 每日公車訂閱推播
- 受保護的 internal daily push endpoint，可搭配 Render Cron Job
- `/test` 測試路由，可檢查訊息類型、alt text 與摘要

## 技術架構

```text
traffic_bot/
├── app.py
├── config.py
├── services/
│   ├── tdx_client.py
│   ├── bus_service.py
│   ├── bike_service.py
│   └── parking_service.py
├── flex/
│   ├── menu.py
│   ├── common.py
│   ├── bus.py
│   ├── bike.py
│   ├── parking.py
│   └── subscription.py
├── scripts/
│   └── setup_rich_menu.py
├── assets/
│   └── rich_menu.png
├── repositories/
│   └── subscription_repository.py
├── utils/
│   ├── line_message.py
│   └── time_format.py
└── tests/
    └── test_app.py
```

`app.py` 負責 Flask routes、LINE webhook 與訊息分派。TDX 查詢放在 `services/`，LINE Flex JSON 放在 `flex/`，共用元件集中在 `flex/common.py`，訂閱資料存取集中在 `repositories/`。Flex Message 只使用 TDX 或台中 OpenData 實際回傳欄位；若資料來源未提供欄位，畫面會直接隱藏該 row，不會硬填假資料或顯示佔位文字。

## 環境變數

請勿把任何真實 key 寫入程式碼或 commit 到 GitHub。Render 環境變數或本機 `.env` 需設定：

```env
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
TDX_CLIENT_ID=your_tdx_client_id
TDX_CLIENT_SECRET=your_tdx_client_secret
PUSH_TIMEZONE=Asia/Taipei
PUSH_HOUR=8
PUSH_MINUTE=0
ENABLE_DAILY_PUSH=true
INTERNAL_API_TOKEN=
TEST_TOKEN=
```

說明：

- `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`：LINE Developers 後台取得。
- `TDX_CLIENT_ID`、`TDX_CLIENT_SECRET`：TDX 會員中心取得。
- `ENABLE_DAILY_PUSH`：是否在 Flask web process 內啟動每日推播 thread。預設 `true`，保留既有部署行為。
- `INTERNAL_API_TOKEN`：保護 `/internal/push-daily` 的 token。若要使用 Render Cron Job，請設定此值。
- `TEST_TOKEN`：保護 `/test` 的 token。未設定時 `/test` 維持開放，方便既有測試流程。

## 本機執行

```bash
cd traffic_bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

預設網址：

```text
http://127.0.0.1:5050/
```

## LINE Webhook

部署完成後，請到 LINE Developers 後台設定：

```text
https://你的網域/callback
```

啟用 `Use webhook`，並關閉不需要的 Auto-reply，避免官方自動回覆與 Bot 回覆重疊。

## Rich Menu

專案提供 `scripts/setup_rich_menu.py` 產生 LINE Rich Menu 設定。預設是 dry run，只會輸出 JSON，不會修改 LINE 官方帳號。Rich Menu 圖片固定使用 `assets/rich_menu.png`；若檔案不存在，script 會用 Python 產生一張簡潔現代的 6 格 PNG。

```bash
cd traffic_bot
python scripts/setup_rich_menu.py
```

Rich Menu 採 6 格：

- 查公車
- 找 YouBike
- 查停車場
- 我的訂閱
- 服務狀態
- 使用說明

每格使用 LINE message action，送出的文字都能被 Bot dispatcher 處理：

```text
查公車
找 YouBike
查停車場
我的訂閱
服務狀態
使用說明
```

建立 Rich Menu 時，token 只從 `LINE_CHANNEL_ACCESS_TOKEN` 環境變數讀取，不會寫死在程式碼中：

```bash
cd traffic_bot
python scripts/setup_rich_menu.py --apply --set-default
```

若要使用自訂圖片，可以指定 `--image`：

```bash
python scripts/setup_rich_menu.py --apply --image ./assets/rich_menu.png --set-default
```

Rich Menu 版面為上排 `查公車`、`找 YouBike`、`查停車場`，下排 `我的訂閱`、`服務狀態`、`使用說明`。

## Render 部署

此專案保留 Render Blueprint 與手動部署流程。

Blueprint 使用根目錄的 `render.yaml`。手動建立 Web Service 時：

```bash
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --workers 1 --threads 2 --timeout 120
Root Directory: traffic_bot
```

注意事項：

- Render Free web service 會因閒置而休眠；休眠期間 web process 內的 daily push thread 不會執行。
- 目前訂閱資料仍使用 JSON 檔案保存，repository 已加入 lock、格式檢查與 atomic write，但 Render 本機檔案系統不適合長期保存資料。正式營運建議改用 PostgreSQL。
- 若改用 Render Cron Job 觸發推播，建議設定 `ENABLE_DAILY_PUSH=false`，再由 Cron 呼叫 `/internal/push-daily`。

## 每日推播

預設會依下列變數在 Flask web process 內啟動每日推播 thread：

```env
ENABLE_DAILY_PUSH=true
PUSH_TIMEZONE=Asia/Taipei
PUSH_HOUR=8
PUSH_MINUTE=0
```

更穩定的正式做法是使用 Render Cron Job 或外部排程呼叫：

```bash
curl -X POST https://你的-render-service.onrender.com/internal/push-daily \
  -H "Authorization: Bearer $INTERNAL_API_TOKEN"
```

若使用 Cron Job，請把 web service 的 `ENABLE_DAILY_PUSH` 設成 `false`，避免重複推播。

## /test 測試

`/test` 會回傳訊息類型、alt text 與摘要：

```text
/test?text=主選單
/test?text=查公車
/test?text=熱門路線
/test?text=使用說明
/test?text=hi
/test?text=300
/test?text=300公車
/test?text=公車300
/test?text=查300
/test?text=查詢300到站
/test?text=300多久到
/test?text=YouBike台中車站
/test?text=ubike台中車站
/test?text=腳踏車台中車站
/test?text=YouBike
/test?text=找YouBike
/test?text=附近 YouBike
/test?text=停車場
/test?text=查停車
/test?text=查停車場
/test?text=西屯停車場
/test?text=附近停車場
/test?text=重新整理
/test?text=重新查詢
/test?text=換個地點
/test?text=換個區域
/test?text=訂閱300
/test?text=我的訂閱
/test?text=取消訂閱300
/test?text=服務狀態
```

若設定 `TEST_TOKEN`，請帶上：

```text
/test?text=300&token=your_test_token
```

或使用 header：

```text
X-Test-Token: your_test_token
```

## 測試

```bash
cd traffic_bot
python -m unittest discover -s tests -v
```

測試會 mock TDX 查詢，避免測試時消耗外部 API。

## UI 與資料顯示原則

- 主選單使用 5 頁 carousel：首頁總覽、公車查詢、YouBike 查詢、停車場查詢、訂閱與服務。
- 使用說明使用 5 頁 carousel：如何查公車、如何查 YouBike、如何查停車場、如何訂閱公車、常見問題。
- 功能入口會先顯示引導卡片；例如輸入 `查公車` 會提示輸入 `300`、`307` 或 `300 往台中車站`。
- 按鈕採 message action，按下後會送出可被 Bot 辨識的文字。
- 停車場若 TDX 提供剩餘車位數，會以 `剩餘 42 格` 作為主要資訊。
- 若資料來源只提供燈號而沒有剩餘格數，Bot 不會把燈號假裝成剩餘數量；畫面會改顯示總車位、地址與狀態等實際有的資料。
- 缺失欄位不會顯示成 `未提供`、`None`、`N/A` 或 `OpenData 未提供資料`，而是直接隱藏該 row，讓卡片自動重新排版。
- 查無資料會回傳查無資料卡片，提示使用者換個地點、重新輸入或回主選單。

## 按鈕 action 對應

| 顯示文字 | 送出文字 | Bot 行為 |
| --- | --- | --- |
| 查公車 | `查公車` | 顯示公車查詢引導 |
| 找 YouBike | `找 YouBike` | 顯示 YouBike 查詢引導 |
| 查停車場 | `查停車場` | 顯示停車場查詢引導 |
| 熱門路線 | `熱門路線` | 顯示熱門公車路線 |
| 重新整理 | 公車路線，例如 `300` | 重新查詢該路線 |
| 訂閱路線 | `訂閱300` | 訂閱該路線 |
| 重新查詢 | 原查詢文字 | 重新查詢 YouBike 或停車場 |
| 換個地點 | `換個地點` | 顯示 YouBike 查詢引導 |
| 換個區域 | `換個區域` | 顯示停車場查詢引導 |
| 我的訂閱 | `我的訂閱` | 顯示訂閱清單 |
| 服務狀態 | `服務狀態` | 顯示 LINE Bot 與資料服務狀態 |
| 使用說明 | `使用說明` | 顯示多頁使用說明 |
| 主選單 | `主選單` | 回到主選單 carousel |

## 未來可擴充

- 將訂閱資料從 JSON repository 換成 PostgreSQL repository。
- 將每日推播完全改由 Render Cron Job 或 background worker 負責。
- 加入使用者常用站牌、常用停車區域與地理位置查詢。
- 加入 TDX API 快取，降低查詢延遲與 API 壓力。
- 加入觀測與告警，例如錯誤率、TDX timeout、推播成功率。
