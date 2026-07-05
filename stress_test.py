import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from config import PARAMS

def obtener_datos(simbolo, dias=3000):
    exchange = ccxt.bitvavo()
    todos = []
    since = None
    while len(todos) < dias:
        lote = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=1000, since=since)
        if not lote: break
        todos = lote + todos
        since = lote[0][0] - 1000 * 24 * 3600 * 1000
        if len(lote) < 1000: break
        if len(todos) >= dias: break
    df = pd.DataFrame(todos[-dias:], columns=['timestamp','open','high','low','close','volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.sort_values('fecha').drop_duplicates('timestamp').reset_index(drop=True)

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

def calcular_btc_mom(df_btc, fechas_ref):
    btc_precios = df_btc['close']
    btc_fechas  = df_btc['fecha'].iloc[50:].reset_index(drop=True)
    btc_trim    = btc_precios.iloc[50:].reset_index(drop=True)
    mom7  = btc_trim / btc_trim.shift(7) - 1
    mom3  = btc_trim / btc_trim.shift(3) - 1
    btc_map = {}
    for i, f in enumerate(btc_fechas):
        btc_map[f.date()] = (mom7.iloc[i], mom3.iloc[i])
    return btc_map

def btc_ok_en_fecha(btc_map, fecha):
    key = fecha.date() if hasattr(fecha, 'date') else fecha
    if key not in btc_map:
        return True
    m7, m3 = btc_map[key]
    if pd.isna(m7) or pd.isna(m3):
        return True
    if m7 < -0.05 or m3 < -0.03:
        return False
    return True

def backtesting_periodo(scores, precios, fechas, umbral, stop, take, kelly,
                        fecha_ini, fecha_fin, filtro_btc=False, btc_map=None):
    mask = (fechas >= fecha_ini) & (fechas <= fecha_fin)
    indices = fechas[mask].index.tolist()
    if len(indices) < 5:
        return None
    idx_ini = indices[0]
    idx_fin = min(indices[-1], len(scores)-14)
    if idx_ini >= idx_fin:
        return None

    retornos = []
    bloqueadas = 0
    equity = [500.0]
    for i in range(idx_ini, idx_fin):
        if scores[i] >= umbral:
            if filtro_btc and btc_map is not None:
                if not btc_ok_en_fecha(btc_map, fechas.iloc[i]):
                    bloqueadas += 1
                    continue
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
            retornos.append(retorno)
            sizing = min(kelly/100, 0.10) if kelly > 0 else 0.025
            equity.append(equity[-1] + equity[-1] * sizing * retorno)

    if len(retornos) < 2:
        return None
    r = np.array(retornos)
    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak * 100).min()
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    win_rate = sum(1 for x in r if x > 0) / len(r) * 100
    retorno_total = (equity[-1] - 500) / 500 * 100
    return {
        'sharpe': round(sharpe, 2),
        'win_rate': round(win_rate, 1),
        'max_dd': round(max_dd, 1),
        'retorno_total': round(retorno_total, 1),
        'ops': len(retornos),
        'bloqueadas': bloqueadas,
    }

PERIODOS = {
    'Crash mayo 2021':   (pd.Timestamp('2021-04-15'), pd.Timestamp('2021-07-15')),
    'Bear market 2022':  (pd.Timestamp('2022-01-01'), pd.Timestamp('2022-12-31')),
    'Colapso FTX nov22': (pd.Timestamp('2022-10-15'), pd.Timestamp('2022-12-15')),
    'Bull market 2023':  (pd.Timestamp('2023-01-01'), pd.Timestamp('2023-12-31')),
    'Mercado actual':    (pd.Timestamp('2025-01-01'), pd.Timestamp('2026-06-20')),
}

ACTIVOS_OP = {k: v for k, v in PARAMS.items() if v['kelly'] > 0}

print("Descargando BTC para filtro...")
df_btc = obtener_datos('BTC/EUR')
btc_map = calcular_btc_mom(df_btc, None)
print("✅ BTC listo\n")

print("=" * 75)
print("  STRESS TEST — Con y sin filtro BTC")
print("=" * 75)

for simbolo, p in ACTIVOS_OP.items():
    usa_filtro = p.get('filtro_btc', False)
    print(f"\n── {simbolo} (filtro BTC: {'✅ activo' if usa_filtro else '❌ inactivo'})\n")
    print(f"  {'Periodo':<22} {'Sin filtro':>10} {'Con filtro':>11} {'Mejora':>8} {'Ops bloq.':>10}")
    print("  " + "─" * 65)

    df = obtener_datos(simbolo)
    precios = df['close'].iloc[50:].reset_index(drop=True)
    fechas  = df['fecha'].iloc[50:].reset_index(drop=True)
    scores  = calcular_scores(df['close'])

    for nombre, (ini, fin) in PERIODOS.items():
        r_sin = backtesting_periodo(scores, precios, fechas, p['umbral'], p['stop'], p['take'], p['kelly'], ini, fin, filtro_btc=False)
        r_con = backtesting_periodo(scores, precios, fechas, p['umbral'], p['stop'], p['take'], p['kelly'], ini, fin, filtro_btc=True, btc_map=btc_map)

        if r_sin and r_con:
            mejora = r_con['sharpe'] - r_sin['sharpe']
            emoji = "✅" if mejora > 0 else "❌"
            print(f"  {nombre:<22} {r_sin['sharpe']:>9.2f} {r_con['sharpe']:>10.2f} {mejora:>+8.2f}  {r_con['bloqueadas']:>5} señales  {emoji}")
        elif r_sin:
            print(f"  {nombre:<22} {r_sin['sharpe']:>9.2f} {'sin datos':>10}")
        else:
            print(f"  {nombre:<22} {'sin datos':>9}")

print("\n" + "=" * 75)
print("✅ Stress test completado")
