"""
screener_yfinance.py — Exploración experimental
Aplica el modelo de scoring percentil del Sistema V2 a activos
fuera de cripto: ETFs, forex, commodities.
NO modifica el sistema real — solo investigación.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats

# ── Activos a explorar ───────────────────────────────────────────
CANDIDATOS = {
    'GLD':     {'nombre': 'Oro ETF',       'stop': 0.02, 'take': 0.06, 'umbral': 5},
    'SPY':     {'nombre': 'S&P 500 ETF',   'stop': 0.02, 'take': 0.06, 'umbral': 5},
    'QQQ':     {'nombre': 'Nasdaq ETF',    'stop': 0.02, 'take': 0.06, 'umbral': 5},
    'EURUSD=X':{'nombre': 'EUR/USD',       'stop': 0.01, 'take': 0.03, 'umbral': 5},
    'GC=F':    {'nombre': 'Futuros Oro',   'stop': 0.02, 'take': 0.06, 'umbral': 5},
    'BTC-USD': {'nombre': 'BTC (control)', 'stop': 0.02, 'take': 0.08, 'umbral': 5},
}

PERIODO_TRAIN = '5y'   # Datos históricos
PERIODO_TEST  = '1y'   # Out-of-sample

def obtener_datos(ticker, periodo):
    df = yf.download(ticker, period=periodo, interval='1d', progress=False)
    if df.empty:
        return None
    # Aplanar columnas MultiIndex si existen
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[['Close']].copy()
    df.columns = ['close']
    df = df.dropna().reset_index()
    return df

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

def calcular_kelly(precios, scores, umbral, stop, take):
    ganancias, perdidas = [], []
    for i in range(len(scores) - 14):
        if scores[i] >= umbral:
            p_entrada = precios.iloc[i]
            retorno = None
            for j in range(1, 15):
                p = precios.iloc[i + j]
                if p <= p_entrada * (1 - stop):
                    retorno = -stop; break
                elif p >= p_entrada * (1 + take):
                    retorno = take; break
            if retorno is None:
                retorno = (precios.iloc[i + 14] - p_entrada) / p_entrada
            if retorno > 0:
                ganancias.append(retorno)
            else:
                perdidas.append(abs(retorno))
    if not ganancias or not perdidas:
        return None, 0, 0
    p = len(ganancias) / (len(ganancias) + len(perdidas))
    b = np.mean(ganancias) / np.mean(perdidas)
    kelly = (p * b - (1 - p)) / b * 100
    n_ops = len(ganancias) + len(perdidas)
    win_rate = p * 100
    return round(kelly, 1), n_ops, round(win_rate, 1)

def walk_forward(ticker, params):
    # Train: datos completos
    df_train = obtener_datos(ticker, PERIODO_TRAIN)
    if df_train is None or len(df_train) < 200:
        return None

    precios_train = df_train['close']
    scores_train  = calcular_scores(precios_train)
    kelly_train, ops_train, wr_train = calcular_kelly(
        precios_train.iloc[50:].reset_index(drop=True),
        scores_train, params['umbral'], params['stop'], params['take']
    )

    # Test: último año (out-of-sample)
    df_test = obtener_datos(ticker, PERIODO_TEST)
    if df_test is None or len(df_test) < 100:
        return None

    precios_test = df_test['close']
    scores_test  = calcular_scores(precios_test)
    kelly_test, ops_test, wr_test = calcular_kelly(
        precios_test.iloc[50:].reset_index(drop=True),
        scores_test, params['umbral'], params['stop'], params['take']
    )

    return {
        'kelly_train': kelly_train,
        'ops_train':   ops_train,
        'wr_train':    wr_train,
        'kelly_test':  kelly_test,
        'ops_test':    ops_test,
        'wr_test':     wr_test,
    }

# ── Ejecutar screener ────────────────────────────────────────────
print("=" * 70)
print("  SCREENER EXPERIMENTAL — Modelo V2 en activos no cripto")
print("  Usando yfinance | Train: 5 años | Test: 1 año (out-of-sample)")
print("=" * 70)
print(f"\n  {'Activo':<12} {'Nombre':<18} {'Kelly Train':>12} {'Kelly Test':>11} {'Ops Test':>9} {'WR Test':>8}")
print("  " + "-" * 68)

aprobados = []
for ticker, params in CANDIDATOS.items():
    resultado = walk_forward(ticker, params)
    if resultado is None:
        print(f"  {ticker:<12} {params['nombre']:<18} {'Sin datos':>12}")
        continue

    kt = f"{resultado['kelly_train']}%" if resultado['kelly_train'] is not None else "N/A"
    kte = f"{resultado['kelly_test']}%" if resultado['kelly_test'] is not None else "N/A"
    veredicto = "✅ APROBADO" if resultado['kelly_test'] and resultado['kelly_test'] > 0 else "❌ Rechazado"

    print(f"  {ticker:<12} {params['nombre']:<18} {kt:>12} {kte:>11} {resultado['ops_test']:>9} {resultado['wr_test']:>7}%  {veredicto}")

    if resultado['kelly_test'] and resultado['kelly_test'] > 0:
        aprobados.append((ticker, params['nombre'], resultado['kelly_test']))

print("\n" + "=" * 70)
if aprobados:
    print(f"\n  ACTIVOS CON KELLY POSITIVO EN TEST:")
    for ticker, nombre, kt in sorted(aprobados, key=lambda x: x[2], reverse=True):
        print(f"    {ticker:<12} {nombre:<18} Kelly test: {kt}%")
else:
    print("  Ningún activo con Kelly positivo en test.")
print("=" * 70)
