"""
Environment Configuration for Loan Recovery Agent

This module manages environment variables for the loan recovery agent.
Provides sensible defaults for streaming environments.
"""

import os
from pathlib import Path


def get_env_var(var_name: str, default: str = None, required: bool = False) -> str:
    """
    Get an environment variable with optional default.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if not set
        required: Whether the variable is required
        
    Returns:
        The value of the environment variable or default
        
    Raises:
        ValueError: If required variable is not set and no default provided
    """
    value = os.getenv(var_name, default)
    if required and not value:
        raise ValueError(f"❌ {var_name} must be set in .env file")
    return value


# Get the directory where this config file is located
CURRENT_DIR = Path(__file__).parent

# Default customer data file path (points to the included sample dataset)
DEFAULT_CUSTOMER_DATA_FILE = str(CURRENT_DIR / "assets" / "loan_customers_dataset.csv")

# Configuration with defaults for bidirectional streaming
GEMINI_MODEL = get_env_var(
    "GEMINI_MODEL",
    default="gemini-2.0-flash-exp",  # Default model for streaming
    required=False
)

# Google API Key - not required if using Vertex AI auth
GOOGLE_API_KEY = get_env_var(
    "GOOGLE_API_KEY",
    default=None,
    required=False
)

# Vertex AI usage - defaults to false (uses Google AI Studio)
GOOGLE_GENAI_USE_VERTEXAI = get_env_var(
    "GOOGLE_GENAI_USE_VERTEXAI",
    default="false",
    required=False
)

# Customer data file - defaults to included sample dataset
CUSTOMER_DATA_FILE = get_env_var(
    "CUSTOMER_DATA_FILE",
    default=DEFAULT_CUSTOMER_DATA_FILE,
    required=False
)

# Print configuration on import
print(f"📋 Loan Recovery Agent Configuration:")
print(f"   Model: {GEMINI_MODEL}")
print(f"   Customer Data: {CUSTOMER_DATA_FILE}")
print(f"   Using Vertex AI: {GOOGLE_GENAI_USE_VERTEXAI}")








