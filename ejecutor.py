import os
import ccxt
from dotenv import load_dotenv
import requests

load_dotenv()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CAPITAL_BASE = 1000

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

def get_exchange():
    return ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_SECRET_KEY"),
        'enableRateLimit': True,
        'options': {'defaultType': 'spot', 'fetchCurrencies': False},
    })

def saldo_disponible(exchange, moneda='USDC'):
    balance = exchange.fetch_balance()
    return balance['free'].get(moneda, 0)

def posicion_abierta(exchange, simbolo):
    try:
        ordenes = exchange.fetch_open_orders(simbolo.replace('USDT', 'USDC'))
        return len(ordenes) > 0
    except:
        return False

def ejecutar_compra(simbolo, señal):
    exchange = get_exchange()
    simbolo_usdc = simbolo.replace('USDT', 'USDC')
    if posicion_abierta(exchange, simbolo):
        print(f"⚠️ {simbolo}: posición ya abierta — ignorada")
        return False
    kelly_pct    = min(señal['kelly'] / 4 / 100, 0.10)
    capital      = round(CAPITAL_BASE * kelly_pct, 2)
    precio       = señal['precio']
    cantidad     = round(capital / precio, 4)
    stop_precio  = round(precio * (1 - señal['stop']/100), 4)
    take_precio  = round(precio * (1 + señal['take']/100), 4)
    stop_limit   = round(stop_precio * 0.998, 4)
    try:
        orden         = exchange.create_market_buy_order(simbolo_usdc, cantidad)
        precio_real   = orden['average'] or precio
        cantidad_real = orden['filled']
        print(f"✅ Compra: {cantidad_real} {simbolo} a ${precio_real}")
        exchange.create_order(
            simbolo_usdc, 'OCO', 'sell', cantidad_real, take_precio,
            {'stopPrice': stop_precio, 'stopLimitPrice': stop_limit, 'stopLimitTimeInForce': 'GTC'},
        )
        print(f"✅ OCO: stop ${stop_precio} | take ${take_precio}")
        enviar_telegram(f"""<b>🤖 EJECUCIÓN AUTOMÁTICA</b>

{simbolo}
Precio: <b>${precio_real:.4f}</b>
Cantidad: <b>{cantidad_real}</b>
Capital: <b>${capital:.2f}</b>

Stop: ${stop_precio} ({señal['stop']:.0f}%)
Take: ${take_precio} ({señal['take']:.0f}%)
✅ OCO colocado automáticamente""")

        # Registrar en operaciones_reales.csv
        import csv, os
        from datetime import datetime, timezone
        archivo = '/root/proyectos-quant/operaciones_reales.csv'
        fecha_eval = (datetime.now(timezone.utc).strftime('%Y-%m-%d'))
        nueva_fila = {
            'fecha_entrada': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
            'activo': simbolo,
            'sistema': '4h' if 'horizonte' in señal else 'diario',
            'precio_entrada': round(precio_real, 6),
            'cantidad': cantidad_real,
            'capital_usdc': round(capital, 2),
            'stop_loss': stop_precio,
            'take_profit': take_precio,
            'kelly': f"{kelly_pct*100:.1f}%",
            'fecha_cierre': '',
            'precio_cierre': '',
            'retorno_pct': '',
            'resultado': '',
            'notas': 'Ejecución automática'
        }
        file_exists = os.path.exists(archivo)
        with open(archivo, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=nueva_fila.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(nueva_fila)
        print(f"✅ Registrado en operaciones_reales.csv")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        enviar_telegram(f"❌ Error ejecución {simbolo}: {e}")
        return False

if __name__ == "__main__":
    exchange = get_exchange()
    saldo = saldo_disponible(exchange)
    print(f"✅ Conexión OK — Saldo USDC: ${saldo:.2f}")
    print(f"   Capital base: ${CAPITAL_BASE}")
    print(f"   BNB Kelly/4 (10%): ${CAPITAL_BASE * 0.10:.0f} por operación")
