import time
from PySide6.QtWidgets import QMessageBox

from app.methods.base import MethodBase, ControlMode
from app.instruments.EGG273A import EGG273A
from app.config import DEBUGGING


class GalvanostaticConstantCurrent(MethodBase):
    name = "Galvanostatic Constant Current"
    mode = ControlMode.GALVANOSTAT

    xlabel = "Time (s)"
    ylabel = "Voltage (mV)"

    @classmethod
    def parameters(cls):
        return {
            "current": {
                "label": "Current (µA)",
                "default": 100
            },
            "duration": {
                "label": "Total Time (s)",
                "default": 20
            },
            "dt": {
                "label": "Sampling Interval dt (s)",
                "default": 0.1
            }
        }

    # -------------------------------------------------
    # Main execution
    # -------------------------------------------------
    def run(self, stop_event, emit, progress_cb):

        # -----------------------------
        # Read parameters
        # -----------------------------
        I_uA = self.params["current"]
        duration = self.params["duration"]
        dt = self.params["dt"]

        # Convert to amperes
        I = I_uA * 1e-6

        # -----------------------------
        # DEBUG MODE PRINT
        # -----------------------------
        if DEBUGGING:
            print("\n====== GALVANOSTAT DEBUG MODE ======")
            print(f"Current  = {I_uA} µA")
            print(f"Duration = {duration} s")
            print(f"dt       = {dt} s")
            print("===================================\n")

        # -----------------------------
        # Instrument wrapper
        # -----------------------------
        instrument = EGG273A(self.device)

        try:
            # --- Configure instrument ---
            instrument.set_mode(self.mode)
            instrument.set_value(I)  # constant current

            t0 = time.time()
            t = 0.0

            # -----------------------------
            # Measurement loop
            # -----------------------------
            while t <= duration:

                if stop_event.is_set():
                    if DEBUGGING:
                        print("⏹ Galvanostatic run stopped by user")
                    break

                # Read voltage
                V = instrument.read_value()

                # Emit (time, voltage)
                emit(t, V)

                # Progress
                progress_cb(min(t / duration, 1.0))

                time.sleep(dt)
                t = time.time() - t0

            if DEBUGGING:
                print("✅ Galvanostatic run finished\n")
                instrument.set_value(0)

        except Exception as e:
            print(f"[WARN] Galvanostatic method failed: {e}")

        finally:
            # Always turn current OFF
            try:
                instrument.set_value(0)
            except Exception:
                pass
