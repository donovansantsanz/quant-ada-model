# Quantitative Crypto Trading System

A fully autonomous quantitative trading system for cryptocurrency markets,
built in Python from scratch by an 18-year-old mathematics student.
Analyzes 5 assets on a daily timeframe and BNB on a 4H timeframe,
with automatic execution, Telegram alerts, and real capital deployed.

## Model Evolution

### V1 (baseline)
- 7 technical indicators: MM7/20/50, RSI, Bollinger Bands, MACD, Monte Carlo
- Combined score 1-10 with 3-of-4 consensus rule
- Results: Win rate 13.9% | Sharpe -4.69

### V2 (current — evidence-based)
- Statistical analysis identified only 4 predictors with p < 0.05
- Percentile-based scoring without lookahead bias
- Per-asset optimized parameters via grid search
- BTC momentum filter (mom3 < -5%) as macro regime filter
- Kelly/4 position sizing, capped at 10% per asset
- Walk-forward validated out-of-sample for all active assets
- Dual timeframe: daily (5 assets) + 4H (BNB only)
- Running 24/7 on Hetzner VPS with full automation

## Walk-Forward Validation Results (Daily System)

| Asset     | Sharpe Train | Sharpe Test | Kelly  | BTC Filter | Status      |
|-----------|-------------|-------------|--------|------------|-------------|
| ADA/USDT  | 2.92        | 11.57       | 16.9%  | Active     | ✅ Live     |
| SOL/USDT  | 7.61        | 6.35        | 23.1%  | Disabled   | ✅ Live     |
| ETH/USDT  | 3.14        | 0.83        | 18.3%  | Active     | ✅ Live     |
| BNB/USDT  | 7.29        | 7.14        | 28.4%  | Active     | ✅ Live     |
| BTC/USDT  | 4.39        | 4.49        | 15.1%  | Disabled   | ✅ Live     |
| AVAX/USDT | —           | —           | —      | Disabled   | 👁 Obs      |
| XRP/USDT  | —           | 3.35        | —      | Disabled   | 👁 Obs      |

## Walk-Forward Validation Results (4H System)

| Asset     | Sharpe Train | Sharpe Test | Status      |
|-----------|-------------|-------------|-------------|
| BNB/USDT  | 0.45        | 0.32        | ✅ Live     |
| ETH/USDT  | —           | Negative    | ❌ Rejected |
| ADA/USDT  | —           | Negative    | ❌ Rejected |
| SOL/USDT  | —           | Negative    | ❌ Rejected |

## Optimized Parameters (Daily System)

| Asset     | Threshold | Stop Loss | Take Profit | BTC Filter |
|-----------|-----------|-----------|-------------|------------|
| ADA/USDT  | 5/10      | 3%        | 8%          | Active     |
| SOL/USDT  | 6/10      | 3%        | 10%         | Disabled   |
| ETH/USDT  | 4/10      | 3%        | 10%         | Active     |
| BNB/USDT  | 7/10      | 2%        | 10%         | Active     |
| BTC/USDT  | 5/10      | 2%        | 8%          | Disabled   |

## Automation Pipeline

1. **monitor_v2.py** runs at 10:30 UTC — calculates scores, applies BTC filter, saves signals to JSON
2. **ejecutor.py** reads JSON — if COMPRAR signal and no open position, executes market buy, places stop-limit + limit orders automatically, logs to CSV
3. **evaluador_real.py** runs hourly — detects closed positions, cancels orphan orders, applies trailing stop in Binance
4. **monitor_4h.py** runs every 4H — same pipeline for 4H system
5. **monitor_salud.py** runs Sundays 10:00 UTC — rolling 90d Kelly vs full-sample Kelly per asset
6. **evaluador.py** runs Mondays 11:00 UTC — weekly Telegram summary
7. **watchdog.py** monitors system health — Telegram alert on failure

## Position Sizing

- Capital base: $1,000 USDC
- Kelly/4 with 10% cap per asset
- Available USDC balance used when below Kelly-calculated capital
- Stop-limit + limit orders placed automatically after every buy
- Trailing stop: 2% below current price when position moves favorably

## Scripts in Production (22)

| Script | Description |
|--------|-------------|
| config.py | Single source of parameters — daily system |
| monitor_v2.py | Daily monitor — scores, BTC filter, JSON output |
| monitor_4h.py | 4H monitor — scores, JSON output |
| ejecutor.py | Automatic execution — buy + stop-limit + limit |
| evaluador_real.py | Hourly evaluator — orphan cancel, trailing stop, P&L |
| evaluador.py | Weekly Telegram summary — Mondays 11:00 UTC |
| monitor_salud.py | Weekly health check — Sundays 10:00 UTC |
| paper_trading.py | Daily paper trading — signal logging |
| paper_trading_4h.py | 4H paper trading — signal logging |
| walk_forward.py | Out-of-sample validation — daily system |
| screener_activos.py | Asset screener with liquidity filter + multiple testing correction |
| checklist_expansion.py | Objective criteria for capital expansion |
| optimizador.py | Grid search calibration — daily system |
| optimizador_4h.py | Grid search calibration — 4H system |
| analisis_drawdown.py | Drawdown and streak analysis |
| stress_test.py | Historical stress test 2021–2026 |
| resumen_modelo.py | Printable technical sheet — daily system |
| resumen_modelo_4h.py | Printable technical sheet — 4H system |
| dashboard.py | Full system status in one command |
| mis_operaciones.py | Live P&L of open positions |
| historial.py | Clean view of daily paper trading CSV |
| watchdog.py | Automated health monitor — Telegram alert on failure |

## Infrastructure

| Component | Detail |
|-----------|--------|
| Server | Hetzner CX22 — Ubuntu 24.04 |
| IP | 116.203.91.120 |
| Exchange | Binance Spot (USDC pairs) |
| Data | ccxt library |
| Notifications | Telegram bot |
| Scheduling | cron (6 tasks) |
| Version control | GitHub |

## Capital Expansion Checklist

Before scaling capital, all 4 criteria must be met:
- [ ] ≥ 30 closed operations
- [ ] Win rate ≥ 30%
- [ ] Consistency with backtest ± 15%
- [ ] Positive accumulated return

## Author

18-year-old mathematics student at Universidad de La Laguna (Tenerife, Spain).
Building toward a quantitative finance career and PhD application (MIT, Princeton, NYU Courant).

X: [@donovan_quant](https://x.com/donovan_quant)
GitHub: [donovansantsanz](https://github.com/donovansantsanz)
