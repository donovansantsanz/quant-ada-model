from datetime import datetime, timezone
from config_4h import PARAMS_4H, PARAMS_4H_OBS

ahora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

print("=" * 60)
print("  FICHA TÉCNICA — Quant Trading System 4H")
print(f"  {ahora}")
print("=" * 60)

print("\n📊 ACTIVOS OPERATIVOS")
print(f"  {'Activo':<12} {'Umbral':<8} {'Stop':<7} {'Take':<7} {'Kelly':<8} {'Horizonte':<12} {'Sharpe test'}")
print(f"  {'─'*70}")

WALK_FORWARD = {
    'BNB/USDT': {'sharpe_train': 2.23, 'sharpe_test': 0.32, 'win_rate': 75.0},
}

for simbolo, p in PARAMS_4H.items():
    wf = WALK_FORWARD.get(simbolo, {})
    sharpe_test = wf.get('sharpe_test', '—')
    wr = wf.get('win_rate', '—')
    horizonte_h = p['horizonte_velas'] * 4
    icon = '✅' if isinstance(sharpe_test, float) and sharpe_test > 0 else '⚠️'
    print(f"  {simbolo:<12} {p['umbral']:<8} {p['stop']*100:.0f}%{'':<4} {p['take']*100:.0f}%{'':<4} {p['kelly']:.1f}%{'':<3} {horizonte_h}h{'':<8} {sharpe_test} {icon}")

print(f"\n👁  ACTIVOS EN OBSERVACIÓN")
print(f"  {'Activo':<12} {'Razón':<45} {'Sharpe test'}")
print(f"  {'─'*70}")

OBS_SHARPE = {
    'ETH/USDT': -2.50,
    'ADA/USDT': -2.70,
    'SOL/USDT': -2.50,
    'BTC/USDT': -0.18,
}

for simbolo in PARAMS_4H_OBS:
    sharpe = OBS_SHARPE.get(simbolo, '—')
    print(f"  {simbolo:<12} {'Sharpe test negativo en walk-forward 4h':<45} {sharpe} ❌")

print(f"\n⚙️  PARÁMETROS DEL SISTEMA")
print(f"  Timeframe:      4 horas")
print(f"  Scoring:        Percentiles históricos (sin lookahead bias)")
print(f"  Filtro macro:   No aplicado en 4h")
print(f"  Validación:     Walk-forward out-of-sample (1000 velas)")
print(f"  Ejecución:      Cron cada 4h — 00:00 04:00 08:00 12:00 16:00 20:00 UTC")
print(f"  Alertas:        Telegram — solo señales COMPRAR")
print(f"  Paper trading:  Desde 2026-06-20")

print(f"\n📁 SCRIPTS 4H")
scripts = [
    ('config_4h.py',          'Fuente única de parámetros 4h'),
    ('monitor_4h.py',         'Monitor 4h — alertas Telegram'),
    ('paper_trading_4h.py',   'Registro y evaluación de señales 4h'),
    ('historial_4h.py',       'Vista limpia del paper trading 4h'),
    ('optimizador_4h.py',     'Grid search calibración 4h'),
    ('walk_forward_4h.py',    'Validación out-of-sample 4h'),
    ('resumen_modelo_4h.py',  'Esta ficha técnica'),
]
for nombre, desc in scripts:
    print(f"  {nombre:<26} {desc}")

print("\n" + "=" * 60)
print("  github.com/donovansantsanz/quant-ada-model")
print("=" * 60 + "\n")
