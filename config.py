# Activos operativos (Kelly positivo)
PARAMS = {
    'ADA/USDT':  {'umbral': 5, 'stop': 0.03, 'take': 0.08, 'kelly': 16.9, 'filtro_btc': True},
    'SOL/USDT':  {'umbral': 6, 'stop': 0.03, 'take': 0.10, 'kelly': 23.1, 'filtro_btc': False},
    'ETH/USDT':  {'umbral': 4, 'stop': 0.03, 'take': 0.10, 'kelly': 18.3, 'filtro_btc': True},
    'BNB/USDT':  {'umbral': 7, 'stop': 0.02, 'take': 0.10, 'kelly': 28.4, 'filtro_btc': True},

    'BTC/USDT':  {'umbral': 5, 'stop': 0.02, 'take': 0.08, 'kelly': 15.1, 'filtro_btc': False},
}

# Activos en observación
PARAMS_OBS = {
    'AVAX/USDT': {'umbral': 7, 'stop': 0.02, 'take': 0.10, 'filtro_btc': False},
}
