import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from itertools import product

def obtener_datos(simbolo, dias=365):
    exchange = ccxt.bitvavo()
    velas = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=dias)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.sort_values('fecha').reset_index(drop=True)

def calcular_score(precios, precio):
    mm7  = precios.rolling(7).mean()
    mm20 = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1

    scores = []
    for i in range(50, len(precios)):
        p = precios.iloc[i]
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
    return scores, precios.iloc[50:].reset_index(drop=True)

def backtesting(scores, precios, umbral, stop, take):
    retornos = []
    for i in range(len(scores)-14):
        if scores[i] >= umbral:
            p_entrada = precios.iloc[i]
            p_stop    = p_entrada * (1 - stop)
            p_take    = p_entrada * (1 + take)
            retorno   = None
            for j in range(1, 15):
                p = precios.iloc[i+j]
                if p <= p_stop:
                    retorno = -stop
                    break
                elif p >= p_take:
                    retorno = take
                    break
            if retorno is None:
                retorno = (precios.iloc[i+14] - p_entrada) / p_entrada
            retornos.append(retorno)
    if len(retornos) < 5:
        return -999
    r = np.array(retornos)
    return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else -999

ACTIVOS = ['BTC/EUR', 'BNB/EUR', 'AVAX/EUR']
UMBRALES = [3, 4, 5, 6, 7]
STOPS    = [0.02, 0.03, 0.05]
TAKES    = [0.06, 0.08, 0.10, 0.15]

print("Optimizando parámetros...\n")

for simbolo in ACTIVOS:
    print(f"── {simbolo}")
    df = obtener_datos(simbolo)
    precios = df['close']
    scores, precios_trim = calcular_score(precios, precios.iloc[-1])

    mejor_sharpe = -999
    mejor_params = None

    for umbral, stop, take in product(UMBRALES, STOPS, TAKES):
        sharpe = backtesting(scores, precios_trim, umbral, stop, take)
        if sharpe > mejor_sharpe:
            mejor_sharpe = sharpe
            mejor_params = (umbral, stop, take)

    u, s, t = mejor_params
    print(f"   Umbral: {u} | Stop: {s*100:.0f}% | Take: {t*100:.0f}% | Sharpe: {mejor_sharpe:.2f}\n")

print("✅ Optimización completada")
