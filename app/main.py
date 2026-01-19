# -----------------------
# Activate venv .venv/bin/activate.fish   or   .venv/bin/activate
# -----------------------


import os
import threading
import time
import importlib.util
import customtkinter as ctk
from tkinter import messagebox
from tkinter import simpledialog
import json
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import re
import csv
import pyvisa

from app.methods.loader import load_methods
from app.instruments.EGG273A import EGG273A
from app.config import DEBUGGING

from datetime import datetime

# -----------------------
# Config
# -----------------------
APP_NAME = "EGG_273A_Potentiostat"
DATA_FOLDER = "app/Data"
METHODS_FOLDER = "Methods"
WINDOW_SIZE = "900x640"
METHODS_PATHS = ["Methods/BuiltIn", "Methods/Custom"]

method_classes = load_methods()
print("Available methods:")
for i, method_cls in enumerate(method_classes):
    print(f"{i + 1}. {method_cls.name}")

# -----------------------
# Helpers
# -----------------------
def module_exists(name):
    """Return True if module can be imported."""
    return importlib.util.find_spec(name) is not None

def safe_list_resources():
    """Try to list VISA resources if pyvisa available, else return []"""
    try:
        rm = pyvisa.ResourceManager()
        return list(rm.list_resources())
    except Exception:
        return []
    
class SafeFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._after_ids = []

    def safe_after(self, delay_ms, callback):
        after_id = self.after(delay_ms, callback)
        self._after_ids.append(after_id)
        return after_id

    def cancel_all_after(self):
        for after_id in self._after_ids:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self._after_ids.clear()

# -----------------------
# Loading Frame
# -----------------------
class LoadingFrame(SafeFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self, width=620, height=240)
        self.container.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(self.container, text=APP_NAME, font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(12,6))

        self.status_label = ctk.CTkLabel(self.container, text="Preparing...", anchor="w")
        self.status_label.pack(fill="x", padx=18, pady=(6,4))

        self.progress = ctk.CTkProgressBar(self.container, width=560)
        self.progress.set(0.0)
        self.progress.pack(padx=18, pady=(6,12))

        self.detail_label = ctk.CTkLabel(self.container, text="", anchor="w", wraplength=560, text_color="#9aa0a6")
        self.detail_label.pack(fill="x", padx=18, pady=(0,8))

        # Start loader thread
        self.safe_after(300, self.start_loading)

    def start_loading(self):
        thread = threading.Thread(target=self._do_loading, daemon=True)
        thread.start()

    def _update_ui(self, step_text, detail_text=None, progress=None):
        # Thread-safe UI updates via .after
        def _upd():
            self.status_label.configure(text=step_text)
            if detail_text is not None:
                self.detail_label.configure(text=detail_text)
            if progress is not None:
                self.progress.set(progress)
        self.safe_after(0, _upd)

    def _do_loading(self):

        steps = [
            ("Checking folders", f"Ensuring '{DATA_FOLDER}' and '{METHODS_FOLDER}' exist."),
            ("Probing required packages", "Checking pyvisa, matplotlib, csv, time..."),
            ("Scanning for VISA devices", "Looking for connected instruments (if pyvisa installed)."),
            ("Finalizing", "Setting up UI...")
        ]

        # Step 1: Ensure folders
        self._update_ui(steps[0][0], steps[0][1], 0.05)
        time.sleep(0.35)
        os.makedirs(DATA_FOLDER, exist_ok=True)
        os.makedirs(METHODS_FOLDER, exist_ok=True)
        time.sleep(0.2)
        self._update_ui(steps[0][0], f"Folders ready: '{DATA_FOLDER}', '{METHODS_FOLDER}'", 0.15)
        time.sleep(0.25)

        # Step 2: Check modules
        self._update_ui(steps[1][0], "Checking: pyvisa, matplotlib, customtkinter", 0.25)
        time.sleep(0.25)
        mods = {
            "pyvisa": module_exists("pyvisa"),
            "matplotlib": module_exists("matplotlib"),
            "csv": module_exists("csv"),  # always True
            "time": module_exists("time"),  # always True
        }
        detail = ", ".join(f"{k}: {'OK' if v else 'Missing'}" for k, v in mods.items())
        self._update_ui(steps[1][0], detail, 0.45)
        time.sleep(0.45)

        # Show methods
        for cls in method_classes:
            detail = ", "+cls.name
            self._update_ui(steps[1][0], detail, 0.5)
            time.sleep(0.3)
        

        # Step 3: Scan VISA devices (if available)
        self._update_ui(steps[2][0], steps[2][1], 0.55)
        devices = []
        if mods["pyvisa"]:
            devices = safe_list_resources()
            devs_text = f"Found {len(devices)} device(s): {devices}" if devices else "No VISA devices found."
        else:
            devs_text = "pyvisa not installed — skipping device scan."
        self._update_ui(steps[2][0], devs_text, 0.75)
        time.sleep(0.6)

        # Step 4: Finalize
        self._update_ui(steps[3][0], "Launching main UI...", 0.95)
        time.sleep(0.5)

        # Prepare state to pass to main page
        initial_state = {
            "pyvisa_installed": mods["pyvisa"],
            "matplotlib_installed": mods["matplotlib"],
            "visa_devices": devices
        }

        # Short pause so progress bar is visible
        self._update_ui("Done", "Opening application...", 1.0)
        time.sleep(0.4)

        # Switch to main page in main thread
        self.safe_after(0, lambda: self.controller.on_loading_done(initial_state))
    
    def destroy(self):
        # cancel all after callbacks
        self.cancel_all_after()
        super().destroy()

# -----------------------
# Main App / Pages
# -----------------------
class MainPage(ctk.CTkFrame):
    def __init__(self, master, controller, initial_state):
        super().__init__(master)
        self.controller = controller
        self.initial_state = initial_state

        # VISA Resource Manager
        self.rm = pyvisa.ResourceManager('@py') ##Change to '@py'
        self.device = None

        # layout: left status bar + main area
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Main tab view
        self.tabview = ctk.CTkTabview(self, width=600)
        self.tabview.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        self.tabview.add("Config")
        self.tabview.add("Methods")

        self._build_config_tab()
        self._build_methods_tab()

        # Left status indicator (rounded rectangle-like)
        self.status_frame = ctk.CTkFrame(self, width=80, corner_radius=20)
        self.status_frame.grid(row=0, column=0, sticky="ns", padx=(16,8), pady=16)
        self.status_frame.grid_propagate(False)

        # Inner colored indicator (we'll change its bg)
        self.indicator = ctk.CTkFrame(self.status_frame, width=36, height=500, corner_radius=18)
        self.indicator.place(relx=0.5, rely=0.5, anchor="center")

        # Disconnect button below indicator
        self.disconnect_btn = ctk.CTkButton(self.status_frame, text="⏏", command=self._ask_disconnect, state="disable",
                                            width=40, height=40, corner_radius=20, fg_color=self.status_frame.cget("fg_color"))#, hover_color=self.tabview.cget("fg_color"))
        self.disconnect_btn.place(relx=0.5, rely=0.95, anchor="center")

        # set initial status color based on initial_state
        self._update_status_color()

    def _build_config_tab(self):
        frame = self.tabview.tab("Config")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Configuration / Connection", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(12,6))

        # Data user/project selection area
        row = 1
        ctk.CTkLabel(frame, text="User:").grid(row=row, column=0, sticky="w", padx=12, pady=(8,2))
        self.user_combo = ctk.CTkComboBox(frame, values=self._list_users(), command=self._on_user_selected)
        self.user_combo.configure(state="readonly")
        self.user_combo.grid(row=row+1, column=0, sticky="we", padx=12)
        self.new_user_btn = ctk.CTkButton(frame, text="New User", command=self._new_user_popup)
        self.new_user_btn.grid(row=row+1, column=1, padx=6)

        ctk.CTkLabel(frame, text="Project:").grid(row=row+2, column=0, sticky="w", padx=12, pady=(8,2))
        self.project_combo = ctk.CTkComboBox(frame, values=self._list_projects())
        self.project_combo.grid(row=row+3, column=0, sticky="we", padx=12)
        self.new_proj_btn = ctk.CTkButton(frame, text="New Project", command=self._new_project_popup)
        self.new_proj_btn.grid(row=row+3, column=1, padx=6)

        #self.user_combo.bind("<<ComboboxSelected>>", self._on_user_selected)

        ctk.CTkLabel(frame, text="Experiment name:").grid(row=row+4, column=0, sticky="w", padx=12, pady=(8,2))
        self.experiment_entry = ctk.CTkEntry(frame, placeholder_text="experiment_name")
        self.experiment_entry.grid(row=row+5, column=0, sticky="we", padx=12, pady=(0,12))

        # Device selection
        ctk.CTkLabel(frame, text="Available devices (VISA):").grid(row=row+6, column=0, sticky="w", padx=12, pady=(6,2))
        self.device_combo = ctk.CTkComboBox(frame, values=self.initial_state.get("visa_devices", []), command=self._refresh_devices)
        self.device_combo.configure(state="readonly")
        self.device_combo.set("Refresh devices")
        self.device_combo.grid(row=row+7, column=0, sticky="we", padx=12, pady=(0,6))

        # Buttons
        self.refresh_btn = ctk.CTkButton(frame, text="Refresh", command=self._refresh_devices)
        self.refresh_btn.grid(row=row+7, column=1, sticky="we", padx=12, pady=(0,6))
        self.connect_btn = ctk.CTkButton(frame, text="Connect", command=self._connect_device, state="normal" if self.initial_state.get("visa_devices") else "disabled")
        self.connect_btn.grid(row=row+8, column=0, sticky="we", padx=12, pady=(0,6))

    def _check_save_path(self, filepath):
        folder = os.path.dirname(filepath)

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Cannot create save directory:\n{folder}\n\n{e}"
            )
            return False

        try:
            test_path = os.path.join(folder, ".write_test")
            with open(test_path, "w") as f:
                f.write("test")
            os.remove(test_path)
        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"No write permission in:\n{folder}\n\n{e}"
            )
            return False

        return True

    def _build_methods_tab(self):
        f = self.tabview.tab("Methods")

        # --- Load methods ---
        self.methods = method_classes
        method_names = [m.name for m in self.methods] if self.methods else ["No methods found"]

        # --- Top frame for dropdown + button ---
        top_frame = ctk.CTkFrame(f)
        top_frame.pack(fill="x", padx=12, pady=12)

        # Dropdown to select method
        self.method_combo = ctk.CTkComboBox(top_frame, values=method_names, width=250)
        self.method_combo.set("Select a method")
        self.method_combo.pack(side="left", padx=(0, 10))

        # --- Instrument status label ---
        #self.status_label = ctk.CTkLabel(top_frame, text="Instrument: unknown", text_color="gray")
        #self.status_label.pack(side="left", padx=(10, 0))

        # --- Middle frame with plot (left) and inputs (right) ---
        middle_frame = ctk.CTkFrame(f)
        middle_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Left frame for matplotlib plot
        plot_frame = ctk.CTkFrame(middle_frame)
        plot_frame.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=6)

        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_xlabel("Voltage (mV)/Time(s)/...")
        self.ax.set_ylabel("Current (A)/Voltage (V)/...")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Right frame for method inputs (for now blank)
        self.inputs_frame = ctk.CTkScrollableFrame(middle_frame, width=300, height=400, label_text="Method Inputs")
        self.inputs_frame.pack(side="left", fill="both", expand=False, padx=(6, 0), pady=6)
        self.inputs_frame.grid_columnconfigure(0, weight=1)
        self.inputs_frame.grid_columnconfigure(1, weight=1)

        # Dictionary to store input widgets
        self.input_widgets = {}

        def stop_method():
            if self.controller.current_thread and self.controller.current_thread.is_alive():
                print("⏹ Stop requested by user")
                self.controller.stop_event.set()

        # Function to populate inputs based on selected method
        def update_inputs(event=None):
            # clear old widgets
            for widget in self.inputs_frame.winfo_children():
                widget.destroy()
            self.input_widgets.clear()

            selected_name = self.method_combo.get()
            
            # Method is now a CLASS, not a dict
            method_cls = next((m for m in self.methods if m.name == selected_name), None)
            if not method_cls:
                return

            params = method_cls.parameters()

            # Update axis labels dynamically
            self.ax.cla()
            self.ax.set_xlabel(method_cls.xlabel)
            self.ax.set_ylabel(method_cls.ylabel)
            self.ax.grid(True)
            self.canvas.draw_idle()

            row = 0
            for var_name, meta in params.items():
                label_text = meta.get("label", var_name)
                default_val = meta.get("default", "")

                label = ctk.CTkLabel(
                    self.inputs_frame,
                    text=label_text,
                    anchor="w",
                    wraplength=250
                )
                label.grid(row=row, column=0, sticky="w", padx=6, pady=4)

                entry = ctk.CTkEntry(self.inputs_frame)
                entry.insert(0, str(default_val))
                entry.grid(row=row, column=1, sticky="we", padx=6, pady=4)

                self.input_widgets[var_name] = entry
                row += 1

            # --- Buttons frame ---
            btn_frame = ctk.CTkFrame(self.inputs_frame)
            btn_frame.grid(row=row, column=0, columnspan=2, pady=(12, 4), sticky="we")
            btn_frame.grid_columnconfigure(0, weight=1)
            btn_frame.grid_columnconfigure(1, weight=1)

            run_btn = ctk.CTkButton(btn_frame, text="▶ Run", command=run_method)
            run_btn.grid(row=0, column=0, padx=(0, 5), sticky="we")

            stop_btn = ctk.CTkButton(
                btn_frame,
                text="⏹ Stop",
                fg_color="red",
                command=stop_method
            )
            stop_btn.grid(row=0, column=1, padx=(5, 0), sticky="we")

            # --- Progress bar ---
            self.progress_bar = ctk.CTkProgressBar(self.inputs_frame)
            self.progress_bar.grid(
                row=row + 1,
                column=0,
                columnspan=2,
                sticky="we",
                padx=6,
                pady=(0, 6)
            )
            self.progress_bar.set(0.0)

        # Bind dropdown change
        self.method_combo.configure(command=update_inputs)

        # Run method simulation
        def run_method():
            
            # -----------------------
            # Prepare save path FIRST
            # -----------------------
            user = self.user_combo.get()
            project = self.project_combo.get()
            experiment = self.experiment_entry.get() or "experiment"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            folder = os.path.join(DATA_FOLDER, user, project)
            filename = f"{experiment}_{self.method_combo.get()}_{timestamp}.csv"
            filepath = os.path.join(folder, filename)

            # --- Pre-run save validation ---
            if not self._check_save_path(filepath):
                return

            if not messagebox.askokcancel(
                "Confirm Run",
                f"Data will be saved to:\n\n{filepath}\n\nProceed?"
            ):
                return

            # ---------------- SAFETY CHECK ----------------
            if not DEBUGGING and self.device is None:
                messagebox.showerror(
                    "No device connected",
                    "No electrochemical instrument detected.\n\n"
                    "Connect a device or enable DEBUGGING mode."
                )
                return
            
            self.controller.stop_event.clear()

            selected_name = self.method_combo.get()
            method_cls = next((m for m in self.methods if m.name == selected_name), None)
            if not method_cls:
                messagebox.showwarning("Warning", "Select a valid method first.")
                return

            # Instantiate method
            method = method_cls(self.device)

            # Collect params
            params = {}
            for k, entry in self.input_widgets.items():
                val = entry.get()
                try:
                    params[k] = float(val) if "." in val else int(val)
                except Exception:
                    params[k] = val

            method.set_params(params)

            # Update axis labels dynamically
            self.ax.cla()
            self.ax.set_xlabel(method.xlabel)
            self.ax.set_ylabel(method.ylabel)
            self.ax.grid(True)
            self.canvas.draw_idle()

            # -----------------------
            # Prepare CSV file
            # -----------------------

            csv_file = open(filepath, "w", newline="")
            csv_writer = csv.writer(csv_file)

            # --- Metadata ---
            csv_writer.writerow([f"# Method: {method.name}"])
            csv_writer.writerow([f"# Mode: {method.mode.value}"])
            csv_writer.writerow([f"# Timestamp: {timestamp}"])
            csv_writer.writerow([f"# User: {user}"])
            csv_writer.writerow([f"# Project: {project}"])
            csv_writer.writerow(["# ----------------------------------"])
            csv_writer.writerow(["# PARAMETERS"])

            # --- Parameters ---
            for k, v in params.items():
                csv_writer.writerow([k, v])

            csv_writer.writerow(["# ----------------------------------"])
            csv_writer.writerow(["# DATA"])
            csv_writer.writerow([method.xlabel, method.ylabel])

            def emit(x, y):
                def _update():
                    self.ax.plot(x, y, 'bo')
                    self.canvas.draw_idle()
                    csv_writer.writerow([x, y])
                self.after(0, _update)

            def progress_cb(f):
                self.after(0, lambda: self.progress_bar.set(f))

            def task():
                try:
                    method.run(self.stop_event, emit, progress_cb)
                finally:
                    csv_file.close()
                    print(f"Data saved to: {filepath}")
                self.after(0, lambda: messagebox.showinfo(
                    "Saved",
                    f"Data saved successfully:\n{filepath}"
                ))

            self.controller.current_thread = threading.Thread(target=task, daemon=True)
            self.controller.current_thread.start()

            



    # -------------------------
    # Simple actions / helpers
    # -------------------------
    def _list_users(self):
        users = []
        try:
            users = [d for d in os.listdir(DATA_FOLDER) if os.path.isdir(os.path.join(DATA_FOLDER, d))]
        except Exception:
            users = []
        return users

    def _list_projects(self):
        projects = []
        try:
            user = self.user_combo.get()  # <-- get current combo value
            projects = [
                d for d in os.listdir(os.path.join(DATA_FOLDER, user))
                if os.path.isdir(os.path.join(DATA_FOLDER, user, d))
            ]
        except Exception:
            projects = []
        return projects

    def _on_user_selected(self, event=None):
        self.reload_project_combo()

    def reload_project_combo(self):
        if not hasattr(self, "project_combo"):
            print("Project combo not yet created — skipping reload.")
            return

        projects = self._list_projects()
        if projects:
            self.project_combo.configure(values=projects, state="readonly")
            self.project_combo.set(projects[0])
        else:
            self.project_combo.set("No projects found")
            self.project_combo.configure(values=[], state="disabled")

    def _new_user_popup(self):
        name = simpledialog.askstring("New User", "Enter new user/folder name:")
        if name:
            path = os.path.join(DATA_FOLDER, name)
            try:
                os.makedirs(path, exist_ok=True)
                self.user_combo.configure(values=self._list_users())
                messagebox.showinfo("Created", f"Created folder: {path}")
                self.user_combo.set(name)
                self.reload_project_combo()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _new_project_popup(self):
        user = self.user_combo.get()
        if not user:
            messagebox.showwarning("Select user", "Please select a user folder first.")
            return
        name = simpledialog.askstring("New Project", "Enter new project/folder name:")
        if name:
            path = os.path.join(DATA_FOLDER, user, name)
            try:
                os.makedirs(path, exist_ok=True)
                messagebox.showinfo("Created", f"Created folder: {path}")
                self.reload_project_combo()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _refresh_devices(self):
        # refresh VISA device list
        devices = safe_list_resources()
        self.device_combo.configure(values=devices)
        # adjust connect button
        if devices:
            self.connect_btn.configure(state="normal")
            self.device_combo.set(devices[0])
        else:
            self.device_combo.set("No devices found")
            self.connect_btn.configure(state="disabled")
        # update status colour
        self._update_status_color()

    def _connect_device(self):
        dev = self.device_combo.get()
        if not dev:
            messagebox.showwarning("No device", "Select a device first.")
            return
        # For now, attempt to open resource to test connection (non-blocking quick test)
        try:
            self.device = self.rm.open_resource(dev)
            self.device.read_termination = '\r\n'
            self.device.write_termination = '\r\n'
            self.device.timeout = 5000

            # Initialize device
            # self.device.write("MODE 2")  # potentiostat mode
            # self.device.write("CELL 1")  # turn cell ON


            # attempt ID or IDN
            try:
                # Query ID, Version, Error
                self.device.write("ID")
                dev_id = self.device.read().strip()

                self.device.write("VER")
                version = self.device.read().strip()

                self.device.write("ERR")
                error = self.device.read().strip()

                messagebox.showinfo("Connected",
                            f"Connected to {dev}\n\n"
                            f"ID: {dev_id}\n"
                            f"Version: {version}\n"
                            f"Error: {error}")
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))

            # Mark as connected (for now simply set the indicator and enable disconnect)
            self._set_connected(True)
            messagebox.showinfo("Connected", f"Connection test to {dev} completed (quick test).")
        except Exception as e:
            messagebox.showerror("Connection failed", f"Could not open {dev}:\n{e}")
            self._set_connected(False)

    def _set_connected(self, connected: bool):
        if connected:
            self.disconnect_btn.configure(state="normal", fg_color=self.cget("fg_color"))
            # store state if needed
            self.controller.connected = True
        else:
            self.disconnect_btn.configure(state="disabled", fg_color=self.status_frame.cget("fg_color"))
            self.controller.connected = False
        self._update_status_color()

    def _ask_disconnect(self):
        if not getattr(self.controller, "connected", False):
            return
        if messagebox.askyesno("Disconnect", "Are you sure you want to disconnect the device?"):
            # Here we would safely send the "CELL 0" or close instrument safely.
            if self.device:
                try:
                    self.device.write("CELL 0")  # turn cell OFF
                    self.device.close()
                except:
                    pass
            self.device = None
            self._set_connected(False)
            messagebox.showinfo("Disconnected", "Device disconnected.")
            self._update_status_color()

    def _update_status_color(self):
        # Decide color:
        # - red: pyvisa missing or no devices found
        # - blue: devices found but not connected
        # - green: connected
        connected = self.device
        devices = self.device_combo.cget("values") or []

        if connected:
            color = "#2ecc71"  # green
        elif devices:
            color = "#3498db"  # blue
        else:
            color = "#e74c3c"  # red

        # apply color to indicator
        self.indicator.configure(fg_color=color)
    
    class MainPage(ctk.CTkFrame):
        def destroy(self):
            # destroy matplotlib canvas safely
            if hasattr(self, "canvas"):
                self.canvas.get_tk_widget().destroy()
                plt.close(self.fig)  # close the figure
            super().destroy()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Thread control ---
        self.current_thread = None
        self.stop_event = threading.Event()
        self.instrument = EGG273A(device=None)

        # store after IDs
        self._after_ids = []

        self.title(APP_NAME)
        self.geometry(WINDOW_SIZE)
        self.resizable(False, False)
        # center window on screen
        self.eval('tk::PlaceWindow . center')

        self.connected = False
        self.loading_frame = LoadingFrame(self, self)
        self.loading_frame.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self, event=None):
        if self.current_thread and self.current_thread.is_alive():
            self.stop_event.set()
            time.sleep(0.1)
        if hasattr(self, "main_page"):
            if hasattr(self.main_page, "canvas"):
                self.main_page.canvas.get_tk_widget().destroy()
            if hasattr(self.main_page, "fig"):
                plt.close(self.main_page.fig)
            self.main_page.destroy()
        if hasattr(self, "loading_frame"):
            self.loading_frame.destroy()
        self.after(50, self.destroy)  # destroy root slightly later

    def on_loading_done(self, initial_state):
        # destroy loading and show main page
        #self.configure(fg_color=APP_BG)
        self.loading_frame.pack_forget()
        self.main_page = MainPage(self, self, initial_state)
        self.main_page.pack(fill="both", expand=True)

if __name__ == "__main__":
    ctk.set_appearance_mode("Light")  # or "Dark"
    ctk.set_default_color_theme("dark-blue")
    app = App()
    app.mainloop()
