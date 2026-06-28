import ccxt
import pandas as pd
import numpy as np
from scipy import stats

def obtener_datos(simbolo, dias=500):
    exchange = ccxt.binance()
    velas = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=dias)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.sort_values('fecha').reset_index(drop=True)

def calcular_scores(precios):
    mm7  = precios.rolling(7).mean()
    mm20 = precios.rolling(20).mean()
    dist_mm20   = (precios - mm20) / mm20
    dist_mm7    = (precios - mm7)  / mm7
    vol_30      = precios.pct_change().rolling(30).std()
    momentum_14 = precios / precios.shift(14) - 1
    scores = []
    for i in range(50, len(precios)):
        pct_mm20 = stats.percentileofscore(dist_mm20.iloc[:i].dropna(), dist_mm20.iloc[i])
        pct_mm7  = stats.percentileofscore(dist_mm7.iloc[:i].dropna(),  dist_mm7.iloc[i])
        pct_vol  = stats.percentileofscore(vol_30.iloc[:i].dropna(),    vol_30.iloc[i])
        pct_mom  = stats.percentileofscore(momentum_14.iloc[:i].dropna(), momentum_14.iloc[i])
        puntos = 0
        if pct_mm20 < 20:   puntos += 3
        elif pct_mm20 < 40: puntos += 1
        elif pct_mm20 > 80: puntos -= 3
        elif pct_mm20 > 60: puntos -= 1
        if pct_mm7 < 20:    puntos += 2
        elif pct_mm7 < 40:  puntos += 1
        elif pct_mm7 > 80:  puntos -= 2
        elif pct_mm7 > 60:  puntos -= 1
        if pct_mom < 20:    puntos += 2
        elif pct_mom < 40:  puntos += 1
        elif pct_mom > 80:  puntos -= 2
        elif pct_mom > 60:  puntos -= 1
        if pct_vol > 80:    puntos -= 2
        elif pct_vol > 60:  puntos -= 1
        elif pct_vol < 20:  puntos += 1
        scores.append(max(-10, min(10, puntos)))
    return scores

def backtesting_periodo(scores, precios, umbral, stop, take, inicio, fin):
    retornos = []
    for i in range(inicio, min(fin, len(scores)-14)):
        if scores[i] >= umbral:
            p_entrada = precios.iloc[i]
            p_stop    = p_entrada * (1 - stop)
            p_take    = p_entrada * (1 + take)
            retorno   = None
            for j in range(1, 15):
                p = precios.iloc[i+j]
                if p <= p_stop:
                    retorno = -stop; break
                elif p >= p_take:
                    retorno = take;  break
            if retorno is None:
                retorno = (precios.iloc[i+14] - p_entrada) / p_entrada
            retornos.append(retorno)
    if len(retornos) < 3:
        return -999, 0
    r = np.array(retornos)
    if r.std() == 0:
        sharpe = 99.0 if r.mean() > 0 else -99.0
    else:
        sharpe = r.mean() / r.std() * np.sqrt(252)
    return round(sharpe, 2), len(retornos)

UMBRAL = 6
STOP   = 0.03
TAKE   = 0.08
VOLUMEN_MIN_USD = 20_000_000

YA_EN_SISTEMA = {'ADA/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'BTC/USDT', 'AVAX/USDT'}

CANDIDATOS = [
    'XRP/USDT', 'DOGE/USDT', 'LINK/USDT', 'DOT/USDT', 'POL/USDT',
    'LTC/USDT', 'ATOM/USDT', 'NEAR/USDT', 'APT/USDT', 'ARB/USDT',
    'OP/USDT', 'INJ/USDT', 'FIL/USDT', 'TON/USDT', 'SUI/USDT',
]

print("=" * 70)
print("  SCREENER DE ACTIVOS — Walk-Forward con correccion multiples pruebas")
print("=" * 70)

exchange = ccxt.binance()

print(f"\n  Filtro de liquidez (volumen diario > ${VOLUMEN_MIN_USD/1e6:.0f}M)...\n")
candidatos_liquidos = []
for simbolo in CANDIDATOS:
    if simbolo in YA_EN_SISTEMA:
        continue
    try:
        ticker = exchange.fetch_ticker(simbolo)
        vol_usd = ticker['quoteVolume']
        if vol_usd and vol_usd >= VOLUMEN_MIN_USD:
            candidatos_liquidos.append(simbolo)
            print(f"  OK {simbolo:<12} volumen ${vol_usd/1e6:>6.0f}M")
        else:
            v = vol_usd/1e6 if vol_usd else 0
            print(f"  NO {simbolo:<12} volumen ${v:>6.0f}M — insuficiente")
    except Exception as e:
        print(f"  ?? {simbolo:<12} no disponible ({str(e)[:30]})")

n_pruebas = len(candidatos_liquidos)
UMBRAL_BASE = 1.0
umbral_corregido = round(UMBRAL_BASE + 0.15 * np.log(max(n_pruebas, 1)), 2)

print(f"\n  Walk-forward sobre {n_pruebas} candidatos liquidos")
print(f"  Umbral Sharpe base: {UMBRAL_BASE} | corregido por {n_pruebas} pruebas: {umbral_corregido}\n")

print(f"  {'Activo':<12} {'Train':>14} {'Test':>14} {'Veredicto':>16}")
print("  " + "-" * 60)

aprobados = []
for simbolo in candidatos_liquidos:
    try:
        df = obtener_datos(simbolo, dias=500)
        precios = df['close']
        if len(precios) < 200:
            print(f"  {simbolo:<12} historico insuficiente")
            continue
        scores = calcular_scores(precios)
        precios_trim = precios.iloc[50:].reset_index(drop=True)
        n = len(scores)
        corte = int(n * 0.74)
        sharpe_train, ops_train = backtesting_periodo(scores, precios_trim, UMBRAL, STOP, TAKE, 0, corte)
        sharpe_test, ops_test = backtesting_periodo(scores, precios_trim, UMBRAL, STOP, TAKE, corte, n)
        if sharpe_test >= umbral_corregido and ops_test >= 5:
            veredicto = "APROBADO"
            aprobados.append((simbolo, sharpe_train, sharpe_test, ops_test))
        elif sharpe_test > 0:
            veredicto = "Debil"
        else:
            veredicto = "Sobreajuste"
        print(f"  {simbolo:<12} {sharpe_train:>7.2f} ({ops_train:>2}ops)  {sharpe_test:>7.2f} ({ops_test:>2}ops)  {veredicto:>16}")
    except Exception as e:
        print(f"  {simbolo:<12} error: {str(e)[:35]}")

print("\n" + "=" * 70)
if aprobados:
    print(f"  CANDIDATOS APROBADOS ({len(aprobados)}):")
    for simbolo, st, stest, ops in aprobados:
        print(f"    {simbolo:<12} Sharpe test {stest:.2f} ({ops} ops)")
    print(f"\n  Recomendacion: pasar a OBSERVACION primero (como AVAX), no directo a real.")
else:
    print(f"  NINGUN candidato supera el umbral corregido ({umbral_corregido}).")
    print(f"  Esto es normal y SANO — el filtro funciona y no anades activos por azar.")
print("=" * 70)
