import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

# ── DESCARGAR HISTÓRICO DESDE BINANCE ───────────────────────────
print("Descargando datos históricos de Binance...")

exchange = ccxt.bitvavo()

# 365 días de velas diarias
velas = exchange.fetch_ohlcv('ADA/EUR', timeframe='1d', limit=365)

# Convertir a DataFrame
df = pd.DataFrame(velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df[['fecha', 'open', 'high', 'low', 'close', 'volume']]
df = df.sort_values('fecha').reset_index(drop=True)

print(f"✅ {len(df)} días descargados")
print(f"   Desde: {df['fecha'].iloc[0].strftime('%Y-%m-%d')}")
print(f"   Hasta: {df['fecha'].iloc[-1].strftime('%Y-%m-%d')}")
print(f"   Precio más reciente: ${df['close'].iloc[-1]:.4f}")

# ── CALCULAR VOLATILIDAD Y DRIFT ─────────────────────────────────
log_returns = np.log(df['close'] / df['close'].shift(1)).dropna()
volatilidad = log_returns.std()
drift       = log_returns.mean()

print(f"   Volatilidad diaria: {volatilidad:.6f}")
print(f"   Drift diario:       {drift:.6f}")

# ── GUARDAR CSV ──────────────────────────────────────────────────
df.to_csv('ada_historico.csv', index=False)
print("✅ Datos guardados en ada_historico.csv")