import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os

# Crear carpeta datos
datos_dir = os.path.expanduser('~/proyectos-quant/datos')
os.makedirs(datos_dir, exist_ok=True)

bitvavo = ccxt.bitvavo({'operatorId': 1001})
activos = ['ADA/EUR', 'SOL/EUR', 'ETH/EUR', 'BNB/EUR', 'BTC/EUR']

# 90 días atrás
hace_90d = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

for par in activos:
    print(f"Descargando {par}...")
    try:
        ohlcv = bitvavo.fetch_ohlcv(par, '1d', since=hace_90d, limit=300)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['asset'] = par.split('/')[0]
        
        filename = os.path.join(datos_dir, f"{par.replace('/', '_')}_90d.csv")
        df.to_csv(filename, index=False)
        print(f"✓ {par} — {len(df)} candles")
    except Exception as e:
        print(f"✗ {par}: {e}")

print("\nDatos descargados.")
