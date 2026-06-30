import os
import ccxt
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

load_dotenv()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ARCHIVO = '/root/proyectos-quant/operaciones_reales.csv'

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

def cancelar_orden(exchange, simbolo, orden_id, etiqueta='orden'):
    """Cancela una orden por ID. Silencia errores si ya no existe."""
    if not orden_id or str(orden_id).strip() == '':
        return
    try:
        exchange.cancel_order(str(orden_id), simbolo)
        print(f"  🗑 {etiqueta} #{orden_id} cancelada")
    except Exception as e:
        # La orden puede ya estar ejecutada o cancelada — no es error crítico
        print(f"  ℹ️ {etiqueta} #{orden_id} no cancelable: {e}")

def colocar_stop_limit(exchange, simbolo, cantidad, stop_precio):
    """Coloca una nueva orden stop-limit y devuelve su ID."""
    stop_limit = round(stop_precio * 0.998, 4)
    orden = exchange.create_order(
        simbolo,
        'stop_loss_limit',
        'sell',
        cantidad,
        stop_limit,
        {'stopPrice': stop_precio, 'timeInForce': 'GTC'},
    )
    return orden['id']

def determinar_precio_cierre(exchange, simbolo, stop, take):
    """Intenta obtener el precio real de cierre desde el historial."""
    try:
        historial    = exchange.fetch_orders(simbolo, limit=10)
        ordenes_sell = [
            o for o in historial
            if o['side'] == 'sell' and o['status'] == 'closed'
        ]
        if ordenes_sell:
            ultima = sorted(ordenes_sell, key=lambda x: x['timestamp'])[-1]
            return float(ultima['average'] or ultima['price'])
    except:
        pass
    return exchange.fetch_ticker(simbolo)['last']

def evaluar_operaciones():
    if not os.path.exists(ARCHIVO):
        print("No hay operaciones registradas")
        return

    df = pd.read_csv(ARCHIVO)
    # Columnas que pueden recibir valores numéricos en runtime -> float
    for col in ('stop_loss', 'precio_cierre', 'retorno_pct'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # Columnas de texto/ID -> object, para evitar conflictos dtype
    for col in ('orden_stop_id', 'orden_take_id', 'fecha_cierre', 'resultado'):
        if col in df.columns:
            df[col] = df[col].astype('object')
    exchange     = get_exchange()
    ahora        = datetime.now(timezone.utc)
    actualizaciones = 0

    # Asegurar columnas nuevas si el CSV es antiguo
    for col in ('orden_stop_id', 'orden_take_id'):
        if col not in df.columns:
            df[col] = ''

    for idx, fila in df.iterrows():
        # Saltar operaciones ya cerradas
        if pd.notna(fila['resultado']) and str(fila['resultado']).strip() != '':
            continue

        simbolo        = str(fila['activo']).replace('USDT', 'USDC')
        simbolo_orig   = str(fila['activo'])
        precio_entrada = float(fila['precio_entrada'])
        stop           = float(fila['stop_loss'])
        take           = float(fila['take_profit'])
        cantidad       = float(fila['cantidad'])
        stop_id        = str(fila.get('orden_stop_id', '')).strip()
        take_id        = str(fila.get('orden_take_id', '')).strip()

        try:
            ordenes_abiertas = exchange.fetch_open_orders(simbolo)
            ids_abiertos     = {str(o['id']) for o in ordenes_abiertas}

            # ── CASO 1: ninguna orden abierta → posición cerrada ─────────
            if len(ordenes_abiertas) == 0:
                precio_cierre = determinar_precio_cierre(exchange, simbolo, stop, take)
                retorno  = round((precio_cierre - precio_entrada) / precio_entrada * 100, 2)
                pnl_usdc = round((precio_cierre - precio_entrada) * cantidad, 2)

                if precio_cierre <= stop * 1.01:
                    resultado = 'stop_loss'
                elif precio_cierre >= take * 0.99:
                    resultado = 'take_profit'
                else:
                    resultado = 'cerrado'

                df.at[idx, 'fecha_cierre']  = ahora.strftime('%Y-%m-%d %H:%M')
                df.at[idx, 'precio_cierre'] = precio_cierre
                df.at[idx, 'retorno_pct']   = retorno
                df.at[idx, 'resultado']     = resultado
                actualizaciones += 1

                print(f"✅ {simbolo_orig} cerrado — {resultado} | {retorno:.2f}%")
                enviar_telegram(f"""<b>📊 Operación cerrada</b>
{simbolo_orig}
Entrada: ${precio_entrada}
Cierre: ${precio_cierre:.4f}
Retorno: <b>{retorno:.2f}%</b>
P&L: <b>${pnl_usdc:+.2f} USDC</b>
Resultado: <b>{resultado}</b>""")

            # ── CASO 2: solo una orden abierta → la otra se ejecutó ──────
            elif len(ordenes_abiertas) == 1:
                # Cancelar la orden huérfana
                orden_huerfana = ordenes_abiertas[0]
                cancelar_orden(exchange, simbolo, orden_huerfana['id'], 'huérfana')

                precio_cierre = determinar_precio_cierre(exchange, simbolo, stop, take)
                retorno  = round((precio_cierre - precio_entrada) / precio_entrada * 100, 2)
                pnl_usdc = round((precio_cierre - precio_entrada) * cantidad, 2)

                if precio_cierre <= stop * 1.01:
                    resultado = 'stop_loss'
                elif precio_cierre >= take * 0.99:
                    resultado = 'take_profit'
                else:
                    resultado = 'cerrado'

                df.at[idx, 'fecha_cierre']  = ahora.strftime('%Y-%m-%d %H:%M')
                df.at[idx, 'precio_cierre'] = precio_cierre
                df.at[idx, 'retorno_pct']   = retorno
                df.at[idx, 'resultado']     = resultado
                actualizaciones += 1

                print(f"✅ {simbolo_orig} cerrado (huérfana cancelada) — {resultado} | {retorno:.2f}%")
                enviar_telegram(f"""<b>📊 Operación cerrada</b>
{simbolo_orig}
Entrada: ${precio_entrada}
Cierre: ${precio_cierre:.4f}
Retorno: <b>{retorno:.2f}%</b>
P&L: <b>${pnl_usdc:+.2f} USDC</b>
Resultado: <b>{resultado}</b>
<i>Orden huérfana cancelada automáticamente</i>""")

            # ── CASO 3: dos órdenes abiertas → posición activa ───────────
            else:
                precio_actual = exchange.fetch_ticker(simbolo)['last']
                nuevo_stop    = round(precio_actual * 0.98, 4)

                if nuevo_stop > stop * 1.02:
                    # Trailing stop: cancelar stop antiguo, colocar nuevo
                    try:
                        cancelar_orden(exchange, simbolo, stop_id, 'stop antiguo')
                        nuevo_stop_id = colocar_stop_limit(exchange, simbolo, cantidad, nuevo_stop)

                        df.at[idx, 'stop_loss']     = nuevo_stop
                        df.at[idx, 'orden_stop_id'] = nuevo_stop_id
                        actualizaciones += 1

                        print(f"🔼 {simbolo_orig} trailing stop: ${stop} → ${nuevo_stop} (#{nuevo_stop_id})")
                        enviar_telegram(f"""<b>🔼 Trailing stop actualizado</b>
{simbolo_orig}
Precio actual: <b>${precio_actual:.4f}</b>
Stop anterior: ${stop}
Stop nuevo: <b>${nuevo_stop}</b>
<i>Actualizado automáticamente en Binance</i>""")

                    except Exception as trail_err:
                        print(f"⚠️ Error en trailing stop {simbolo_orig}: {trail_err}")
                        enviar_telegram(f"""<b>⚠️ Trailing stop — acción manual requerida</b>
{simbolo_orig}
Precio actual: ${precio_actual:.4f}
Stop sugerido: <b>${nuevo_stop}</b>
Error automático: {trail_err}
<b>Mueve el stop manualmente en Binance</b>""")
                else:
                    print(f"⏸ {simbolo_orig} sin cambios | precio: ${precio_actual:.2f} | stop: ${stop}")

        except Exception as e:
            print(f"⚠️ Error evaluando {simbolo_orig}: {e}")

    if actualizaciones > 0:
        df.to_csv(ARCHIVO, index=False)
        print(f"✅ {actualizaciones} actualizaciones guardadas")
    else:
        print(f"✅ Sin cambios — {ahora.strftime('%Y-%m-%d %H:%M UTC')}")

evaluar_operaciones()
