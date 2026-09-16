"""
Tests — Macro-Gated Model
"""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.baselines import BaseModel
from models.macro_gated_model import MacroGatedModel
from features.macro_features import MacroRegime


class MockPredictor(BaseModel):
    """Predictor that always returns the injected signals."""
    def __init__(self, signals):
        super().__init__(name="MockPredictor")
        self.signals = np.array(signals)

    def fit(self, X, y):
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.signals[:len(X)]

    def predict_proba(self, X):
        n = len(X)
        proba = np.zeros((n, 3))
        for i, s in enumerate(self.predict(X)):
            proba[i, s] = 1.0
        return proba


class TestMacroGatedModel:
    def test_veto_buy_on_dollar_pressure(self):
        feature_names = ["feat1", "macro_regime_code", "dxy_ret_5d", "brent_ret_5d", "vix_spike_regime"]
        # Raw signals: all BUY (1)
        raw_signals = [1, 1, 1]
        base = MockPredictor(raw_signals)

        gated = MacroGatedModel(base, feature_names=feature_names)

        # Row 0: Neutral -> BUY allowed
        # Row 1: Dollar Pressure -> BUY vetoed to WAIT (0)
        # Row 2: DXY extreme spike -> BUY vetoed to WAIT (0)
        X = np.array([
            [1.0, MacroRegime.NEUTRAL, 0.001, 0.0, 0],
            [1.0, MacroRegime.DOLLAR_PRESSURE, 0.006, 0.0, 0],
            [1.0, MacroRegime.NEUTRAL, 0.010, 0.0, 0],
        ])

        preds = gated.predict(X)
        assert preds[0] == 1  # Allowed
        assert preds[1] == 0  # Vetoed
        assert preds[2] == 0  # Vetoed

    def test_veto_sell_on_risk_off(self):
        feature_names = ["feat1", "macro_regime_code", "dxy_ret_5d", "brent_ret_5d", "vix_spike_regime"]
        # Raw signals: all SELL (2)
        raw_signals = [2, 2, 2]
        base = MockPredictor(raw_signals)

        gated = MacroGatedModel(base, feature_names=feature_names)

        # Row 0: Neutral -> SELL allowed
        # Row 1: Risk Off Flight -> SELL vetoed to WAIT (0)
        # Row 2: VIX spike -> SELL vetoed to WAIT (0)
        X = np.array([
            [1.0, MacroRegime.NEUTRAL, 0.0, 0.0, 0],
            [1.0, MacroRegime.RISK_OFF_FLIGHT, 0.0, 0.0, 0],
            [1.0, MacroRegime.NEUTRAL, 0.0, 0.0, 1],
        ])

        preds = gated.predict(X)
        assert preds[0] == 2  # Allowed
        assert preds[1] == 0  # Vetoed
        assert preds[2] == 0  # Vetoed
