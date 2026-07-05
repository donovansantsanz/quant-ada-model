import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from config import PARAMS, PARAMS_OBS

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

def backtesting_completo(simbolo, umbral, stop, take, kelly, dias=500):
    exchange = ccxt.bitvavo()
    velas = exchange.fetch_ohlcv(simbolo, timeframe='1d', limit=dias)
    df = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    precios = df['close']
    scores = calcular_scores(precios)
    precios_trim = precios.iloc[50:].reset_index(drop=True)
    n = len(scores)
    corte = int(n * 0.74)

    def run(inicio, fin):
        retornos = []
        equity = [500.0]
        for i in range(inicio, min(fin, n-14)):
            if scores[i] >= umbral:
                p_entrada = precios_trim.iloc[i]
                retorno = None
                for j in range(1, 15):
                    p = precios_trim.iloc[i+j]
                    if p <= p_entrada * (1-stop):
                        retorno = -stop; break
                    elif p >= p_entrada * (1+take):
                        retorno = take; break
                if retorno is None:
                    retorno = (precios_trim.iloc[i+14] - p_entrada) / p_entrada
                retornos.append(retorno)
                sizing = min(kelly/100, 0.10) if kelly > 0 else 0.025
                equity.append(equity[-1] + equity[-1] * sizing * retorno)

        if len(retornos) < 3:
            return None
        r = np.array(retornos)
        equity = np.array(equity)
        peak = np.maximum.accumulate(equity)
        max_dd = ((equity - peak) / peak * 100).min()
        sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
        win_rate = sum(1 for x in retornos if x > 0) / len(retornos) * 100
        return {
            'sharpe': round(sharpe, 2),
            'win_rate': round(win_rate, 1),
            'max_dd': round(max_dd, 1),
            'ops': len(retornos),
            'retorno_total': round((equity[-1] - 500) / 500 * 100, 1),
        }

    train = run(0, corte)
    test  = run(corte, n)
    return train, test

print("=" * 60)
print(f"  FICHA TÉCNICA — Quant Trading System V2")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 60)

print("\n📊 ACTIVOS OPERATIVOS\n")
print(f"  {'Activo':<12} {'Sharpe train':>13} {'Sharpe test':>12} {'Win rate':>10} {'Max DD':>8} {'Kelly':>7}")
print("  " + "─" * 58)

for simbolo, p in PARAMS.items():
    if p['kelly'] <= 0:
        continue
    train, test = backtesting_completo(simbolo, p['umbral'], p['stop'], p['take'], p['kelly'])
    if train and test:
        v = "✅" if test['sharpe'] > 1.0 else "⚠️ "
        print(f"  {simbolo:<12} {train['sharpe']:>12.2f} {test['sharpe']:>12.2f} {test['win_rate']:>9.1f}% {test['max_dd']:>7.1f}% {p['kelly']:>6.1f}%  {v}")

print("\n👁  ACTIVOS EN OBSERVACIÓN\n")
print(f"  {'Activo':<12} {'Umbral':>7} {'BTC filter':>11} {'Kelly':>7}")
print("  " + "─" * 40)
for simbolo, p in PARAMS_OBS.items():
    filtro = "Activo" if p['filtro_btc'] else "Inactivo"
    print(f"  {simbolo:<12} {p['umbral']:>7} {filtro:>11}    pendiente")

print("\n SCRIPTS EN PRODUCCION\n")
scripts = [
    ("config.py",              "Parametros sistema diario"),
    ("config_4h.py",           "Parametros sistema 4h"),
    ("monitor_v2.py",          "Monitor diario — alertas Telegram"),
    ("monitor_4h.py",          "Monitor 4h — BNB/EUR"),
    ("paper_trading.py",       "Paper trading diario"),
    ("paper_trading_4h.py",    "Paper trading 4h"),
    ("ejecutor.py",            "Ejecucion automatica — Binance API"),
    ("evaluador_real.py",      "Cierre automatico + trailing stop"),
    ("evaluador.py",           "Resumen semanal automatico"),
    ("dashboard.py",           "Estado del sistema en tiempo real"),
    ("watchdog.py",            "Monitoreo de salud del sistema"),
    ("monitor_salud.py",       "Kelly rolling 90 dias por activo"),
    ("walk_forward.py",        "Validacion out-of-sample diario"),
    ("walk_forward_4h.py",     "Validacion out-of-sample 4h"),
    ("optimizador.py",         "Calibracion de parametros"),
    ("analisis_drawdown.py",   "Analisis de drawdown y rachas"),
    ("stress_test.py",         "Stress test historico 2021-2026"),
    ("resumen_modelo.py",      "Esta ficha tecnica"),
    ("historial.py",           "Historial limpio de senales"),
    ("historial_4h.py",        "Historial limpio senales 4h"),
]
for nombre, desc in scripts:
    print(f"  {nombre:<27} {desc}")
print("\n INFRAESTRUCTURA\n")
print("  Servidor:   Hetzner CX22 — Ubuntu 24.04 — 24/7")
print("  IP:         116.203.91.120")
print("  Cron:       6 tareas activas")
print("    10:30 UTC diario  — monitor_v2 + paper_trading")
print("    */4h              — monitor_4h + paper_trading_4h")
print("    */1h              — watchdog + evaluador_real")
print("    Lunes 11:00 UTC   — evaluador (resumen semanal)")
print("    Domingo 10:00 UTC — monitor_salud")
print("  Exchange:   Binance (API key IP-restringida)")
print("  Capital:    $1000 USDC base | Kelly/4 | max 10% por activo")
print("  Alertas:    Telegram Bot API")
print("\n" + "=" * 60)
print("  github.com/donovansantsanz/quant-ada-model")
print("=" * 60 + "\n")
