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
df['ret7d'] = df['close'].pct_change(7)
df['vol5d'] = df['ret'].rolling(5).std()
vol5d_vals = df['vol5d'].dropna().values
df['vol5d_pct'] = df['vol5d'].apply(
    lambda x: stats.percentileofscore(vol5d_vals, x) if pd.notna(x) else np.nan
)

print("=" * 65)
print("EXPERIMENTO 4 — Walk-Forward del filtro de velocidad de caida")
print("=" * 65)

# Split train/test (70/30)
n = len(df)
n_train = int(n * 0.70)
df_train = df.iloc[:n_train].copy()
df_test  = df.iloc[n_train:].copy()

print(f"\nTrain: {df_train['date'].iloc[0].date()} → {df_train['date'].iloc[-1].date()} ({n_train} días)")
print(f"Test:  {df_test['date'].iloc[0].date()} → {df_test['date'].iloc[-1].date()} ({len(df_test)} días)")

from config import PARAMS
umbral_score = PARAMS['BNB/EUR']['umbral']
stop = PARAMS['BNB/EUR']['stop']
take = PARAMS['BNB/EUR']['take']

def calcular_scores(df_sub):
    precios = df_sub['close'].reset_index(drop=True)
    mm20 = precios.rolling(20).mean()
    mm7  = precios.rolling(7).mean()
    dist_mm20 = (precios - mm20) / mm20
    dist_mm7  = (precios - mm7) / mm7
    mom14 = precios / precios.shift(14) - 1
    vol30 = precios.pct_change().rolling(30).std()
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
    return scores

def simular_operaciones(df_sub, umbral_ret7d=None, umbral_vol=None):
    precios = df_sub['close'].reset_index(drop=True)
    retornos = []
    for i in range(len(df_sub)):
        row = df_sub.iloc[i]
        if row['score'] is None or row['score'] < umbral_score:
            continue
        # Aplicar filtros si se especifican
        if umbral_ret7d and pd.notna(row['ret7d']) and row['ret7d'] < umbral_ret7d:
            continue
        if umbral_vol and pd.notna(row['vol5d_pct']) and row['vol5d_pct'] > umbral_vol:
            continue
        p_entrada = row['close']
        retorno = None
        for j in range(1, 15):
            if i + j >= len(df_sub):
                break
            p = df_sub['close'].iloc[i + j]
            if p <= p_entrada * (1 - stop):
                retorno = -stop; break
            elif p >= p_entrada * (1 + take):
                retorno = take; break
        if retorno is None and i + 14 < len(df_sub):
            retorno = (df_sub['close'].iloc[i + 14] - p_entrada) / p_entrada
        if retorno is not None:
            retornos.append(retorno)
    if len(retornos) < 3:
        return -999, 0
    r = np.array(retornos)
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else -999
    return round(sharpe, 2), len(retornos)

# Calcular scores
print("\nCalculando scores (puede tardar 1-2 min)...")
df['score'] = calcular_scores(df)

df_train['score'] = df['score'].iloc[:n_train].values
df_test['score']  = df['score'].iloc[n_train:].values

# TRAIN: Grid search sobre umbrales
print("\n📊 TRAIN — Grid search de umbrales:")
print(f"\n  {'Filtro':<30} {'Sharpe':>8} {'Ops':>5}")
print(f"  {'-'*45}")

umbrales_ret = [None, -0.05, -0.08, -0.10, -0.12, -0.15]
umbrales_vol = [None, 70, 75, 80, 85, 90]

mejor_sharpe_train = -999
mejor_config = (None, None)
resultados_train = []

# Sin filtro (baseline)
s, n_ops = simular_operaciones(df_train)
print(f"  {'Sin filtro':<30} {s:>8.2f} {n_ops:>5}")
resultados_train.append(('Sin filtro', None, None, s, n_ops))

# Solo ret7d
for u_ret in umbrales_ret[1:]:
    s, n_ops = simular_operaciones(df_train, umbral_ret7d=u_ret)
    label = f"ret7d < {u_ret:.0%}"
    print(f"  {label:<30} {s:>8.2f} {n_ops:>5}")
    resultados_train.append((label, u_ret, None, s, n_ops))
    if s > mejor_sharpe_train and n_ops >= 3:
        mejor_sharpe_train = s
        mejor_config = (u_ret, None)

# Solo vol5d
for u_vol in umbrales_vol[1:]:
    s, n_ops = simular_operaciones(df_train, umbral_vol=u_vol)
    label = f"vol5d > p{u_vol}"
    print(f"  {label:<30} {s:>8.2f} {n_ops:>5}")
    resultados_train.append((label, None, u_vol, s, n_ops))
    if s > mejor_sharpe_train and n_ops >= 3:
        mejor_sharpe_train = s
        mejor_config = (None, u_vol)

# Combinado
for u_ret in umbrales_ret[1:]:
    for u_vol in umbrales_vol[1:]:
        s, n_ops = simular_operaciones(df_train, umbral_ret7d=u_ret, umbral_vol=u_vol)
        label = f"ret7d<{u_ret:.0%} + vol>p{u_vol}"
        if s > mejor_sharpe_train and n_ops >= 3:
            mejor_sharpe_train = s
            mejor_config = (u_ret, u_vol)
            print(f"  {label:<30} {s:>8.2f} {n_ops:>5}  ← mejor combinado")

print(f"\n  ✅ Mejor config en TRAIN: ret7d={mejor_config[0]}, vol={mejor_config[1]} | Sharpe={mejor_sharpe_train:.2f}")

# TEST: aplicar mejor config
print(f"\n📊 TEST — Aplicando mejor config fuera de muestra:")
s_base_test, n_base = simular_operaciones(df_test)
s_filtro_test, n_filtro = simular_operaciones(df_test, umbral_ret7d=mejor_config[0], umbral_vol=mejor_config[1])

print(f"\n  Sin filtro:     Sharpe {s_base_test:.2f} ({n_base} ops)")
print(f"  Con filtro:     Sharpe {s_filtro_test:.2f} ({n_filtro} ops)")
print(f"  Mejora:         {s_filtro_test - s_base_test:+.2f}")

if s_filtro_test > s_base_test:
    print(f"\n  ✅ El filtro MEJORA el Sharpe fuera de muestra — resultado robusto")
else:
    print(f"\n  ❌ El filtro NO mejora fuera de muestra — posible overfitting en train")

print("\n✅ Experimento 4 completado")
