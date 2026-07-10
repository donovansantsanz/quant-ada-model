import json
import os
from datetime import datetime

regimen_file = os.path.expanduser('~/proyectos-quant/regimen_actual.json')
prev_regimen_file = os.path.expanduser('~/proyectos-quant/regimen_anterior.json')

# Cargar régimen actual
with open(regimen_file, 'r') as f:
    actual = json.load(f)

# Cargar régimen anterior (si existe)
if os.path.exists(prev_regimen_file):
    with open(prev_regimen_file, 'r') as f:
        anterior = json.load(f)
else:
    anterior = {'activos': {}}

# Detectar cambios a FAVORABLE
cambios = []
for par, data_actual in actual['activos'].items():
    data_anterior = anterior['activos'].get(par, {})
    
    regimen_anterior = data_anterior.get('final_regime', 'UNKNOWN')
    regimen_actual = data_actual['final_regime']
    
    # Si cambió a FAVORABLE
    if regimen_anterior != 'FAVORABLE' and regimen_actual == 'FAVORABLE':
        cambios.append({
            'asset': par,
            'anterior': regimen_anterior,
            'actual': regimen_actual,
            'rsi': data_actual['rsi'],
            'ma20_slope': data_actual['ma20_slope'],
            'precio': data_actual['precio']
        })

# Guardar régimen actual como anterior para próxima ejecución
with open(prev_regimen_file, 'w') as f:
    json.dump(actual, f, indent=2)

# Si hay cambios, alertar
if cambios:
    print("=" * 60)
    print("🔥 EDGE DETECTED — RÉGIMEN CAMBIÓ A FAVORABLE")
    print("=" * 60)
    for cambio in cambios:
        print(f"\n{cambio['asset']}")
        print(f"  Régimen anterior: {cambio['anterior']} → Actual: {cambio['actual']}")
        print(f"  RSI: {cambio['rsi']:.2f}")
        print(f"  MA20 slope: {cambio['ma20_slope']:.6f}")
        print(f"  Precio: {cambio['precio']:.4f}")
        
        # Aquí iría el Telegram alert, pero por ahora solo log
        print(f"  → Sistema tiene edge nuevamente")
else:
    print(f"[{datetime.now().isoformat()}] Sin cambios a FAVORABLE")


# ── ALERTA TELEGRAM ──────────────────────────────────────────────
if cambios:
    import requests
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))
    
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    lineas = ["<b>🟢 EDGE DETECTADO</b>\n"]
    for cambio in cambios:
        lineas.append(f"🟢 {cambio['asset']}: {cambio['anterior']} → <b>FAVORABLE</b>")
        lineas.append(f"   RSI: {cambio['rsi']:.1f} | Precio: €{cambio['precio']:.4f}")
    
    msg = "\n".join(lineas)
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Error Telegram: {e}")
