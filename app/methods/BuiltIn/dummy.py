# app/methods/BuiltIn/dummy.py

import time
from app.methods.base import MethodBase, ControlMode
from app.instruments.EGG273A import EGG273A


class DummyMethod(MethodBase):
    """
    Dummy electrochemical method used to test:
    - threading
    - stop handling
    - plotting
    - instrument abstraction
    """

    name = "Dummy Test Method"
    mode = ControlMode.POTENTIOSTAT

    xlabel = "Point index"
    ylabel = "Current (A)"

    @classmethod
    def parameters(cls):
        return {
            "points": {
                "label": "Number of points",
                "type": int,
                "default": 100
            },
            "delay": {
                "label": "Delay per point (s)",
                "type": float,
                "default": 0.05
            },
            "setpoint": {
                "label": "Applied voltage (V)",
                "type": float,
                "default": 0.1
            }
        }

    def run(self, stop_event, emit, progress):
        total = int(self.params["points"])
        delay = float(self.params["delay"])
        setpoint = float(self.params["setpoint"])

        # 🔹 Wrap the low-level device into an instrument
        instrument = EGG273A(self.device)

        try:
            # --- Configure instrument ---
            instrument.set_mode(self.mode)
            instrument.set_value(setpoint)

            # --- Acquisition loop ---
            for i in range(total):

                if stop_event.is_set():
                    print("Dummy method stopped by user.")
                    return

                y = instrument.read_value()
                emit(i, y)

                progress((i + 1) / total)
                time.sleep(delay)

            print("Dummy method finished successfully.")

        finally:
            self.safe_shutdown()
