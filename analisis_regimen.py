"""
Análisis de régimen de mercado — solo lectura, no toca el sistema.
Mide en qué estado están los activos y por qué el sistema (mean-reversion) no da señales.
"""
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from config import PARAMS

ex = ccxt.bitvavo()

print("="*70)
print("  ANÁLISIS DE RÉGIMEN — por qué el sistema no da señales")
print("="*70)

resumen = []
for simbolo in PARAMS:
    velas = ex.fetch_ohlcv(simbolo, timeframe='1d', limit=365)
    df = pd.DataFrame(velas, columns=['ts','o','h','l','close','v'])
    precios = df['close']
    actual = precios.iloc[-1]

    mm20 = precios.rolling(20).mean().iloc[-1]
    mm50 = precios.rolling(50).mean().iloc[-1]
    dist_mm20 = (actual - mm20) / mm20 * 100

    pct_90  = stats.percentileofscore(precios.iloc[-90:], actual)
    pct_365 = stats.percentileofscore(precios, actual)

    ret_30 = (actual / precios.iloc[-31] - 1) * 100
    ret_7  = (actual / precios.iloc[-8]  - 1) * 100

    vol_30 = precios.pct_change().rolling(30).std()
    pct_vol = stats.percentileofscore(vol_30.dropna(), vol_30.iloc[-1])

    tendencia = "alcista" if actual > mm50 else "bajista"

    resumen.append({
        'activo': simbolo, 'pct_365': pct_365, 'pct_90': pct_90,
        'dist_mm20': dist_mm20, 'ret_30': ret_30, 'ret_7': ret_7,
        'pct_vol': pct_vol, 'tendencia': tendencia
    })

df_r = pd.DataFrame(resumen)
print("\n  POSICIÓN DE CADA ACTIVO (percentil = dónde está el precio vs su historia)")
print("  " + "-"*66)
print(f"  {'Activo':<9}{'pct365':>8}{'pct90':>8}{'vs MM20':>9}{'ret30d':>9}{'ret7d':>8}{'volPct':>8}  {'tend':<8}")
for _, r in df_r.iterrows():
    print(f"  {r['activo']:<9}{r['pct_365']:>7.0f}%{r['pct_90']:>7.0f}%{r['dist_mm20']:>+8.1f}%{r['ret_30']:>+8.1f}%{r['ret_7']:>+7.1f}%{r['pct_vol']:>7.0f}%  {r['tendencia']:<8}")

print("\n  LECTURA AGREGADA")
print("  " + "-"*66)
print(f"  Percentil 365d medio:  {df_r['pct_365'].mean():.0f}%  (>50 = caros vs su año, <50 = baratos)")
print(f"  Percentil 90d medio:   {df_r['pct_90'].mean():.0f}%")
print(f"  Dist. MM20 media:      {df_r['dist_mm20'].mean():+.1f}%  (>0 = por encima de su media)")
print(f"  Retorno 30d medio:     {df_r['ret_30'].mean():+.1f}%")
print(f"  Vol percentil media:   {df_r['pct_vol'].mean():.0f}%  (baja vol = poco movimiento)")
alcistas = (df_r['tendencia']=='alcista').sum()
print(f"  Activos en tendencia alcista: {alcistas}/{len(df_r)}")
