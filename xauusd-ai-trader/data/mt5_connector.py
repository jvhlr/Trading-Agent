"""
XAUUSD AI Trading Research System — MT5 Connector

Handles MetaTrader 5 terminal connection, symbol discovery, and symbol
confirmation for XAUUSD. Designed with graceful degradation: if MT5 is
not installed or not running, the system logs a clear warning and allows
the rest of the codebase to operate with stored/sample data.

Safety: This module performs NO trading operations. It is read-only.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Attempt to import MetaTrader5 ────────────────────────────────────────────
# MT5 is optional — the system must work without it during development.
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore[assignment]
    MT5_AVAILABLE = False
    logger.warning(
        "MetaTrader5 package not installed. MT5 connectivity is disabled. "
        "Install with: pip install MetaTrader5"
    )


# ── MT5 Timeframe Mapping ────────────────────────────────────────────────────
# Maps string timeframe names to MT5 timeframe constants.
# Only populated if MT5 is available.
TIMEFRAME_MAP: dict[str, int] = {}
if MT5_AVAILABLE:
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }


@dataclass
class SymbolInfo:
    """Structured information about a broker symbol."""
    name: str
    description: str
    currency_base: str
    currency_profit: str
    digits: int
    spread: int
    trade_mode: int
    point: float
    tick_size: float
    tick_value: float
    volume_min: float
    volume_max: float
    volume_step: float

    def __str__(self) -> str:
        return (
            f"{self.name:20s} | {self.description:40s} | "
            f"digits={self.digits} spread={self.spread} "
            f"tick_size={self.tick_size} tick_value={self.tick_value}"
        )


class MT5Connector:
    """
    MetaTrader 5 connection manager.

    Provides:
    - Terminal initialization and shutdown
    - Gold/XAUUSD symbol discovery
    - Symbol metadata retrieval

    Does NOT provide any trading functionality.
    """

    def __init__(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        path: Optional[str] = None,
        timeout: int = 30,
    ):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.timeout = timeout
        self._connected = False

    @property
    def is_available(self) -> bool:
        """Whether the MT5 Python package is installed."""
        return MT5_AVAILABLE

    @property
    def is_connected(self) -> bool:
        """Whether we have an active MT5 terminal connection."""
        return self._connected

    def connect(self) -> bool:
        """
        Initialize connection to the MT5 terminal.

        Returns True if connected successfully, False otherwise.
        Does NOT raise exceptions — connection failure is an expected
        state during development.
        """
        if not MT5_AVAILABLE:
            logger.error(
                "Cannot connect to MT5: MetaTrader5 package is not installed. "
                "Install with: pip install MetaTrader5"
            )
            return False

        # Build initialization kwargs
        init_kwargs: dict = {}
        if self.path:
            init_kwargs["path"] = self.path
        if self.login:
            init_kwargs["login"] = self.login
        if self.password:
            init_kwargs["password"] = self.password
        if self.server:
            init_kwargs["server"] = self.server
        if self.timeout:
            init_kwargs["timeout"] = self.timeout * 1000  # MT5 uses milliseconds

        logger.info("Attempting MT5 connection (server=%s, login=%s)...", self.server, self.login)

        if not mt5.initialize(**init_kwargs):
            error = mt5.last_error()
            logger.error("MT5 initialization failed: %s", error)
            self._connected = False
            return False

        # Log terminal info
        terminal_info = mt5.terminal_info()
        if terminal_info:
            logger.info(
                "MT5 connected — company=%s, build=%s, connected=%s",
                terminal_info.company,
                terminal_info.build,
                terminal_info.connected,
            )

        self._connected = True
        return True

    def disconnect(self) -> None:
        """Cleanly shut down the MT5 connection."""
        if MT5_AVAILABLE and self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 connection closed.")

    def discover_gold_symbols(self, search_patterns: tuple[str, ...] | None = None) -> list[SymbolInfo]:
        """
        Query available symbols and identify likely gold/USD candidates.

        Args:
            search_patterns: Tuple of symbol name patterns to search for.
                Defaults to common gold naming conventions.

        Returns:
            List of SymbolInfo for matching symbols.
        """
        if not self._connected:
            logger.error("Cannot discover symbols: not connected to MT5.")
            return []

        if search_patterns is None:
            search_patterns = ("XAUUSD", "XAUUSDm", "XAUUSD.", "GOLD")

        candidates: list[SymbolInfo] = []
        seen_names: set[str] = set()

        for pattern in search_patterns:
            symbols = mt5.symbols_get(pattern)
            if symbols is None:
                continue
            for sym in symbols:
                if sym.name in seen_names:
                    continue
                seen_names.add(sym.name)
                candidates.append(SymbolInfo(
                    name=sym.name,
                    description=sym.description,
                    currency_base=sym.currency_base,
                    currency_profit=sym.currency_profit,
                    digits=sym.digits,
                    spread=sym.spread,
                    trade_mode=sym.trade_mode,
                    point=sym.point,
                    tick_size=sym.trade_tick_size,
                    tick_value=sym.trade_tick_value,
                    volume_min=sym.volume_min,
                    volume_max=sym.volume_max,
                    volume_step=sym.volume_step,
                ))

        # Also search by description keywords
        all_symbols = mt5.symbols_get()
        if all_symbols:
            for sym in all_symbols:
                if sym.name in seen_names:
                    continue
                desc_lower = sym.description.lower()
                if ("gold" in desc_lower or "xau" in desc_lower) and "usd" in desc_lower:
                    seen_names.add(sym.name)
                    candidates.append(SymbolInfo(
                        name=sym.name,
                        description=sym.description,
                        currency_base=sym.currency_base,
                        currency_profit=sym.currency_profit,
                        digits=sym.digits,
                        spread=sym.spread,
                        trade_mode=sym.trade_mode,
                        point=sym.point,
                        tick_size=sym.trade_tick_size,
                        tick_value=sym.trade_tick_value,
                        volume_min=sym.volume_min,
                        volume_max=sym.volume_max,
                        volume_step=sym.volume_step,
                    ))

        logger.info("Found %d gold/USD symbol candidate(s).", len(candidates))
        for c in candidates:
            logger.info("  Candidate: %s", c)

        return candidates

    def get_symbol_info(self, symbol_name: str) -> Optional[SymbolInfo]:
        """
        Retrieve detailed information for a specific symbol.

        Args:
            symbol_name: The broker's symbol name (e.g., 'XAUUSDm').

        Returns:
            SymbolInfo if found, None otherwise.
        """
        if not self._connected:
            logger.error("Cannot get symbol info: not connected to MT5.")
            return None

        info = mt5.symbol_info(symbol_name)
        if info is None:
            logger.warning("Symbol '%s' not found on broker.", symbol_name)
            return None

        return SymbolInfo(
            name=info.name,
            description=info.description,
            currency_base=info.currency_base,
            currency_profit=info.currency_profit,
            digits=info.digits,
            spread=info.spread,
            trade_mode=info.trade_mode,
            point=info.point,
            tick_size=info.trade_tick_size,
            tick_value=info.trade_tick_value,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
        )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
