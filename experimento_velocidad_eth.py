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

print("=" * 65)
print("EXPERIMENTO 3b — Velocidad de caida en ETH/EUR")
print("Replicacion para verificar si conclusiones de BNB generalizan")
print("=" * 65)

from config import PARAMS
umbral_score = PARAMS['ETH/EUR']['umbral']
stop = PARAMS['ETH/EUR']['stop']
take = PARAMS['ETH/EUR']['take']

print(f"\nETH/EUR params: umbral={umbral_score}, stop={stop*100:.0f}%, take={take*100:.0f}%")
print(f"BNB/EUR params: umbral=7, stop=2%, take=10%")
print(f"Diferencia clave: ETH tiene umbral más BAJO y stop más AMPLIO")

ohlcv = exchange.fetch_ohlcv('ETH/EUR', '1d', limit=365)
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

# Calcular scores ETH
print("\nCalculando scores ETH...")
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
señales = df[df['score'] >= umbral_score].copy()

print(f"\nTotal señales ETH (score >= {umbral_score}): {len(señales)}")
print(f"(BNB tenia 17 señales con umbral 7 — ETH con umbral 4 debería tener más)\n")

def simular_operaciones(df_sub, umbral_ret7d=None, umbral_vol=None):
    retornos = []
    for i in range(len(df_sub)):
        row = df_sub.iloc[i]
        if row.get('score') is None or row['score'] < umbral_score:
            continue
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

# Año completo
print("📊 AÑO COMPLETO — ETH:")
print(f"\n  {'Filtro':<30} {'Sharpe':>8} {'Ops':>5}")
print(f"  {'-'*45}")

s, n = simular_operaciones(df)
print(f"  {'Sin filtro':<30} {s:>8.2f} {n:>5}")

for u_ret in [-0.05, -0.08, -0.10]:
    s, n = simular_operaciones(df, umbral_ret7d=u_ret)
    print(f"  {'ret7d < '+f'{u_ret:.0%}':<30} {s:>8.2f} {n:>5}")

for u_vol in [70, 80]:
    s, n = simular_operaciones(df, umbral_vol=u_vol)
    print(f"  {'vol5d > p'+str(u_vol):<30} {s:>8.2f} {n:>5}")

# Detalle señales con alertas
print(f"\n📊 SEÑALES ETH — velocidad de caida:")
print(f"\n  {'Fecha':<12} {'Precio':>8} {'ret7d':>7} {'vol5d_pct':>10} {'Alerta'}")
print(f"  {'-'*55}")

for _, row in señales.iterrows():
    alertas = []
    if pd.notna(row['ret7d']) and row['ret7d'] < -0.10: alertas.append("⚠️ret7d")
    if pd.notna(row['vol5d_pct']) and row['vol5d_pct'] > 80: alertas.append("⚠️vol")
    flag = " ".join(alertas)
    ret7d_str = f"{row['ret7d']:+.1%}" if pd.notna(row['ret7d']) else "N/A"
    vol_str = f"{row['vol5d_pct']:.0f}%" if pd.notna(row['vol5d_pct']) else "N/A"
    print(f"  {str(row['date'].date()):<12} €{row['close']:>7.0f} {ret7d_str:>7} {vol_str:>10}  {flag}")

# Comparacion final BNB vs ETH
print(f"\n📊 COMPARACIÓN BNB vs ETH (sin filtro, año completo):")
print(f"  BNB: Sharpe 7.15, 67 ops, stop 2%, umbral 7")
s_eth, n_eth = simular_operaciones(df)
print(f"  ETH: Sharpe {s_eth:.2f}, {n_eth} ops, stop {stop*100:.0f}%, umbral {umbral_score}")

print("\n✅ Experimento 3b completado")
