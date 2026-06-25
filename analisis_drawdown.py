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

def analizar_drawdown(scores, precios, umbral, stop, take, kelly_pct, capital=500):
    equity = [capital]
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
                    retorno = -stop; break
                elif p >= p_take:
                    retorno = take;  break
            if retorno is None:
                retorno = (precios.iloc[i+14] - p_entrada) / p_entrada

            sizing = min(kelly_pct / 100, 0.10)
            ganancia = equity[-1] * sizing * retorno
            equity.append(equity[-1] + ganancia)
            retornos.append(retorno)

    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak * 100

    max_dd = drawdowns.min()
    avg_dd = drawdowns[drawdowns < 0].mean() if any(drawdowns < 0) else 0
    capital_final = equity[-1]
    retorno_total = (capital_final - capital) / capital * 100
    win_rate = sum(1 for r in retornos if r > 0) / len(retornos) * 100 if retornos else 0
    perdidas_consec = 0
    max_perdidas_consec = 0
    for r in retornos:
        if r < 0:
            perdidas_consec += 1
            max_perdidas_consec = max(max_perdidas_consec, perdidas_consec)
        else:
            perdidas_consec = 0

    return {
        'capital_final': capital_final,
        'retorno_total': retorno_total,
        'max_drawdown': max_dd,
        'avg_drawdown': avg_dd,
        'win_rate': win_rate,
        'operaciones': len(retornos),
        'max_perdidas_consec': max_perdidas_consec,
    }

from config import PARAMS as ACTIVOS

print("Análisis de Drawdown — Capital inicial: €500\n")
print(f"{'Activo':<12} {'Capital final':>14} {'Retorno':>9} {'Max DD':>8} {'Win rate':>10} {'Racha pérd':>12}")
print("─" * 70)

for simbolo, cfg in ACTIVOS.items():
    df = obtener_datos(simbolo, dias=500)
    precios = df['close'].iloc[50:].reset_index(drop=True)
    scores = calcular_scores(df['close'])

    r = analizar_drawdown(scores, precios, cfg['umbral'], cfg['stop'], cfg['take'], cfg['kelly'])

    emoji = "✅" if r['max_drawdown'] > -15 else "⚠️ "
    print(f"{simbolo:<12} €{r['capital_final']:>12.2f} {r['retorno_total']:>+8.1f}% {r['max_drawdown']:>7.1f}% {r['win_rate']:>9.1f}% {r['max_perdidas_consec']:>8} seguidas  {emoji}")

print("\n✅ Análisis completado")
