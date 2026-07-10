import pandas as pd
import numpy as np
import os
from datetime import datetime

datos_dir = os.path.expanduser('~/proyectos-quant/datos')
activos = ['ADA/EUR', 'SOL/EUR', 'ETH/EUR', 'BNB/EUR', 'BTC/EUR']

def calcular_indicadores(df):
    """Calcula RSI, MA20, Bollinger, volatilidad"""
    df = df.copy()
    
    # RSI (14 períodos)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MA20
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma20_slope'] = df['ma20'].diff()
    
    # Bollinger (20, 2)
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['sma20'] + (df['std20'] * 2)
    df['bb_lower'] = df['sma20'] - (df['std20'] * 2)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    
    # Volatilidad (std de returns últimos 20d)
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(window=20).std()
    
    return df

print("=" * 80)
print("DETECTOR DE RÉGIMEN — 7 JULIO 2026")
print("=" * 80)

for par in activos:
    filename = os.path.join(datos_dir, f"{par.replace('/', '_')}_90d.csv")
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    df = calcular_indicadores(df)
    
    # Últimos valores
    ultimo = df.iloc[-1]
    rsi_actual = ultimo['rsi']
    ma20_slope = ultimo['ma20_slope']
    precio = ultimo['close']
    ma20 = ultimo['ma20']
    bb_width = ultimo['bb_width']
    volatility = ultimo['volatility']
    
    # Clasificación RSI
    if rsi_actual < 30:
        rsi_regime = "OVERSOLD"
    elif rsi_actual > 70:
        rsi_regime = "OVERBOUGHT"
    else:
        rsi_regime = "NEUTRAL"
    
    # Clasificación MA20 slope
    if ma20_slope > 0.01:
        ma_regime = "TRENDING UP"
    elif ma20_slope < -0.01:
        ma_regime = "TRENDING DOWN"
    else:
        ma_regime = "FLAT"
    
    # Clasificación volatilidad
    vol_percentil = (df['volatility'] < volatility).sum() / len(df) * 100
    if vol_percentil < 33:
        vol_regime = "COMPRIMIDA"
    elif vol_percentil > 66:
        vol_regime = "EXPANDIDA"
    else:
        vol_regime = "NORMAL"
    
    # Precio vs MA20
    if precio > ma20:
        price_position = "ARRIBA de MA20"
    else:
        price_position = "ABAJO de MA20"
    
    print(f"\n{par}")
    print(f"  Precio: {precio:.4f} | MA20: {ma20:.4f} → {price_position}")
    print(f"  RSI: {rsi_actual:.2f} → {rsi_regime}")
    print(f"  MA20 slope: {ma20_slope:.6f} → {ma_regime}")
    print(f"  Volatilidad: {volatility:.6f} ({vol_percentil:.0f} percentil) → {vol_regime}")
    print(f"  BB Width: {bb_width:.4f}")
    
    # Clasificación final
    if precio > ma20 and rsi_actual > 50 and ma_regime == "TRENDING UP":
        final = "🔴 RÉGIMEN ADVERSO (mean-reversion está muerta)"
    elif precio < ma20 and rsi_actual < 50:
        final = "🟢 RÉGIMEN FAVORABLE (mean-reversion posible)"
    else:
        final = "🟡 RÉGIMEN MIXTO (vigilancia)"
    
    print(f"  {final}")

print("\n" + "=" * 80)
