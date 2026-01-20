# app/instruments/EEG273A.py
import math
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
                I = float(value)

                # ---------------- ZERO CURRENT ----------------
                if I == 0:
                    n1, n2 = 0, -6
                else:
                    # Non-zero current
                    sign = -1 if I < 0 else 1
                    I_abs = abs(I)

                    # Find exponent so mantissa is within limits
                    n2 = int(math.floor(math.log10(I_abs)))
                    n2 = max(min(n2, -3), -10)

                    n1 = int(round(I_abs / (10 ** n2)))
                    n1 *= sign

                    # Clamp mantissa
                    if abs(n1) > 2000:
                        n1 = 2000 * sign

                self.device.write(f"SETI {n1} {n2}")

                if DEBUGGING:
                    print(f"SETI {n1} {n2}  -> {n1 * 10**n2:.3e} A")

                

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
                voltage = float(response[0])

                return voltage
