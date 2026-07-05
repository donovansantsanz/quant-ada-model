import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from config_4h import PARAMS_4H

exchange = ccxt.bitvavo()

def calcular_score(df, idx):
    precios = df['close']
    mm7  = precios.rolling(7).mean()
    mm20 = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1

    hist_mm20 = dist_mm20.iloc[:idx].dropna()
    hist_mm7  = dist_mm7.iloc[:idx].dropna()
    hist_vol  = vol_30.iloc[:idx].dropna()
    hist_mom  = momentum_14.iloc[:idx].dropna()

    if len(hist_mm20) < 30:
        return None

    pct_mm20 = stats.percentileofscore(hist_mm20, dist_mm20.iloc[idx])
    pct_mm7  = stats.percentileofscore(hist_mm7,  dist_mm7.iloc[idx])
    pct_vol  = stats.percentileofscore(hist_vol,  vol_30.iloc[idx])
    pct_mom  = stats.percentileofscore(hist_mom,  momentum_14.iloc[idx])

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

    return max(-10, min(10, puntos))

def walk_forward(simbolo, params):
    velas = exchange.fetch_ohlcv(simbolo, timeframe='4h', limit=500)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    umbral   = params['umbral']
    horizonte = params['horizonte_velas']
    split    = int(len(df) * 0.7)

    resultados = {'TRAIN': [], 'TEST': []}

    for i in range(50, len(df) - horizonte):
        score = calcular_score(df, i)
        if score is None:
            continue
        if score >= umbral:
            ret = (df['close'].iloc[i + horizonte] - df['close'].iloc[i]) / df['close'].iloc[i]
            fase = 'TRAIN' if i < split else 'TEST'
            resultados[fase].append(ret)

    print(f"\n{'─'*60}")
    print(f"  {simbolo}")
    for fase, ops in resultados.items():
        if ops:
            sr = np.mean(ops) / np.std(ops) * np.sqrt(len(ops)) if np.std(ops) > 0 else 0
            wr = sum(1 for r in ops if r > 0) / len(ops) * 100
            print(f"  {fase}: Sharpe {sr:.2f} | Win rate {wr:.1f}% | {len(ops)} ops")
        else:
            print(f"  {fase}: Sin operaciones")

print("=" * 60)
print("  WALK-FORWARD 4H — Lógica percentiles")
print("=" * 60)

for simbolo, params in PARAMS_4H.items():
    walk_forward(simbolo, params)

print(f"\n{'='*60}")
print("  Walk-forward 4h completado")
print("=" * 60)
