# app/instruments/base.py
from abc import ABC, abstractmethod
from app.methods.base import ControlMode

class InstrumentBase(ABC):

    @abstractmethod
    def set_mode(self, mode: ControlMode):
        pass

    @abstractmethod
    def set_value(self, value: float):
        """
        Sets voltage (potentiostat) OR current (galvanostat)
        depending on current mode.
        """
        pass

    @abstractmethod
    def read_value(self) -> float:
        """
        Reads current (potentiostat) OR voltage (galvanostat)
        depending on current mode.
        """
        pass
