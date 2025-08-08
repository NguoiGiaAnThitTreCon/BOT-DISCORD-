# data.py
import json
import os

DATA_FILE = "balances.json"

def load_balances():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_balances(balances):
    with open(DATA_FILE, "w") as f:
        json.dump(balances, f)
