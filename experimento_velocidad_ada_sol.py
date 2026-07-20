import pandas as pd
import numpy as np
import os
import ccxt
from dotenv import load_dotenv
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))

exchange = ccxt.bitvavo({
    'apiKey': os.getenv("BITVAVO_API_KEY"),
    'secret': os.getenv("BITVAVO_API_SECRET"),
    'enableRateLimit': True,
    'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
})

print("=" * 65)
print("EXPERIMENTO 3c — Velocidad de caida en ADA/EUR y SOL/EUR")
print("=" * 65)

from config import PARAMS

def analizar_activo(par):
    params = PARAMS[par]
    umbral_score = params['umbral']
    stop = params['stop']
    take = params['take']

    ohlcv = exchange.fetch_ohlcv(par, '1d', limit=365)
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
    df['date'] = pd.to_datetime(df['ts'], unit='ms')
    df = df.sort_values('date').reset_index(drop=True)
    df['ret'] = df['close'].pct_change()
    df['ret7d'] = df['close'].pct_change(7)
    df['vol5d'] = df['ret'].rolling(5).std()
    vol5d_vals = df['vol5d'].dropna().values
    df['vol5d_pct'] = df['vol5d'].apply(
        lambda x: stats.percentileofscore(vol5d_vals, x) if pd.notna(x) else np.nan
    )

    precios = df['close'].reset_index(drop=True)
    mm20 = precios.rolling(20).mean()
    mm7  = precios.rolling(7).mean()
    dist_mm20 = (precios - mm20) / mm20
    dist_mm7  = (precios - mm7) / mm7
    mom14 = precios / precios.shift(14) - 1
    vol30 = precios.pct_change().rolling(30).std()

    scores = []
    for i in range(len(precios)):
        if i < 50:
            scores.append(None)
            continue
        pa = precios.iloc[i]
        p1 = stats.percentileofscore(dist_mm20.iloc[:i].dropna(), (pa - mm20.iloc[i]) / mm20.iloc[i])
        p2 = stats.percentileofscore(dist_mm7.iloc[:i].dropna(),  (pa - mm7.iloc[i]) / mm7.iloc[i])
        p3 = stats.percentileofscore(mom14.iloc[:i].dropna(), mom14.iloc[i])
        p4 = stats.percentileofscore(vol30.iloc[:i].dropna(), vol30.iloc[i])
        pts = 0
        if p1 < 20: pts += 3
        elif p1 < 40: pts += 1
        elif p1 > 80: pts -= 3
        elif p1 > 60: pts -= 1
        if p2 < 20: pts += 2
        elif p2 < 40: pts += 1
        elif p2 > 80: pts -= 2
        elif p2 > 60: pts -= 1
        if p3 < 20: pts += 2
        elif p3 < 40: pts += 1
        elif p3 > 80: pts -= 2
        elif p3 > 60: pts -= 1
        if p4 > 80: pts -= 2
        elif p4 > 60: pts -= 1
        elif p4 < 20: pts += 1
        scores.append(max(-10, min(10, pts)))

    df['score'] = scores

    def simular(df_sub, umbral_ret7d=None, umbral_vol=None):
        retornos = []
        for i in range(len(df_sub)):
            row = df_sub.iloc[i]
            if row.get('score') is None or row['score'] < umbral_score:
                continue
            if umbral_ret7d and pd.notna(row['ret7d']) and row['ret7d'] < umbral_ret7d:
                continue
            if umbral_vol and pd.notna(row['vol5d_pct']) and row['vol5d_pct'] > umbral_vol:
                continue
            p_entrada = row['close']
            retorno = None
            for j in range(1, 15):
                if i + j >= len(df_sub):
                    break
                p = df_sub['close'].iloc[i + j]
                if p <= p_entrada * (1 - stop):
                    retorno = -stop; break
                elif p >= p_entrada * (1 + take):
                    retorno = take; break
            if retorno is None and i + 14 < len(df_sub):
                retorno = (df_sub['close'].iloc[i + 14] - p_entrada) / p_entrada
            if retorno is not None:
                retornos.append(retorno)
        if len(retornos) < 3:
            return -999, 0
        r = np.array(retornos)
        sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else -999
        return round(sharpe, 2), len(retornos)

    print(f"\n{'='*55}")
    print(f"{par} — umbral={umbral_score}, stop={stop*100:.0f}%, take={take*100:.0f}%")
    print(f"{'='*55}")

    señales = df[df['score'] >= umbral_score]
    print(f"Total señales: {len(señales)}")

    print(f"\n  {'Filtro':<30} {'Sharpe':>8} {'Ops':>5}")
    print(f"  {'-'*45}")

    s, n = simular(df)
    print(f"  {'Sin filtro':<30} {s:>8.2f} {n:>5}")

    for u_ret in [-0.05, -0.08, -0.10]:
        s, n = simular(df, umbral_ret7d=u_ret)
        print(f"  {'ret7d < '+f'{u_ret:.0%}':<30} {s:>8.2f} {n:>5}")

    for u_vol in [70, 80]:
        s, n = simular(df, umbral_vol=u_vol)
        print(f"  {'vol5d > p'+str(u_vol):<30} {s:>8.2f} {n:>5}")

    return simular(df)[0]

print("\nCalculando scores (puede tardar 2-3 min)...")
sharpe_ada = analizar_activo('ADA/EUR')
sharpe_sol = analizar_activo('SOL/EUR')

print(f"\n{'='*65}")
print(f"RESUMEN COMPARATIVO — 4 ACTIVOS:")
print(f"{'='*65}")
print(f"\n  {'Activo':<10} {'Umbral':>7} {'Stop':>6} {'Sharpe_base':>12} {'Filtro_mejora?':>15}")
print(f"  {'-'*55}")
print(f"  {'BNB':<10} {'7':>7} {'2%':>6} {'7.15':>12} {'❌ No (OOS)':>15}")
print(f"  {'ETH':<10} {'4':>7} {'3%':>6} {'2.18':>12} {'✅ Sí':>15}")
print(f"  {'ADA':<10} {'5':>7} {'3%':>6} {sharpe_ada:>12.2f} {'?':>15}")
print(f"  {'SOL':<10} {'6':>7} {'3%':>6} {sharpe_sol:>12.2f} {'?':>15}")

print("\n✅ Experimento 3c completado")
