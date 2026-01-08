from .login import LoginWindow
from .main_menu import MainMenu
try:
    from .training import TrainingWindow
except Exception:
    TrainingWindow = None

__all__ = [
    "LoginWindow",
    "MainMenu",
    "TrainingWindow",
    "UnifiedProcessingWindow",
]