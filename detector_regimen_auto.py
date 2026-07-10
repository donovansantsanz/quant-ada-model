import pandas as pd
import numpy as np
import json
import os
import ccxt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))

datos_dir = os.path.expanduser('~/proyectos-quant/datos')
os.makedirs(datos_dir, exist_ok=True)

activos = ['ADA/EUR', 'SOL/EUR', 'ETH/EUR', 'BNB/EUR', 'BTC/EUR']

# ── DESCARGAR DATOS FRESCOS ──────────────────────────────────────
bitvavo = ccxt.bitvavo({
    'apiKey': os.getenv("BITVAVO_API_KEY"),
    'secret': os.getenv("BITVAVO_API_SECRET"),
    'enableRateLimit': True,
    'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
})

hace_90d = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

for par in activos:
    try:
        ohlcv = bitvavo.fetch_ohlcv(par, '1d', since=hace_90d, limit=300)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['asset'] = par.split('/')[0]
        filename = os.path.join(datos_dir, f"{par.replace('/', '_')}_90d.csv")
        df.to_csv(filename, index=False)
    except Exception as e:
        print(f"Error descargando {par}: {e}")

# ── ANALIZAR RÉGIMEN ─────────────────────────────────────────────
def calcular_indicadores(df):
    df = df.copy()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma20_slope'] = df['ma20'].diff()
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['sma20'] + (df['std20'] * 2)
    df['bb_lower'] = df['sma20'] - (df['std20'] * 2)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(window=20).std()
    return df

regimen_data = {
    'timestamp': datetime.now().isoformat(),
    'activos': {}
}

for par in activos:
    filename = os.path.join(datos_dir, f"{par.replace('/', '_')}_90d.csv")
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    df = calcular_indicadores(df)

    ultimo = df.iloc[-1]
    rsi_actual = float(ultimo['rsi'])
    ma20_slope = float(ultimo['ma20_slope'])
    precio = float(ultimo['close'])
    ma20 = float(ultimo['ma20'])
    volatility = float(ultimo['volatility'])

    if rsi_actual < 30:
        rsi_regime = "OVERSOLD"
    elif rsi_actual > 70:
        rsi_regime = "OVERBOUGHT"
    else:
        rsi_regime = "NEUTRAL"

    if ma20_slope > 0.01:
        ma_regime = "TRENDING_UP"
    elif ma20_slope < -0.01:
        ma_regime = "TRENDING_DOWN"
    else:
        ma_regime = "FLAT"

    if precio > ma20:
        price_position = "ARRIBA_MA20"
    else:
        price_position = "ABAJO_MA20"

    if precio > ma20 and rsi_actual > 50 and ma_regime == "TRENDING_UP":
        final_regime = "ADVERSO"
    elif precio < ma20 and rsi_actual < 50:
        final_regime = "FAVORABLE"
    else:
        final_regime = "MIXTO"

    regimen_data['activos'][par] = {
        'precio': precio,
        'ma20': ma20,
        'rsi': rsi_actual,
        'ma20_slope': ma20_slope,
        'volatility': volatility,
        'rsi_regime': rsi_regime,
        'ma_regime': ma_regime,
        'price_position': price_position,
        'final_regime': final_regime
    }

output_file = os.path.expanduser('~/proyectos-quant/regimen_actual.json')
with open(output_file, 'w') as f:
    json.dump(regimen_data, f, indent=2)

print(f"[{datetime.now().isoformat()}] Regimen actualizado")
for par, data in regimen_data['activos'].items():
    print(f"  {par}: {data['final_regime']} | RSI: {data['rsi']:.1f} | MA20 slope: {data['ma20_slope']:.4f}")

# ── ALERTA TELEGRAM ──────────────────────────────────────────────
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

emojis = {'ADVERSO': '🔴', 'MIXTO': '🟡', 'FAVORABLE': '🟢'}

lineas = ["<b>📊 Régimen diario</b>\n"]
for par, data in regimen_data['activos'].items():
    emoji = emojis.get(data['final_regime'], '⚪')
    lineas.append(f"{emoji} {par}: <b>{data['final_regime']}</b> | RSI: {data['rsi']:.1f}")

msg = "\n".join(lineas)

try:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
except Exception as e:
    print(f"Error Telegram: {e}")
