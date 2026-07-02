import os
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import PARAMS

load_dotenv()

from datetime import datetime as _dt

ARCHIVO = "paper_trading_registro.csv"

# ── PARÁMETROS ÓPTIMOS POR ACTIVO ────────────────────────────────

# ── CARGAR O CREAR REGISTRO ──────────────────────────────────────
if os.path.exists(ARCHIVO):
    registro = pd.read_csv(ARCHIVO, dtype={
        'salida': 'object', 'acierto': 'object', 'evaluado': 'object'
    })
else:
    registro = pd.DataFrame(columns=[
        'fecha', 'activo', 'precio_entrada', 'decision',
        'score', 'rsi', 'prob_mc', 'stop_loss', 'take_profit',
        'kelly', 'fecha_evaluacion', 'precio_evaluacion',
        'retorno_pct', 'salida', 'acierto', 'evaluado'
    ])
    registro = registro.astype({
        'precio_entrada': 'float64', 'rsi': 'float64',
        'stop_loss': 'float64', 'take_profit': 'float64',
        'precio_evaluacion': 'float64', 'retorno_pct': 'float64',
        'salida': 'object', 'acierto': 'object', 'evaluado': 'object'
    })


# ── FILTRO BTC ───────────────────────────────────────────────────
def filtro_btc():
    exchange   = ccxt.binance()
    velas      = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', limit=10)
    df         = pd.DataFrame(velas, columns=['timestamp','open','high','low','close','volume'])
    precios    = df['close']
    mom_7      = precios.iloc[-1] / precios.iloc[-8] - 1
    mom_3      = precios.iloc[-1] / precios.iloc[-4] - 1
    if mom_3 < -0.05:
        return False
    return True

import json as _json

def analizar(simbolo, btc_ok):
    """Lee los resultados del monitor_v2.py en lugar de recalcular."""
    json_path = '/root/proyectos-quant/monitor_resultados.json'
    if not os.path.exists(json_path):
        print(f"⚠️  JSON no encontrado — recalculando {simbolo}")
        return None
    with open(json_path) as f:
        resultados = _json.load(f)
    if simbolo not in resultados:
        print(f"⚠️  {simbolo} no en JSON")
        return None
    return resultados[simbolo]


# ── EVALUAR SEÑALES PENDIENTES ───────────────────────────────────
hoy      = datetime.now().date()
exchange = ccxt.binance()

for idx, fila in registro.iterrows():
    if str(fila['evaluado']) == 'False' or fila['evaluado'] == False:
        fecha_eval = pd.to_datetime(fila['fecha_evaluacion']).date()
        if hoy >= fecha_eval and fila['decision'] == 'COMPRAR':
            # Descargar velas desde entrada hasta hoy
            simbolo    = fila['activo']
            p_entrada  = float(fila['precio_entrada'])
            stop       = float(fila['stop_loss']) / 100
            take       = float(fila['take_profit']) / 100

            from datetime import timezone
            fecha_entrada_ts = int(pd.to_datetime(fila['fecha']).replace(tzinfo=timezone.utc).timestamp() * 1000)
            fecha_eval_ts    = int(pd.to_datetime(fila['fecha_evaluacion']).replace(tzinfo=timezone.utc).timestamp() * 1000)
            velas = exchange.fetch_ohlcv(simbolo, timeframe='1d', since=fecha_entrada_ts, limit=20)
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
            print(f"✅ {simbolo} — Retorno: {retorno_final:.2f}% — Salida: {salida} — {'ACIERTO' if acierto else 'FALLO'}")

# ── REGISTRAR SEÑALES DE HOY ─────────────────────────────────────
btc_ok = filtro_btc()

for simbolo in PARAMS:
    ya_registrado = (
        not registro.empty and
        ((registro['fecha'].str.startswith(str(hoy))) & (registro['activo'] == simbolo)).any()
    )

    if not ya_registrado:
        print(f"Analizando {simbolo}...")
        d = analizar(simbolo, btc_ok)

        nueva_fila = {
            'fecha':             _dt.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%d %H:%M'),
            'activo':            simbolo,
            'precio_entrada':    d['precio'],
            'decision':          d['decision'],
            'score':             d['puntos'],
            'rsi':               d['rsi'],
            'prob_mc':           d['prob_mc'],
            'stop_loss':         d['stop'],
            'take_profit':       d['take'],
            'kelly':             d['kelly'],
            'fecha_evaluacion':  str(hoy + timedelta(days=14)),
            'precio_evaluacion': None,
            'retorno_pct':       None,
            'salida':            None,
            'acierto':           None,
            'evaluado':          False
        }
        registro = pd.concat([registro, pd.DataFrame([nueva_fila])], ignore_index=True)
        print(f"   {simbolo}: {d['decision']} | Score: {d['puntos']} | RSI: {d['rsi']}")

# ── GUARDAR ──────────────────────────────────────────────────────
registro.to_csv(ARCHIVO, index=False)
print(f"\n✅ Registro guardado en {ARCHIVO} — {_dt.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}")

# ── TRACK RECORD ─────────────────────────────────────────────────
evaluados = registro[registro['evaluado'] == True]
if len(evaluados) > 0:
    compras = evaluados[evaluados['decision'] == 'COMPRAR']
    if len(compras) > 0:
        win_rate = compras['acierto'].mean() * 100
        print(f"\n📊 TRACK RECORD ACTUAL")
        print(f"   Operaciones evaluadas: {len(compras)}")
        print(f"   Win rate:              {win_rate:.1f}%")
        print(f"   Retorno medio:         {compras['retorno_pct'].mean():.2f}%")
        stops = len(compras[compras['salida'] == 'stop_loss'])
        takes = len(compras[compras['salida'] == 'take_profit'])
        print(f"   Stop loss activado:    {stops} veces")
        print(f"   Take profit activado:  {takes} veces")