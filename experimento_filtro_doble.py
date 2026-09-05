import pandas as pd
import numpy as np
from conexion import get_exchange
import warnings
warnings.filterwarnings('ignore')

exchange = get_exchange()

# Parámetros
SIMBOLO = 'BNB/EUR'
TIMEFRAME = '4h'
VENTANA = 90  # días para percentiles
RSI_PERIODO = 14

def calcular_rsi(precios, periodo=14):
    delta = precios.diff()
    ganancia = delta.clip(lower=0).rolling(periodo).mean()
    perdida = (-delta.clip(upper=0)).rolling(periodo).mean()
    rs = ganancia / perdida
    return 100 - (100 / (1 + rs))

# Descargar datos
print("Descargando datos...")
ohlcv = exchange.fetch_ohlcv(SIMBOLO, TIMEFRAME, limit=1000)
df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
df['fecha'] = pd.to_datetime(df['ts'], unit='ms')
df = df.set_index('fecha')

# Calcular vol5d y RSI
df['retorno'] = df['close'].pct_change()
df['vol5d'] = df['retorno'].rolling(5).std()
df['rsi'] = calcular_rsi(df['close'], RSI_PERIODO)

# Percentiles rolling
resultados = []
ventana_bars = VENTANA * 6  # 4h → 6 barras/día

for i in range(ventana_bars, len(df)):
    ventana = df.iloc[i-ventana_bars:i]
    fila = df.iloc[i]
    
    vol5d_pct = (ventana['vol5d'] < fila['vol5d']).mean() * 100
    rsi_pct = (ventana['rsi'] < fila['rsi']).mean() * 100
    
    resultados.append({
        'fecha': fila.name,
        'close': fila['close'],
        'vol5d_pct': vol5d_pct,
        'rsi_pct': rsi_pct,
        'rsi': fila['rsi']
    })

res = pd.DataFrame(resultados)

# Estadísticas
print(f"\nTotal barras analizadas: {len(res)}")
print(f"Sin filtro — señales posibles: {len(res)}")
print(f"Filtro vol5d<p70 — señales: {(res['vol5d_pct'] < 70).sum()}")
print(f"Filtro doble (vol5d<p70 + RSI<p30) — señales: {((res['vol5d_pct'] < 70) & (res['rsi_pct'] < 30)).sum()}")

print(f"\nCorrelación vol5d_pct vs rsi_pct: {res['vol5d_pct'].corr(res['rsi_pct']):.3f}")
print("\nEstadísticas RSI percentil cuando vol5d<p70:")
subset = res[res['vol5d_pct'] < 70]
print(subset['rsi_pct'].describe())

# Retorno forward (24h = 6 barras de 4h)
FORWARD_BARS = 6

df_reset = df.reset_index()
res['retorno_24h'] = np.nan

for idx, row in res.iterrows():
    pos = df_reset[df_reset['fecha'] == row['fecha']].index
    if len(pos) == 0:
        continue
    pos = pos[0]
    if pos + FORWARD_BARS < len(df_reset):
        precio_entrada = df_reset.loc[pos, 'close']
        precio_salida = df_reset.loc[pos + FORWARD_BARS, 'close']
        res.at[idx, 'retorno_24h'] = (precio_salida - precio_entrada) / precio_entrada * 100

# Comparación de retornos
sin_filtro = res['retorno_24h'].dropna()
solo_vol = res[res['vol5d_pct'] < 70]['retorno_24h'].dropna()
doble = res[(res['vol5d_pct'] < 70) & (res['rsi_pct'] < 30)]['retorno_24h'].dropna()

print("\n=== RETORNO MEDIO 24h TRAS SEÑAL ===")
print(f"Sin filtro:      {sin_filtro.mean():.3f}% (n={len(sin_filtro)})")
print(f"Solo vol5d<p70:  {solo_vol.mean():.3f}% (n={len(solo_vol)})")
print(f"Doble filtro:    {doble.mean():.3f}% (n={len(doble)})")

print("\n=== % DE SEÑALES CON RETORNO POSITIVO ===")
print(f"Sin filtro:      {(sin_filtro > 0).mean()*100:.1f}%")
print(f"Solo vol5d<p70:  {(solo_vol > 0).mean()*100:.1f}%")
print(f"Doble filtro:    {(doble > 0).mean()*100:.1f}%")
