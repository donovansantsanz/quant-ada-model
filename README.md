# Quantitative Crypto Trading System

A fully autonomous quantitative trading system for cryptocurrency markets,
built in Python from scratch by an 18-year-old mathematics student.
Analyzes 5 assets on a daily timeframe and BNB on a 4H timeframe,
with automatic execution, Telegram alerts, and real capital deployed.

> **July 2026 — Exchange migration.** On July 1st 2026, Binance suspended spot
> services for EU users pending MiCA licensing. The system was migrated to
> **Bitvavo** (MiCA-licensed, EUR pairs) in a single day: exchange layer,
> order-type syntax, and pair notation were all adapted. The strategy logic
> (scoring, filters, sizing) is exchange-agnostic and unchanged. Live-validation
> operations from Binance are archived separately (`venue` column) so the
> Bitvavo validation window starts clean.

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

| Asset    | Sharpe Train | Sharpe Test | Kelly  | BTC Filter | Status      |
|----------|-------------|-------------|--------|------------|-------------|
| ADA/EUR  | 2.92        | 11.57       | 16.9%  | Active     | ✅ Live     |
| SOL/EUR  | 7.61        | 6.35        | 23.1%  | Disabled   | ✅ Live     |
| ETH/EUR  | 3.14        | 0.83        | 18.3%  | Active     | ✅ Live     |
| BNB/EUR  | 7.29        | 7.14        | 28.4%  | Active     | ✅ Live     |
| BTC/EUR  | 4.39        | 4.49        | 15.1%  | Disabled   | ✅ Live     |
| AVAX/EUR | —           | —           | —      | Disabled   | 👁 Obs      |
| XRP/EUR  | —           | 3.35        | —      | Disabled   | 👁 Obs      |

*Walk-forward validated on Binance/USDT historical data prior to the July 2026 MiCA migration. BTC's high train Sharpe collapsing out-of-sample is a documented example of overfitting; it is the weakest active asset and monitored accordingly.*

## Walk-Forward Validation Results (4H System)

| Asset    | Sharpe Train | Sharpe Test | Status      |
|----------|-------------|-------------|-------------|
| BNB/EUR  | 0.45        | 0.32        | ✅ Live     |
| ETH/EUR  | —           | Negative    | ❌ Rejected |
| ADA/EUR  | —           | Negative    | ❌ Rejected |
| SOL/EUR  | —           | Negative    | ❌ Rejected |

*Validated on Binance/USDT historical data prior to migration. BNB is the only 4H asset with a consistent positive out-of-sample test.*

## Optimized Parameters (Daily System)

| Asset    | Threshold | Stop Loss | Take Profit | BTC Filter |
|----------|-----------|-----------|-------------|------------|
| ADA/EUR  | 5/10      | 3%        | 8%          | Active     |
| SOL/EUR  | 6/10      | 3%        | 10%         | Disabled   |
| ETH/EUR  | 4/10      | 3%        | 10%         | Active     |
| BNB/EUR  | 7/10      | 2%        | 10%         | Active     |
| BTC/EUR  | 5/10      | 2%        | 8%          | Disabled   |

## Automation Pipeline

1. **monitor_v2.py** runs at 10:30 UTC — calculates scores, applies BTC filter, saves signals to JSON
2. **ejecutor.py** — on a COMPRAR signal with no open position, executes market buy and places protection orders automatically (stopLossLimit + takeProfitLimit, both trigger-based so neither locks balance until it fires), logs to CSV
3. **evaluador_real.py** runs hourly — matches orders by ID, detects closed positions, cancels orphan orders, applies trailing stop on Bitvavo
4. **monitor_4h.py** runs every 4H — same pipeline for the 4H system
5. **watchdog.py** runs hourly — log/disk/memory health, Telegram alert on failure

## Position Sizing

- Capital base: €1,000 (scaling up progressively)
- Kelly/4 with 10% cap per asset
- Real available EUR balance used when below Kelly-calculated capital
- stopLossLimit + takeProfitLimit orders placed automatically after every buy
- Trailing stop: 2% below current price when position moves favorably

## Scripts (27)

| Script | Description |
|--------|-------------|
| conexion.py | Centralized Bitvavo connection (credentials + mandatory operatorId) |
| config.py | Single source of parameters — daily system |
| config_4h.py | Parameters — 4H system |
| monitor_v2.py | Daily monitor — scores, BTC filter, JSON output |
| monitor_4h.py | 4H monitor — scores, JSON output, position validation |
| detector_regimen_auto.py | Daily regime detector — downloads fresh data, classifies FAVORABLE/MIXTO/ADVERSO, Telegram |
| monitor_edge_return.py | Alerts when an asset returns to FAVORABLE regime |
| validador_posiciones.py | Checks real Bitvavo balance to prevent duplicate positions |
| descargar_datos.py | Downloads 90d OHLCV from Bitvavo for regime analysis |
| graficos.py | Equity curve + return distribution PNGs |
| ejecutor.py | Automatic execution — buy + stopLossLimit + takeProfitLimit |
| evaluador_real.py | Hourly evaluator — ID matching, orphan cancel, trailing stop, P&L |
| monitor_salud.py | Weekly health check — rolling 90d Kelly vs full-sample |
| paper_trading.py | Daily paper trading — signal logging (archived, superseded by live) |
| paper_trading_4h.py | 4H paper trading — signal logging (archived, superseded by live) |
| walk_forward.py | Out-of-sample validation — daily system |
| screener_activos.py | Asset screener with liquidity filter + multiple testing correction |
| checklist_expansion.py | Objective criteria for capital expansion (Bitvavo window only) |
| optimizador.py | Grid search calibration — daily system |
| optimizador_4h.py | Grid search calibration — 4H system |
| analisis_drawdown.py | Drawdown and streak analysis |
| stress_test.py | Historical stress test 2021–2026 |
| resumen_modelo.py | Printable technical sheet — daily system |
| dashboard.py | Full system status in one command |
| mis_operaciones.py | Live P&L of open positions |
| historial.py | Clean view of daily paper trading CSV |
| watchdog.py | Automated health monitor — Telegram alert on failure |

## Infrastructure

| Component | Detail |
|-----------|--------|
| Server | Hetzner CX22 — Ubuntu 24.04 |
| Exchange | Bitvavo Spot (EUR pairs, MiCA-licensed) |
| Data & orders | ccxt library |
| Notifications | Telegram bot |
| Scheduling | cron (5 active tasks) |
| Version control | GitHub |

## Capital Expansion Checklist

Before scaling capital, all 4 criteria must be met (Bitvavo validation window):
- [ ] ≥ 30 closed operations
- [ ] Win rate ≥ 30%
- [ ] Consistency with backtest ± 15%
- [ ] Positive accumulated return

## Author

18-year-old mathematics student at Universidad de La Laguna (Tenerife, Spain).
Building toward a quantitative finance career and PhD application (MIT, Princeton, NYU Courant).

X: [@donovan_quant](https://x.com/donovan_quant)
GitHub: [donovansantsanz](https://github.com/donovansantsanz)
