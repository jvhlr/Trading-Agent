# XAUUSD AI Trading Research System — Features Package

from .price_features import add_all_price_features, add_returns, add_rolling_returns, add_candle_anatomy, add_rolling_volatility
from .technical_features import add_all_technical_features, add_sma, add_ema, add_rsi, add_macd, add_atr, add_adx, add_bollinger_bands
from .structure_features import add_all_structure_features, detect_swings, add_swing_patterns, add_session_levels, classify_trend
from .label_generator import add_direction_target, add_binary_target

__all__ = [
    "add_all_price_features",
    "add_returns",
    "add_rolling_returns",
    "add_candle_anatomy",
    "add_rolling_volatility",
    "add_all_technical_features",
    "add_sma",
    "add_ema",
    "add_rsi",
    "add_macd",
    "add_atr",
    "add_adx",
    "add_bollinger_bands",
    "add_all_structure_features",
    "detect_swings",
    "add_swing_patterns",
    "add_session_levels",
    "classify_trend",
    "add_direction_target",
    "add_binary_target",
]
