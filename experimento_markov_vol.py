"""
Experimento 6 — Markov-Switching Rolling con Volatilidad Realizada
Hipótesis: usar vol5d como variable de estado hace el modelo más reactivo
que usar retornos logarítmicos (Experimento 2).
La volatilidad explota antes de que el precio colapse del todo.
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
print("EXPERIMENTO 6 — Markov Rolling con Volatilidad Realizada")
print("=" * 60)
print(f"Datos: {len(df)} días | ventana mínima: 90 días")

# Rolling Markov sobre vol5d
VENTANA_MIN = 90
resultados = []

for i in range(VENTANA_MIN, len(df)):
    ventana = df['vol5d'].iloc[:i].values
    try:
        modelo = MarkovRegression(ventana, k_regimes=2, switching_variance=True)
        res = modelo.fit(disp=False)
        # Régimen con mayor volatilidad = turbulento
        vol_regimen = [res.params[f'sigma2[{k}]'] for k in range(2)]
        regimen_turbulento = int(np.argmax(vol_regimen))
        p_turbulento = res.smoothed_marginal_probabilities[regimen_turbulento][-1]
        resultados.append({
            'date': df['date'].iloc[i],
            'precio': df['close'].iloc[i],
            'vol5d': df['vol5d'].iloc[i],
            'p_turbulento': p_turbulento
        })
    except:
        resultados.append({
            'date': df['date'].iloc[i],
            'precio': df['close'].iloc[i],
            'vol5d': df['vol5d'].iloc[i],
            'p_turbulento': np.nan
        })

res_df = pd.DataFrame(resultados)

print("\n--- Caso clave: Enero 2026 ---")
caso = res_df[(res_df['date'] >= '2026-01-20') & (res_df['date'] <= '2026-02-10')]
for _, row in caso.iterrows():
    estado = "TURBUL" if row['p_turbulento'] > 0.5 else "CALMA"
    print(f"{row['date'].strftime('%Y-%m-%d')} | €{row['precio']:.0f} | vol5d={row['vol5d']:.4f} | P(turb)={row['p_turbulento']:.2f} → {estado}")

print("\n--- Comparación con Experimento 2 (retornos) ---")
print("Exp 2 (retornos): detectó turbulencia el 2026-02-01 (precio ya -12%)")
print("Exp 6 (vol5d):    ¿detecta antes?")

print("\n--- Umbrales de alerta (P > 0.4) ---")
alertas = res_df[res_df['p_turbulento'] > 0.4][['date','precio','p_turbulento']]
print(alertas.tail(20).to_string(index=False))

print("\n--- Estadísticas generales ---")
print(f"Días en turbulencia (P>0.5): {(res_df['p_turbulento'] > 0.5).sum()}")
print(f"Días en calma (P<0.5): {(res_df['p_turbulento'] < 0.5).sum()}")
