# Activos operativos (Kelly positivo)
PARAMS = {
    'ADA/EUR':  {'umbral': 5, 'stop': 0.03, 'take': 0.08, 'kelly': 16.9, 'filtro_btc': True},
    'SOL/EUR':  {'umbral': 6, 'stop': 0.03, 'take': 0.10, 'kelly': 23.1, 'filtro_btc': False},
    'ETH/EUR':  {'umbral': 4, 'stop': 0.03, 'take': 0.10, 'kelly': 18.3, 'filtro_btc': True},
    'BNB/EUR':  {'umbral': 7, 'stop': 0.02, 'take': 0.10, 'kelly': 28.4, 'filtro_btc': True},

    'BTC/EUR':  {'umbral': 5, 'stop': 0.02, 'take': 0.08, 'kelly': 15.1, 'filtro_btc': False},
}

# Activos en observación
PARAMS_OBS = {
    'AVAX/EUR': {'umbral': 7, 'stop': 0.02, 'take': 0.10, 'filtro_btc': False},
    'XRP/EUR': {'umbral': 6, 'stop': 0.03, 'take': 0.08, 'filtro_btc': False},
}
