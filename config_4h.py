# Parámetros optimizados para timeframe 4h
# Walk-forward validado out-of-sample (1000 velas, lógica percentiles)
# BNB: único activo con test positivo consistente

PARAMS_4H = {
    'BNB/EUR': {'umbral': 6, 'stop': 0.02, 'take': 0.10, 'kelly': 44.6, 'horizonte_velas': 6},
}

# En observación — Sharpe test negativo en walk-forward 4h:
# ETH/EUR: test -2.50 | ADA/EUR: test -2.70 | SOL/EUR: test -2.50
# BTC/EUR: excluido etapa anterior (Sharpe test -0.18)
PARAMS_4H_OBS = {
    'ETH/EUR': {'umbral': 6, 'stop': 0.01, 'take': 0.05, 'horizonte_velas': 6},
    'ADA/EUR': {'umbral': 6, 'stop': 0.01, 'take': 0.03, 'horizonte_velas': 6},
    'SOL/EUR': {'umbral': 6, 'stop': 0.01, 'take': 0.03, 'horizonte_velas': 6},
    'BTC/EUR': {'umbral': 6, 'stop': 0.01, 'take': 0.08, 'horizonte_velas': 12},
}
