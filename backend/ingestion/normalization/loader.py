"""
CSV loader for the ingestion layer.

Loads raw GST datasets preserving string dtypes so leading-zero
periods ("012026") survive parsing.
"""

import os

import pandas as pd

# Columns holding zero-padded codes that pandas would coerce to int
_STR_COLUMNS = {
    "gstr2b": ["claim_period"],
    "payments": ["return_period"],
    "taxpayers": ["state_code"],
}


def load_datasets(data_dir: str) -> dict:
    """Load every dataset CSV found in *data_dir* as str-typed DataFrames."""
    dfs = {}
    for name in ("taxpayers", "gstr1", "gstr2b", "payments", "einvoice"):
        path = os.path.join(data_dir, f"{name}.csv")
        if not os.path.exists(path):
            continue
        dtype = {col: str for col in _STR_COLUMNS.get(name, [])}
        dfs[name] = pd.read_csv(path, dtype=dtype)
    return dfs
