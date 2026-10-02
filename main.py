import os
import json
from datetime import datetime, timedelta
import requests
import pandas as pd

# FinMind API Token (可選，有 Token 請求限額較高)
FINMIND_TOKEN = os.getenv("FINMIND_API_TOKEN", "")

def fetch_finmind_data(dataset, stock_id, start_date):
    """通用 FinMind API 資料抓取"""
    url = f"https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("msg") == "success" and data.get("data"):
            return pd.DataFrame(data["data"])
    except Exception as e:
        print(f"Error fetching {dataset} for {stock_id}: {e}")
    return pd.DataFrame()

def get_taiex_and_pivot():
    """抓取加權指數並計算 Pivot 樞紐關卡與即時動態"""
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    df = fetch_finmind_data("TaiwanStockPrice", "TAIEX", start_date)
    
    if df.empty:
        # 備用預設值 (避免 API 異常時壞掉)
        return {
            "price": 23000.0, "change": 150.0, "change_pct": 0.65,
            "high": 23100.0, "low": 22850.0, "close_prev": 22850.0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pivot": {"p": 22983.3, "s1": 22866.7, "s2": 22733.3, "r1": 23116.7, "r2": 23233.3}
        }

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    high = float(latest['max'])
    low = float(latest['min'])
    close = float(latest['close'])
    prev_close = float(prev['close'])

    price_change = round(close - prev_close, 2)
    change_pct = round((price_change / prev_close) * 100, 2)

    # Standard Pivot Points 計算公式
    P = round((high + low + close) / 3, 1)
    R1 = round((2 * P) - low, 1)
    S1 = round((2 * P) - high, 1)
    R2 = round(P + (high - low), 1)
    S2 = round(P - (high - low), 1)

    return {
        "price": close,
        "change": price_change,
        "change_pct": change_pct,
        "high": high,
        "low": low,
        "close_prev": prev_close,
        "date": str(latest['date']),
        "pivot": {"p": P, "s1": S1, "s2": S2, "r1": R1, "r2": R2}
    }

def get_institutional_and_retail_oi():
    """抓取台指期三大法人未平倉與計算散戶多空比"""
    start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
    df = fetch_finmind_data("TaiwanFuturesInstitutionalInvestors", "TX", start_date)

    dates, foreign_oi, investment_trust_oi, retail_ratio = [], [], [], []

    if not df.empty:
        # 過濾多空淨口數
        df['Net_OI'] = df['long_open_interest'] - df['short_open_interest']
        unique_dates = sorted(df['date'].unique())[-5:] # 取近 5 個交易日

        for d in unique_dates:
            sub = df[df['date'] == d]
            f_oi = sub[sub['name'] == 'Foreign_Investor']['Net_OI'].sum() if not sub[sub['name'] == 'Foreign_Investor'].empty else 0
            it_oi = sub[sub['name'] == 'Investment_Trust']['Net_OI'].sum() if not sub[sub['name'] == 'Investment_Trust'].empty else 0
            
            # 簡化散戶多空比推算邏輯 (以三大法人反向推估)
            total_institutional = f_oi + it_oi
            r_ratio = round((-total_institutional / 10000) * 2.5, 2) # 範例比率計算

            dates.append(d[-5:]) # MM-DD
            foreign_oi.append(int(f_oi))
            investment_trust_oi.append(int(it_oi))
            retail_ratio.append(r_ratio)
    else:
        # 預設近 5 日範例數據
        dates = ["5天前", "4天前", "3天前", "2天前", "昨日"]
        foreign_oi = [-31000, -28000, -30000, -27000, -25000]
        investment_trust_oi = [11500, 12800, 13000, 12500, 13200]
        retail_ratio = [8.2, 5.1, 11.5, 3.8, -2.5]

    return {
        "dates": dates,
        "foreign_oi": foreign_oi,
        "investment_trust_oi": investment_trust_oi,
        "retail_ratio": retail_ratio
    }

def get_vpvr_data():
    """計算近 30 日量價累積分佈圖 (VPVR)"""
    start_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
    df = fetch_finmind_data("TaiwanStockPrice", "TAIEX", start_date)

    if not df.empty and len(df) >= 10:
        # 分組區間價格 (每 100 點為一階)
        min_p = int(df['min'].min() // 100 * 100)
        max_p = int(df['max'].max() // 100 * 100)
        
        # 以收盤價與成交張數做簡易 Volume Profile 累積
        prices = list(range(min_p, max_p + 100, 100))[-7:] # 取 7 個主要區間
        volumes = [int((df[df['close'].between(p, p+99)]['Trading_Volume'].sum()) / 1000) for p in prices]
        
        # 找出 POC (Volume 最高區間)
        max_vol_idx = volumes.index(max(volumes)) if volumes and max(volumes) > 0 else 0
        poc_price = prices[max_vol_idx]

        price_labels = [f"{p} (POC)" if p == poc_price else str(p) for p in prices]
    else:
        price_labels = ["23,200", "23,100", "23,000 (POC)", "22,900", "22,800", "22,700", "22,600"]
        volumes = [12500, 24800, 68000, 44800, 31000, 18000, 9500]
        poc_price = 23000

    return {
        "prices": price_labels,
        "volumes": volumes,
        "poc": poc_price
    }

def main():
    print("Fetching market data...")
    taiex = get_taiex_and_pivot()
    chips = get_institutional_and_retail_oi()
    vpvr = get_vpvr_data()

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "taiex": taiex,
        "chips": chips,
        "vpvr": vpvr
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print("data.json successfully generated!")

if __name__ == "__main__":
    main()
