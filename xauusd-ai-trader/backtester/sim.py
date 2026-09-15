"""
Realistic Research Backtester Simulator for XAUUSD.

Enforces strict zero look-ahead execution invariants:
1. Signal generated at candle T.
2. Trade entry strictly executes at candle T+1 Open price + transaction costs.
3. Intra-candle Stop-Loss and Take-Profit evaluation against High/Low price boundaries.
4. Position sizing based on ATR risk budgeting.
"""

from typing import List, Optional
import pandas as pd
import numpy as np
from .types import Trade, BacktestConfig, BacktestResult, ExitReason


def run_backtest(
    df: pd.DataFrame,
    predictions: np.ndarray,
    config: Optional[BacktestConfig] = None,
) -> BacktestResult:
    """
    Runs realistic single-pass trade execution simulation.

    Args:
        df: DataFrame containing open, high, low, close, atr_14, timestamp.
        predictions: Array of predicted signals (-1: SELL, 0: WAIT, +1: BUY) aligned to df.
        config: BacktestConfig instance (default parameters if None).

    Returns:
        BacktestResult object containing equity curve, trade log, and metrics.
    """
    if config is None:
        config = BacktestConfig()

    n_bars = len(df)
    if len(predictions) != n_bars:
        raise ValueError(
            f"Predictions length ({len(predictions)}) does not match DataFrame length ({n_bars})"
        )

    # Extract required price series
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    timestamps = (
        df["timestamp"] if "timestamp" in df.columns else pd.Series(df.index)
    )

    # Calculate or retrieve ATR for dynamic SL/TP
    if "atr_14" in df.columns:
        atrs = df["atr_14"].values
    else:
        # Simple high-low range fallback if ATR not pre-computed
        atrs = (df["high"] - df["low"]).rolling(14, min_periods=1).mean().values

    capital = config.initial_capital
    equity_curve = np.zeros(n_bars)
    equity_curve[0] = capital

    trades: List[Trade] = []
    current_trade: Optional[Trade] = None
    trade_counter = 0

    half_spread = config.spread_dollars / 2.0
    slippage = config.slippage_dollars

    for i in range(n_bars - 1):
        # 1. Update existing open trade if any
        if current_trade is not None:
            # Check exit conditions on current bar i
            side = current_trade.side
            sl = current_trade.sl_price
            tp = current_trade.tp_price

            exit_price = None
            exit_reason = None

            # Check intra-bar SL / TP boundaries
            if side == 1:  # BUY Position
                if sl is not None and lows[i] <= sl:
                    # Gapped below SL -> exit at open or SL price, minus slippage
                    exit_price = min(opens[i], sl) - slippage
                    exit_reason = ExitReason.STOP_LOSS.value
                elif tp is not None and highs[i] >= tp:
                    # Gapped above TP -> exit at open or TP price
                    exit_price = max(opens[i], tp)
                    exit_reason = ExitReason.TAKE_PROFIT.value
            elif side == -1:  # SELL Position
                if sl is not None and highs[i] >= sl:
                    # Gapped above SL -> exit at open or SL price, plus slippage
                    exit_price = max(opens[i], sl) + slippage
                    exit_reason = ExitReason.STOP_LOSS.value
                elif tp is not None and lows[i] <= tp:
                    # Gapped below TP -> exit at open or TP price
                    exit_price = min(opens[i], tp)
                    exit_reason = ExitReason.TAKE_PROFIT.value

            # Check max holding duration
            if exit_reason is None:
                holding_bars = i - current_trade.entry_index
                if holding_bars >= config.max_holding_bars:
                    if side == 1:
                        exit_price = opens[i] - half_spread - slippage
                    else:
                        exit_price = opens[i] + half_spread + slippage
                    exit_reason = ExitReason.HOLDING_EXPIRED.value

            # Check signal reversal
            if exit_reason is None and predictions[i] != 0 and predictions[i] != side:
                if side == 1:
                    exit_price = opens[i] - half_spread - slippage
                else:
                    exit_price = opens[i] + half_spread + slippage
                exit_reason = ExitReason.SIGNAL_REVERSAL.value

            # Execute trade closure if exit triggered
            if exit_reason is not None and exit_price is not None:
                current_trade.exit_index = i
                current_trade.exit_time = timestamps.iloc[i]
                current_trade.exit_price = exit_price
                current_trade.exit_reason = exit_reason

                # Calculate PnL
                if side == 1:
                    gross_pnl = (exit_price - current_trade.entry_price) * current_trade.units
                else:
                    gross_pnl = (current_trade.entry_price - exit_price) * current_trade.units

                comm = config.commission_per_unit * current_trade.units
                net_pnl = gross_pnl - comm

                current_trade.gross_pnl = gross_pnl
                current_trade.net_pnl = net_pnl
                current_trade.return_pct = net_pnl / (current_trade.entry_price * current_trade.units)

                capital += net_pnl
                trades.append(current_trade)
                current_trade = None

        # 2. Process new entry signal at bar i -> Executes at bar i+1 Open
        if current_trade is None and i < n_bars - 1:
            sig = predictions[i]
            if sig != 0:
                next_bar_idx = i + 1
                next_open = opens[next_bar_idx]
                next_time = timestamps.iloc[next_bar_idx]
                atr_val = atrs[i] if not np.isnan(atrs[i]) and atrs[i] > 0 else 2.0

                if sig == 1:  # BUY Entry
                    entry_price = next_open + half_spread + slippage
                    sl_price = entry_price - (atr_val * config.sl_atr_mult) if config.use_atr_sl_tp else None
                    tp_price = entry_price + (atr_val * config.tp_atr_mult) if config.use_atr_sl_tp else None
                else:  # SELL Entry
                    entry_price = next_open - half_spread - slippage
                    sl_price = entry_price + (atr_val * config.sl_atr_mult) if config.use_atr_sl_tp else None
                    tp_price = entry_price - (atr_val * config.tp_atr_mult) if config.use_atr_sl_tp else None

                # Calculate position sizing (risk budgeting)
                if config.fixed_units is not None:
                    units = config.fixed_units
                else:
                    risk_dollars = capital * config.risk_pct_per_trade
                    sl_dist = abs(entry_price - sl_price) if sl_price is not None else (entry_price * 0.01)
                    units = risk_dollars / sl_dist if sl_dist > 0 else 1.0

                trade_counter += 1
                current_trade = Trade(
                    trade_id=trade_counter,
                    side=int(sig),
                    entry_index=next_bar_idx,
                    entry_time=next_time,
                    entry_price=entry_price,
                    units=units,
                    sl_price=sl_price,
                    tp_price=tp_price,
                )

        # Record equity curve
        unrealized_pnl = 0.0
        if current_trade is not None:
            # Unrealized mark-to-market at bar i close
            if current_trade.side == 1:
                unrealized_pnl = (closes[i] - current_trade.entry_price) * current_trade.units
            else:
                unrealized_pnl = (current_trade.entry_price - closes[i]) * current_trade.units

        equity_curve[i] = capital + unrealized_pnl

    # Close any open trade at end of dataset
    if current_trade is not None:
        last_idx = n_bars - 1
        exit_price = closes[last_idx]
        current_trade.exit_index = last_idx
        current_trade.exit_time = timestamps.iloc[last_idx]
        current_trade.exit_price = exit_price
        current_trade.exit_reason = ExitReason.END_OF_DATA.value

        if current_trade.side == 1:
            gross_pnl = (exit_price - current_trade.entry_price) * current_trade.units
        else:
            gross_pnl = (current_trade.entry_price - exit_price) * current_trade.units

        net_pnl = gross_pnl - (config.commission_per_unit * current_trade.units)
        current_trade.gross_pnl = gross_pnl
        current_trade.net_pnl = net_pnl
        current_trade.return_pct = net_pnl / (current_trade.entry_price * current_trade.units)

        capital += net_pnl
        trades.append(current_trade)

    equity_curve[-1] = capital
    equity_series = pd.Series(equity_curve, index=timestamps)

    # 3. Compute Summary Statistics
    n_trades = len(trades)
    if n_trades > 0:
        net_pnls = np.array([t.net_pnl for t in trades])
        wins = net_pnls[net_pnls > 0]
        losses = net_pnls[net_pnls < 0]

        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = n_wins / n_trades

        total_gains = np.sum(wins)
        total_losses = abs(np.sum(losses))
        profit_factor = float(total_gains / total_losses) if total_losses > 0 else (999.0 if total_gains > 0 else 0.0)
        expectancy = float(np.mean(net_pnls))
    else:
        n_wins = 0
        n_losses = 0
        win_rate = 0.0
        profit_factor = 0.0
        expectancy = 0.0

    total_net_pnl = capital - config.initial_capital
    net_return_pct = total_net_pnl / config.initial_capital

    # Calculate Max Drawdown
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (running_max - equity_curve) / running_max
    max_dd_pct = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
    max_dd_dollars = float(np.max(running_max - equity_curve)) if len(running_max) > 0 else 0.0

    # Calculate Sharpe & Sortino Ratios
    bar_returns = pd.Series(equity_curve).pct_change().dropna().values
    if len(bar_returns) > 1 and np.std(bar_returns) > 1e-8:
        mean_ret = np.mean(bar_returns)
        std_ret = np.std(bar_returns)
        sharpe = float((mean_ret / std_ret) * np.sqrt(252 * 24))  # Annualized H1

        downside_returns = bar_returns[bar_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 1 else 1e-8
        sortino = float((mean_ret / downside_std) * np.sqrt(252 * 24)) if downside_std > 0 else 0.0
    else:
        sharpe = 0.0
        sortino = 0.0

    return BacktestResult(
        initial_capital=config.initial_capital,
        final_equity=capital,
        net_return_pct=net_return_pct,
        total_net_pnl=total_net_pnl,
        n_trades=n_trades,
        n_wins=n_wins,
        n_losses=n_losses,
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy_dollars=expectancy,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_dollars=max_dd_dollars,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        trades=trades,
        equity_curve=equity_series,
    )
