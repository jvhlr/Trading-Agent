"""
Evaluation Module for XAUUSD Trading System.

Computes statistical classification metrics and realistic financial metrics.
Per the directive:
1. Compare ML performance against non-ML baselines.
2. Account for transaction costs (spread + slippage).
3. Evaluate expectancy and drawdown.
"""

from dataclasses import dataclass
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, log_loss, brier_score_loss


@dataclass
class ClassificationMetrics:
    """Dataclass holding statistical ML classification performance."""

    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    log_loss: float
    brier_score: float

    def __str__(self) -> str:
        return (
            f"Acc: {self.accuracy*100:.2f}% | F1: {self.f1_macro:.4f} | "
            f"Prec: {self.precision_macro:.4f} | Rec: {self.recall_macro:.4f} | "
            f"LogLoss: {self.log_loss:.4f} | Brier: {self.brier_score:.4f}"
        )


@dataclass
class FinancialMetrics:
    """Dataclass holding simulated financial metrics under transaction costs."""

    n_trades: int
    win_rate: float
    expectancy_pct: float  # Expected net return per active trade (%)
    gross_return_pct: float
    net_return_pct: float
    total_spread_cost_pct: float
    profit_factor: float
    max_drawdown_pct: float

    def __str__(self) -> str:
        return (
            f"Trades: {self.n_trades} | WinRate: {self.win_rate*100:.1f}% | "
            f"Net Return: {self.net_return_pct*100:.2f}% | Exp/Trade: {self.expectancy_pct*100:.3f}% | "
            f"PF: {self.profit_factor:.2f} | MaxDD: {self.max_drawdown_pct*100:.2f}%"
        )


def evaluate_classification(
    y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray
) -> ClassificationMetrics:
    """
    Computes statistical classification metrics.

    Args:
        y_true: True class labels (-1, 0, 1).
        y_pred: Predicted class labels (-1, 0, 1).
        y_prob: Predicted probability distribution array of shape (N, 3).

    Returns:
        ClassificationMetrics instance.
    """
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )

    # Compute multiclass log loss safely
    try:
        ll = log_loss(y_true, y_prob, labels=[-1, 0, 1])
    except Exception:
        ll = 999.0

    # Brier score (multi-class mean squared error of probability predictions)
    try:
        # Convert y_true to one-hot encoding
        classes = np.array([-1, 0, 1])
        y_true_oh = np.zeros((len(y_true), 3))
        for idx, cls in enumerate(classes):
            y_true_oh[:, idx] = (y_true == cls).astype(float)
        brier = np.mean(np.sum((y_prob - y_true_oh) ** 2, axis=1))
    except Exception:
        brier = 1.0

    return ClassificationMetrics(
        accuracy=float(acc),
        precision_macro=float(prec),
        recall_macro=float(rec),
        f1_macro=float(f1),
        log_loss=float(ll),
        brier_score=float(brier),
    )


def evaluate_financial(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    returns: np.ndarray,
    spread_pct: float = 0.00015,  # ~$0.30 per $2000 gold bar (~1.5 bps)
) -> FinancialMetrics:
    """
    Simulates simple single-bar holding performance with transaction costs.

    Args:
        y_true: Ground truth direction.
        y_pred: Predicted direction (-1: SELL, 0: WAIT, +1: BUY).
        returns: Actual bar returns (price[t+1] - price[t]) / price[t].
        spread_pct: One-way transaction cost per trade (spread + slippage).

    Returns:
        FinancialMetrics instance.
    """
    # Active trades are non-zero predictions
    active_mask = y_pred != 0
    n_trades = int(np.sum(active_mask))

    if n_trades == 0:
        return FinancialMetrics(
            n_trades=0,
            win_rate=0.0,
            expectancy_pct=0.0,
            gross_return_pct=0.0,
            net_return_pct=0.0,
            total_spread_cost_pct=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
        )

    # Calculate trade returns
    pred_direction = y_pred[active_mask]
    actual_returns = returns[active_mask]

    gross_trade_returns = pred_direction * actual_returns
    net_trade_returns = gross_trade_returns - spread_pct

    # Win rate
    wins = np.sum(net_trade_returns > 0)
    win_rate = wins / n_trades

    # Gross and Net returns
    gross_return_total = float(np.sum(gross_trade_returns))
    net_return_total = float(np.sum(net_trade_returns))
    total_spread_cost = n_trades * spread_pct
    expectancy = net_return_total / n_trades

    # Profit factor
    gains = np.sum(net_trade_returns[net_trade_returns > 0])
    losses = np.abs(np.sum(net_trade_returns[net_trade_returns < 0]))
    profit_factor = float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0)

    # Max Drawdown of cumulative net return curve
    cum_returns = np.cumsum(net_trade_returns)
    running_max = np.maximum.accumulate(cum_returns)
    drawdowns = running_max - cum_returns
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    return FinancialMetrics(
        n_trades=n_trades,
        win_rate=float(win_rate),
        expectancy_pct=float(expectancy),
        gross_return_pct=gross_return_total,
        net_return_pct=net_return_total,
        total_spread_cost_pct=total_spread_cost,
        profit_factor=profit_factor,
        max_drawdown_pct=max_dd,
    )
