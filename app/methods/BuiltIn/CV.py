import time
import numpy as np
from PySide6.QtWidgets import QMessageBox

from app.methods.base import MethodBase, ControlMode
from app.instruments.EGG273A import EGG273A
from app.config import DEBUGGING


class CyclicVoltammetry(MethodBase):
    name = "Cyclic Voltammetry"
    mode = ControlMode.POTENTIOSTAT

    xlabel = "Potential (V)"
    ylabel = "Current (A)"

    @classmethod
    def parameters(cls):
        return {
            "E_start": {
                "label": "Start Potential (V)",
                "default": -0.5
            },
            "E_vertex": {
                "label": "Vertex Potential (V)",
                "default": 0.5
            },
            "scan_rate": {
                "label": "Scan Rate (V/s)",
                "default": 0.05
            },
            "cycles": {
                "label": "Number of Cycles",
                "default": 1
            },
            "step": {
                "label": "Potential Step (V)",
                "default": 0.005
            }
        }

    # -------------------------------------------------
    # Main execution
    # -------------------------------------------------
    def run(self, stop_event, emit, progress_cb):

        # -----------------------------
        # Read parameters
        # -----------------------------
        E_start = self.params["E_start"]
        E_vertex = self.params["E_vertex"]
        scan_rate = self.params["scan_rate"]
        cycles = int(self.params["cycles"])
        step = self.params["step"]

        # -----------------------------
        # DEBUG MODE PRINT
        # -----------------------------
        if DEBUGGING:
            print("\n========== CV DEBUG MODE ==========")
            print(f"E_start    = {E_start} V")
            print(f"E_vertex   = {E_vertex} V")
            print(f"Scan rate  = {scan_rate} V/s")
            print(f"Cycles     = {cycles}")
            print(f"Step       = {step} V")
            print("===================================\n")

        # -----------------------------
        # Generate potential waveform
        # -----------------------------
        forward = np.arange(E_start, E_vertex, step)
        backward = np.arange(E_vertex, E_start, -step)
        single_cycle = np.concatenate((forward, backward))
        waveform = np.tile(single_cycle, cycles)

        total_points = len(waveform)

        # dwell time per point
        dt = step / scan_rate

        # -----------------------------
        # REAL DEVICE MODE
        # -----------------------------

        # 🔹 Wrap the low-level device into an instrument
        instrument = EGG273A(self.device)

        try:
            # --- Configure instrument ---
            instrument.set_mode(self.mode)
            instrument.set_value(E_start)

            # -----------------------------
            # Run CV
            # -----------------------------
            for i, E in enumerate(waveform):

                if stop_event.is_set():
                    if DEBUGGING:
                        print("⏹ CV stopped by user")
                    break

                # ---- Set potential ----
                instrument.set_value(E)
                if DEBUGGING:
                        print(f"Potential: {E}")

                # ---- Real current ----
                I = instrument.read_value()
                if DEBUGGING:
                        print(f"Current: {I}")

                # ---- Emit point ----
                emit(E, I)

                # ---- Progress ----
                progress_cb((i + 1) / total_points)

                time.sleep(dt)


            if DEBUGGING:
                print("✅ CV finished\n")
        
        except Exception as e:
                print(f"[WARN] Method failed: {e}")

