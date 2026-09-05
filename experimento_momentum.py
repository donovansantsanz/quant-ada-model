import pandas as pd
import numpy as np
from conexion import get_exchange
import warnings
warnings.filterwarnings('ignore')

exchange = get_exchange()

SIMBOLO = 'BNB/EUR'
TIMEFRAME = '4h'
FORWARD_BARS = 6
VENTANA_TRAIN = 90 * 6
VENTANA_TEST = 30 * 6

print("Descargando datos...")
ohlcv = exchange.fetch_ohlcv(SIMBOLO, TIMEFRAME, limit=1000)
df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
df['fecha'] = pd.to_datetime(df['ts'], unit='ms')
df = df.reset_index(drop=True)
df['retorno'] = df['close'].pct_change()
df['mom_5']  = df['close'] / df['close'].shift(5) - 1
df['mom_10'] = df['close'] / df['close'].shift(10) - 1
df['mom_20'] = df['close'] / df['close'].shift(20) - 1

resultados = []
inicio = VENTANA_TRAIN

while inicio + VENTANA_TEST + FORWARD_BARS <= len(df):
    train = df.iloc[inicio - VENTANA_TRAIN:inicio]
    test  = df.iloc[inicio:inicio + VENTANA_TEST]

    for i in range(len(test) - FORWARD_BARS):
        fila = test.iloc[i]
        mom5_pct  = (train['mom_5']  < fila['mom_5']).mean()  * 100
        mom10_pct = (train['mom_10'] < fila['mom_10']).mean() * 100
        mom20_pct = (train['mom_20'] < fila['mom_20']).mean() * 100

        idx_global = inicio + i
        precio_entrada = df.loc[idx_global, 'close']
        precio_salida  = df.loc[idx_global + FORWARD_BARS, 'close']
        retorno = (precio_salida - precio_entrada) / precio_entrada * 100

        resultados.append({
            'mom5_pct':  mom5_pct,
            'mom10_pct': mom10_pct,
            'mom20_pct': mom20_pct,
            'retorno_24h': retorno
        })

    inicio += VENTANA_TEST

res = pd.DataFrame(resultados)

sin_filtro = res['retorno_24h'].dropna()

# Momentum fuerte: precio en percentil alto de retornos
mom_fuerte  = res[(res['mom5_pct'] > 70) & (res['mom10_pct'] > 70)]['retorno_24h'].dropna()
mom_extremo = res[(res['mom5_pct'] > 80) & (res['mom10_pct'] > 80)]['retorno_24h'].dropna()

# Comparar con mean reversion (precio en percentil bajo)
mean_rev = res[(res['mom5_pct'] < 30) & (res['mom10_pct'] < 30)]['retorno_24h'].dropna()

print(f"\nTotal barras fuera de muestra: {len(res)}")
print("\n=== MOMENTUM vs MEAN REVERSION (walk-forward) ===\n")
print(f"{'Estrategia':<20} {'WR%':<10} {'Ret%':<10} {'n':<6}")
print("-" * 46)
print(f"{'Sin filtro':<20} {(sin_filtro>0).mean()*100:<10.1f} {sin_filtro.mean():<10.3f} {len(sin_filtro):<6}")
print(f"{'Mean reversion':<20} {(mean_rev>0).mean()*100:<10.1f} {mean_rev.mean():<10.3f} {len(mean_rev):<6}")
print(f"{'Momentum >p70':<20} {(mom_fuerte>0).mean()*100:<10.1f} {mom_fuerte.mean():<10.3f} {len(mom_fuerte):<6}")
print(f"{'Momentum >p80':<20} {(mom_extremo>0).mean()*100:<10.1f} {mom_extremo.mean():<10.3f} {len(mom_extremo):<6}")
