"""
CSV Reader Tool for Customer Data
==================================
Reads and searches customer data from CSV files.
Port of Google ADK's read_customer_data function.
"""

import csv
import os
from pathlib import Path
from typing import Optional, Dict, Any


def read_customer_data(
    file_path: Optional[str] = None,
    customer_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reads customer data from CSV file and searches by customer name.
    
    Args:
        file_path: Path to CSV file (defaults to loan_recovery/data/loan_customers_dataset.csv)
        customer_name: Customer name to search for (case-insensitive partial match)
    
    Returns:
        Dictionary containing customer data, status, and messages
        
    Example returns:
        - Customer found: {"status": "success", "customer_found": True, "is_defaulter": True, "customer_profile": {...}}
        - Not found: {"status": "not_found", "message": "No customer found...", "available_names_sample": [...]}
        - Error: {"status": "error", "message": "Error message"}
    """
    try:
        # Default file path
        if file_path is None:
            current_dir = Path(__file__).parent.parent
            file_path = str(current_dir / "data" / "loan_customers_dataset.csv")
        
        # Check if file exists
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"Customer database file not found at: {file_path}"
            }
        
        # Read CSV file
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            columns = reader.fieldnames if reader.fieldnames else []
        
        # Find name and status columns (case-insensitive)
        name_col = None
        status_col = None
        for col in columns:
            if col.lower() == 'name':
                name_col = col
            if col.lower() == 'status':
                status_col = col
        
        # If no customer name provided, return summary
        if not customer_name:
            total_customers = len(rows)
            defaulters = [row for row in rows if row.get(status_col, '').lower() == 'defaulter']
            sample_names = [row[name_col] for row in rows[:10] if name_col in row]
            
            return {
                "status": "success",
                "message": "Customer database loaded successfully. Please provide a customer name to search.",
                "summary": {
                    "total_customers": total_customers,
                    "total_defaulters": len(defaulters),
                    "columns": columns,
                    "sample_names": sample_names
                }
            }
        
        # Search for customer (case-insensitive partial match)
        if not name_col:
            return {
                "status": "error",
                "message": f"CSV file does not contain a 'Name' column. Available columns: {columns}"
            }
        
        # Perform search
        matching_customers = []
        for row in rows:
            row_name = row.get(name_col, '')
            if customer_name.lower() in row_name.lower():
                matching_customers.append(row)
        
        # No matches found
        if len(matching_customers) == 0:
            sample_names = [row[name_col] for row in rows[:20] if name_col in row]
            return {
                "status": "not_found",
                "message": f"No customer found with name containing '{customer_name}'. Please check the spelling.",
                "available_names_sample": sample_names
            }
        
        # Single match - return customer profile
        if len(matching_customers) == 1:
            customer = matching_customers[0]
            
            # Clean data - replace empty values with "N/A"
            customer_clean = {}
            for key, value in customer.items():
                if not value or (isinstance(value, str) and value.strip() == ''):
                    customer_clean[key] = "N/A"
                else:
                    customer_clean[key] = str(value).strip()
            
            # Check if customer is a defaulter
            customer_status = customer_clean.get(status_col, customer_clean.get('Status', '')).lower()
            
            return {
                "status": "success",
                "customer_found": True,
                "is_defaulter": customer_status == 'defaulter',
                "customer_profile": customer_clean,
                "message": f"Customer '{customer_clean.get(name_col)}' found successfully."
            }
        
        # Multiple matches found
        match_names = [row.get(name_col, 'N/A') for row in matching_customers]
        return {
            "status": "multiple_matches",
            "message": f"Found {len(matching_customers)} customers matching '{customer_name}'. Please be more specific.",
            "matching_customers": match_names
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reading customer data: {str(e)}"
        }

