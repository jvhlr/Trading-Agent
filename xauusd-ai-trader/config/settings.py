"""
XAUUSD AI Trading Research System — Configuration Loader

Central configuration management. Loads defaults from YAML, overrides from
environment variables (.env), and provides typed access to all settings.

Safety invariant: LIVE_TRADING_ENABLED is ALWAYS False in this codebase.
No configuration file or environment variable can set it to True — this is
enforced at load time.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Resolve project paths ────────────────────────────────────────────────────
# Project root is the directory containing this config/ package
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent  # The AI Crypto Trading Bot directory


@dataclass(frozen=True)
class MT5Config:
    """MetaTrader 5 connection settings."""
    login: int | None = None
    password: str | None = None
    server: str | None = None
    path: str | None = None
    connection_timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 5

    @property
    def is_configured(self) -> bool:
        """Check if MT5 credentials are provided."""
        return all([self.login, self.password, self.server])


@dataclass(frozen=True)
class SymbolConfig:
    """Symbol mapping configuration."""
    internal_symbol: str = "XAUUSD"
    broker_symbol: str | None = None
    gold_search_patterns: tuple[str, ...] = (
        "XAUUSD", "XAUUSDm", "XAUUSD.a", "XAUUSD.i", "GOLD", "GOLDm"
    )


@dataclass(frozen=True)
class DataConfig:
    """Data collection and storage settings."""
    timeframes: tuple[str, ...] = ("M1", "M5", "M15", "H1", "H4", "D1")
    default_lookback_days: int = 365
    max_lookback_days: int = 1825
    storage_path: str = "data/raw/xauusd_research.db"

    @property
    def storage_full_path(self) -> Path:
        return PROJECT_ROOT / self.storage_path


@dataclass(frozen=True)
class ValidationConfig:
    """Data validation thresholds."""
    max_missing_candle_pct: float = 5.0
    max_duplicate_count: int = 0
    max_spread_multiplier: float = 10.0
    min_price: float = 100.0
    max_price: float = 50000.0


@dataclass(frozen=True)
class PriceFeatureConfig:
    """Price feature parameters."""
    rolling_return_periods: tuple[int, ...] = (5, 10, 20)
    rolling_volatility_periods: tuple[int, ...] = (10, 20, 50)


@dataclass(frozen=True)
class TechnicalFeatureConfig:
    """Technical indicator parameters."""
    sma_periods: tuple[int, ...] = (20, 50, 200)
    ema_periods: tuple[int, ...] = (12, 26, 50)
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    adx_period: int = 14
    bollinger_period: int = 20
    bollinger_std: float = 2.0


@dataclass(frozen=True)
class StructureFeatureConfig:
    """Market structure feature parameters."""
    swing_lookback: int = 5
    trend_sma_period: int = 20


@dataclass(frozen=True)
class ResearchConfig:
    """Phase 0 research definition parameters."""
    prediction_target: str = "direction"
    prediction_timeframe: str = "H1"
    prediction_horizon: int = 1
    neutral_zone_pips: float = 5.0
    assumed_spread_points: float = 30.0
    assumed_commission_per_lot: float = 7.0
    assumed_slippage_points: float = 10.0
    primary_metric: str = "expectancy"
    secondary_metrics: tuple[str, ...] = (
        "profit_factor", "net_return", "max_drawdown", "win_rate", "calibration"
    )


@dataclass(frozen=True)
class Settings:
    """
    Top-level settings container. Immutable after creation.

    Safety: live_trading_enabled is ALWAYS False. This is a system invariant
    enforced in load_settings() and cannot be overridden.
    """
    environment: str = "development"
    log_level: str = "INFO"
    live_trading_enabled: bool = False  # INVARIANT: always False

    mt5: MT5Config = field(default_factory=MT5Config)
    symbol: SymbolConfig = field(default_factory=SymbolConfig)
    data: DataConfig = field(default_factory=DataConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    price_features: PriceFeatureConfig = field(default_factory=PriceFeatureConfig)
    technical_features: TechnicalFeatureConfig = field(default_factory=TechnicalFeatureConfig)
    structure_features: StructureFeatureConfig = field(default_factory=StructureFeatureConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)


def _load_yaml_config() -> dict[str, Any]:
    """Load the default YAML configuration file."""
    config_path = Path(__file__).parent / "default_config.yaml"
    if not config_path.exists():
        logger.warning("default_config.yaml not found at %s, using hardcoded defaults", config_path)
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _to_tuple(val: Any) -> tuple:
    """Convert a list (from YAML) to a tuple (for frozen dataclasses)."""
    if isinstance(val, list):
        return tuple(val)
    return val


def load_settings() -> Settings:
    """
    Load settings from YAML defaults + environment variable overrides.

    Returns an immutable Settings instance. LIVE_TRADING_ENABLED is
    unconditionally forced to False regardless of any configuration.
    """
    # Load .env from workspace root (where .env lives)
    env_path = WORKSPACE_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded environment from %s", env_path)

    # Load YAML defaults
    cfg = _load_yaml_config()

    # Parse MT5 credentials from environment
    mt5_login_raw = os.getenv("MT5_LOGIN", "")
    mt5_login = int(mt5_login_raw) if mt5_login_raw.strip() else None

    mt5 = MT5Config(
        login=mt5_login,
        password=os.getenv("MT5_PASSWORD") or None,
        server=os.getenv("MT5_SERVER") or None,
        path=os.getenv("MT5_PATH") or None,
        connection_timeout_seconds=cfg.get("mt5", {}).get("connection_timeout_seconds", 30),
        retry_attempts=cfg.get("mt5", {}).get("retry_attempts", 3),
        retry_delay_seconds=cfg.get("mt5", {}).get("retry_delay_seconds", 5),
    )

    # Parse symbol config
    sym_cfg = cfg.get("symbol", {})
    symbol = SymbolConfig(
        internal_symbol=sym_cfg.get("internal_symbol", "XAUUSD"),
        broker_symbol=sym_cfg.get("broker_symbol"),
        gold_search_patterns=_to_tuple(sym_cfg.get("gold_search_patterns", SymbolConfig.gold_search_patterns)),
    )

    # Parse data config
    data_cfg = cfg.get("data", {})
    data = DataConfig(
        timeframes=_to_tuple(data_cfg.get("timeframes", DataConfig.timeframes)),
        default_lookback_days=data_cfg.get("default_lookback_days", 365),
        max_lookback_days=data_cfg.get("max_lookback_days", 1825),
        storage_path=data_cfg.get("storage_path", "data/raw/xauusd_research.db"),
    )

    # Parse validation config
    val_cfg = cfg.get("validation", {})
    validation = ValidationConfig(
        max_missing_candle_pct=val_cfg.get("max_missing_candle_pct", 5.0),
        max_duplicate_count=val_cfg.get("max_duplicate_count", 0),
        max_spread_multiplier=val_cfg.get("max_spread_multiplier", 10.0),
        min_price=val_cfg.get("min_price", 100.0),
        max_price=val_cfg.get("max_price", 50000.0),
    )

    # Parse feature configs
    feat_cfg = cfg.get("features", {})

    price_cfg = feat_cfg.get("price", {})
    price_features = PriceFeatureConfig(
        rolling_return_periods=_to_tuple(price_cfg.get("rolling_return_periods", (5, 10, 20))),
        rolling_volatility_periods=_to_tuple(price_cfg.get("rolling_volatility_periods", (10, 20, 50))),
    )

    tech_cfg = feat_cfg.get("technical", {})
    technical_features = TechnicalFeatureConfig(
        sma_periods=_to_tuple(tech_cfg.get("sma_periods", (20, 50, 200))),
        ema_periods=_to_tuple(tech_cfg.get("ema_periods", (12, 26, 50))),
        rsi_period=tech_cfg.get("rsi_period", 14),
        macd_fast=tech_cfg.get("macd_fast", 12),
        macd_slow=tech_cfg.get("macd_slow", 26),
        macd_signal=tech_cfg.get("macd_signal", 9),
        atr_period=tech_cfg.get("atr_period", 14),
        adx_period=tech_cfg.get("adx_period", 14),
        bollinger_period=tech_cfg.get("bollinger_period", 20),
        bollinger_std=tech_cfg.get("bollinger_std", 2.0),
    )

    struct_cfg = feat_cfg.get("structure", {})
    structure_features = StructureFeatureConfig(
        swing_lookback=struct_cfg.get("swing_lookback", 5),
        trend_sma_period=struct_cfg.get("trend_sma_period", 20),
    )

    # Parse research config
    res_cfg = cfg.get("research", {})
    research = ResearchConfig(
        prediction_target=res_cfg.get("prediction_target", "direction"),
        prediction_timeframe=res_cfg.get("prediction_timeframe", "H1"),
        prediction_horizon=res_cfg.get("prediction_horizon", 1),
        neutral_zone_pips=res_cfg.get("neutral_zone_pips", 5.0),
        assumed_spread_points=res_cfg.get("assumed_spread_points", 30.0),
        assumed_commission_per_lot=res_cfg.get("assumed_commission_per_lot", 7.0),
        assumed_slippage_points=res_cfg.get("assumed_slippage_points", 10.0),
        primary_metric=res_cfg.get("primary_metric", "expectancy"),
        secondary_metrics=_to_tuple(res_cfg.get("secondary_metrics", ResearchConfig.secondary_metrics)),
    )

    sys_cfg = cfg.get("system", {})

    # ── SAFETY INVARIANT ──────────────────────────────────────────────────
    # LIVE_TRADING_ENABLED is ALWAYS False. We log a warning if anyone
    # tried to set it to True in config or environment.
    env_trading = os.getenv("LIVE_TRADING_ENABLED", "false").lower()
    yaml_trading = sys_cfg.get("live_trading_enabled", False)
    if env_trading == "true" or yaml_trading is True:
        logger.critical(
            "LIVE_TRADING_ENABLED was set to True in configuration. "
            "This is BLOCKED by the system safety invariant. Trading remains DISABLED."
        )

    settings = Settings(
        environment=os.getenv("ENVIRONMENT", sys_cfg.get("environment", "development")),
        log_level=os.getenv("LOG_LEVEL", sys_cfg.get("log_level", "INFO")),
        live_trading_enabled=False,  # INVARIANT: hardcoded
        mt5=mt5,
        symbol=symbol,
        data=data,
        validation=validation,
        price_features=price_features,
        technical_features=technical_features,
        structure_features=structure_features,
        research=research,
    )

    logger.info("Settings loaded — environment=%s, trading=%s", settings.environment, settings.live_trading_enabled)
    return settings
