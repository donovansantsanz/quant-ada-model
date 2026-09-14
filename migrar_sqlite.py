import sqlite3
import pandas as pd
from datetime import datetime, timezone

CSV = '/root/proyectos-quant/operaciones_reales.csv'
DB  = '/root/proyectos-quant/operaciones.db'

df = pd.read_csv(CSV)

conn = sqlite3.connect(DB)
cur  = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS operaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_entrada    TEXT,
    activo           TEXT,
    sistema          TEXT,
    precio_entrada   REAL,
    cantidad         REAL,
    capital_usdc     REAL,
    stop_loss        REAL,
    take_profit      REAL,
    kelly            TEXT,
    precio_senal     REAL,
    slippage_bps     REAL,
    orden_stop_id    TEXT,
    orden_take_id    TEXT,
    fecha_cierre     TEXT,
    precio_cierre    REAL,
    retorno_pct      REAL,
    resultado        TEXT,
    notas            TEXT,
    venue            TEXT,
    timeframe        TEXT,
    capital_eur      REAL,
    riesgo_pct       REAL,
    precio_apertura_vela REAL,
    dias_en_trade    REAL,
    stop             REAL,
    take             REAL,
    insertado_en     TEXT
)
''')

ahora = datetime.now(timezone.utc).isoformat()
insertadas = 0
for _, row in df.iterrows():
    fecha = str(row.get('fecha_entrada', ''))
    activo = str(row.get('activo', ''))
    exists = cur.execute(
        'SELECT 1 FROM operaciones WHERE fecha_entrada=? AND activo=?',
        (fecha, activo)
    ).fetchone()
    if not exists:
        cur.execute('''
        INSERT INTO operaciones (
            fecha_entrada, activo, sistema, precio_entrada, cantidad, capital_usdc,
            stop_loss, take_profit, kelly, precio_senal, slippage_bps,
            orden_stop_id, orden_take_id, fecha_cierre, precio_cierre,
            retorno_pct, resultado, notas, venue, timeframe, capital_eur,
            riesgo_pct, precio_apertura_vela, dias_en_trade, stop, take, insertado_en
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            fecha, activo,
            row.get('sistema'), row.get('precio_entrada'), row.get('cantidad'),
            row.get('capital_usdc'), row.get('stop_loss'), row.get('take_profit'),
            row.get('kelly'), row.get('precio_senal'), row.get('slippage_bps'),
            row.get('orden_stop_id'), row.get('orden_take_id'),
            row.get('fecha_cierre'), row.get('precio_cierre'),
            row.get('retorno_pct'), row.get('resultado'), row.get('notas'),
            row.get('venue'), row.get('timeframe'), row.get('capital_eur'),
            row.get('riesgo_pct'), row.get('precio_apertura_vela'),
            row.get('dias_en_trade'), row.get('stop'), row.get('take'), ahora
        ))
        insertadas += 1

conn.commit()
total = cur.execute('SELECT COUNT(*) FROM operaciones').fetchone()[0]
conn.close()
print(f"Sync completado — {insertadas} nuevas insertadas, {total} total en DB")
