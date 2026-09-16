"""
XAUUSD AI Trading Research System — Macro-Gated Model Wrapper

Wraps any base statistical or machine-learning classifier (e.g. Momentum baseline,
Gradient Boosting, Random Forest) and applies deterministic macroeconomic regime
constraints to filter out high-risk false signals.
"""

from typing import Optional, List, Dict
import numpy as np
from models.baselines import BaseModel
from features.macro_features import MacroRegime


class MacroGatedModel(BaseModel):
    """
    Macro-Gated Model Wrapper.
    
    Evaluates underlying technical model predictions through a deterministic
    macroeconomic filter to eliminate signals that oppose strong macro tailwinds/headwinds.
    """

    def __init__(
        self,
        base_model: BaseModel,
        macro_feature_names: Optional[List[str]] = None,
        feature_names: Optional[List[str]] = None,
        block_buy_on_dollar_pressure: bool = True,
        block_sell_on_risk_off: bool = True,
        block_buy_on_dxy_spike: bool = True,
        block_sell_on_oil_spike: bool = True,
    ):
        super().__init__(name=f"MacroGated_{base_model.name}")
        self.base_model = base_model
        self.macro_feature_names = macro_feature_names or []
        self.feature_names = feature_names or []
        self.block_buy_on_dollar_pressure = block_buy_on_dollar_pressure
        self.block_sell_on_risk_off = block_sell_on_risk_off
        self.block_buy_on_dxy_spike = block_buy_on_dxy_spike
        self.block_sell_on_oil_spike = block_sell_on_oil_spike

        self._regime_idx: Optional[int] = None
        self._dxy_ret_idx: Optional[int] = None
        self._oil_ret_idx: Optional[int] = None
        self._vix_spike_idx: Optional[int] = None

        self._resolve_feature_indices()

    def _resolve_feature_indices(self) -> None:
        """Resolve indices of macro feature columns in the feature array X."""
        if not self.feature_names:
            return

        name_to_idx = {name: i for i, name in enumerate(self.feature_names)}
        self._regime_idx = name_to_idx.get("macro_regime_code")
        self._dxy_ret_idx = name_to_idx.get("dxy_ret_5d")
        self._oil_ret_idx = name_to_idx.get("brent_ret_5d")
        self._vix_spike_idx = name_to_idx.get("vix_spike_regime")

    def set_feature_names(self, names: List[str]) -> None:
        """Set feature names and re-resolve column indices."""
        self.feature_names = names
        self._resolve_feature_indices()

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MacroGatedModel":
        """Fit the underlying base model."""
        self.base_model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Generate base model predictions and apply deterministic macro gating.
        0 = WAIT, 1 = BUY, 2 = SELL
        """
        raw_preds = self.base_model.predict(X).copy()
        n = len(raw_preds)

        if not self.feature_names or self._regime_idx is None:
            # If no macro feature index mapping, return raw predictions
            return raw_preds

        gated_preds = raw_preds.copy()
        for i in range(n):
            pred = raw_preds[i]
            if pred == 0:
                continue

            regime = int(X[i, self._regime_idx]) if self._regime_idx is not None else 0
            dxy_ret = float(X[i, self._dxy_ret_idx]) if self._dxy_ret_idx is not None else 0.0
            oil_ret = float(X[i, self._oil_ret_idx]) if self._oil_ret_idx is not None else 0.0
            vix_spike = int(X[i, self._vix_spike_idx]) if self._vix_spike_idx is not None else 0

            # ── Veto Logic for BUY (1) ───────────────────────────────────
            if pred == 1:
                # Veto BUY if Dollar is strongly pressing (headwind)
                if self.block_buy_on_dollar_pressure and regime == MacroRegime.DOLLAR_PRESSURE:
                    gated_preds[i] = 0
                elif self.block_buy_on_dxy_spike and dxy_ret > 0.0075:
                    gated_preds[i] = 0

            # ── Veto Logic for SELL (2) ──────────────────────────────────
            elif pred == 2:
                # Veto SELL if Market is in Risk-Off safe haven flight
                if self.block_sell_on_risk_off and (regime == MacroRegime.RISK_OFF_FLIGHT or vix_spike == 1):
                    gated_preds[i] = 0
                elif self.block_sell_on_oil_spike and oil_ret > 0.03:
                    gated_preds[i] = 0

        return gated_preds

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities, redistributing vetoed probabilities into WAIT.
        """
        raw_proba = self.base_model.predict_proba(X).copy()
        preds = self.predict(X)

        n = len(preds)
        gated_proba = np.zeros_like(raw_proba)

        for i in range(n):
            filtered_pred = preds[i]
            raw_p = raw_proba[i]

            if filtered_pred == 0 and np.argmax(raw_p) != 0:
                # Veto occurred: assign full confidence to WAIT
                gated_proba[i, 0] = 1.0
                gated_proba[i, 1] = 0.0
                gated_proba[i, 2] = 0.0
            else:
                gated_proba[i] = raw_p

        return gated_proba
