# app/methods/base.py
from abc import ABC, abstractmethod
from enum import Enum

class ControlMode(Enum):
    POTENTIOSTAT = "potentiostat"
    GALVANOSTAT = "galvanostat"

class MethodBase(ABC):
    name: str = "Unnamed Method"
    mode: ControlMode = ControlMode.POTENTIOSTAT

    # Default axis labels (can be overridden)
    xlabel: str = "X"
    ylabel: str = "Y"

    def __init__(self, device):
        self.device = device
        self.params = {}

    @classmethod
    @abstractmethod
    def parameters(cls) -> dict:
        pass

    def set_params(self, params: dict):
        self.params = params

    def safe_shutdown(self):
        try:
            if hasattr(self.device, "disable"):
                self.device.disable()
        except Exception as e:
            print(f"[WARN] Safe shutdown failed: {e}")

    @abstractmethod
    def run(self, stop_event, emit, progress):
        """
        progress(fraction) → updates GUI progress bar
        """
        pass
