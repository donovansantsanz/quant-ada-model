# Parámetros optimizados para timeframe 4h
# Walk-forward validado out-of-sample (1000 velas, lógica percentiles)
# BNB: único activo con test positivo consistente

PARAMS_4H = {
    'BNB/USDT': {'umbral': 6, 'stop': 0.02, 'take': 0.10, 'kelly': 44.6, 'horizonte_velas': 6},
}

# En observación — Sharpe test negativo en walk-forward 4h:
# ETH/USDT: test -2.50 | ADA/USDT: test -2.70 | SOL/USDT: test -2.50
# BTC/USDT: excluido etapa anterior (Sharpe test -0.18)
PARAMS_4H_OBS = {
    'ETH/USDT': {'umbral': 6, 'stop': 0.01, 'take': 0.05, 'horizonte_velas': 6},
    'ADA/USDT': {'umbral': 6, 'stop': 0.01, 'take': 0.03, 'horizonte_velas': 6},
    'SOL/USDT': {'umbral': 6, 'stop': 0.01, 'take': 0.03, 'horizonte_velas': 6},
    'BTC/USDT': {'umbral': 6, 'stop': 0.01, 'take': 0.08, 'horizonte_velas': 12},
}
