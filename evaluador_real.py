import os
import ccxt
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
from conexion import get_exchange

load_dotenv()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ARCHIVO = '/root/proyectos-quant/operaciones_reales.csv'

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

def limpiar_id(x):
    """Convierte un ID a string. Enteros de Binance -> str sin .0.
    UUID de Bitvavo -> se devuelven tal cual (float() falla y cae al except)."""
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s

def id_valido(x):
    s = str(x).strip().lower()
    return s not in ('', 'nan', 'none')

def estado_orden(exchange, simbolo, orden_id):
    """Devuelve el status de una orden por ID, o None si no existe/error."""
    if not id_valido(orden_id):
        return None
    try:
        o = exchange.fetch_order(limpiar_id(orden_id), simbolo)
        return o['status']  # 'open', 'closed', 'canceled', etc.
    except Exception as e:
        print(f"  ℹ️ no se pudo consultar orden #{orden_id}: {e}")
        return None

def cancelar_orden(exchange, simbolo, orden_id, etiqueta='orden'):
    if not id_valido(orden_id):
        return
    try:
        exchange.cancel_order(limpiar_id(orden_id), simbolo)
        print(f"  🗑 {etiqueta} #{orden_id} cancelada")
    except Exception as e:
        print(f"  ℹ️ {etiqueta} #{orden_id} no cancelable: {e}")

def colocar_stop_limit(exchange, simbolo, cantidad, stop_precio):
    stop_limit = round(stop_precio * 0.998, 4)
    orden = exchange.create_order(
        simbolo, 'stopLossLimit', 'sell', cantidad, stop_limit,
        {'triggerPrice': stop_precio},
    )
    return orden['id']

def registrar_cierre(df, idx, precio_entrada, precio_cierre, cantidad, resultado, ahora, extra=''):
    retorno = round((precio_cierre - precio_entrada) / precio_entrada * 100, 2)
    pnl_eur = round((precio_cierre - precio_entrada) * cantidad, 2)
    df.at[idx, 'fecha_cierre']  = ahora.strftime('%Y-%m-%d %H:%M')
    df.at[idx, 'precio_cierre'] = precio_cierre
    df.at[idx, 'retorno_pct']   = retorno
    df.at[idx, 'resultado']     = resultado
    simbolo_orig = str(df.at[idx, 'activo'])
    print(f"✅ {simbolo_orig} cerrado — {resultado} | {retorno:.2f}%")
    enviar_telegram(f"""<b>📊 Operación cerrada</b>
{simbolo_orig}
Entrada: €{precio_entrada}
Cierre: €{precio_cierre:.4f}
Retorno: <b>{retorno:.2f}%</b>
P&L: <b>€{pnl_eur:+.2f} EUR</b>
Resultado: <b>{resultado}</b>{extra}""")
    return retorno

def evaluar_operaciones():
    if not os.path.exists(ARCHIVO):
        print("No hay operaciones registradas")
        return

    df = pd.read_csv(ARCHIVO, dtype={'orden_stop_id': str, 'orden_take_id': str})
    for col in ('stop_loss', 'precio_cierre', 'retorno_pct'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ('orden_stop_id', 'orden_take_id', 'fecha_cierre', 'resultado'):
        if col in df.columns:
            df[col] = df[col].astype('object')

    exchange     = get_exchange()
    ahora        = datetime.now(timezone.utc)
    actualizaciones = 0

    for idx, fila in df.iterrows():
        resultado_val = str(fila['resultado']).strip() if pd.notna(fila['resultado']) else ''
        if resultado_val not in ('', 'nan'):
            continue

        simbolo        = str(fila['activo']).replace('/USDT', '/EUR').replace('/USDC', '/EUR')
        simbolo_orig   = str(fila['activo'])
        precio_entrada = float(fila['precio_entrada'])
        stop           = float(fila['stop_loss'])
        take           = float(fila['take_profit'])
        cantidad       = float(fila['cantidad'])
        stop_id        = fila.get('orden_stop_id', '')
        take_id        = fila.get('orden_take_id', '')

        try:
            # ── MÉTODO POR ID (operaciones con IDs guardados) ────────────
            if id_valido(stop_id) or id_valido(take_id):
                est_stop = estado_orden(exchange, simbolo, stop_id)
                est_take = estado_orden(exchange, simbolo, take_id)

                stop_ejecutado = est_stop in ('closed', 'filled')
                take_ejecutado = est_take in ('closed', 'filled')
                stop_abierto   = est_stop == 'open'
                take_abierto   = est_take == 'open'

                if stop_ejecutado:
                    cancelar_orden(exchange, simbolo, take_id, 'take huérfano')
                    registrar_cierre(df, idx, precio_entrada, stop, cantidad,
                                     'stop_loss', ahora,
                                     '\n<i>Stop ejecutado, take cancelado</i>')
                    actualizaciones += 1

                elif take_ejecutado:
                    cancelar_orden(exchange, simbolo, stop_id, 'stop huérfano')
                    registrar_cierre(df, idx, precio_entrada, take, cantidad,
                                     'take_profit', ahora,
                                     '\n<i>Take ejecutado, stop cancelado</i>')
                    actualizaciones += 1

                elif stop_abierto and take_abierto:
                    # Posición activa → trailing stop
                    precio_actual = exchange.fetch_ticker(simbolo)['last']
                    nuevo_stop    = round(precio_actual * 0.98, 4)
                    if nuevo_stop > stop * 1.02:
                        try:
                            cancelar_orden(exchange, simbolo, stop_id, 'stop antiguo')
                            nuevo_stop_id = colocar_stop_limit(exchange, simbolo, cantidad, nuevo_stop)
                            df.at[idx, 'stop_loss']     = nuevo_stop
                            df.at[idx, 'orden_stop_id'] = nuevo_stop_id
                            actualizaciones += 1
                            print(f"🔼 {simbolo_orig} trailing: €{stop} -> €{nuevo_stop} (#{nuevo_stop_id})")
                            enviar_telegram(f"""<b>🔼 Trailing stop actualizado</b>
{simbolo_orig}
Precio actual: <b>€{precio_actual:.4f}</b>
Stop anterior: €{stop}
Stop nuevo: <b>€{nuevo_stop}</b>
<i>Actualizado automáticamente en Bitvavo</i>""")
                        except Exception as te:
                            print(f"⚠️ Error trailing {simbolo_orig}: {te}")
                    else:
                        print(f"⏸ {simbolo_orig} sin cambios | precio: €{precio_actual:.2f} | stop: €{stop}")

                else:
                    print(f"⚠️ {simbolo_orig} estado ambiguo — stop:{est_stop} take:{est_take} — sin acción")

            # ── MÉTODO ANTIGUO (operaciones sin IDs, por compatibilidad) ─
            else:
                ordenes_abiertas = exchange.fetch_open_orders(simbolo)
                if len(ordenes_abiertas) == 0:
                    precio_cierre = exchange.fetch_ticker(simbolo)['last']
                    resultado = 'stop_loss' if precio_cierre <= stop * 1.01 else ('take_profit' if precio_cierre >= take * 0.99 else 'cerrado')
                    registrar_cierre(df, idx, precio_entrada, precio_cierre, cantidad, resultado, ahora)
                    actualizaciones += 1
                else:
                    print(f"⏸ {simbolo_orig} (sin IDs) {len(ordenes_abiertas)} órdenes — sin acción")

        except Exception as e:
            print(f"⚠️ Error evaluando {simbolo_orig}: {e}")

    if actualizaciones > 0:
        df.to_csv(ARCHIVO, index=False)
        print(f"✅ {actualizaciones} actualizaciones guardadas")
    else:
        print(f"✅ Sin cambios — {ahora.strftime('%Y-%m-%d %H:%M UTC')}")

evaluar_operaciones()
