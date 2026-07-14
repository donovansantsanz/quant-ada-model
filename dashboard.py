import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import subprocess

def separador(titulo=""):
    if titulo:
        print(f"\n{'─'*60}")
        print(f"  {titulo}")
        print(f"{'─'*60}")
    else:
        print(f"{'─'*60}")

ahora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
print("=" * 60)
print(f"  DASHBOARD — Quant Trading System (Bitvavo/EUR)")
print(f"  {ahora}")
print("=" * 60)

def mostrar_senales_json(path_json, titulo):
    separador(titulo)
    p = Path(path_json)
    if not p.exists():
        print("  Sin datos (JSON no encontrado)")
        return
    try:
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        print(f"  Última ejecución: {mtime.strftime('%Y-%m-%d %H:%M UTC')}")
        with open(p) as f:
            datos = json.load(f)
        compras = 0
        for simbolo, d in datos.items():
            decision = d.get('decision', '?')
            score = d.get('puntos', d.get('score', '?'))
            rsi = d.get('rsi', 0)
            precio = d.get('precio', 0)
            icon = '🟢' if decision == 'COMPRAR' else ('🚫' if decision == 'BLOQUEADO' else '⏸')
            if decision == 'COMPRAR':
                compras += 1
            precio_str = f"€{precio:.4f}" if precio < 1 else f"€{precio:.2f}"
            try:
                print(f"  {icon} {simbolo:<10} Score: {score:>3}  RSI: {rsi:.1f}  {precio_str}")
            except (ValueError, TypeError):
                print(f"  {icon} {simbolo:<10} Score: {score}  RSI: {rsi}  {precio_str}")
        print(f"\n  Señales COMPRAR en última ejecución: {compras}")
    except Exception as e:
        print(f"  Error leyendo JSON: {e}")

# ── SISTEMA DIARIO (desde JSON del monitor migrado) ──
mostrar_senales_json('/root/proyectos-quant/monitor_resultados.json', 'SISTEMA DIARIO — Últimas señales')

# ── SISTEMA 4H (desde JSON del monitor migrado) ──
mostrar_senales_json('/root/proyectos-quant/monitor_4h_resultados.json', 'SISTEMA 4H — Últimas señales')

# ── OPERACIONES REALES (solo Bitvavo) ──
separador("OPERACIONES REALES")
ARCHIVO_REAL = '/root/proyectos-quant/operaciones_reales.csv'
if os.path.exists(ARCHIVO_REAL):
    df_real = pd.read_csv(ARCHIVO_REAL)
    if 'venue' not in df_real.columns:
        df_real['venue'] = 'binance'
    df_real['venue'] = df_real['venue'].fillna('binance')
    df_bv = df_real.copy()
    df_bin = df_real[df_real['venue'] == 'binance']

    abiertas = df_bv[df_bv['resultado'].isna() | (df_bv['resultado'] == '')]
    cerradas = df_bv[df_bv['resultado'].notna() & (df_bv['resultado'] != '') & (df_bv['resultado'] != 'cerrado_manual')]
    print(f"  Operaciones abiertas: {len(abiertas)}")
    for _, r in abiertas.iterrows():
        print(f"  🔵 {r['activo']} | Entrada: €{r['precio_entrada']} | Stop: €{r['stop_loss']} | Take: €{r['take_profit']}")
    print(f"  Operaciones cerradas: {len(cerradas)}")
    if len(cerradas) > 0:
        retorno_total = cerradas['retorno_pct'].astype(float).sum()
        stops = (cerradas['resultado'] == 'stop_loss').sum()
        takes = (cerradas['resultado'] == 'take_profit').sum()
        print(f"  Stop loss: {stops} | Take profit: {takes} | Retorno acumulado: {retorno_total:+.2f}%")
    print(f"  Progreso ventana validación: {len(cerradas)}/30 operaciones cerradas")
else:
    print("  Sin operaciones")

# ── SALDO BITVAVO ──
separador("SALDO BITVAVO (EUR)")
try:
    from conexion import get_exchange
    exchange = get_exchange()
    balance = exchange.fetch_balance()
    hay_algo = False
    for moneda in ['EUR', 'BNB', 'ADA', 'SOL', 'ETH', 'BTC']:
        total = balance['total'].get(moneda, 0)
        libre = balance['free'].get(moneda, 0)
        if total and total > 0:
            print(f"  {moneda:<6} libre: {libre:.4f} | total: {total:.4f}")
            hay_algo = True
    if not hay_algo:
        print("  Sin saldo detectado")
except Exception as e:
    print(f"  Error conectando a Bitvavo: {e}")

# ── LOGS (crons activos migrados) ──
separador("ÚLTIMAS EJECUCIONES CRON")
logs = {
    'Diario   (10:30 UTC)': '/root/logs/monitor.log',
    '4H       (*/4h UTC) ': '/root/logs/monitor_4h.log',
    'Evaluador(cada hora)': '/root/logs/evaluador_real.log',
    'Watchdog (cada hora)': '/root/logs/watchdog.log',
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
print(f"  Exchange:  Bitvavo (EUR, MiCA)")
print(f"  Memoria:   {mem[2]}MB usado / {mem[1]}MB total")
print(f"  Disco:     {disco[2]} usado / {disco[1]} total ({disco[4]})")

print("\n" + "=" * 60)
