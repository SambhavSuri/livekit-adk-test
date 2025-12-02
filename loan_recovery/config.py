"""
Configuration for Loan Recovery Multi-Agent System
==================================================
Environment variables and default settings.
"""

import os
from pathlib import Path

# Get the directory where this config file is located
CURRENT_DIR = Path(__file__).parent

# Default customer data file path
DEFAULT_CUSTOMER_DATA_FILE = str(CURRENT_DIR / "data" / "loan_customers_dataset.csv")

# Configuration with environment variable overrides
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
CUSTOMER_DATA_FILE = os.getenv("CUSTOMER_DATA_FILE", DEFAULT_CUSTOMER_DATA_FILE)

# Print configuration on import
print(f"📋 Loan Recovery Multi-Agent Configuration:")
print(f"   Model: {GEMINI_MODEL}")
print(f"   Customer Data: {CUSTOMER_DATA_FILE}")
print(f"   File exists: {os.path.exists(CUSTOMER_DATA_FILE)}")

