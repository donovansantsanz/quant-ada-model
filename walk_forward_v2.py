"""
walk_forward_v2.py — Validación honesta (SOLO ANÁLISIS)
=========================================================
A diferencia de walk_forward.py, este script:
  1. Optimiza parámetros usando SOLO el tramo de train
  2. Valida esos parámetros en un test que la optimización nunca vio
  3. NO toca config.py — solo reporta qué saldría

Esto evita el sesgo de optimizar y validar sobre los mismos datos.
Compara los parámetros "honestos" con los actuales de producción.
"""
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from config import PARAMS

# ── Datos ────────────────────────────────────────────────────────
def obtener_datos(simbolo, dias=500):
    exchange = ccxt.binance()
    velas = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=dias)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.sort_values('fecha').reset_index(drop=True)

# ── Scoring point-in-time (idéntico al de producción) ────────────
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

# ── Backtest de un periodo ───────────────────────────────────────
def backtest(scores, precios, umbral, stop, take, inicio, fin):
    retornos = []
    for i in range(inicio, min(fin, len(scores)-14)):
        if scores[i] >= umbral:
            p_entrada = precios.iloc[i]
            retorno = None
            for j in range(1, 15):
                p = precios.iloc[i+j]
                if p <= p_entrada * (1 - stop):
                    retorno = -stop; break
                elif p >= p_entrada * (1 + take):
                    retorno = take;  break
            if retorno is None:
                retorno = (precios.iloc[i+14] - p_entrada) / p_entrada
            retornos.append(retorno)
    if len(retornos) < 5:   # mínimo defendible más alto que el original (era 3)
        return None, 0
    r = np.array(retornos)
    if r.std() == 0:
        sharpe = 99.0 if r.mean() > 0 else -99.0
    else:
        sharpe = r.mean() / r.std() * np.sqrt(252)
    return round(sharpe, 2), len(retornos)

# ── Grid de búsqueda (solo sobre train) ──────────────────────────
GRID_UMBRAL = [4, 5, 6, 7]
GRID_STOP   = [0.02, 0.03]
GRID_TAKE   = [0.06, 0.08, 0.10]

def optimizar_en_train(scores, precios, corte):
    """Busca los mejores parámetros usando SOLO el tramo de train."""
    mejor = {'sharpe': -999, 'umbral': None, 'stop': None, 'take': None, 'ops': 0}
    for umbral in GRID_UMBRAL:
        for stop in GRID_STOP:
            for take in GRID_TAKE:
                sharpe, ops = backtest(scores, precios, umbral, stop, take, 0, corte)
                if sharpe is not None and sharpe > mejor['sharpe']:
                    mejor = {'sharpe': sharpe, 'umbral': umbral, 'stop': stop, 'take': take, 'ops': ops}
    return mejor

# ── Ejecución ────────────────────────────────────────────────────
print("=" * 78)
print("  WALK-FORWARD HONESTO — Optimización solo-train + validación out-of-sample")
print("  SOLO ANÁLISIS — no modifica config.py ni el sistema en producción")
print("=" * 78)
print(f"\n  {'Activo':<10} {'PARÁMETROS HONESTOS (opt. en train)':<38} {'Test OOS':<16} {'vs PROD'}")
print("  " + "-" * 76)

for simbolo, cfg_prod in PARAMS.items():
    df = obtener_datos(simbolo, dias=500)
    precios = df['close']
    scores = calcular_scores(precios)
    precios_trim = precios.iloc[50:].reset_index(drop=True)
    n = len(scores)
    corte = int(n * 0.74)

    # 1. Optimizar SOLO en train
    mejor = optimizar_en_train(scores, precios_trim, corte)

    if mejor['umbral'] is None:
        print(f"  {simbolo:<10} sin datos suficientes en train")
        continue

    # 2. Validar esos parámetros en el test que la optimización NO vio
    sharpe_test, ops_test = backtest(
        scores, precios_trim,
        mejor['umbral'], mejor['stop'], mejor['take'],
        corte, n
    )

    # 3. Comparar con producción
    prod_str = f"u{cfg_prod['umbral']} s{int(cfg_prod['stop']*100)} t{int(cfg_prod['take']*100)}"
    honesto_str = f"u{mejor['umbral']} s{int(mejor['stop']*100)} t{int(mejor['take']*100)}"
    igual = (mejor['umbral'] == cfg_prod['umbral'] and
             abs(mejor['stop'] - cfg_prod['stop']) < 0.001 and
             abs(mejor['take'] - cfg_prod['take']) < 0.001)
    marca = "✅ igual" if igual else "⚠️ DIFIERE"

    if sharpe_test is None:
        test_str = "sin ops test"
        veredicto = "❌"
    else:
        test_str = f"Sharpe {sharpe_test} ({ops_test} ops)"
        veredicto = "✅" if sharpe_test > 0 else "❌"

    print(f"  {simbolo:<10} {honesto_str:<8} train Sharpe {mejor['sharpe']:<6} ({mejor['ops']:>2} ops)   "
          f"{veredicto} {test_str:<16} {marca} (prod: {prod_str})")

print("\n" + "=" * 78)
print("  LECTURA:")
print("  - 'DIFIERE' = la optimización honesta daría parámetros distintos a producción")
print("  - Test OOS positivo con parámetros que difieren = producción podría estar subóptima")
print("  - Test OOS negativo = ni siquiera la optimización honesta generaliza en ese activo")
print("  - NO se ha modificado nada. Esto es solo diagnóstico.")
print("=" * 78)
