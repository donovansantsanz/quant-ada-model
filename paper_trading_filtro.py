"""
Paper trading paralelo con filtro vol5d > p70.
Corre en paralelo al sistema real para comparar:
- Serie A: sistema actual (sin filtro) → operaciones_reales.csv
- Serie B: sistema con filtro vol5d > p70 → paper_trading_filtro.csv

NO ejecuta ordenes reales. Solo registra si habria operado o no.
"""
import os
import csv
import ccxt
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))

ARCHIVO = os.path.expanduser('~/proyectos-quant/paper_trading_filtro.csv')

def get_exchange():
    return ccxt.bitvavo({
        'apiKey': os.getenv("BITVAVO_API_KEY"),
        'secret': os.getenv("BITVAVO_API_SECRET"),
        'enableRateLimit': True,
        'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
    })

def calcular_vol5d_pct(exchange, simbolo):
    """Calcula el percentil historico de la volatilidad 5d actual."""
    ohlcv = exchange.fetch_ohlcv(simbolo, '1d', limit=180)
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
    df['ret'] = df['close'].pct_change()
    df['vol5d'] = df['ret'].rolling(5).std()
    vol5d_vals = df['vol5d'].dropna().values
    vol5d_actual = df['vol5d'].iloc[-1]
    if np.isnan(vol5d_actual) or len(vol5d_vals) < 10:
        return None
    return stats.percentileofscore(vol5d_vals, vol5d_actual)

def registrar(fecha, activo, sistema, score, umbral, rsi, precio,
              decision_real, decision_filtro, vol5d_pct, motivo_filtro):
    """Registra una señal en el CSV de paper trading."""
    escribir_header = not os.path.exists(ARCHIVO)
    with open(ARCHIVO, 'a', newline='') as f:
        writer = csv.writer(f)
        if escribir_header:
            writer.writerow([
                'fecha', 'activo', 'sistema', 'score', 'umbral', 'rsi',
                'precio', 'decision_real', 'decision_filtro',
                'vol5d_pct', 'motivo_filtro'
            ])
        writer.writerow([
            fecha, activo, sistema, score, umbral, round(rsi, 1),
            precio, decision_real, decision_filtro,
            round(vol5d_pct, 1) if vol5d_pct else 'N/A', motivo_filtro
        ])

def evaluar_señal(simbolo, score, umbral, rsi, precio, sistema):
    """Evalua si el filtro vol5d habria bloqueado esta señal."""
    if score < umbral:
        return  # No es señal de compra, no registrar

    exchange = get_exchange()
    vol5d_pct = calcular_vol5d_pct(exchange, simbolo)
    fecha = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    decision_real = "COMPRAR"

    if vol5d_pct is not None and vol5d_pct > 70:
        decision_filtro = "BLOQUEADO"
        motivo = f"vol5d_pct={vol5d_pct:.0f}% > 70%"
    else:
        decision_filtro = "COMPRAR"
        motivo = f"vol5d_pct={vol5d_pct:.0f}% <= 70%" if vol5d_pct else "sin datos"

    registrar(fecha, simbolo, sistema, score, umbral, rsi, precio,
              decision_real, decision_filtro, vol5d_pct, motivo)

    print(f"[paper_filtro] {simbolo} | Score {score}/{umbral} | vol5d={vol5d_pct:.0f}% | {decision_filtro}")

    return decision_filtro

if __name__ == '__main__':
    # Test manual
    print("Paper trading filtro — test")
    print(f"CSV: {ARCHIVO}")
    if os.path.exists(ARCHIVO):
        df = pd.read_csv(ARCHIVO)
        print(f"Registros: {len(df)}")
        print(df.tail(5).to_string())
    else:
        print("Sin registros todavia")
