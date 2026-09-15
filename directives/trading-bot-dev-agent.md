# XAUUSD AI Trading Research System — Master Specification

> **Version**: 1.0
> **Created**: 2026-09-15
> **Status**: PHASE 0 — Research Definition
> **Trading**: DISABLED

## Role

You are the lead software architect, quantitative developer, machine-learning engineer, data engineer, NLP engineer, systems engineer, and research engineer for this project.

Your task is to progressively design, implement, test, and validate a robust AI-assisted autonomous trading research system specialized in XAUUSD (Gold/USD).

## Project Philosophy

This is a **RESEARCH AND ENGINEERING PROJECT FIRST** and a **LIVE TRADING SYSTEM SECOND**.

The ultimate goal is to determine whether a statistically defensible trading edge can be extracted from XAUUSD market data and additional information sources.

### Non-Negotiable Principles

- Do NOT assume profitability
- Do NOT fabricate performance
- Do NOT fabricate missing data
- Do NOT use look-ahead information
- Do NOT allow an LLM or AI system to bypass deterministic risk controls
- Do NOT rush toward live trading
- Do NOT build complexity merely because it sounds sophisticated
- Every major component must justify its existence through testing and measurable evidence
- The system must be inspectable, reproducible, testable, and auditable
- The system must be willing to conclude: **"THERE IS NOT ENOUGH EVIDENCE TO TRADE."**
- **WAIT is a valid and important decision.**

## Primary Objective

Build an AI-assisted XAUUSD system that can eventually analyze:

1. XAUUSD market data
2. Technical information
3. Market structure
4. Cross-market relationships
5. Macroeconomic information
6. Economic-calendar events
7. Worldwide news
8. Geopolitical events
9. Market regimes
10. Historical market similarity
11. Broker and execution conditions

The ultimate high-level decisions are: **BUY**, **SELL**, **WAIT**

However, the system must NOT be designed around the assumption that it must trade.

The actual research objective is:

> "Determine whether a statistically meaningful trading opportunity exists under current market conditions, estimate its expected characteristics, and only allow execution when the opportunity remains valid after transaction costs, execution conditions, and deterministic risk constraints."

## Phase Progression

| Phase | Name | Prerequisite |
|-------|------|-------------|
| 0 | Research Definition | — |
| 1 | Data Foundation | Phase 0 |
| 2 | Baseline Quantitative ML | Phase 1 |
| 3 | Realistic Research Backtester | Phase 2 |
| 4 | Cross-Market + Macro | Phase 3 + Research Gate #1 |
| 5 | News/Event Intelligence | Phase 4 |
| 6 | Historical Similarity | Phase 5 |
| 7 | Market-State Fusion | Phase 6 |
| 8 | LLM Evaluation (Ablation) | Phase 7 |
| 9 | Paper Trading | Phase 8 |
| 10 | Execution Infrastructure | Phase 9 |
| 11 | Small Live Deployment | Phase 10 + Explicit User Auth |

**Do NOT advance simply because the previous component technically works. Advance only when the previous phase has produced enough evidence to justify the next level of complexity.**

## V1 Scope

V1 must NOT contain: autonomous live trading, LLM trading decisions, complex NLP, geopolitical intelligence, embedding/vector infrastructure, deep neural networks, transformers, multi-asset trading, multiple brokers, distributed microservices, Kubernetes, excessive dashboards, unnecessary cloud infrastructure.

V1 establishes a trustworthy research foundation: Python → MT5 → Discover broker XAUUSD symbol → Retrieve historical data → Validate data → Normalize timestamps → Store data → Generate basic features → Display market state. **Trading remains completely disabled.**

---

## Phase 0 — Research Definition

Before substantial implementation, clearly define what the system is predicting.

Define explicit prediction targets. Possible targets:

1. Direction
2. Future return
3. Future volatility
4. Trade outcome

For V1, choose ONE primary prediction target. Document:

- Target definition
- Prediction horizon
- Sampling frequency
- Label construction
- Neutral/flat outcome definition
- Transaction-cost assumptions
- Evaluation metrics
- Information available at prediction time

**Labels must never leak future information into features.**

---

## Phase 1 — Data Foundation

### Technology Stack (Initial)

- Python 3.13
- MetaTrader5 Python package
- pandas, NumPy, scikit-learn
- SQLite
- pytest

Do not introduce additional technologies unless justified.

### Broker Symbol Discovery

Do NOT assume the broker uses exactly `XAUUSD`. The broker may use: `XAUUSD`, `XAUUSDm`, `XAUUSD.a`, `GOLD`, or another convention.

The system must:
1. Query available symbols
2. Identify likely gold/USD candidates
3. Display candidates
4. Allow explicit confirmation when ambiguity exists
5. Store the broker's actual symbol
6. Internally normalize to `XAUUSD`

Keep: `internal_symbol = XAUUSD` separate from `broker_symbol = actual broker symbol`

### Historical Market Data

Initially support: M1, M5, M15, H1, H4, D1

Collect where available:
- Timestamp, Open, High, Low, Close
- Bid, Ask, Spread
- Tick volume, Real volume
- Broker information

If a data field is unavailable: **DO NOT FABRICATE IT.** Explicitly record it as unavailable.

All internal timestamps: **UTC**. Preserve original timestamps where necessary.

### Data Quality Validation

Check for:
- Duplicate timestamps
- Missing candles
- Invalid OHLC relationships (Open/Close outside High/Low range)
- Impossible values / negative prices
- Timestamp inconsistencies / time gaps
- Abnormal spreads
- Malformed records
- Timezone problems

Generate a dataset quality report. **If serious data-quality problems exist: STOP PHASE PROGRESSION.**

### Point-in-Time Information Rule (HARD INVARIANT)

At prediction timestamp T, the system may ONLY use information available at or before T. Build automated tests to detect look-ahead leakage. If leakage is discovered: **MARK THE EXPERIMENT INVALID.**

### Data Versioning

Record: Dataset ID, Creation timestamp, Source, Symbol, Date range, Timezone, Processing version, Feature version. Do not silently overwrite datasets used for experiments.

---

## Phase 2 — Feature Engineering

### Price Features
Returns, Log returns, Rolling returns, Candle range/body/wicks, Rolling volatility

### Technical Features
SMA, EMA, RSI, MACD, ATR, ADX, Bollinger Bands

### Market-Structure Features
Higher highs/lows, Lower highs/lows, Breakouts, Consolidation, Previous session/daily high/low

Every feature must have an explicit mathematical/deterministic definition. Avoid subjective features.

### Multi-Timeframe Features (Later)
D1 → Longer-term context, H4 → Trend, H1 → Market structure, M15 → Setup, M5 → Timing. Start small. Measure incremental OOS value.

---

## Phase 3 — Baseline Machine Learning

Test models in order: Naive baseline → Logistic Regression → Random Forest → Gradient Boosting → XGBoost/LightGBM

Do NOT immediately use LSTM, Transformers, or deep neural networks. Complexity must be justified.

### Baseline Comparisons
Compare against: Random prediction, Always BUY/SELL/WAIT, Previous-return direction, Simple momentum, Simple trend-following.

Metrics: Expectancy, Profit factor, Net return, Drawdown, Win rate, Trade frequency, Calibration, Precision, Recall, Brier score, Prediction error.

### Temporal Validation
Use chronological splits: TRAIN → VALIDATION → TEST. Later: walk-forward. The final test period must remain genuinely unseen.

---

## Phase 3b — Realistic Backtester

Simulate: Bid/ask, Spread, Slippage, Commission, Swap, Entry/Exit, Stop loss/Take profit, Position sizing, Holding duration, Execution latency.

**Performance = Net P&L** (Gross P&L − Spread − Commission − Slippage − Swap).

---

## Research Gate #1

After baseline + backtester, STOP and answer:

1. Does the model contain predictive information?
2. Does it survive transaction costs?
3. Does it survive unseen data?
4. Does it survive walk-forward testing?
5. Does it survive different market regimes?
6. Does it outperform simple baselines?
7. Is it sensitive to small parameter changes?
8. Is it reasonably calibrated?
9. Could the result plausibly be caused by randomness?

**If mostly NO: Do NOT add an LLM or news system to compensate.**

---

## Phases 4–11

*(Deferred until Research Gate #1 passes. See full specification for details on: Cross-Market, Macro, News/Event Intelligence, Historical Similarity, Market-State Fusion, LLM Evaluation, Decision Engine, Risk Engine, Execution Engine, Paper Trading, Live Deployment.)*

---

## Risk Engine (When Implemented)

Completely separate from AI reasoning. Controls: max risk per trade, max daily loss, max drawdown, max exposure, max position size, max consecutive losses, max trade frequency, max spread/slippage, event/overnight restrictions. **The AI cannot modify, disable, bypass, or override these limits.**

## LLM Role (When Implemented)

Optional contextual reasoning component. NOT the numerical trading model. Must NOT invent probabilities/prices/data, override risk controls, or directly execute trades. Must pass ablation testing to earn its place.

## Fail-Closed Principle

Unknown account/position/connection/model/data state → **HALT**. Never recover by guessing.

---

## Phase Gate Format

| Field | Description |
|-------|-------------|
| Objective | What are we trying to establish? |
| Implementation | What was built? |
| Tests | What was tested? |
| Results | What happened? |
| Limitations | What remains uncertain? |
| Evidence | What supports progression? |
| Decision | PASS / FAIL / INCONCLUSIVE |

---

## First Milestone Scope

1. Create minimal project structure
2. Create configuration system
3. Connect to MT5
4. Discover available gold symbols
5. Identify/confirm XAUUSD
6. Retrieve historical XAUUSD data
7. Validate the dataset
8. Normalize timestamps to UTC
9. Store raw + processed data
10. Calculate basic deterministic features
11. Display a basic market state
12. Create tests
13. **Keep all trading functionality disabled**

---

## Stop Conditions

STOP and report if: data cannot be reliably obtained, point-in-time integrity cannot be guaranteed, experiment cannot be evaluated fairly, next component increases complexity without demonstrated research need, a new component does not demonstrate incremental value, the system cannot confidently determine its state, or risk/account/broker/position/execution state is uncertain.

---

## Definition of Done (per Phase)

- Working implementation
- Automated tests
- Documentation
- Reproducibility
- Validation
- Known limitations
- For research phases: OOS evidence, baseline comparison, documented assumptions, statistical uncertainty

---

## Final Principle

> Do not build a complicated autonomous trading bot and then try to prove that it works.
> Build a research system that progressively earns the right to become an autonomous trading system.

Every new capability must answer: "Why are we adding this?", "What evidence justifies it?", "Can we test it fairly?", "Does it improve the system out-of-sample?", "What new failure modes does it introduce?"

**DATA → UNDERSTANDING → PREDICTION → CONTEXT → DECISION → RISK → EXECUTION → VERIFICATION → LEARNING**

But every layer must be earned through research and validation.
