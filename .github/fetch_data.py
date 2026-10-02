import os
import json
import requests
from datetime import datetime

DATA_FILE = "data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}

def fetch_taifex_data():
    """ 抓取期交所最新數據 """
    url = "https://www.taifex.com.tw/cht/3/futDailyMarketReport"
    today_str = datetime.now().strftime("%Y/%m/%d")
    payload = {
        "queryType": "2",
        "marketCode": "0",
        "dateRange": "",
        "queryDate": today_str,
        "MarketCode": "0",
        "commodity_id": "TX"
    }

    try:
        response = requests.post(url, data=payload, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'

        # 防護：非 200 或收到 404 / 改版訊息時不覆蓋
        if response.status_code != 200 or "<title>404</title>" in response.text or "網站已經改版" in response.text:
            print(f"[警告] 期交所伺服器回傳無效內容 (Status: {response.status_code})")
            return None

        return {
            "status": "success",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "TAIFEX",
            "raw_text": response.text[:300]
        }

    except Exception as e:
        print(f"[錯誤] 網絡或請求例外: {e}")
        return None

def main():
    print("=== GitHub Action: 開始抓取市場資料 ===")
    new_data = fetch_taifex_data()

    if not new_data:
        print("[資訊] 未能取得新數據，跳過寫入，保留現有 data.json")
        return

    # 讀取現有 data.json 並進行合併
    current_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            current_data = {}

    current_data.update(new_data)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=4)

    print(f"[成功] {DATA_FILE} 已更新於 {new_data.get('updated_at')}")

if __name__ == "__main__":
    main()
