import pandas as pd
import numpy as np
from conexion import get_exchange
import warnings
warnings.filterwarnings('ignore')

exchange = get_exchange()

PARES = ['BNB/EUR', 'ETH/EUR', 'SOL/EUR']
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

def analizar_par(simbolo):
    ohlcv = exchange.fetch_ohlcv(simbolo, TIMEFRAME, limit=1000)
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
    df['fecha'] = pd.to_datetime(df['ts'], unit='ms')
    df = df.reset_index(drop=True)
    df['retorno'] = df['close'].pct_change()
    df['vol5d'] = df['retorno'].rolling(5).std()
    df['rsi'] = calcular_rsi(df['close'], RSI_PERIODO)

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
    sin_filtro = res['retorno_24h'].dropna()
    doble = res[(res['vol5d_pct'] < 70) & (res['rsi_pct'] < 30)]['retorno_24h'].dropna()

    return {
        'sin_filtro_wr': (sin_filtro > 0).mean() * 100,
        'sin_filtro_ret': sin_filtro.mean(),
        'doble_wr': (doble > 0).mean() * 100,
        'doble_ret': doble.mean(),
        'doble_n': len(doble)
    }

print("Analizando pares en 4h...\n")
for par in PARES:
    print(f"--- {par} ---")
    r = analizar_par(par)
    print(f"Sin filtro:    WR {r['sin_filtro_wr']:.1f}% | Ret {r['sin_filtro_ret']:.3f}%")
    print(f"Filtro doble:  WR {r['doble_wr']:.1f}% | Ret {r['doble_ret']:.3f}% (n={r['doble_n']})")
    print()
