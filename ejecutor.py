import os
import csv
import ccxt
from dotenv import load_dotenv
from datetime import datetime, timezone
import requests

load_dotenv()

TOKEN        = os.getenv("TELEGRAM_TOKEN")
CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID")
CAPITAL_BASE = 1000
ARCHIVO      = '/root/proyectos-quant/operaciones_reales.csv'

COLUMNAS = [
    'fecha_entrada', 'activo', 'sistema',
    'precio_entrada', 'cantidad', 'capital_usdc',
    'stop_loss', 'take_profit', 'kelly',
    'precio_senal', 'slippage_bps',            # ← slippage
    'orden_stop_id', 'orden_take_id',          # ← nuevas
    'fecha_cierre', 'precio_cierre',
    'retorno_pct', 'resultado', 'notas',
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

def get_exchange():
    return ccxt.binance({
        'apiKey':  os.getenv("BINANCE_API_KEY"),
        'secret':  os.getenv("BINANCE_SECRET_KEY"),
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

def colocar_ordenes_proteccion(exchange, simbolo_usdc, cantidad_real, stop_precio, take_precio):
    """
    Coloca stop-limit y limit por separado.
    Devuelve (orden_stop_id, orden_take_id) o lanza excepción.

    - Stop-limit: se activa en stop_precio, ejecuta a stop_precio * 0.998
    - Limit (take): ejecuta exactamente en take_precio
    """
    stop_limit = round(stop_precio * 0.998, 4)

    # 1. Orden stop-limit (stop loss)
    orden_stop = exchange.create_order(
        simbolo_usdc,
        'stop_loss_limit',
        'sell',
        cantidad_real,
        stop_limit,
        {'stopPrice': stop_precio, 'timeInForce': 'GTC'},
    )

    # 2. Orden limit (take profit)
    orden_take = exchange.create_order(
        simbolo_usdc,
        'limit',
        'sell',
        cantidad_real,
        take_precio,
        {'timeInForce': 'GTC'},
    )

    return orden_stop['id'], orden_take['id']

def ejecutar_compra(simbolo, señal):
    exchange     = get_exchange()
    simbolo_usdc = simbolo.replace('USDT', 'USDC')

    if posicion_abierta(exchange, simbolo):
        print(f"⚠️ {simbolo}: posición ya abierta — ignorada")
        return False

    kelly_pct = min(señal['kelly'] / 4 / 100, 0.10)
    capital   = round(CAPITAL_BASE * kelly_pct, 2)
    saldo     = saldo_disponible(exchange)

    if saldo < 10:
        print(f"⚠️ Saldo insuficiente: ${saldo:.2f} USDC")
        enviar_telegram(f"⚠️ Saldo insuficiente: ${saldo:.2f} USDC — operación cancelada")
        return False

    capital      = round(min(capital, saldo * 0.99), 2)
    precio       = señal['precio']
    cantidad     = round(capital / precio, 4)
    stop_precio  = round(precio * (1 - señal['stop'] / 100), 4)
    take_precio  = round(precio * (1 + señal['take'] / 100), 4)

    try:
        # ── Compra de mercado ────────────────────────────────────────────
        orden         = exchange.create_market_buy_order(simbolo_usdc, cantidad)
        precio_real   = orden['average'] or precio
        cantidad_real = orden['filled']
        print(f"✅ Compra: {cantidad_real} {simbolo} a ${precio_real}")

        # ── Órdenes de protección ────────────────────────────────────────
        orden_stop_id = ''
        orden_take_id = ''
        proteccion_ok = False

        try:
            orden_stop_id, orden_take_id = colocar_ordenes_proteccion(
                exchange, simbolo_usdc, cantidad_real, stop_precio, take_precio
            )
            proteccion_ok = True
            print(f"✅ Protección colocada — stop #{orden_stop_id} | take #{orden_take_id}")

            enviar_telegram(f"""<b>✅ EJECUCIÓN AUTOMÁTICA</b>
{simbolo}
Precio entrada: <b>${precio_real:.4f}</b>
Cantidad: <b>{cantidad_real}</b>
Capital: <b>${capital:.2f} USDC</b>
Stop loss: ${stop_precio} (ID: {orden_stop_id})
Take profit: ${take_precio} (ID: {orden_take_id})
<i>Órdenes colocadas automáticamente</i>""")

        except Exception as prot_err:
            print(f"⚠️ Error colocando protección: {prot_err}")
            enviar_telegram(f"""<b>⚠️ COMPRA EJECUTADA — PROTECCIÓN MANUAL REQUERIDA</b>
{simbolo}
Precio entrada: <b>${precio_real:.4f}</b>
Cantidad: <b>{cantidad_real}</b>
Capital: <b>${capital:.2f} USDC</b>

Coloca manualmente en Binance:
• Stop limit — trigger: {stop_precio} | limit: {round(stop_precio * 0.998, 4)}
• Take profit — limit: {take_precio}
Cantidad: {cantidad_real}

<b>⚠️ Posición desprotegida hasta que lo hagas</b>""")

        # ── Slippage: diferencia entre precio de señal y fill real ───────
        precio_senal = round(precio, 6)
        slippage_bps = round((precio_real - precio) / precio * 10000, 1)

        # ── Registro en CSV ──────────────────────────────────────────────
        nueva_fila = {
            'fecha_entrada':  datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
            'activo':         simbolo,
            'sistema':        '4h' if 'horizonte' in señal else 'diario',
            'precio_entrada': round(precio_real, 6),
            'cantidad':       cantidad_real,
            'capital_usdc':   round(capital, 2),
            'stop_loss':      stop_precio,
            'take_profit':    take_precio,
            'kelly':          f"{kelly_pct * 100:.1f}%",
            'precio_senal':   precio_senal,
            'slippage_bps':   slippage_bps,
            'orden_stop_id':  orden_stop_id,
            'orden_take_id':  orden_take_id,
            'fecha_cierre':   '',
            'precio_cierre':  '',
            'retorno_pct':    '',
            'resultado':      '',
            'notas':          'Automática' if proteccion_ok else 'Protección manual pendiente',
        }

        file_exists = os.path.exists(ARCHIVO)
        with open(ARCHIVO, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNAS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(nueva_fila)

        print(f"✅ Registrado en operaciones_reales.csv")
        return True

    except Exception as e:
        print(f"❌ Error en ejecución: {e}")
        enviar_telegram(f"❌ Error ejecución {simbolo}: {e}")
        return False


if __name__ == "__main__":
    exchange = get_exchange()
    saldo    = saldo_disponible(exchange)
    print(f"✅ Conexión OK — Saldo USDC: ${saldo:.2f}")
    print(f"   Capital base: ${CAPITAL_BASE}")
    print(f"   Kelly/4 máx (10%): ${CAPITAL_BASE * 0.10:.0f} por operación")
