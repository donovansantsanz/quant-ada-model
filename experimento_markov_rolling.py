import pandas as pd
import numpy as np
import os
import ccxt
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
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
df['ret'] = np.log(df['close'] / df['close'].shift(1))
df = df.dropna().reset_index(drop=True)

print("=" * 60)
print("EXPERIMENTO 2 — Markov-Switching ROLLING (sin lookahead)")
print("=" * 60)
print(f"Datos: {len(df)} días | ventana mínima: 90 días")
print("Ajustando modelo día a día (puede tardar 1-2 min)...")

MIN_WINDOW = 90
prob_turbul_rolling = [np.nan] * len(df)

for i in range(MIN_WINDOW, len(df)):
    try:
        datos_pasados = df['ret'].iloc[:i]
        modelo = MarkovRegression(datos_pasados, k_regimes=2, switching_variance=True)
        resultado = modelo.fit(disp=False, maxiter=100)
        # Probabilidad del último día (el que predecimos)
        probs = resultado.smoothed_marginal_probabilities
        # El régimen turbulento es el de mayor varianza
        var0 = resultado.params['sigma2[0]']
        var1 = resultado.params['sigma2[1]']
        idx_turbul = 1 if var1 > var0 else 0
        prob_turbul_rolling[i] = probs[idx_turbul].iloc[-1]
    except:
        prob_turbul_rolling[i] = np.nan

df['prob_turbul_rolling'] = prob_turbul_rolling

print("✅ Modelo rolling completado")

# Calcular scores de BNB
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

# Señales de compra
señales = df[(df['score'] >= umbral) & (df['prob_turbul_rolling'].notna())].copy()

print(f"\n📊 SEÑALES COMPRAR BNB — RÉGIMEN MARKOV ROLLING:")
print(f"\n  {'Fecha':<12} {'Precio':>8} {'Score':>6} {'P(turb)_rolling':>16} {'Régimen':>9}")
print(f"  {'-'*60}")

for _, row in señales.iterrows():
    reg = "TURBUL" if row['prob_turbul_rolling'] > 0.5 else "CALMA"
    flag = " ⚠️" if row['prob_turbul_rolling'] > 0.5 else ""
    print(f"  {str(row['date'].date()):<12} €{row['close']:>7.2f} {int(row['score']):>6} {row['prob_turbul_rolling']:>16.2f} {reg:>9}{flag}")

# Resumen
señales_calma  = señales[señales['prob_turbul_rolling'] <= 0.5]
señales_turbul = señales[señales['prob_turbul_rolling'] > 0.5]
print(f"\n📊 RESUMEN:")
print(f"  Total señales: {len(señales)}")
print(f"  En CALMA (rolling):     {len(señales_calma)} ({len(señales_calma)/len(señales)*100:.0f}%)")
print(f"  En TURBULENTO (rolling): {len(señales_turbul)} ({len(señales_turbul)/len(señales)*100:.0f}%)")

# El caso clave: enero 2026
print(f"\n📊 CASO CLAVE — ENERO 2026 (crash):")
enero = señales[(señales['date'] >= '2026-01-25') & (señales['date'] <= '2026-02-10')]
if len(enero) > 0:
    for _, row in enero.iterrows():
        reg = "TURBUL ⚠️" if row['prob_turbul_rolling'] > 0.5 else "CALMA"
        print(f"  {str(row['date'].date()):<12} €{row['close']:>7.2f} P(turb)={row['prob_turbul_rolling']:.2f} → {reg}")
else:
    print("  Sin señales en ese periodo")

print("\n✅ Experimento 2 completado")
