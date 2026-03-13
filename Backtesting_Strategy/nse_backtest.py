"""
NSE F&O Historical Backtest — 5 Scan Rules
==========================================
LOGIC:
- Scan conditions are checked on DAILY candles (as designed)
- 5-min candles are used only to find the exact trigger TIME
- For each day a stock passes a scan, we find the first 5-min
  candle where the key price level was crossed → that is the
  trigger time logged in the CSV

SETUP:
    pip install pyotp pandas numpy requests pytz

"""

import requests
import pyotp
import pandas as pd
import numpy as np
import time
import pytz
import json
import csv
import os
from datetime import datetime, timedelta
from io import StringIO

# ─────────────────────────────────────────────
#  YOUR CREDENTIALS
# ─────────────────────────────────────────────
API_KEY       = ""         # From AngelOne app dashboard
CLIENT_ID     = ""       # Your AngelOne login ID  e.g. A12345678
PIN           = ""             # Your 4-digit trading PIN
TOTP_SECRET   = ""     # Alphanumeric secret from authenticator setup
# ─────────────────────────────────────────────

#You can change the date here according to which data you are looking for
FROM_DATE  = "2026-01-01 09:15"
TO_DATE    = "2026-03-13 15:30"

'''Comment out this line - Change the folder location (Folder_Direction)
OUTPUT_CSV = r"Folder_Direction\nse_scan_results.csv"
'''


FNO_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "KOTAKBANK",
    "SBIN", "AXISBANK", "BAJFINANCE", "LT", "WIPRO", "HCLTECH",
    "MARUTI", "TATAMOTORS", "ADANIENT", "ADANIPORTS", "BAJAJFINSV",
    "BHARTIARTL", "BPCL", "COALINDIA", "DIVISLAB", "DRREDDY",
    "EICHERMOT", "GRASIM", "HDFCLIFE", "HEROMOTOCO", "HINDALCO",
    "HINDUNILVR", "IOC", "JSWSTEEL", "M&M", "NESTLEIND", "NTPC",
    "ONGC", "POWERGRID", "SUNPHARMA", "TATACONSUM", "TATASTEEL",
    "TECHM", "TITAN", "ULTRACEMCO", "UPL", "VEDL", "ZOMATO",
    "IRCTC", "DIXON", "POLYCAB", "TRENT", "HAVELLS", "CHOLAFIN",
    "SHRIRAMFIN", "PFC", "RECLTD", "CANBK", "FEDERALBNK",
    "INDHOTEL", "INDIGO", "PERSISTENT", "MPHASIS", "OFSS",
    "APOLLOHOSP", "ASIANPAINT", "AUROPHARMA", "BANDHANBNK",
    "BATAINDIA", "BEL", "BHEL", "BIOCON", "BOSCHLTD", "CIPLA",
    "DABUR", "DEEPAKNTR", "GLENMARK", "GODREJCP", "GODREJPROP",
    "GRANULES", "IEX", "IGL", "IPCALAB", "JUBLFOOD", "LICHSGFIN",
    "LUPIN", "MANAPPURAM", "MFSL", "MRF", "MUTHOOTFIN",
    "NAVINFLUOR", "OBEROIRLTY", "PIDILITIND", "RAMCOCEM",
    "SAIL", "SIEMENS", "SRF", "TORNTPHARM", "TVSMOTOR", "VOLTAS",
    "AARTIIND", "ACC", "ALKEM", "BALKRISIND", "CUMMINSIND",
    "GSPL", "HINDPETRO", "INDUSTOWER", "JKCEMENT",
    "NYKAA", "PAYTM", "ZEEL", "ABFRL", "DELHIVERY", "ICICIPRULI"
]


# =============================================================
#  LOGIN
# =============================================================

def login():
    print("\n[1/4] Logging in to AngelOne...")
    totp = pyotp.TOTP(TOTP_SECRET).now()
    url  = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
    headers = {
        "Content-Type":    "application/json",
        "Accept":          "application/json",
        "X-UserType":      "USER",
        "X-SourceID":      "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP":"127.0.0.1",
        "X-MACAddress":    "00:00:00:00:00:00",
        "X-PrivateKey":    API_KEY
    }
    payload = {"clientcode": CLIENT_ID, "password": PIN, "totp": totp}
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    if not data.get("status"):
        raise Exception(f"Login failed: {data.get('message', 'Unknown error')}")
    print("   ✓ Logged in successfully")
    return data["data"]["jwtToken"]


# =============================================================
#  SCRIP MASTER
# =============================================================

def get_symbol_token_map():
    print("\n[2/4] Downloading scrip master...")
    urls = [
        "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json",
        "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
    ]
    scrips = None
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and resp.text.strip().startswith("["):
                scrips = resp.json()
                break
        except:
            continue
    if not scrips:
        print("   ❌ Could not download scrip master")
        return {}
    token_map = {}
    for s in scrips:
        if s.get("exch_seg") != "NSE":
            continue
        sym_field = s.get("symbol", "")
        name      = s.get("name", "").strip().upper()
        tok       = s.get("token", "")
        if not tok:
            continue
        if sym_field.endswith("-EQ"):
            sym = sym_field.replace("-EQ", "").strip().upper()
            token_map[sym] = tok
        elif name and name not in token_map:
            token_map[name] = tok
    print(f"   ✓ Loaded {len(token_map)} NSE EQ symbols")
    sample = list(token_map.items())[:5]
    print(f"   Sample tokens: {sample}")
    return token_map


# =============================================================
#  FETCH CANDLES
# =============================================================

def fetch_candles(token, auth_token, symbol, from_date, to_date, interval):
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData"
    headers = {
        "Content-Type":    "application/json",
        "Accept":          "application/json",
        "X-PrivateKey":    API_KEY,
        "X-UserType":      "USER",
        "X-SourceID":      "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP":"127.0.0.1",
        "X-MACAddress":    "00:00:00:00:00:00",
        "Authorization":   f"Bearer {auth_token}"
    }
    payload = {
        "exchange":    "NSE",
        "symboltoken": token,
        "interval":    interval,
        "fromdate":    from_date,
        "todate":      to_date
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        data = resp.json()
        if data.get("status") and data.get("data"):
            df = pd.DataFrame(data["data"],
                              columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(
                df["timestamp"], utc=True).dt.tz_convert("Asia/Kolkata")
            df = df.sort_values("timestamp").reset_index(drop=True)
            for col in ["open","high","low","close","volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
    except Exception as e:
        print(f"      ⚠ Error fetching {symbol}: {e}")
    return pd.DataFrame()



# =============================================================
#  Your Strategy
# =============================================================

'You can put your code here which you created usign Claude for your stretegy' 




# =============================================================
#  FIND TRIGGER TIME FROM 5-MIN CANDLES
#  Given a day where scan fired, find the first 5-min candle
#  where the key price level (prev_high) was crossed
# =============================================================

def find_trigger_time(df_5min_day, prev_high, scan_num):
    """
    Walk through 5-min candles for that day.
    Return the timestamp of the first candle where
    close crossed above prev_high (the key breakout level).
    If none found, return market open time (09:15).
    """
    for _, candle in df_5min_day.iterrows():
        if candle["close"] > prev_high:
            ts = str(candle["timestamp"])[:19].replace("T", " ")
            return ts
    # Fallback — return first candle time of that day
    ts = str(df_5min_day.iloc[0]["timestamp"])[:19].replace("T", " ")
    return ts


# =============================================================
#  MAIN
# =============================================================

# Create the main function and call that strategy here