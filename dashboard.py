import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

def separador(titulo=""):
    if titulo:
        print(f"\n{'─'*60}")
        print(f"  {titulo}")
        print(f"{'─'*60}")
    else:
        print(f"{'─'*60}")

ahora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
print("=" * 60)
print(f"  DASHBOARD — Quant Trading System")
print(f"  {ahora}")
print("=" * 60)

# ── SISTEMA DIARIO ──
separador("SISTEMA DIARIO — Últimas señales")
CSV_D = Path('/root/proyectos-quant/paper_trading_registro.csv')
if CSV_D.exists():
    df = pd.read_csv(CSV_D)
    df['fecha'] = pd.to_datetime(df["fecha"], format="mixed")
    ultima = df['fecha'].max()
    print(f"  Última ejecución: {ultima.strftime('%Y-%m-%d %H:%M UTC')}")
    hoy = df[df['fecha'] == ultima]
    for _, r in hoy.iterrows():
        icon = '🟢' if r['decision'] == 'COMPRAR' else '⏸'
        print(f"  {icon} {r['activo']:<12} Score: {r['score']:>3}  RSI: {r['rsi']:.1f}  ${r['precio_entrada']:.4f}" if r['precio_entrada'] < 1
              else f"  {icon} {r['activo']:<12} Score: {r['score']:>3}  RSI: {r['rsi']:.1f}  ${r['precio_entrada']:.2f}")
    compras_d = (df['decision'] == 'COMPRAR').sum()
    print(f"\n  Total señales COMPRAR: {compras_d} | Registros: {len(df)}")
    print(f"  Primera evaluación: 2026-07-04")
else:
    print("  Sin datos")

# ── SISTEMA 4H ──
separador("SISTEMA 4H — Últimas señales")
CSV_4H = Path('/root/proyectos-quant/paper_trading_4h_registro.csv')
if CSV_4H.exists():
    df4 = pd.read_csv(CSV_4H)
    df4['fecha'] = pd.to_datetime(df4['fecha'])
    ultima4 = df4['fecha'].max()
    print(f"  Última ejecución: {ultima4.strftime('%Y-%m-%d %H:%M UTC')}")
    recientes = df4[df4['fecha'] == ultima4]
    for _, r in recientes.iterrows():
        icon = '🟢' if r['decision'] == 'COMPRAR' else '⏸'
        precio = f"${r['precio_entrada']:.2f}"
        print(f"  {icon} {r['activo']:<12} Score: {r['score']:>3}  RSI: {r['rsi']:.1f}  {precio}")
    compras_4h = (df4['decision'] == 'COMPRAR').sum()
    prox_eval = df4['fecha_evaluacion'].dropna().iloc[-1] if len(df4) > 0 else 'N/A'
    print(f"\n  Total señales COMPRAR: {compras_4h} | Registros: {len(df4)}")
    print(f"  Próxima evaluación: {prox_eval}")
else:
    print("  Sin datos")

# ── OPERACIONES REALES ──
separador("OPERACIONES REALES")
import csv, os
ARCHIVO_REAL = '/root/proyectos-quant/operaciones_reales.csv'
if os.path.exists(ARCHIVO_REAL):
    df_real = pd.read_csv(ARCHIVO_REAL)
    abiertas = df_real[df_real['resultado'].isna() | (df_real['resultado'] == '')]
    cerradas = df_real[df_real['resultado'].notna() & (df_real['resultado'] != '')]
    print(f"  Operaciones abiertas: {len(abiertas)}")
    for _, r in abiertas.iterrows():
        print(f"  🔵 {r['activo']} | Entrada: ${r['precio_entrada']} | Stop: ${r['stop_loss']} | Take: ${r['take_profit']}")
    print(f"  Operaciones cerradas: {len(cerradas)}")
    if len(cerradas) > 0:
        retorno_total = cerradas['retorno_pct'].astype(float).sum()
        stops = (cerradas['resultado'] == 'stop_loss').sum()
        takes = (cerradas['resultado'] == 'take_profit').sum()
        print(f"  Stop loss: {stops} | Take profit: {takes} | Retorno acumulado: {retorno_total:.2f}%")
else:
    print("  Sin operaciones")

# ── SALDO BINANCE ──
separador("SALDO BINANCE")
try:
    import ccxt
    from dotenv import load_dotenv
    load_dotenv()
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'enableRateLimit': True,
        'options': {'defaultType': 'spot', 'fetchCurrencies': False},
    })
    balance = exchange.fetch_balance()
    for moneda in ['USDC', 'BNB', 'ADA', 'SOL', 'ETH', 'BTC']:
        libre = balance['free'].get(moneda, 0)
        total = balance['total'].get(moneda, 0)
        if total > 0:
            print(f"  {moneda:<6} libre: {libre:.4f} | total: {total:.4f}")
except Exception as e:
    print(f"  Error conectando a Binance: {e}")

# ── LOGS ──
separador("ÚLTIMAS EJECUCIONES CRON")
import subprocess
logs = {
    'Diario  (10:30 UTC)': '/root/logs/monitor.log',
    '4H      (*/4h UTC) ': '/root/logs/monitor_4h.log',
    'Salud   (dom 10:00)': '/root/logs/salud.log',
    'Evaluad (lun 11:00)': '/root/logs/evaluador.log',
}
for nombre, path in logs.items():
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        ultima_linea = subprocess.run(['tail', '-1', path], capture_output=True, text=True).stdout.strip()
        print(f"  {nombre}: {ultima_linea[:45]}")
    else:
        print(f"  {nombre}: Sin ejecuciones")

# ── SERVIDOR ──
separador("INFRAESTRUCTURA")
mem = subprocess.run(['free', '-m'], capture_output=True, text=True).stdout.split('\n')[1].split()
disco = subprocess.run(['df', '-h', '/'], capture_output=True, text=True).stdout.split('\n')[1].split()
print(f"  Servidor:  Hetzner CX22 — 116.203.91.120")
print(f"  Memoria:   {mem[2]}MB usado / {mem[1]}MB total")
print(f"  Disco:     {disco[2]} usado / {disco[1]} total ({disco[4]})")
print(f"  Paper trading desde: 2026-06-20")

print("\n" + "=" * 60)
