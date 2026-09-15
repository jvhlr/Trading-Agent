"""
Baseline Models Module for XAUUSD Trading System.

Provides non-machine-learning reference benchmarks:
1. Random Baseline (Uniform or Class-Weighted)
2. Majority Class / Always WAIT Baseline (Always 0)
3. Previous Return Momentum Baseline (Continuation)
4. SMA Crossover Baseline (Fast SMA > Slow SMA)

Every baseline implements fit(X, y), predict(X), predict_proba(X).
"""

from abc import ABC, abstractmethod
import numpy as np


class BaseModel(ABC):
    """Abstract Base Class for all Models and Baselines."""

    def __init__(self, name: str):
        self.name = name
        self.classes_ = np.array([-1, 0, 1])

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseModel":
        """Fit model to training data."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict discrete class labels (-1, 0, 1)."""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities for [-1, 0, 1]."""
        pass


class RandomBaseline(BaseModel):
    """Random Prediction Baseline (Uniform or Class-Weighted)."""

    def __init__(self, weighted: bool = True, seed: int = 42):
        super().__init__(name=f"Random ({'Weighted' if weighted else 'Uniform'})")
        self.weighted = weighted
        self.seed = seed
        self.class_probs_ = np.array([1 / 3, 1 / 3, 1 / 3])

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomBaseline":
        if self.weighted and len(y) > 0:
            classes, counts = np.unique(y, return_counts=True)
            prob_dict = {c: cnt / len(y) for c, cnt in zip(classes, counts)}
            self.class_probs_ = np.array(
                [prob_dict.get(-1, 0.0), prob_dict.get(0, 0.0), prob_dict.get(1, 0.0)]
            )
            total = self.class_probs_.sum()
            if total > 0:
                self.class_probs_ /= total
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        return rng.choice(self.classes_, size=len(X), p=self.class_probs_)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.tile(self.class_probs_, (len(X), 1))


class MajorityWaitBaseline(BaseModel):
    """Always Predict WAIT / FLAT (Class 0) Baseline."""

    def __init__(self):
        super().__init__(name="Majority (Always WAIT)")

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MajorityWaitBaseline":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.zeros(len(X), dtype=int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        # 100% probability assigned to class 0
        probs = np.zeros((len(X), 3))
        probs[:, 1] = 1.0  # Index 1 corresponds to class 0
        return probs


class PreviousReturnMomentumBaseline(BaseModel):
    """
    Previous Return Momentum Baseline.

    Predicts continuation of previous candle direction:
      If prev_return > 0 -> +1 (UP)
      If prev_return < 0 -> -1 (DOWN)
      If prev_return == 0 -> 0 (WAIT)
    """

    def __init__(self, return_feature_idx: int = 0):
        super().__init__(name="Momentum (Prev Return)")
        self.return_feature_idx = return_feature_idx

    def fit(self, X: np.ndarray, y: np.ndarray) -> "PreviousReturnMomentumBaseline":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if X.shape[1] <= self.return_feature_idx:
            return np.zeros(len(X), dtype=int)
        prev_returns = X[:, self.return_feature_idx]
        preds = np.zeros(len(X), dtype=int)
        preds[prev_returns > 0] = 1
        preds[prev_returns < 0] = -1
        return preds

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        preds = self.predict(X)
        probs = np.zeros((len(X), 3))
        for i, p in enumerate(preds):
            if p == -1:
                probs[i, 0] = 0.8
                probs[i, 1] = 0.1
                probs[i, 2] = 0.1
            elif p == 0:
                probs[i, 0] = 0.1
                probs[i, 1] = 0.8
                probs[i, 2] = 0.1
            else:
                probs[i, 0] = 0.1
                probs[i, 1] = 0.1
                probs[i, 2] = 0.8
        return probs


class SMACrossoverBaseline(BaseModel):
    """
    Fast/Slow SMA Crossover Baseline.

    Predicts:
      +1 (BUY) when Fast SMA > Slow SMA
      -1 (SELL) when Fast SMA < Slow SMA
    """

    def __init__(self, fast_sma_idx: int = 0, slow_sma_idx: int = 1):
        super().__init__(name="SMA Crossover (Trend)")
        self.fast_sma_idx = fast_sma_idx
        self.slow_sma_idx = slow_sma_idx

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SMACrossoverBaseline":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if max(self.fast_sma_idx, self.slow_sma_idx) >= X.shape[1]:
            return np.zeros(len(X), dtype=int)
        fast_sma = X[:, self.fast_sma_idx]
        slow_sma = X[:, self.slow_sma_idx]

        preds = np.zeros(len(X), dtype=int)
        preds[fast_sma > slow_sma] = 1
        preds[fast_sma < slow_sma] = -1
        return preds

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        preds = self.predict(X)
        probs = np.zeros((len(X), 3))
        for i, p in enumerate(preds):
            if p == -1:
                probs[i] = [0.7, 0.2, 0.1]
            elif p == 0:
                probs[i] = [0.2, 0.6, 0.2]
            else:
                probs[i] = [0.1, 0.2, 0.7]
        return probs
