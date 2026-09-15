"""
Classifier Models Module for XAUUSD Trading System.

Machine-Learning Classifiers:
1. Logistic Regression (Linear baseline with regularization)
2. Random Forest (Ensemble non-linear decision trees)
3. Gradient Boosting (Sequential boosting ensemble)

Wraps scikit-learn models with standard BaseModel interface fit/predict/predict_proba.
Always returns 3-class probability distribution aligned to [-1, 0, 1].
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from .baselines import BaseModel


def _align_probabilities(
    probs: np.ndarray, model_classes: np.ndarray, target_classes: np.ndarray = np.array([-1, 0, 1])
) -> np.ndarray:
    """
    Aligns scikit-learn predict_proba output to fixed class order [-1, 0, 1].
    Handles cases where training data did not contain all 3 classes.
    """
    n_samples = len(probs)
    n_targets = len(target_classes)
    aligned = np.zeros((n_samples, n_targets))

    for idx, cls in enumerate(model_classes):
        if cls in target_classes:
            target_idx = np.where(target_classes == cls)[0][0]
            aligned[:, target_idx] = probs[:, idx]

    # Normalize rows to sum to 1.0
    row_sums = aligned.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    aligned /= row_sums
    return aligned


class LogisticRegressionModel(BaseModel):
    """Logistic Regression Classifier."""

    def __init__(self, C: float = 1.0, max_iter: int = 1000, random_state: int = 42):
        super().__init__(name="Logistic Regression")
        self.model = LogisticRegression(
            C=C, max_iter=max_iter, random_state=random_state, class_weight="balanced"
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionModel":
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros(len(X), dtype=int)
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            probs = np.zeros((len(X), 3))
            probs[:, 1] = 1.0
            return probs
        raw_probs = self.model.predict_proba(X)
        return _align_probabilities(raw_probs, self.model.classes_)


class RandomForestModel(BaseModel):
    """Random Forest Classifier."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 5,
        min_samples_split: int = 10,
        random_state: int = 42,
    ):
        super().__init__(name="Random Forest")
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=random_state,
            class_weight="balanced",
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestModel":
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros(len(X), dtype=int)
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            probs = np.zeros((len(X), 3))
            probs[:, 1] = 1.0
            return probs
        raw_probs = self.model.predict_proba(X)
        return _align_probabilities(raw_probs, self.model.classes_)


class GradientBoostingModel(BaseModel):
    """Gradient Boosting Classifier."""

    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 3,
        random_state: int = 42,
    ):
        super().__init__(name="Gradient Boosting")
        self.model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=random_state,
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GradientBoostingModel":
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros(len(X), dtype=int)
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            probs = np.zeros((len(X), 3))
            probs[:, 1] = 1.0
            return probs
        raw_probs = self.model.predict_proba(X)
        return _align_probabilities(raw_probs, self.model.classes_)
