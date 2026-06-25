import os
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import shutil

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

ahora = datetime.now(timezone.utc)

CHECKS = [
    {'nombre': 'Monitor diario',       'log': '/root/logs/monitor.log',        'max_horas': 25},
    {'nombre': 'Monitor 4h',           'log': '/root/logs/monitor_4h.log',     'max_horas': 5},
    {'nombre': 'Paper trading diario', 'log': '/root/logs/paper_trading.log',  'max_horas': 25},
    {'nombre': 'Paper trading 4h',     'log': '/root/logs/paper_trading_4h.log','max_horas': 5},
]

alertas = []

for check in CHECKS:
    path = Path(check['log'])
    if not path.exists() or path.stat().st_size == 0:
        alertas.append(f"⚠️ {check['nombre']}: log vacío o inexistente")
        continue
    modificado = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    horas = (ahora - modificado).total_seconds() / 3600
    if horas > check['max_horas']:
        alertas.append(f"⚠️ {check['nombre']}: sin actividad hace {horas:.1f}h (máx {check['max_horas']}h)")

# Disco
uso = shutil.disk_usage('/')
pct_libre = uso.free / uso.total * 100
if pct_libre < 10:
    alertas.append(f"⚠️ Disco: solo {pct_libre:.1f}% libre")

# Memoria
with open('/proc/meminfo') as f:
    mem = {l.split(':')[0]: int(l.split(':')[1].strip().split()[0]) for l in f if ':' in l}
pct_mem = mem.get('MemAvailable', 0) / mem.get('MemTotal', 1) * 100
if pct_mem < 10:
    alertas.append(f"⚠️ Memoria: solo {pct_mem:.1f}% disponible")

if alertas:
    msg = "<b>🚨 WATCHDOG — Alerta del sistema</b>\n\n"
    msg += "\n".join(alertas)
    msg += f"\n\n{ahora.strftime('%Y-%m-%d %H:%M UTC')}"
    enviar_telegram(msg)
    print(f"Alertas enviadas: {len(alertas)}")
    for a in alertas: print(f"  {a}")
else:
    print(f"✅ Watchdog OK — {ahora.strftime('%Y-%m-%d %H:%M UTC')}")
