import os
import sys
MODO_TEST = "--test" in sys.argv
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
import requests
from dotenv import load_dotenv
from config_4h import PARAMS_4H
from datetime import datetime, timezone

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

def analizar_4h(simbolo):
    exchange = ccxt.bitvavo()
    velas = exchange.fetch_ohlcv(simbolo, timeframe="4h", limit=500)
    df = pd.DataFrame(velas, columns=["timestamp","open","high","low","close","volume"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    precios = df["close"]
    ticker = exchange.fetch_ticker(simbolo)
    precio_actual = ticker["last"]
    mm7  = precios.rolling(7).mean()
    mm20 = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1
    delta     = precios.diff()
    ganancias = delta.clip(lower=0).rolling(14).mean()
    perdidas  = (-delta).clip(lower=0).rolling(14).mean()
    rsi       = 100 - (100 / (1 + ganancias / perdidas))
    rsi_actual = rsi.iloc[-1]
    from scipy import stats as st
    pct_mm20 = st.percentileofscore(dist_mm20.dropna(), (precio_actual - mm20.iloc[-1]) / mm20.iloc[-1])
    pct_mm7  = st.percentileofscore(dist_mm7.dropna(),  (precio_actual - mm7.iloc[-1])  / mm7.iloc[-1])
    pct_vol  = st.percentileofscore(vol_30.dropna(),    vol_30.iloc[-1])
    pct_mom  = st.percentileofscore(momentum_14.dropna(), momentum_14.iloc[-1])
    puntos = 0
    if pct_mm20 < 20:   puntos += 3
    elif pct_mm20 < 40: puntos += 1
    elif pct_mm20 > 80: puntos -= 3
    elif pct_mm20 > 60: puntos -= 1
    if pct_mm7 < 20:    puntos += 2
    elif pct_mm7 < 40:  puntos += 1
    elif pct_mm7 > 80:  puntos -= 2
    elif pct_mm7 > 60:  puntos -= 1
    if pct_mom < 20:    puntos += 2
    elif pct_mom < 40:  puntos += 1
    elif pct_mom > 80:  puntos -= 2
    elif pct_mom > 60:  puntos -= 1
    if pct_vol > 80:    puntos -= 2
    elif pct_vol > 60:  puntos -= 1
    elif pct_vol < 20:  puntos += 1
    puntos = max(-10, min(10, puntos))
    params = PARAMS_4H[simbolo]
    umbral = params["umbral"]
    kelly  = params["kelly"]
    if puntos >= umbral and kelly > 0:
        decision = "COMPRAR"
        sizing = f"{min(kelly/4/100, 0.10)*100:.1f}% del capital"
    else:
        decision = "MANTENER"
        sizing = "—"
    return {
        "precio":    precio_actual,
        "decision":  decision,
        "puntos":    puntos,
        "score":     puntos,
        "kelly":     kelly,
        "umbral":    umbral,
        "rsi":       rsi_actual,
        "sizing":    sizing,
        "stop":      params["stop"] * 100,
        "take":      params["take"] * 100,
        "horizonte": params["horizonte_velas"] * 4,
    }

ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
print(f"Monitor 4h — {ahora}")

for simbolo in PARAMS_4H:
    d = analizar_4h(simbolo)
    print(f"  -> {simbolo}: {d['decision']} | Score: {d['puntos']}/{d['umbral']} | RSI: {d['rsi']:.1f}")
    if d["decision"] == "COMPRAR":
        stop_precio = round(d["precio"] * (1 - d["stop"]/100), 4)
        take_precio = round(d["precio"] * (1 + d["take"]/100), 4)
        msg = f"<b>SIGNAL 4H — {simbolo}</b>\n\nPrecio: <b>€{d['precio']:.4f}</b>\nScore: <b>{d['puntos']}/{d['umbral']}</b>\nRSI: <b>{d['rsi']:.1f}</b>\n\nStop: €{stop_precio} ({d['stop']:.0f}%)\nTake: €{take_precio} ({d['take']:.0f}%)\nHorizonte: {d['horizonte']}h\nKelly/4: {d['sizing']}\n\n<b>COMPRAR</b>"
        enviar_telegram(msg)
        print(f"     Telegram enviado")
        # Validar que no hay posicion abierta para este activo
        from validador_posiciones import tiene_posicion_abierta
        if tiene_posicion_abierta(simbolo):
            print(f"     ⚠️ {simbolo} ya tiene posicion abierta — SKIP")
            enviar_telegram(f"⚠️ {simbolo} ya tiene posicion abierta — no se ejecuta nueva orden")
        elif MODO_TEST:
            print(f"     [TEST] COMPRA simulada — no se ejecuta orden real")
        else:
            from ejecutor import ejecutar_compra
            ejecutar_compra(simbolo, d)

print("Monitor 4h completado")

# ── GUARDAR RESULTADOS EN JSON ───────────────────────────────────
import json
resultados_4h = {}
for simbolo in PARAMS_4H:
    resultados_4h[simbolo] = analizar_4h(simbolo)
with open('/root/proyectos-quant/monitor_4h_resultados.json', 'w') as f:
    json.dump({k: {kk: float(vv) if hasattr(vv, 'item') else vv for kk, vv in v.items()} for k, v in resultados_4h.items()}, f)
