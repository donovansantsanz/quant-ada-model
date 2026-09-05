import pandas as pd
import numpy as np
from conexion import get_exchange
import warnings
warnings.filterwarnings('ignore')

exchange = get_exchange()

SIMBOLO = 'BNB/EUR'
TIMEFRAME = '4h'
RSI_PERIODO = 14
FORWARD_BARS = 6
VENTANA_TRAIN = 90 * 6
VENTANA_TEST = 30 * 6

def calcular_rsi(precios, periodo=14):
    delta = precios.diff()
    ganancia = delta.clip(lower=0).rolling(periodo).mean()
    perdida = (-delta.clip(upper=0)).rolling(periodo).mean()
    rs = ganancia / perdida
    return 100 - (100 / (1 + rs))

print("Descargando datos...")
ohlcv = exchange.fetch_ohlcv(SIMBOLO, TIMEFRAME, limit=1000)
df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
df['fecha'] = pd.to_datetime(df['ts'], unit='ms')
df = df.reset_index(drop=True)
df['retorno'] = df['close'].pct_change()
df['vol5d'] = df['retorno'].rolling(5).std()
df['rsi'] = calcular_rsi(df['close'], RSI_PERIODO)

# Calcular percentiles rolling walk-forward
resultados = []
inicio = VENTANA_TRAIN

while inicio + VENTANA_TEST + FORWARD_BARS <= len(df):
    train = df.iloc[inicio - VENTANA_TRAIN:inicio]
    test = df.iloc[inicio:inicio + VENTANA_TEST]

    for i in range(len(test) - FORWARD_BARS):
        fila = test.iloc[i]
        vol5d_pct = (train['vol5d'] < fila['vol5d']).mean() * 100
        rsi_pct = (train['rsi'] < fila['rsi']).mean() * 100

        idx_global = inicio + i
        precio_entrada = df.loc[idx_global, 'close']
        precio_salida = df.loc[idx_global + FORWARD_BARS, 'close']
        retorno = (precio_salida - precio_entrada) / precio_entrada * 100

        resultados.append({
            'vol5d_pct': vol5d_pct,
            'rsi_pct': rsi_pct,
            'retorno_24h': retorno
        })

    inicio += VENTANA_TEST

res = pd.DataFrame(resultados)

# Grid search de umbrales
VOL_UMBRALES = [60, 70, 80]
RSI_UMBRALES = [20, 30, 40]

print("\n=== OPTIMIZACIÓN DE UMBRALES (walk-forward) ===\n")
print(f"{'vol<':<8} {'rsi<':<8} {'WR%':<10} {'Ret%':<10} {'n':<6}")
print("-" * 42)

mejores = []
for vol_u in VOL_UMBRALES:
    for rsi_u in RSI_UMBRALES:
        subset = res[(res['vol5d_pct'] < vol_u) & (res['rsi_pct'] < rsi_u)]['retorno_24h'].dropna()
        if len(subset) < 20:
            continue
        wr = (subset > 0).mean() * 100
        ret = subset.mean()
        print(f"p{vol_u:<7} p{rsi_u:<7} {wr:<10.1f} {ret:<10.3f} {len(subset):<6}")
        mejores.append((vol_u, rsi_u, wr, ret, len(subset)))

print("\n--- Referencia ---")
ref = res['retorno_24h'].dropna()
print(f"Sin filtro:    WR {(ref>0).mean()*100:.1f}% | Ret {ref.mean():.3f}% (n={len(ref)})")
