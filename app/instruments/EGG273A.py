# app/instruments/EEG273A.py
from app.instruments.base import InstrumentBase
from app.methods.base import ControlMode
from app.config import DEBUGGING

class EGG273A(InstrumentBase):

    def __init__(self, device=None):
        """
        device: serial / GPIB object (None in DEBUGGING)
        """
        self.device = device

    def set_mode(self, mode):
        self.mode = mode

        if DEBUGGING and self.device is None:
            if self.mode == ControlMode.POTENTIOSTAT:
                print("MODE 2")  # potentiostat mode
                print("CELL 1")  # turn cell ON
            else:
                print("MODE 1")  # galvanostat mode
                print("CELL 1")  # turn cell ON
        else:
            if self.mode == ControlMode.POTENTIOSTAT:
                self.device.write("MODE 2")  # potentiostat mode
                self.device.write("CELL 1")  # turn cell ON
            else:
                self.device.write("MODE 1")  # galvanostat mode
                self.device.write("CELL 1")  # turn cell ON

    def set_value(self, value):
        if DEBUGGING and self.device is None:
            if self.mode == ControlMode.POTENTIOSTAT:
                print(f"SETE {value}")
            else:
                print(f"SETI {value}")
        else:
            if self.mode == ControlMode.POTENTIOSTAT:
                self.device.write(f"SETE {value}")
            else:
                self.device.write(f"SETI {value}")

    def read_value(self):
        if DEBUGGING and self.device is None:
            if self.mode == ControlMode.POTENTIOSTAT:
                print(f"READI")
                return 0.001
            else:
                print(f"READE")
                return 0.001
        else:
            if self.mode == ControlMode.POTENTIOSTAT:
                self.device.write("READI")
                response = self.device.read().strip().split(',')

                value, exp = map(float, response)
                current = value * (10 ** exp)

                return current
            else:
                self.device.write("READE")
                response = self.device.read().strip().split(',')
                voltage = response

                return voltage
