"""
Análisis retrospectivo — SOLO INVESTIGACIÓN, no toca el sistema.
Pregunta: en los suelos importantes del último año, ¿el sistema dio señal
cerca del suelo, o llegó tarde / no llegó?
"""
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from config import PARAMS

ex = ccxt.bitvavo()

def calcular_score_en(precios_hist):
    mm7  = precios_hist.rolling(7).mean()
    mm20 = precios_hist.rolling(20).mean()
    dist_mm20 = (precios_hist - mm20) / mm20
    dist_mm7  = (precios_hist - mm7) / mm7
    vol_30 = precios_hist.pct_change().rolling(30).std()
    mom_14 = precios_hist / precios_hist.shift(14) - 1
    i = len(precios_hist) - 1
    if i < 50:
        return None
    pct_mm20 = stats.percentileofscore(dist_mm20.iloc[:i].dropna(), dist_mm20.iloc[i])
    pct_mm7  = stats.percentileofscore(dist_mm7.iloc[:i].dropna(),  dist_mm7.iloc[i])
    pct_vol  = stats.percentileofscore(vol_30.iloc[:i].dropna(),    vol_30.iloc[i])
    pct_mom  = stats.percentileofscore(mom_14.iloc[:i].dropna(),    mom_14.iloc[i])
    p = 0
    if pct_mm20 < 20: p += 3
    elif pct_mm20 < 40: p += 1
    elif pct_mm20 > 80: p -= 3
    elif pct_mm20 > 60: p -= 1
    if pct_mm7 < 20: p += 2
    elif pct_mm7 < 40: p += 1
    elif pct_mm7 > 80: p -= 2
    elif pct_mm7 > 60: p -= 1
    if pct_mom < 20: p += 2
    elif pct_mom < 40: p += 1
    elif pct_mom > 80: p -= 2
    elif pct_mom > 60: p -= 1
    if pct_vol > 80: p -= 2
    elif pct_vol > 60: p -= 1
    elif pct_vol < 20: p += 1
    return max(-10, min(10, p))

print("="*70)
print("  ¿EL SISTEMA CAPTURA LOS SUELOS? — análisis retrospectivo")
print("="*70)

for simbolo in PARAMS:
    umbral = PARAMS[simbolo]['umbral']
    velas = ex.fetch_ohlcv(simbolo, timeframe='1d', limit=365)
    df = pd.DataFrame(velas, columns=['ts','o','h','l','close','v'])
    precios = df['close'].reset_index(drop=True)

    suelos = []
    W = 10
    for i in range(60, len(precios)-W):
        ventana = precios.iloc[i-W:i+W+1]
        if precios.iloc[i] == ventana.min():
            max_prev = precios.iloc[i-20:i].max()
            caida = (precios.iloc[i] - max_prev) / max_prev
            if caida <= -0.15:
                suelos.append(i)
    suelos_limpios = []
    for s in suelos:
        if not suelos_limpios or s - suelos_limpios[-1] > 15:
            suelos_limpios.append(s)

    print(f"\n  {simbolo}  (umbral compra = {umbral}) — {len(suelos_limpios)} suelos relevantes")
    if not suelos_limpios:
        print("    (sin caídas >15% seguidas de suelo en el año)")
        continue

    for s in suelos_limpios:
        mejor_score = -99
        dia_senal = None
        for d in range(max(0, s-3), min(len(precios), s+8)):
            sc = calcular_score_en(precios.iloc[:d+1])
            if sc is None:
                continue
            if sc > mejor_score:
                mejor_score = sc
            if sc >= umbral and dia_senal is None:
                dia_senal = d - s
        fecha = pd.to_datetime(df['ts'].iloc[s], unit='ms').strftime('%Y-%m-%d')
        if dia_senal is not None:
            estado = f"SEÑAL (día {dia_senal:+d} vs suelo)"
        else:
            estado = f"SIN señal (mejor score {mejor_score}, umbral {umbral})"
        print(f"    Suelo {fecha}: {estado}")
