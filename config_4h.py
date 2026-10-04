# Parámetros optimizados para timeframe 4h
# Walk-forward validado out-of-sample (lógica percentiles)

PARAMS_4H = {
    'BNB/EUR':  {'umbral': 5, 'stop': 0.02, 'take': 0.10, 'kelly': 44.6, 'horizonte_velas': 6},
    'AVAX/EUR': {'umbral': 5, 'stop': 0.02, 'take': 0.08, 'kelly': 20.0, 'horizonte_velas': 6},
    'ETH/EUR':  {'umbral': 5, 'stop': 0.01, 'take': 0.05, 'kelly': 71.8, 'horizonte_velas': 6},
    'XRP/EUR':  {'umbral': 5, 'stop': 0.03, 'take': 0.08, 'kelly': 83.9, 'horizonte_velas': 6},
}

# En observación — Sharpe test negativo o train débil:
# ADA/EUR: test 2.54 pero train 0.04 — sospechoso
# SOL/EUR: test 3.48 pero train 0.36 — sospechoso
# BTC/EUR: test 2.55, train 0.93 — pendiente de más datos
PARAMS_4H_OBS = {
    'ADA/EUR': {'umbral': 5, 'stop': 0.01, 'take': 0.03, 'horizonte_velas': 6},
    'SOL/EUR': {'umbral': 5, 'stop': 0.01, 'take': 0.03, 'horizonte_velas': 6},
    'BTC/EUR': {'umbral': 5, 'stop': 0.01, 'take': 0.08, 'horizonte_velas': 12},
    'XRP/EUR': {'umbral': 5, 'stop': 0.03, 'take': 0.08, 'horizonte_velas': 6},
}
