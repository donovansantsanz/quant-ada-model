import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from itertools import product

exchange = ccxt.binance()

def obtener_datos_4h(simbolo, limit=500):
    velas = exchange.fetch_ohlcv(simbolo, timeframe='4h', limit=limit)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    return df.sort_values('timestamp').reset_index(drop=True)

def calcular_score_4h(df, idx):
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

def optimizar(simbolo):
    df = obtener_datos_4h(simbolo)
    split = int(len(df) * 0.7)
    df_train = df.iloc[:split].reset_index(drop=True)

    umbrales   = [3, 4, 5, 6, 7]
    horizontes = [3, 6, 12, 24]

    mejor_sharpe = -99
    mejor_params = None
    resultados = []

    for umbral, horizonte in product(umbrales, horizontes):
        ops = []
        for i in range(50, len(df_train) - horizonte):
            score = calcular_score_4h(df_train, i)
            if score is None:
                continue
            if score >= umbral:
                ret = (df_train['close'].iloc[i + horizonte] - df_train['close'].iloc[i]) / df_train['close'].iloc[i]
                ops.append(ret)

        if len(ops) >= 5:
            sr = np.mean(ops) / np.std(ops) * np.sqrt(len(ops)) if np.std(ops) > 0 else 0
            wr = sum(1 for r in ops if r > 0) / len(ops) * 100
            resultados.append((sr, umbral, horizonte, len(ops), wr))
            if sr > mejor_sharpe:
                mejor_sharpe = sr
                mejor_params = (umbral, horizonte, len(ops), wr)

    resultados.sort(reverse=True)

    print(f"\n{'─'*60}")
    print(f"  {simbolo} — Top 5 combinaciones (train)")
    print(f"  {'Umbral':<8} {'Horizonte':<12} {'Sharpe':<10} {'Win%':<8} {'Ops'}")
    print(f"  {'─'*55}")
    for sr, umb, hor, n, wr in resultados[:5]:
        print(f"  {umb:<8} {hor}v ({hor*4}h){'':<4} {sr:<10.2f} {wr:<8.1f} {n}")

    if mejor_params:
        print(f"\n  ✅ Mejor: umbral={mejor_params[0]}, horizonte={mejor_params[1]}v, Sharpe={mejor_sharpe:.2f}, WR={mejor_params[3]:.1f}%, ops={mejor_params[2]}")

    return mejor_params

ACTIVOS = ['ETH/USDT', 'ADA/USDT', 'SOL/USDT', 'BNB/USDT']

print("=" * 60)
print("  OPTIMIZADOR 4H — Grid search en datos train (70%)")
print("=" * 60)

for simbolo in ACTIVOS:
    optimizar(simbolo)

print(f"\n{'='*60}")
print("  Optimización completada — validar con walk_forward_4h.py")
print("=" * 60)
