# Trading-Agent

![XAUUSD AI Trading Research Workstation, Market Chart view](img/trading-agent-gui.jpg)

PySide6 desktop research station for XAUUSD (gold): backtesting, ML classifiers, and macro-gated signal research. Live trading is disabled by design. The system runs in a fail-closed research mode.

## What it does

- **Market data**: MT5 connector ingests and validates historical candles (512,000+ bars across 7 timeframes, M1 to D1) into a versioned SQLite store.
- **Feature engineering**: 35 price, technical, and market-structure features, built with zero look-ahead bias.
- **ML classifiers**: Logistic Regression, Random Forest, and Gradient Boosting, benchmarked against non-ML baselines.
- **Realistic backtester**: bar-by-bar simulation with spread, slippage, and commission costs, ATR-based stop loss and take profit, and 18-fold walk-forward validation.
- **Macro intelligence**: cross-market data (DXY, US yields, VIX, silver, Brent crude) aligned without look-ahead. A macro-gating wrapper filters out signals during adverse regimes, which cut model losses by more than half in walk-forward audits.
- **Research workstation GUI**: 12 pages (Market Chart, ML Lab, Backtester, Market Intel, Risk Engine, Paper Trading, and more) with interactive candlestick and equity-curve charts.

## Status

Research prototype, work in progress. 110 of 110 tests passing. Paper and live trading phases are locked on purpose. See [PROGRESS_REPORT.md](PROGRESS_REPORT.md) for the full phase-by-phase research report.

## Run it

Requirements: Python 3.13. A MetaTrader 5 terminal is needed for live data connection; the GUI and stored data work offline.

```bash
pip install -r xauusd-ai-trader/requirements.txt
python run_gui.py
```

On Windows you can also double-click `run_gui.bat`.

## Project structure

```
Trading-Agent/
├── run_gui.py / run_gui.bat    # workstation launcher
├── PROGRESS_REPORT.md          # phase-by-phase research report
└── xauusd-ai-trader/
    ├── app/                    # PySide6 GUI (12 pages)
    ├── data/                   # MT5 connector, validators, SQLite stores
    ├── features/               # feature engineering
    ├── models/                 # ML classifiers and macro-gated wrapper
    ├── backtester/             # execution simulator, walk-forward engine
    ├── main.py                 # pipeline entry points
    ├── train.py / backtest.py
    └── tests/                  # 110 tests
```
