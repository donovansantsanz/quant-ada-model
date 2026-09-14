import pandas as pd
import numpy as np
from datetime import datetime, timezone

ARCHIVO = '/root/proyectos-quant/operaciones_reales.csv'

ahora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
df = pd.read_csv(ARCHIVO)
cerradas = df[df['resultado'].notna() & (df['resultado'] != '')].copy()
cerradas['retorno_pct'] = pd.to_numeric(cerradas['retorno_pct'], errors='coerce')

print("=" * 68)
print("  DASHBOARD DE MÉTRICAS REALES")
print(f"  {ahora}")
print("=" * 68)

def racha_max(resultados):
    max_gan = max_per = cur_gan = cur_per = 0
    for r in resultados:
        if r == 'take_profit':
            cur_gan += 1; cur_per = 0
        else:
            cur_per += 1; cur_gan = 0
        max_gan = max(max_gan, cur_gan)
        max_per = max(max_per, cur_per)
    return max_gan, max_per

def sharpe_real(retornos):
    if len(retornos) < 2:
        return float('nan')
    return retornos.mean() / retornos.std()

activos_orden = ['BNB/EUR', 'AVAX/EUR', 'BNB/USDT', 'ADA/USDT', 'BTC/USDT', 'ETH/USDT']

for activo in activos_orden:
    ops = cerradas[cerradas['activo'] == activo]
    if len(ops) == 0:
        continue

    n = len(ops)
    wins     = ops[ops['resultado'] == 'take_profit']
    losses   = ops[ops['resultado'] != 'take_profit']
    manuales = len(ops[ops['resultado'] == 'cerrado_manual'])
    wr = len(wins) / n * 100
    avg_win  = wins['retorno_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['retorno_pct'].mean() if len(losses) > 0 else 0
    expectativa = (wr/100 * avg_win) + ((1 - wr/100) * avg_loss)
    sharpe = sharpe_real(ops['retorno_pct'])
    total  = ops['retorno_pct'].sum()
    r_gan, r_per = racha_max(ops['resultado'].tolist())

    icono = '✅' if expectativa > 0 else '❌'
    print(f"\n  {icono} {activo} — {n} ops")
    print(f"     Win rate:    {wr:.0f}%  ({len(wins)}W / {len(losses)}L, {manuales} manuales)")
    print(f"     Avg win:     {avg_win:+.2f}%   Avg loss: {avg_loss:+.2f}%")
    print(f"     Expectativa: {expectativa:+.3f}% por op")
    if not np.isnan(sharpe):
        print(f"     Sharpe real: {sharpe:.2f}")
    else:
        print(f"     Sharpe real: —")
    print(f"     Racha max:   {r_gan} ganadoras / {r_per} perdedoras consecutivas")
    print(f"     Total:       {total:+.2f}%")

print("\n" + "=" * 68)
total_all = cerradas['retorno_pct'].sum()
n_all = len(cerradas)
wr_all = len(cerradas[cerradas['resultado'] == 'take_profit']) / n_all * 100
print(f"  GLOBAL: {n_all} ops | Win rate: {wr_all:.0f}% | Retorno total: {total_all:+.2f}%")
print("=" * 68 + "\n")
