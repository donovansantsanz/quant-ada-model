import ccxt
import pandas as pd
import numpy as np
from scipy import stats

def obtener_datos(simbolo, dias=500):
    exchange = ccxt.binance()
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

def backtesting_periodo(scores, precios, umbral, stop, take, inicio, fin):
    retornos = []
    for i in range(inicio, min(fin, len(scores)-14)):
        if scores[i] >= umbral:
            p_entrada = precios.iloc[i]
            p_stop    = p_entrada * (1 - stop)
            p_take    = p_entrada * (1 + take)
            retorno   = None
            for j in range(1, 15):
                p = precios.iloc[i+j]
                if p <= p_stop:
                    retorno = -stop; break
                elif p >= p_take:
                    retorno = take;  break
            if retorno is None:
                retorno = (precios.iloc[i+14] - p_entrada) / p_entrada
            retornos.append(retorno)
    if len(retornos) < 3:
        return -999, 0
    r = np.array(retornos)
    if r.std() == 0:
        sharpe = 99.0 if r.mean() > 0 else -99.0
    else:
        sharpe = r.mean() / r.std() * np.sqrt(252)
    return round(sharpe, 2), len(retornos)

from config import PARAMS
ACTIVOS = {k: {'umbral': v['umbral'], 'stop': v['stop'], 'take': v['take']} for k, v in PARAMS.items()}

print("Walk-Forward Validation\n")
print(f"{'Activo':<12} {'Train (270d)':>14} {'Test (95d)':>12} {'Veredicto':>12}")
print("─" * 55)

for simbolo, cfg in ACTIVOS.items():
    df = obtener_datos(simbolo, dias=500)
    precios = df['close']
    scores = calcular_scores(precios)
    precios_trim = precios.iloc[50:].reset_index(drop=True)

    n = len(scores)
    corte = int(n * 0.74)

    sharpe_train, ops_train = backtesting_periodo(
        scores, precios_trim, cfg['umbral'], cfg['stop'], cfg['take'], 0, corte)
    sharpe_test, ops_test = backtesting_periodo(
        scores, precios_trim, cfg['umbral'], cfg['stop'], cfg['take'], corte, n)

    if sharpe_test > 1.0:
        veredicto = "✅ Robusto"
    elif sharpe_test > 0:
        veredicto = "⚠️  Débil"
    else:
        veredicto = "❌ Sobreajuste"

    print(f"{simbolo:<12} {sharpe_train:>8.2f} ({ops_train:>2} ops)  {sharpe_test:>6.2f} ({ops_test:>2} ops)  {veredicto}")

print("\n✅ Walk-forward completado")
