import os
import ccxt
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

ARCHIVO = '/root/proyectos-quant/operaciones_reales.csv'

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_SECRET_KEY"),
        'enableRateLimit': True,
        'options': {'defaultType': 'spot', 'fetchCurrencies': False},
    })

ahora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
print("=" * 64)
print(f"  MIS OPERACIONES — P&L EN VIVO")
print(f"  {ahora}")
print("=" * 64)

df = pd.read_csv(ARCHIVO)
abiertas = df[df['resultado'].isna() | (df['resultado'] == '')]

if len(abiertas) == 0:
    print("\n  No hay operaciones abiertas")
else:
    exchange = get_exchange()
    pnl_total = 0.0
    print()
    for _, r in abiertas.iterrows():
        simbolo = r['activo'].replace('USDT', 'USDC')
        try:
            precio_actual = exchange.fetch_ticker(simbolo)['last']
        except Exception:
            precio_actual = float(r['precio_entrada'])

        p_entrada = float(r['precio_entrada'])
        cantidad  = float(r['cantidad'])
        stop      = float(r['stop_loss'])
        take      = float(r['take_profit'])

        retorno_pct = (precio_actual - p_entrada) / p_entrada * 100
        pnl_usdc    = (precio_actual - p_entrada) * cantidad
        pnl_total  += pnl_usdc

        dist_stop = (precio_actual - stop) / precio_actual * 100
        dist_take = (take - precio_actual) / precio_actual * 100

        icono = "🟢" if retorno_pct >= 0 else "🔴"
        activo_str = r['activo'].replace('/USDT', '')

        print(f"  {icono} {activo_str:<5} | Entrada: ${p_entrada:<11.4f} Actual: ${precio_actual:<11.4f}")
        print(f"         P&L: {retorno_pct:+.2f}% (${pnl_usdc:+.2f})")
        print(f"         Stop: ${stop:.4f} ({dist_stop:+.1f}% lejos) | Take: ${take:.4f} ({dist_take:+.1f}% lejos)")
        print()

    print("-" * 64)
    signo = "🟢" if pnl_total >= 0 else "🔴"
    print(f"  {signo} P&L TOTAL EN VIVO: ${pnl_total:+.2f} USDC")

    cerradas = df[df['resultado'].notna() & (df['resultado'] != '')]
    if len(cerradas) > 0:
        retorno_cerrado = cerradas['retorno_pct'].astype(float).sum()
        print(f"  Operaciones cerradas: {len(cerradas)} | Retorno acumulado: {retorno_cerrado:.2f}%")

print("=" * 64)
