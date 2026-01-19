# app/test_dummy.py
import threading
import time

from app.methods.BuiltIn.dummy import DummyMethod


class FakeInstrument:
    def set_output(self, state):
        print(f"[Instrument] Output set to {state}")


def emit(x, y):
    print(f"DATA -> x={x}, y={y}")


def run_method(method, stop_event):
    method.run(stop_event, emit)


# -------------------------------
# Setup
# -------------------------------
method = DummyMethod(FakeInstrument())
method.params = {
    "points": 10,
    "delay": 0.5
}

stop_event = threading.Event()

# -------------------------------
# Start method in background
# -------------------------------
thread = threading.Thread(
    target=run_method,
    args=(method, stop_event),
    daemon=True
)

print("Starting method...")
thread.start()

# -------------------------------
# Wait halfway, then stop
# -------------------------------
time.sleep(2.5)  # ~5 points (halfway)
print("Stopping method...")
stop_event.set()

# -------------------------------
# Wait for clean shutdown
# -------------------------------
thread.join()
print("Method thread finished.")
