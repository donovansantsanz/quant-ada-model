import os
import csv
import ccxt
from dotenv import load_dotenv
from datetime import datetime, timezone
import requests
from conexion import get_exchange

load_dotenv()

TOKEN        = os.getenv("TELEGRAM_TOKEN")
CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID")
CAPITAL_BASE = 1000
ARCHIVO      = '/root/proyectos-quant/operaciones_reales.csv'

COLUMNAS = [
    'fecha_entrada', 'activo', 'sistema',
    'precio_entrada', 'cantidad', 'capital_usdc',
    'stop_loss', 'take_profit', 'kelly',
    'precio_senal', 'slippage_bps',
    'orden_stop_id', 'orden_take_id',
    'fecha_cierre', 'precio_cierre',
    'retorno_pct', 'resultado', 'notas', 'venue',
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

def saldo_disponible(exchange, moneda='EUR'):
    balance = exchange.fetch_balance()
    return balance['free'].get(moneda, 0)

def posicion_abierta(exchange, simbolo):
    try:
        ordenes = exchange.fetch_open_orders(simbolo.replace('/USDT', '/EUR').replace('/USDC', '/EUR'))
        return len(ordenes) > 0
    except:
        return False

def colocar_ordenes_proteccion(exchange, simbolo, cantidad_real, stop_precio, take_precio):
    """
    Coloca stop-limit y limit por separado (Bitvavo, vía ccxt).
    Devuelve (orden_stop_id, orden_take_id) o lanza excepción.
    """
    stop_limit = round(stop_precio * 0.998, 4)

    # 1. Stop-limit (stop loss) — Bitvavo: stopLossLimit + triggerPrice
    orden_stop = exchange.create_order(
        simbolo,
        'stopLossLimit',
        'sell',
        cantidad_real,
        stop_limit,
        {'triggerPrice': stop_precio},
    )

    # 2. Take-profit con trigger (no bloquea saldo hasta dispararse)
    take_limit = round(take_precio * 0.998, 4)
    orden_take = exchange.create_order(
        simbolo,
        'takeProfitLimit',
        'sell',
        cantidad_real,
        take_limit,
        {'triggerPrice': take_precio},
    )

    return orden_stop['id'], orden_take['id']

def ejecutar_compra(simbolo, señal):
    exchange     = get_exchange()
    simbolo_eur  = simbolo.replace('/USDT', '/EUR').replace('/USDC', '/EUR')

    if posicion_abierta(exchange, simbolo):
        print(f"⚠️ {simbolo}: posición ya abierta — ignorada")
        return False

    kelly_pct = min(señal['kelly'] / 4 / 100, 0.10)
    capital   = round(CAPITAL_BASE * kelly_pct, 2)
    saldo     = saldo_disponible(exchange)

    if saldo < 10:
        print(f"⚠️ Saldo insuficiente: €{saldo:.2f} EUR")
        enviar_telegram(f"⚠️ Saldo insuficiente: €{saldo:.2f} EUR — operación cancelada")
        return False

    capital      = round(min(capital, saldo * 0.99), 2)
    precio       = señal['precio']
    cantidad     = round(capital / precio, 4)
    stop_precio  = round(precio * (1 - señal['stop'] / 100), 4)
    take_precio  = round(precio * (1 + señal['take'] / 100), 4)

    try:
        orden         = exchange.create_market_buy_order(simbolo_eur, cantidad)
        precio_real   = orden['average'] or precio
        cantidad_real = orden['filled']
        print(f"✅ Compra: {cantidad_real} {simbolo} a €{precio_real}")

        orden_stop_id = ''
        orden_take_id = ''
        proteccion_ok = False

        try:
            import time as _time
            ultimo_error = None
            for intento in range(3):
                try:
                    _time.sleep(2)
                    base = simbolo_eur.split('/')[0]
                    bal = exchange.fetch_balance()
                    disponible = bal['free'].get(base, cantidad_real)
                    cantidad_proteger = min(cantidad_real, disponible)
                    cantidad_proteger = float(exchange.amount_to_precision(simbolo_eur, cantidad_proteger))
                    orden_stop_id, orden_take_id = colocar_ordenes_proteccion(
                        exchange, simbolo_eur, cantidad_proteger, stop_precio, take_precio
                    )
                    proteccion_ok = True
                    break
                except Exception as e_intento:
                    ultimo_error = e_intento
                    print(f"  intento {intento+1}/3 fallo: {e_intento}")
            if not proteccion_ok:
                raise ultimo_error
            print(f"✅ Protección colocada — stop #{orden_stop_id} | take #{orden_take_id}")

            enviar_telegram(f"""<b>✅ EJECUCIÓN AUTOMÁTICA</b>
{simbolo}
Precio entrada: <b>€{precio_real:.4f}</b>
Cantidad: <b>{cantidad_real}</b>
Capital: <b>€{capital:.2f} EUR</b>
Stop loss: €{stop_precio} (ID: {orden_stop_id})
Take profit: €{take_precio} (ID: {orden_take_id})
<i>Órdenes colocadas automáticamente</i>""")

        except Exception as prot_err:
            print(f"⚠️ Error colocando protección: {prot_err}")
            enviar_telegram(f"""<b>⚠️ COMPRA EJECUTADA — PROTECCIÓN MANUAL REQUERIDA</b>
{simbolo}
Precio entrada: <b>€{precio_real:.4f}</b>
Cantidad: <b>{cantidad_real}</b>
Capital: <b>€{capital:.2f} EUR</b>

Coloca manualmente en Bitvavo:
- Stop limit — trigger: {stop_precio} | limit: {round(stop_precio * 0.998, 4)}
- Take profit — limit: {take_precio}
Cantidad: {cantidad_real}

<b>⚠️ Posición desprotegida hasta que lo hagas</b>""")

        precio_senal = round(precio, 6)
        slippage_bps = round((precio_real - precio) / precio * 10000, 1)

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
            'venue':          'bitvavo',
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
    print(f"✅ Conexión OK — Saldo EUR: €{saldo:.2f}")
    print(f"   Capital base: €{CAPITAL_BASE}")
    print(f"   Kelly/4 máx (10%): €{CAPITAL_BASE * 0.10:.0f} por operación")
