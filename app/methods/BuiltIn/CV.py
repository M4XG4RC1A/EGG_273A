import time
import math

from app.methods.base import MethodBase, ControlMode


class CVMethod(MethodBase):
    """
    Cyclic Voltammetry (potentiostatic).
    """

    name = "Cyclic Voltammetry"
    mode = ControlMode.POTENTIOSTAT

    @classmethod
    def parameters(cls):
        return {
            "start_voltage": {
                "label": "Start Voltage (V)",
                "type": float,
                "default": -0.5
            },
            "vertex_voltage": {
                "label": "Vertex Voltage (V)",
                "type": float,
                "default": 0.5
            },
            "scan_rate": {
                "label": "Scan Rate (V/s)",
                "type": float,
                "default": 0.1
            },
            "cycles": {
                "label": "Number of cycles",
                "type": int,
                "default": 1
            },
            "dt": {
                "label": "Time step (s)",
                "type": float,
                "default": 0.01
            }
        }

    def run(self, stop_event, emit):
        try:
            p = self.params

            start_v = float(p.get("start_voltage", -0.5))
            vertex_v = float(p.get("vertex_voltage", 0.5))
            scan_rate = float(p.get("scan_rate", 0.1))
            cycles = int(p.get("cycles", 1))
            dt = float(p.get("dt", 0.01))

            dv = scan_rate * dt
            voltage = start_v

            for _ in range(cycles):

                # Forward scan
                while voltage <= vertex_v:

                    if stop_event.is_set():
                        print("CV stopped by user.")
                        return

                    current = self._fake_current(voltage)
                    emit(voltage, current)

                    voltage += dv
                    time.sleep(dt)

                # Reverse scan
                while voltage >= start_v:

                    if stop_event.is_set():
                        print("CV stopped by user.")
                        return

                    current = self._fake_current(voltage)
                    emit(voltage, current)

                    voltage -= dv
                    time.sleep(dt)

            print("CV finished successfully.")

        except Exception as e:
            print(f"CV error: {e}")
            raise

        finally:
            self.safe_shutdown()

    def _fake_current(self, voltage):
        return math.tanh(5 * voltage) + 0.05 * math.sin(20 * voltage)
