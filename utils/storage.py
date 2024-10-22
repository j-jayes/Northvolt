import pandas as pd
import os

def save_to_parquet(df, filename):
    # Ensure the output folder exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_parquet(filename, index=False)

def load_parquet(filename):
    """Load a Parquet file into a DataFrame."""
    if os.path.exists(filename):
        return pd.read_parquet(filename)
    else:
        return pd.DataFrame()