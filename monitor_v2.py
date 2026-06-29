import os
import sys
MODO_TEST = "--test" in sys.argv
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
import requests
from dotenv import load_dotenv

load_dotenv()
from config import PARAMS
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

# ── PARÁMETROS ÓPTIMOS POR ACTIVO ────────────────────────────────

# ── FILTRO BTC ───────────────────────────────────────────────────
def filtro_btc():
    exchange   = ccxt.binance()
    velas      = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', limit=10)
    df         = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    precios    = df['close']
    mom_7      = precios.iloc[-1] / precios.iloc[-8] - 1
    mom_3      = precios.iloc[-1] / precios.iloc[-4] - 1

    if mom_3 < -0.05:
        return False, f"BTC bajando {mom_3*100:.1f}% en 3d — señales bloqueadas"
    return True, f"BTC neutral/alcista (7d: {mom_7*100:.1f}%, 3d: {mom_3*100:.1f}%)"

# ── ANÁLISIS POR ACTIVO ──────────────────────────────────────────
def analizar(simbolo, btc_ok):
    exchange = ccxt.binance()
    velas    = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=365)
    df       = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.sort_values('fecha').reset_index(drop=True)
    precios = df['close']

    ticker        = exchange.fetch_ticker(simbolo)
    precio_actual = ticker['last']

    mm7         = precios.rolling(7).mean()
    mm20        = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1

    delta      = precios.diff()
    ganancias  = delta.clip(lower=0).rolling(14).mean()
    perdidas   = (-delta).clip(lower=0).rolling(14).mean()
    rsi        = 100 - (100 / (1 + ganancias / perdidas))
    rsi_actual = rsi.iloc[-1]

    pct_dist_mm20   = stats.percentileofscore(dist_mm20.dropna(), (precio_actual - mm20.iloc[-1]) / mm20.iloc[-1])
    pct_dist_mm7    = stats.percentileofscore(dist_mm7.dropna(),  (precio_actual - mm7.iloc[-1])  / mm7.iloc[-1])
    pct_vol_30      = stats.percentileofscore(vol_30.dropna(),     vol_30.iloc[-1])
    pct_momentum_14 = stats.percentileofscore(momentum_14.dropna(), momentum_14.iloc[-1])

    puntos = 0
    if pct_dist_mm20 < 20:    puntos += 3
    elif pct_dist_mm20 < 40:  puntos += 1
    elif pct_dist_mm20 > 80:  puntos -= 3
    elif pct_dist_mm20 > 60:  puntos -= 1

    if pct_dist_mm7 < 20:     puntos += 2
    elif pct_dist_mm7 < 40:   puntos += 1
    elif pct_dist_mm7 > 80:   puntos -= 2
    elif pct_dist_mm7 > 60:   puntos -= 1

    if pct_momentum_14 < 20:   puntos += 2
    elif pct_momentum_14 < 40: puntos += 1
    elif pct_momentum_14 > 80: puntos -= 2
    elif pct_momentum_14 > 60: puntos -= 1

    if pct_vol_30 > 80:        puntos -= 2
    elif pct_vol_30 > 60:      puntos -= 1
    elif pct_vol_30 < 20:      puntos += 1

    puntos = max(-10, min(10, puntos))

    params = PARAMS[simbolo]
    umbral = params['umbral']
    kelly  = params['kelly']

    filtro_activo = params.get('filtro_btc', True)
    btc_pasa      = btc_ok if filtro_activo else True

    if puntos >= umbral:
        if btc_pasa and kelly > 0:
            decision = "COMPRAR"
            kelly_usar = min(kelly / 4 / 100, 0.10)
            sizing = f"{kelly_usar*100:.1f}% del capital"
        elif not btc_ok:
            decision = "BLOQUEADO"
            sizing   = "Filtro BTC activo"
        else:
            decision = "MANTENER"
            sizing   = "Kelly negativo"
    else:
        decision = "MANTENER"
        sizing   = "—"

    log_ret     = np.log(precios / precios.shift(1)).dropna()
    volatilidad = log_ret.std()
    drift       = log_ret.mean()
    sims        = np.zeros((30, 5000))
    sims[0]     = precio_actual
    for t in range(1, 30):
        z = np.random.standard_normal(5000)
        sims[t] = sims[t-1] * np.exp((drift - 0.5 * volatilidad**2) + volatilidad * z)
    prob_mc = np.mean(sims[-1] > precio_actual) * 100

    return {
        'precio':   precio_actual,
        'decision': decision,
        'puntos':   puntos,
        'umbral':   umbral,
        'rsi':      rsi_actual,
        'prob_mc':  prob_mc,
        'sizing':   sizing,
        'kelly':    kelly,
        'stop':     params['stop'] * 100,
        'take':     params['take'] * 100,
    }

# ── EJECUTAR ─────────────────────────────────────────────────────
from datetime import datetime
sep = "=" * 40
print(f"\n{sep}")
print(f"Ejecucion: {datetime.now(__import__("datetime").timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print(f"{sep}\n")
print("Analizando mercado...\n")

btc_ok, btc_msg = filtro_btc()
print(f"Filtro BTC: {btc_msg}\n")

resultados_monitor = {}
for simbolo in PARAMS:
    print(f"  → {simbolo}")
    d = analizar(simbolo, btc_ok)
    resultados_monitor[simbolo] = d

    if d['decision'] == "COMPRAR":
        emoji = "✅"
    elif d['decision'] == "BLOQUEADO":
        emoji = "🚫"
    else:
        emoji = "⏸"

    mensaje = f"""<b>📊 {simbolo} — Monitor V2</b>

💰 Precio: <b>${d['precio']:.4f}</b>
📈 RSI: <b>{d['rsi']:.1f}</b>
⚡ Score: <b>{d['puntos']}/10</b> (umbral: {d['umbral']})
🎲 MC prob subida: <b>{d['prob_mc']:.1f}%</b>

🛡 Stop loss: {d['stop']:.0f}%
🎯 Take profit: {d['take']:.0f}%
📐 Kelly: {d['kelly']:.1f}%
🔍 Filtro BTC: {'✅ OK' if btc_ok else '🚫 ACTIVO'}

<b>{emoji} DECISION: {d['decision']}</b>
💼 Sizing: {d['sizing']}"""

    enviar_telegram(mensaje)
    print(f"     {d['decision']} | Score: {d['puntos']} | RSI: {d['rsi']:.1f}")
    if d["decision"] == "COMPRAR":
        if MODO_TEST:
            print(f"     [TEST] COMPRA simulada — no se ejecuta orden real")
        else:
            from ejecutor import ejecutar_compra
            ejecutar_compra(simbolo, d)

import json
with open("/root/proyectos-quant/monitor_resultados.json", "w") as f:
    json.dump({k: {kk: float(vv) if hasattr(vv, "item") else vv for kk, vv in v.items()} for k, v in resultados_monitor.items()}, f)
print("\n✅ Monitor V2 completado")

# ── ACTIVOS EN OBSERVACIÓN ───────────────────────────────────────
from config import PARAMS_OBS

print("\nActivos en observación:")
btc_ok_obs, _ = filtro_btc()

obs_lineas = []
for simbolo, params in PARAMS_OBS.items():
    exchange = ccxt.binance()
    velas    = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=365)
    df       = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    precios  = df['close']

    mm7  = precios.rolling(7).mean()
    mm20 = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1

    from scipy import stats as st
    pct_mm20 = st.percentileofscore(dist_mm20.dropna(), dist_mm20.iloc[-1])
    pct_mm7  = st.percentileofscore(dist_mm7.dropna(),  dist_mm7.iloc[-1])
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

    ticker = exchange.fetch_ticker(simbolo)
    precio = ticker['last']
    umbral = params['umbral']
    cerca  = "⚡ CERCA" if puntos >= umbral - 1 else ""
    obs_lineas.append(f"  {simbolo}: score {puntos} / umbral {umbral} — ${precio:.2f} {cerca}")
    print(f"  {simbolo}: {puntos}/{umbral}")

obs_msg = "<b>👁 Activos en observación</b>\n\n" + "\n".join(obs_lineas)
enviar_telegram(obs_msg)
print("\n✅ Observación enviada")

# ── GUARDAR RESULTADOS EN JSON ───────────────────────────────────
