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
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_SECRET_KEY"),
        'enableRateLimit': True,
        'options': {'defaultType': 'spot', 'fetchCurrencies': False},
    })

def evaluar_operaciones():
    if not os.path.exists(ARCHIVO):
        print("No hay operaciones registradas")
        return

    df = pd.read_csv(ARCHIVO)
    exchange = get_exchange()
    ahora = datetime.now(timezone.utc)
    actualizaciones = 0

    for idx, fila in df.iterrows():
        if pd.notna(fila['resultado']) and fila['resultado'] != '':
            continue

        simbolo      = fila['activo'].replace('USDT', 'USDC')
        simbolo_orig = fila['activo']
        precio_entrada = float(fila['precio_entrada'])
        stop           = float(fila['stop_loss'])
        take           = float(fila['take_profit'])
        cantidad       = float(fila['cantidad'])

        try:
            ordenes_abiertas = exchange.fetch_open_orders(simbolo)

            if len(ordenes_abiertas) == 0:
                # OCO ejecutada — determinar resultado
                try:
                    historial    = exchange.fetch_orders(simbolo, limit=10)
                    ordenes_sell = [o for o in historial if o['side'] == 'sell' and o['status'] == 'closed']
                    if ordenes_sell:
                        ultima        = sorted(ordenes_sell, key=lambda x: x['timestamp'])[-1]
                        precio_cierre = float(ultima['average'] or ultima['price'])
                    else:
                        precio_cierre = exchange.fetch_ticker(simbolo)['last']
                except:
                    precio_cierre = exchange.fetch_ticker(simbolo)['last']

                retorno = round((precio_cierre - precio_entrada) / precio_entrada * 100, 2)
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

                print(f"✅ {simbolo_orig} cerrado — {resultado} | retorno: {retorno:.2f}%")
                enviar_telegram(f"""<b>📊 Operación cerrada</b>
{simbolo_orig}
Entrada: ${precio_entrada}
Cierre: ${precio_cierre:.4f}
Retorno: <b>{retorno:.2f}%</b>
Resultado: <b>{resultado}</b>""")

            else:
                # Posición abierta — aplicar trailing stop
                precio_actual = exchange.fetch_ticker(simbolo)['last']
                stop_actual   = stop
                nuevo_stop    = round(precio_actual * 0.98, 4)  # 2% por debajo del precio actual

                if nuevo_stop > stop_actual:
                    # El precio subió suficiente — mover el stop
                    nuevo_stop_limit = round(nuevo_stop * 0.998, 4)
                    nuevo_take       = take  # take profit no cambia

                    enviar_telegram(f"""<b>🔼 Trailing stop — acción requerida</b>
{simbolo_orig}
Precio actual: <b>${precio_actual:.4f}</b>
Stop actual: ${stop_actual}
Stop sugerido: <b>${nuevo_stop}</b> (2% bajo máximo)
Take profit: ${take}

⚠️ Mueve el stop manualmente en Binance""")
                    print(f"🔼 {simbolo_orig} alerta trailing stop: ${stop_actual} -> ${nuevo_stop}")

                else:
                    print(f"⏸ {simbolo_orig} trailing stop sin cambios | precio: ${precio_actual:.2f} | stop: ${stop_actual}")

        except Exception as e:
            print(f"⚠️ Error evaluando {simbolo_orig}: {e}")

    if actualizaciones > 0:
        df.to_csv(ARCHIVO, index=False)
        print(f"✅ {actualizaciones} actualizaciones guardadas")
    else:
        print(f"✅ Sin cambios — {ahora.strftime('%Y-%m-%d %H:%M UTC')}")

evaluar_operaciones()
