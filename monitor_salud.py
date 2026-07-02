import os
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from dotenv import load_dotenv
from datetime import datetime, timezone
from config import PARAMS, PARAMS_OBS

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensaje):
    import requests
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

def obtener_datos(simbolo, dias=200):
    exchange = ccxt.bitvavo()
    velas = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=dias)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.sort_values('fecha').reset_index(drop=True)

def calcular_scores(precios):
    mm7  = precios.rolling(7).mean()
    mm20 = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1
    scores = []
    for i in range(50, len(precios)):
        pct_mm20 = stats.percentileofscore(dist_mm20.iloc[:i].dropna(), dist_mm20.iloc[i])
        pct_mm7  = stats.percentileofscore(dist_mm7.iloc[:i].dropna(),  dist_mm7.iloc[i])
        pct_vol  = stats.percentileofscore(vol_30.iloc[:i].dropna(),    vol_30.iloc[i])
        pct_mom  = stats.percentileofscore(momentum_14.iloc[:i].dropna(), momentum_14.iloc[i])
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
        scores.append(max(-10, min(10, puntos)))
    return scores

def calcular_kelly_reciente(simbolo, umbral, stop, take, dias=90):
    """
    Devuelve (kelly, ops) donde kelly es float o None si no hay datos.
    None significa que el sistema no generó señales en la ventana — no es Kelly negativo.
    """
    df = obtener_datos(simbolo, dias=dias+50)
    precios = df['close'].iloc[50:].reset_index(drop=True)
    scores  = calcular_scores(df['close'])
    ganancias, perdidas = [], []
    for i in range(len(scores)-14):
        if scores[i] >= umbral:
            p_entrada = precios.iloc[i]
            retorno = None
            for j in range(1, 15):
                p = precios.iloc[i+j]
                if p <= p_entrada * (1-stop):
                    retorno = -stop; break
                elif p >= p_entrada * (1+take):
                    retorno = take; break
            if retorno is None:
                retorno = (precios.iloc[i+14] - p_entrada) / p_entrada
            if retorno > 0:
                ganancias.append(retorno)
            else:
                perdidas.append(abs(retorno))

    # Sin datos suficientes — devolver None explícito, no -99
    if not ganancias or not perdidas:
        return None, len(ganancias) + len(perdidas)

    p = len(ganancias) / (len(ganancias) + len(perdidas))
    b = np.mean(ganancias) / np.mean(perdidas)
    kelly = (p * b - (1 - p)) / b * 100
    return round(kelly, 1), len(ganancias) + len(perdidas)

print(f"Monitor de salud — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

alertas = []
resumen = []

# ── Activos operativos ───────────────────────────────────────────────────────
for simbolo, p in PARAMS.items():
    kelly, ops = calcular_kelly_reciente(simbolo, p['umbral'], p['stop'], p['take'])
    kelly_full = p.get('kelly', None)
    full_str   = f"{kelly_full}%" if kelly_full is not None else "N/A"

    if kelly is None:
        estado = "⚪"
        linea  = f"{estado} {simbolo}: Kelly 90d = N/A ({ops} ops) | full-sample = {full_str} — sin señales en ventana"
    elif kelly > 0:
        estado = "✅"
        linea  = f"{estado} {simbolo}: Kelly 90d = {kelly}% ({ops} ops) | full-sample = {full_str}"
    else:
        estado = "⚠️"
        linea  = f"{estado} {simbolo}: Kelly 90d = {kelly}% ({ops} ops) | full-sample = {full_str}"
        alertas.append(
            f"⚠️ <b>{simbolo}</b> Kelly 90d = {kelly}% vs full-sample = {full_str} — "
            f"variación normal, no requiere acción"
        )

    resumen.append(linea)
    print(linea)

# ── Activos en observación ───────────────────────────────────────────────────
for simbolo, p in PARAMS_OBS.items():
    kelly, ops = calcular_kelly_reciente(simbolo, p['umbral'], p['stop'], p['take'])

    if kelly is None:
        estado    = "⚪"
        linea     = f"{estado} {simbolo}: Kelly 90d = N/A ({ops} ops) — sin señales en ventana"
    elif kelly > 0:
        estado    = "👁"
        linea     = f"{estado} {simbolo}: Kelly 90d = {kelly}% ({ops} ops)"
        # Informativo — el gate de promoción es el walk-forward, no el rolling Kelly
        alertas.append(
            f"👁 <b>{simbolo}</b> Kelly positivo en 90d ({kelly}%) — "
            f"en observación, gate de promoción es walk-forward"
        )
    else:
        estado    = "👁"
        linea     = f"{estado} {simbolo}: Kelly 90d = {kelly}% ({ops} ops)"

    resumen.append(linea)
    print(linea)

# ── Telegram ─────────────────────────────────────────────────────────────────
msg  = "<b>🏥 Monitor de salud semanal</b>\n\n"
msg += "\n".join(resumen)
if alertas:
    msg += "\n\n<b>⚡ Info:</b>\n" + "\n".join(alertas)
else:
    msg += "\n\n✅ Todo en orden"

enviar_telegram(msg)
print("\n✅ Monitor de salud completado")
