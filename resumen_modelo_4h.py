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
    'BNB/EUR':  {'sharpe_train': 2.53, 'sharpe_test': 3.34, 'win_rate': 69.2},
    'AVAX/EUR': {'sharpe_train': 3.58, 'sharpe_test': 1.51, 'win_rate': 48.3},
    'ETH/EUR':  {'sharpe_train': 3.15, 'sharpe_test': 1.98, 'win_rate': 76.5},
    'XRP/EUR':  {'sharpe_train': 2.62, 'sharpe_test': 5.44, 'win_rate': 88.2},
}

for simbolo, p in PARAMS_4H.items():
    wf = WALK_FORWARD.get(simbolo, {})
    sharpe_test = wf.get('sharpe_test', '—')
    horizonte_h = p['horizonte_velas'] * 4
    icon = '✅' if isinstance(sharpe_test, float) and sharpe_test > 0 else '⚠️'
    print(f"  {simbolo:<12} {p['umbral']:<8} {p['stop']*100:.0f}%{'':<4} {p['take']*100:.0f}%{'':<4} {p['kelly']:.1f}%{'':<3} {horizonte_h}h{'':<8} {sharpe_test} {icon}")

print(f"\n👁  ACTIVOS EN OBSERVACIÓN")
print(f"  {'Activo':<12} {'Razón':<50} {'Train':<8} {'Test'}")
print(f"  {'─'*75}")

OBS_INFO = {
    'ADA/EUR': {'razon': 'Train Sharpe 0.04 — edge no estructural', 'train': 0.04, 'test': 2.54},
    'SOL/EUR': {'razon': 'Train Sharpe 0.36 — train débil', 'train': 0.36, 'test': 3.48},
    'BTC/EUR': {'razon': 'Train Sharpe 0.93 — pendiente más datos', 'train': 0.93, 'test': 2.55},
}

for simbolo in PARAMS_4H_OBS:
    if simbolo in OBS_INFO:
        info = OBS_INFO[simbolo]
        print(f"  {simbolo:<12} {info['razon']:<50} {info['train']:<8} {info['test']} ⚠️")

print(f"\n⚙️  PARÁMETROS DEL SISTEMA")
print(f"  Timeframe:      4 horas")
print(f"  Scoring:        Percentiles históricos (sin lookahead bias)")
print(f"  Validación:     Walk-forward out-of-sample (70/30, 500 velas)")
print(f"  Ejecución:      Cron cada 4h — 00:00 04:00 08:00 12:00 16:00 20:00 UTC")
print(f"  Alertas:        Telegram — solo señales COMPRAR")
print(f"  Protección:     Bloqueo tras ≥2 stops consecutivos negativos por activo")
print(f"  Sizing:         Kelly/4, cap 10% del capital")
print(f"  Inicio real:    2026-06-20")

print(f"\n📈 FASE DE VALIDACIÓN")
print(f"  Objetivo:       30 operaciones cerradas")
print(f"  Completadas:    23 / 30")
print(f"  Activos:        4 (BNB, AVAX, ETH, XRP)")
print(f"  Ritmo estimado: ~5-6 ops/mes → fin validación nov 2026")

print(f"\n📁 SCRIPTS 4H")
scripts = [
    ('config_4h.py',          'Fuente única de parámetros 4h'),
    ('monitor_4h.py',         'Monitor 4h — alertas Telegram'),
    ('walk_forward_4h.py',    'Validación out-of-sample 4h'),
    ('dashboard_metricas.py', 'Métricas reales por activo'),
    ('mis_operaciones.py',    'Vista de operaciones abiertas/cerradas'),
    ('migrar_sqlite.py',      'Sincronización CSV → SQLite'),
    ('resumen_modelo_4h.py',  'Esta ficha técnica'),
]
for nombre, desc in scripts:
    print(f"  {nombre:<26} {desc}")

print("\n" + "=" * 60)
print("  github.com/donovansantsanz/quant-ada-model")
print("=" * 60 + "\n")
