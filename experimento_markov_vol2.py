"""
Experimento 6b — Markov Rolling con Volatilidad Realizada (ventana 150d)
Fix: ventana más amplia para garantizar convergencia del optimizador.
"""
import pandas as pd
import numpy as np
import os
import ccxt
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
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
print("EXPERIMENTO 6b — Markov Rolling Vol5d (ventana 150d)")
print("=" * 60)

VENTANA_MIN = 150
resultados = []

for i in range(VENTANA_MIN, len(df)):
    ventana = df['vol5d'].iloc[:i].values
    p_turbulento = np.nan
    for _ in range(3):  # 3 intentos
        try:
            modelo = MarkovRegression(ventana, k_regimes=2, switching_variance=True)
            res = modelo.fit(disp=False)
            vol_regimen = [res.params[f'sigma2[{k}]'] for k in range(2)]
            regimen_turbulento = int(np.argmax(vol_regimen))
            p_turbulento = res.smoothed_marginal_probabilities[regimen_turbulento][-1]
            break
        except:
            continue
    resultados.append({
        'date': df['date'].iloc[i],
        'precio': df['close'].iloc[i],
        'vol5d': df['vol5d'].iloc[i],
        'p_turbulento': p_turbulento
    })
    if i % 20 == 0:
        print(f"  Procesando día {i}/{len(df)}...")

res_df = pd.DataFrame(resultados)

print("\n--- Caso clave: Enero-Febrero 2026 ---")
caso = res_df[(res_df['date'] >= '2026-01-20') & (res_df['date'] <= '2026-02-10')]
for _, row in caso.iterrows():
    if np.isnan(row['p_turbulento']):
        estado = "NaN"
    else:
        estado = "TURBUL" if row['p_turbulento'] > 0.5 else "CALMA"
    print(f"{row['date'].strftime('%Y-%m-%d')} | €{row['precio']:.0f} | vol5d={row['vol5d']:.4f} | P(turb)={row['p_turbulento']:.2f} → {estado}")

nan_count = res_df['p_turbulento'].isna().sum()
print(f"\nNaN restantes: {nan_count}/{len(res_df)}")

print("\n--- Comparación ---")
print("Exp 2 (retornos rolling): detectó turbulencia 2026-02-01 (precio -12%)")
print("Exp 6b (vol5d rolling):   ¿detecta antes?")

print("\n--- Días en turbulencia (P>0.5) ---")
turb = res_df[res_df['p_turbulento'] > 0.5][['date','precio','p_turbulento']]
print(turb.to_string(index=False))
