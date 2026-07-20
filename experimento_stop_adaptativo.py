import pandas as pd
import numpy as np
import os
import ccxt
from dotenv import load_dotenv
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))

exchange = ccxt.bitvavo({
    'apiKey': os.getenv("BITVAVO_API_KEY"),
    'secret': os.getenv("BITVAVO_API_SECRET"),
    'enableRateLimit': True,
    'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
})

ohlcv = exchange.fetch_ohlcv('BNB/EUR', '1d', limit=365)
df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
df['date'] = pd.to_datetime(df['ts'], unit='ms')
df = df.sort_values('date').reset_index(drop=True)
df['ret'] = df['close'].pct_change()

# ATR (Average True Range) — mide volatilidad real del mercado
df['tr'] = pd.concat([
    df['close'].shift(1),
    df[['close']].rename(columns={'close':'prev'}).assign(prev=df['close'].shift(1))
], axis=1).apply(lambda x: x.iloc[0], axis=1)  # placeholder
df['high_low'] = df['close'].rolling(2).max() - df['close'].rolling(2).min()
df['atr14'] = df['high_low'].rolling(14).mean()
df['atr_pct'] = df['atr14'] / df['close']  # ATR como % del precio

# Volatilidad rolling 14d
df['vol14d'] = df['ret'].rolling(14).std()

print("=" * 65)
print("EXPERIMENTO 5 — Stop adaptativo basado en volatilidad")
print("=" * 65)

from config import PARAMS
umbral_score = PARAMS['BNB/EUR']['umbral']
take = PARAMS['BNB/EUR']['take']
stop_fijo = PARAMS['BNB/EUR']['stop']

# Calcular scores
precios = df['close'].reset_index(drop=True)
mm20 = precios.rolling(20).mean()
mm7  = precios.rolling(7).mean()
dist_mm20 = (precios - mm20) / mm20
dist_mm7  = (precios - mm7) / mm7
mom14 = precios / precios.shift(14) - 1
vol30 = precios.pct_change().rolling(30).std()

print("Calculando scores...")
scores = []
for i in range(len(precios)):
    if i < 50:
        scores.append(None)
        continue
    pa = precios.iloc[i]
    p1 = stats.percentileofscore(dist_mm20.iloc[:i].dropna(), (pa - mm20.iloc[i]) / mm20.iloc[i])
    p2 = stats.percentileofscore(dist_mm7.iloc[:i].dropna(),  (pa - mm7.iloc[i]) / mm7.iloc[i])
    p3 = stats.percentileofscore(mom14.iloc[:i].dropna(), mom14.iloc[i])
    p4 = stats.percentileofscore(vol30.iloc[:i].dropna(), vol30.iloc[i])
    pts = 0
    if p1 < 20: pts += 3
    elif p1 < 40: pts += 1
    elif p1 > 80: pts -= 3
    elif p1 > 60: pts -= 1
    if p2 < 20: pts += 2
    elif p2 < 40: pts += 1
    elif p2 > 80: pts -= 2
    elif p2 > 60: pts -= 1
    if p3 < 20: pts += 2
    elif p3 < 40: pts += 1
    elif p3 > 80: pts -= 2
    elif p3 > 60: pts -= 1
    if p4 > 80: pts -= 2
    elif p4 > 60: pts -= 1
    elif p4 < 20: pts += 1
    scores.append(max(-10, min(10, pts)))

df['score'] = scores

def simular_con_stop(df_sub, modo_stop='fijo', multiplicador=1.0):
    """
    modo_stop: 'fijo' usa stop_fijo siempre
               'vol14' usa vol14d * multiplicador como stop
               'atr'   usa atr_pct * multiplicador como stop
    """
    retornos = []
    stops_usados = []
    for i in range(len(df_sub)):
        row = df_sub.iloc[i]
        if row.get('score') is None or row['score'] < umbral_score:
            continue
        p_entrada = row['close']

        if modo_stop == 'fijo':
            stop = stop_fijo
        elif modo_stop == 'vol14':
            stop = min(max(row['vol14d'] * multiplicador, 0.01), 0.10) if pd.notna(row['vol14d']) else stop_fijo
        elif modo_stop == 'atr':
            stop = min(max(row['atr_pct'] * multiplicador, 0.01), 0.10) if pd.notna(row['atr_pct']) else stop_fijo

        stops_usados.append(stop)
        retorno = None
        for j in range(1, 20):  # ventana más amplia para stops más anchos
            if i + j >= len(df_sub):
                break
            p = df_sub['close'].iloc[i + j]
            if p <= p_entrada * (1 - stop):
                retorno = -stop; break
            elif p >= p_entrada * (1 + take):
                retorno = take; break
        if retorno is None and i + 19 < len(df_sub):
            retorno = (df_sub['close'].iloc[i + 19] - p_entrada) / p_entrada
        if retorno is not None:
            retornos.append(retorno)

    if len(retornos) < 3:
        return -999, 0, 0, 0
    r = np.array(retornos)
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else -999
    win_rate = (r > 0).mean() * 100
    stop_medio = np.mean(stops_usados) * 100
    return round(sharpe, 2), len(retornos), round(win_rate, 1), round(stop_medio, 1)

# Periodo completo
print("\n📊 COMPARACIÓN STOP FIJO vs ADAPTATIVO (año completo):")
print(f"\n  {'Config':<30} {'Sharpe':>8} {'Ops':>5} {'Win%':>6} {'Stop%':>7}")
print(f"  {'-'*60}")

s, n, w, st = simular_con_stop(df, 'fijo')
print(f"  {'Stop fijo 2%':<30} {s:>8.2f} {n:>5} {w:>6.1f} {st:>7.1f}%")

for mult in [1.5, 2.0, 2.5, 3.0]:
    s, n, w, st = simular_con_stop(df, 'vol14', mult)
    label = f"Stop vol14d × {mult}"
    print(f"  {label:<30} {s:>8.2f} {n:>5} {w:>6.1f} {st:>7.1f}%")

for mult in [1.5, 2.0, 2.5, 3.0]:
    s, n, w, st = simular_con_stop(df, 'atr', mult)
    label = f"Stop ATR × {mult}"
    print(f"  {label:<30} {s:>8.2f} {n:>5} {w:>6.1f} {st:>7.1f}%")

# Caso específico: periodo problemático nov 2025 - feb 2026
print(f"\n📊 PERIODO PROBLEMÁTICO (nov 2025 - feb 2026):")
df_prob = df[(df['date'] >= '2025-11-01') & (df['date'] < '2026-03-01')].copy().reset_index(drop=True)

print(f"\n  {'Config':<30} {'Sharpe':>8} {'Ops':>5} {'Win%':>6} {'Stop%':>7}")
print(f"  {'-'*60}")

s, n, w, st = simular_con_stop(df_prob, 'fijo')
print(f"  {'Stop fijo 2%':<30} {s:>8.2f} {n:>5} {w:>6.1f} {st:>7.1f}%")

for mult in [1.5, 2.0, 2.5, 3.0]:
    s, n, w, st = simular_con_stop(df_prob, 'vol14', mult)
    label = f"Stop vol14d × {mult}"
    print(f"  {label:<30} {s:>8.2f} {n:>5} {w:>6.1f} {st:>7.1f}%")

# Detalle: ¿cuánto stop habría necesitado para sobrevivir los rebotes de nov?
print(f"\n📊 ¿CUÁNTO STOP HABRÍA NECESITADO EN NOV 2025?")
señales_nov = df[(df['date'] >= '2025-11-01') & (df['date'] < '2025-12-01') & (df['score'] >= umbral_score)].copy().reset_index(drop=True)

for i, row in señales_nov.iterrows():
    p_entrada = row['close']
    min_precio = p_entrada
    max_precio = p_entrada
    for j in range(1, 30):
        if i + j >= len(df):
            break
        p = df['close'].iloc[df.index[df['date'] == row['date']].values[0] + j] if len(df.index[df['date'] == row['date']].values) > 0 else p_entrada
        if p < min_precio: min_precio = p
        if p > max_precio: max_precio = p
        if max_precio >= p_entrada * (1 + take):
            break
    caida_max = (p_entrada - min_precio) / p_entrada * 100
    subida_max = (max_precio - p_entrada) / p_entrada * 100
    alcanzo_take = "✅" if max_precio >= p_entrada * (1 + take) else "❌"
    print(f"  {str(row['date'].date())} €{p_entrada:.0f} | caida_max: -{caida_max:.1f}% | subida_max: +{subida_max:.1f}% | take {alcanzo_take}")

print("\n✅ Experimento 5 completado")
