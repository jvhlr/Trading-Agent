# XAUUSD AI Trading Research System — Models Package

from .dataset_builder import build_dataset, DatasetSplit
from .baselines import (
    BaseModel,
    RandomBaseline,
    MajorityWaitBaseline,
    PreviousReturnMomentumBaseline,
    SMACrossoverBaseline,
)
from .classifiers import (
    LogisticRegressionModel,
    RandomForestModel,
    GradientBoostingModel,
)
from .macro_gated_model import MacroGatedModel
from .evaluation import (
    ClassificationMetrics,
    FinancialMetrics,
    evaluate_classification,
    evaluate_financial,
)

__all__ = [
    "build_dataset",
    "DatasetSplit",
    "BaseModel",
    "RandomBaseline",
    "MajorityWaitBaseline",
    "PreviousReturnMomentumBaseline",
    "SMACrossoverBaseline",
    "LogisticRegressionModel",
    "RandomForestModel",
    "GradientBoostingModel",
    "MacroGatedModel",
    "ClassificationMetrics",
    "FinancialMetrics",
    "evaluate_classification",
    "evaluate_financial",
]
