import os
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from config_4h import PARAMS_4H, PARAMS_4H_OBS

load_dotenv()

ARCHIVO = "/root/proyectos-quant/paper_trading_4h_registro.csv"
ACTIVOS_4H = list(PARAMS_4H.keys())

if os.path.exists(ARCHIVO):
    registro = pd.read_csv(ARCHIVO, dtype={
        'salida': 'object',
        'acierto': 'object',
        'evaluado': 'object'
    })
else:
    registro = pd.DataFrame(columns=[
        'fecha', 'activo', 'precio_entrada', 'decision',
        'score', 'rsi', 'stop_loss', 'take_profit', 'kelly',
        'fecha_evaluacion', 'precio_evaluacion',
        'retorno_pct', 'salida', 'acierto', 'evaluado'
    ])
    registro = registro.astype({
        'precio_entrada': 'float64',
        'score': 'object',
        'rsi': 'float64',
        'stop_loss': 'float64',
        'take_profit': 'float64',
        'precio_evaluacion': 'float64',
        'retorno_pct': 'float64',
        'salida': 'object',
        'acierto': 'object',
        'evaluado': 'object'
    })

import json as _json

def analizar_4h(simbolo):
    """Lee los resultados del monitor_4h.py en lugar de recalcular."""
    json_path = '/root/proyectos-quant/monitor_4h_resultados.json'
    if not os.path.exists(json_path):
        print(f"⚠️  JSON 4h no encontrado para {simbolo}")
        return None
    with open(json_path) as f:
        resultados = _json.load(f)
    if simbolo not in resultados:
        print(f"⚠️  {simbolo} no en JSON 4h")
        return None
    return resultados[simbolo]


ahora    = datetime.now(timezone.utc)
exchange = ccxt.binance()

for idx, fila in registro.iterrows():
    if str(fila['evaluado']) == 'False' or fila['evaluado'] == False:
        fecha_eval = pd.to_datetime(fila['fecha_evaluacion'])
        if fecha_eval.tzinfo is None:
            fecha_eval = fecha_eval.replace(tzinfo=timezone.utc)
        if ahora >= fecha_eval and fila['decision'] == 'COMPRAR':
            simbolo   = fila['activo']
            p_entrada = float(fila['precio_entrada'])
            stop      = float(fila["stop_loss"]) / 100
            take      = float(fila["take_profit"]) / 100

            fecha_entrada_ts = int(pd.to_datetime(fila['fecha']).replace(tzinfo=timezone.utc).timestamp() * 1000)
            fecha_eval_ts    = int(fecha_eval.timestamp() * 1000)
            velas = exchange.fetch_ohlcv(simbolo, timeframe='4h', since=fecha_entrada_ts, limit=50)
            df_eval = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
            df_eval = df_eval[df_eval['timestamp'] <= fecha_eval_ts]

            precio_stop = p_entrada * (1 - stop)
            precio_take = p_entrada * (1 + take)
            retorno_final = None
            salida = "horizonte"

            for _, v in df_eval.iterrows():
                if v['low'] <= precio_stop:
                    retorno_final = -stop * 100
                    salida = "stop_loss"
                    break
                elif v['high'] >= precio_take:
                    retorno_final = take * 100
                    salida = "take_profit"
                    break

            if retorno_final is None:
                ticker = exchange.fetch_ticker(simbolo)
                retorno_final = (ticker['last'] - p_entrada) / p_entrada * 100
                salida = "horizonte"

            acierto = retorno_final > 0
            registro.at[idx, 'precio_evaluacion'] = exchange.fetch_ticker(simbolo)['last']
            registro.at[idx, 'retorno_pct']       = round(retorno_final, 2)
            registro.at[idx, 'salida']            = salida
            registro.at[idx, 'acierto']           = acierto
            registro.at[idx, 'evaluado']          = True
            print(f"✅ {simbolo} — Retorno: {retorno_final:.2f}% — {salida}")

# Registrar señal actual
ahora_str = ahora.strftime('%Y-%m-%d %H:%M')
eval_str  = (ahora + timedelta(days=2)).strftime('%Y-%m-%d %H:%M')

for simbolo in ACTIVOS_4H:
    ya_registrado = (
        not registro.empty and
        ((registro['fecha'] == ahora_str) & (registro['activo'] == simbolo)).any()
    )
    if not ya_registrado:
        d = analizar_4h(simbolo)
        nueva_fila = {
            'fecha':             ahora_str,
            'activo':            simbolo,
            'precio_entrada':    d['precio'],
            'decision':          d['decision'],
            'score':             d['score'],
            'rsi':               d['rsi'],
            'stop_loss':         d['stop'],
            'take_profit':       d['take'],
            'kelly':             d['kelly'],
            'fecha_evaluacion':  eval_str,
            'precio_evaluacion': None,
            'retorno_pct':       None,
            'salida':            None,
            'acierto':           None,
            'evaluado':          False
        }
        registro = pd.concat([registro, pd.DataFrame([nueva_fila])], ignore_index=True)
        print(f"{simbolo} 4h: {d['decision']} | Score: {d['score']} | RSI: {d['rsi']:.1f} | Precio: ${d['precio']:.2f}")

registro.to_csv(ARCHIVO, index=False)
print(f"✅ Registro 4h guardado — {ahora_str} UTC")
