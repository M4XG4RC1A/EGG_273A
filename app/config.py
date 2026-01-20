import json
import os

DEFAULT_CONFIG = {
    "DEBUGGING": False
}

def load_config():
    path = os.path.join(os.getcwd(), "config.json")

    if not os.path.exists(path):
        return DEFAULT_CONFIG

    try:
        with open(path, "r") as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
    except Exception as e:
        print(f"[CONFIG ERROR] {e}")
        return DEFAULT_CONFIG


CONFIG = load_config()
DEBUGGING = CONFIG["DEBUGGING"]
