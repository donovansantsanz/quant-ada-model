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
print("EXPERIMENTO 3 — Velocidad de caida como filtro en tiempo real")
print("=" * 65)

# Scores BNB
from config import PARAMS
umbral = PARAMS['BNB/EUR']['umbral']

precios = df['close'].reset_index(drop=True)
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

df['score'] = scores
señales = df[df['score'] >= umbral].copy()

print(f"\nTotal señales COMPRAR (score >= {umbral}): {len(señales)}\n")
print(f"  {'Fecha':<12} {'Precio':>8} {'ret7d':>7} {'vol5d_pct':>10} {'Alerta':>10}")
print(f"  {'-'*55}")

for _, row in señales.iterrows():
    alertas = []
    if pd.notna(row['ret7d']) and row['ret7d'] < -0.10: alertas.append("⚠️ret7d")
    if pd.notna(row['vol5d_pct']) and row['vol5d_pct'] > 80: alertas.append("⚠️vol")
    flag = " ".join(alertas)
    ret7d_str = f"{row['ret7d']:+.1%}" if pd.notna(row['ret7d']) else "N/A"
    vol_str = f"{row['vol5d_pct']:.0f}%" if pd.notna(row['vol5d_pct']) else "N/A"
    print(f"  {str(row['date'].date()):<12} €{row['close']:>7.2f} {ret7d_str:>7} {vol_str:>10}  {flag}")

# Caso clave enero 2026
print(f"\n📊 CASO CLAVE — ENERO-FEBRERO 2026:")
enero = señales[(señales['date'] >= '2026-01-25') & (señales['date'] <= '2026-02-10')]
if len(enero) > 0:
    for _, row in enero.iterrows():
        r7 = f"{row['ret7d']:+.1%}" if pd.notna(row['ret7d']) else "N/A"
        vp = f"{row['vol5d_pct']:.0f}%" if pd.notna(row['vol5d_pct']) else "N/A"
        a_ret = "⚠️" if pd.notna(row['ret7d']) and row['ret7d'] < -0.10 else "✅"
        a_vol = "⚠️" if pd.notna(row['vol5d_pct']) and row['vol5d_pct'] > 80 else "✅"
        print(f"\n  {str(row['date'].date())} | €{row['close']:.2f}")
        print(f"    ret7d:     {r7:>8}  {a_ret} (umbral < -10%)")
        print(f"    vol5d_pct: {vp:>8}  {a_vol} (umbral > 80%)")
else:
    print("  Sin señales en ese periodo")

# Resumen filtros
print(f"\n📊 IMPACTO DE CADA FILTRO SOBRE LAS {len(señales)} SEÑALES:")
señales_con_datos = señales[señales['ret7d'].notna() & señales['vol5d_pct'].notna()]
for u in [-0.05, -0.10, -0.15]:
    n = (señales_con_datos['ret7d'] < u).sum()
    print(f"  ret7d < {u:.0%}: bloquea {n}/{len(señales_con_datos)} señales ({n/len(señales_con_datos)*100:.0f}%)")
for u in [70, 80, 90]:
    n = (señales_con_datos['vol5d_pct'] > u).sum()
    print(f"  vol5d > p{u}: bloquea {n}/{len(señales_con_datos)} señales ({n/len(señales_con_datos)*100:.0f}%)")

print("\n✅ Experimento 3 completado")
