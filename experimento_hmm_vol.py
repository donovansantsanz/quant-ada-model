"""
Experimento 7 — Hidden Markov Model (hmmlearn) con Volatilidad Realizada
Alternativa al Markov-switching de statsmodels.
Algoritmo: Baum-Welch (EM) — más estable en ventanas cortas que MLE.
Hipótesis: converge en modo rolling donde statsmodels fallaba.
"""
import pandas as pd
import numpy as np
import os
import ccxt
from hmmlearn import hmm
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))
exchange = ccxt.bitvavo({
    'apiKey': os.getenv("BITVAVO_API_KEY"),
    'secret': os.getenv("BITVAVO_API_SECRET"),
    'enableRateLimit': True,
    'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
})

ohlcv = exchange.fetch_ohlcv('BNB/EUR', '1d', limit=400)
df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
df['date'] = pd.to_datetime(df['ts'], unit='ms')
df = df.sort_values('date').reset_index(drop=True)
df['ret'] = np.log(df['close'] / df['close'].shift(1))
df['vol5d'] = df['ret'].rolling(5).std()
df = df.dropna().reset_index(drop=True)

print("=" * 60)
print("EXPERIMENTO 7 — HMM (Baum-Welch) con Vol5d Rolling")
print("=" * 60)
print(f"Datos: {len(df)} días | ventana mínima: 120 días")

VENTANA_MIN = 120
resultados = []
nan_count = 0

for i in range(VENTANA_MIN, len(df)):
    ventana = df['vol5d'].iloc[:i].values.reshape(-1, 1)
    p_turbulento = np.nan
    try:
        modelo = hmm.GaussianHMM(
            n_components=2,
            covariance_type="full",
            n_iter=200,
            random_state=42
        )
        modelo.fit(ventana)
        # Predecir estado actual (último día)
        estado_actual = modelo.predict(ventana)[-1]
        # Régimen turbulento = mayor varianza
        varianzas = [modelo.covars_[k][0][0] for k in range(2)]
        regimen_turbulento = int(np.argmax(varianzas))
        # Probabilidad posterior del último día
        probs = modelo.predict_proba(ventana)[-1]
        p_turbulento = probs[regimen_turbulento]
    except:
        nan_count += 1

    resultados.append({
        'date': df['date'].iloc[i],
        'precio': df['close'].iloc[i],
        'vol5d': df['vol5d'].iloc[i],
        'p_turbulento': p_turbulento
    })

    if i % 30 == 0:
        print(f"  Día {i}/{len(df)} — NaN hasta ahora: {nan_count}")

res_df = pd.DataFrame(resultados)

print(f"\nTotal NaN: {nan_count}/{len(res_df)}")

print("\n--- Caso clave: Enero-Febrero 2026 ---")
caso = res_df[(res_df['date'] >= '2026-01-20') & (res_df['date'] <= '2026-02-10')]
for _, row in caso.iterrows():
    if np.isnan(row['p_turbulento']):
        estado = "NaN"
    else:
        estado = "TURBUL" if row['p_turbulento'] > 0.5 else "CALMA"
    print(f"{row['date'].strftime('%Y-%m-%d')} | €{row['precio']:.0f} | vol5d={row['vol5d']:.4f} | P(turb)={row['p_turbulento']:.2f} → {estado}")

print("\n--- Comparación con experimentos anteriores ---")
print("Exp 2 (statsmodels retornos rolling): detectó turbulencia 2026-02-01")
print("Exp 6b (statsmodels vol5d rolling):   245/245 NaN, no convergió")
print("Exp 7 (hmmlearn vol5d rolling):       ¿converge? ¿detecta antes?")

print("\n--- Días en turbulencia (P>0.5) ---")
turb = res_df[res_df['p_turbulento'] > 0.5][['date','precio','p_turbulento']]
if len(turb) > 0:
    print(turb.to_string(index=False))
else:
    print("Ninguno")
