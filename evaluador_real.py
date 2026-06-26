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
        # Solo operaciones sin cerrar
        if pd.notna(fila['resultado']) and fila['resultado'] != '':
            continue

        simbolo = fila['activo'].replace('USDT', 'USDC')

        try:
            # Verificar si hay órdenes OCO abiertas
            ordenes_abiertas = exchange.fetch_open_orders(simbolo)

            if len(ordenes_abiertas) == 0:
                # Consultar historial de órdenes ejecutadas
                precio_entrada = float(fila['precio_entrada'])
                stop = float(fila['stop_loss'])
                take = float(fila['take_profit'])
                try:
                    historial = exchange.fetch_orders(simbolo, limit=10)
                    ordenes_sell = [o for o in historial if o['side'] == 'sell' and o['status'] == 'closed']
                    if ordenes_sell:
                        ultima = sorted(ordenes_sell, key=lambda x: x['timestamp'])[-1]
                        precio_cierre = float(ultima['average'] or ultima['price'])
                    else:
                        ticker = exchange.fetch_ticker(simbolo)
                        precio_cierre = ticker['last']
                except:
                    ticker = exchange.fetch_ticker(simbolo)
                    precio_cierre = ticker['last']
                retorno = round((precio_cierre - precio_entrada) / precio_entrada * 100, 2)
                if precio_cierre <= stop * 1.01:
                    resultado = 'stop_loss'
                elif precio_cierre >= take * 0.99:
                    resultado = 'take_profit'
                else:
                    resultado = 'cerrado'
                actualizaciones += 1

        except Exception as e:
            print(f"⚠️ Error evaluando {simbolo}: {e}")

    if actualizaciones > 0:
        df.to_csv(ARCHIVO, index=False)
        print(f"✅ {actualizaciones} operaciones actualizadas")
    else:
        print(f"✅ Sin cambios — {ahora.strftime('%Y-%m-%d %H:%M UTC')}")

evaluar_operaciones()
