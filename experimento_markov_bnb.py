import pandas as pd
import numpy as np
import os
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from dotenv import load_dotenv
import ccxt

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))

print("=" * 60)
print("EXPERIMENTO — Markov-Switching en BNB/EUR")
print("Hipótesis 3: ¿distingue el modelo régimen genuino de bull trap?")
print("=" * 60)

# ── DATOS ────────────────────────────────────────────────────────
exchange = ccxt.bitvavo({
    'apiKey': os.getenv("BITVAVO_API_KEY"),
    'secret': os.getenv("BITVAVO_API_SECRET"),
    'enableRateLimit': True,
    'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
})

ohlcv = exchange.fetch_ohlcv('BNB/EUR', '1d', limit=365)
df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
df['date'] = pd.to_datetime(df['ts'], unit='ms')
df = df.sort_values('date').reset_index(drop=True)

# Retornos log (lo que modela Hamilton)
df['ret'] = np.log(df['close'] / df['close'].shift(1))
df = df.dropna()

print(f"\nDatos: {len(df)} días de BNB/EUR")
print(f"Periodo: {df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()}")

# ── MODELO MARKOV-SWITCHING (2 regímenes) ────────────────────────
print("\nAjustando modelo Markov-Switching (2 regímenes)...")
modelo = MarkovRegression(
    df['ret'],
    k_regimes=2,
    switching_variance=True  # cada régimen tiene su propia volatilidad
)
resultado = modelo.fit(disp=False)
print("✅ Modelo ajustado")

# ── RESULTADOS ───────────────────────────────────────────────────
print("\n📊 REGÍMENES DETECTADOS:")
for i in range(2):
    media = resultado.params[f'regime.{i}.const'] * 252 * 100
    vol   = np.sqrt(resultado.params[f'regime.{i}.sigma2'] * 252) * 100
    print(f"\n  Régimen {i}:")
    print(f"    Retorno anualizado: {media:+.1f}%")
    print(f"    Volatilidad anual:  {vol:.1f}%")

# Probabilidades de cada régimen por día
probs = resultado.smoothed_marginal_probabilities
df['prob_reg0'] = probs[0].values
df['prob_reg1'] = probs[1].values
df['regimen_dominante'] = (df['prob_reg1'] > 0.5).astype(int)

# ── COMPARAR CON CLASIFICADOR ACTUAL ────────────────────────────
print("\n📊 COMPARACIÓN CON CLASIFICADOR ACTUAL (MA20 + RSI):")
df['ma20'] = df['close'].rolling(20).mean()
delta = df['close'].diff()
g = delta.clip(lower=0).rolling(14).mean()
p = (-delta).clip(lower=0).rolling(14).mean()
df['rsi'] = 100 - 100/(1 + g/p)
df['clasificador_actual'] = ((df['close'] < df['ma20']) & (df['rsi'] < 50)).astype(int)

df_clean = df.dropna()
acuerdo = (df_clean['regimen_dominante'] == df_clean['clasificador_actual']).mean() * 100
print(f"\n  Acuerdo entre ambos clasificadores: {acuerdo:.1f}%")

# ── SEÑALES DE COMPRA DE BNB y su régimen ───────────────────────
print("\n📊 OPERACIONES REALES DE BNB vs RÉGIMEN MARKOV:")
from config import PARAMS
from scipy import stats

scores = []
precios = df_clean['close'].reset_index(drop=True)
mm20 = precios.rolling(20).mean()
mm7  = precios.rolling(7).mean()
dist_mm20 = (precios - mm20) / mm20
dist_mm7  = (precios - mm7)  / mm7
mom14 = precios / precios.shift(14) - 1
vol30 = precios.pct_change().rolling(30).std()

for i in range(len(precios)):
    if i < 50:
        scores.append(None)
        continue
    p_actual = precios.iloc[i]
    pct_dm20 = stats.percentileofscore(dist_mm20.iloc[:i].dropna(), (p_actual - mm20.iloc[i]) / mm20.iloc[i])
    pct_dm7  = stats.percentileofscore(dist_mm7.iloc[:i].dropna(),  (p_actual - mm7.iloc[i])  / mm7.iloc[i])
    pct_m14  = stats.percentileofscore(mom14.iloc[:i].dropna(), mom14.iloc[i])
    pct_v30  = stats.percentileofscore(vol30.iloc[:i].dropna(), vol30.iloc[i])
    pts = 0
    if pct_dm20 < 20: pts += 3
    elif pct_dm20 < 40: pts += 1
    elif pct_dm20 > 80: pts -= 3
    elif pct_dm20 > 60: pts -= 1
    if pct_dm7 < 20: pts += 2
    elif pct_dm7 < 40: pts += 1
    elif pct_dm7 > 80: pts -= 2
    elif pct_dm7 > 60: pts -= 1
    if pct_m14 < 20: pts += 2
    elif pct_m14 < 40: pts += 1
    elif pct_m14 > 80: pts -= 2
    elif pct_m14 > 60: pts -= 1
    if pct_v30 > 80: pts -= 2
    elif pct_v30 > 60: pts -= 1
    elif pct_v30 < 20: pts += 1
    scores.append(max(-10, min(10, pts)))

df_clean = df_clean.reset_index(drop=True)
df_clean['score'] = scores[:len(df_clean)]
umbral = PARAMS['BNB/EUR']['umbral']

señales = df_clean[df_clean['score'] >= umbral].copy()
print(f"\n  Señales COMPRAR detectadas (score >= {umbral}): {len(señales)}")
print(f"\n  {'Fecha':<12} {'Precio':>8} {'Score':>6} {'Prob_reg0':>10} {'Prob_reg1':>10} {'Régimen':>8}")
print(f"  {'-'*60}")
for _, row in señales.tail(10).iterrows():
    reg = "CALMA" if row['prob_reg0'] > 0.5 else "TURBUL"
    print(f"  {str(row['date'].date()):<12} €{row['close']:>7.2f} {row['score']:>6.0f} {row['prob_reg0']:>10.2f} {row['prob_reg1']:>10.2f} {reg:>8}")

print("\n✅ Experimento completado")
print("Guarda los resultados en notas_investigacion.md")
