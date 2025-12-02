from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
import csv
import os
from typing import Optional

from ..config import GEMINI_MODEL, CUSTOMER_DATA_FILE
from ..prompts import READ_PROFILE_INSTRUCTION
from ..descriptions import READ_PROFILE_DESCRIPTION


def read_customer_data(file_path: Optional[str] = None, customer_name: Optional[str] = None) -> dict:
    """
    Reads customer data from CSV file and optionally filters by customer name.
    
    Args:
        file_path: Path to the CSV file containing customer data (defaults to CUSTOMER_DATA_FILE env var)
        customer_name: Optional customer name to search for (case-insensitive partial match)
    
    Returns:
        Dictionary containing customer data or list of matching customers
    """
    try:
        # Get file path from environment variable if not provided
        if file_path is None:
            file_path = CUSTOMER_DATA_FILE
        
        # Check if file exists
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"File not found: {file_path}. Please provide a valid file path."
            }
        
        # Read file based on extension
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension != '.csv':
            return {
                "status": "error",
                "message": f"Unsupported file format: {file_extension}. Please provide a CSV file."
            }
        
        # Read CSV file
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            columns = reader.fieldnames if reader.fieldnames else []
        
        # Find the name column (case-insensitive)
        name_col = None
        status_col = None
        for col in columns:
            if col.lower() == 'name':
                name_col = col
            if col.lower() == 'status':
                status_col = col
        
        # If no customer name provided, return summary of data
        if not customer_name:
            total_customers = len(rows)
            defaulters = []
            if status_col:
                defaulters = [row for row in rows if row.get(status_col, '').lower() == 'defaulter']
            
            sample_names = []
            if name_col:
                sample_names = [row[name_col] for row in rows[:10] if name_col in row]
            
            return {
                "status": "success",
                "message": "File loaded successfully. Please provide a customer name to search.",
                "summary": {
                    "total_customers": total_customers,
                    "total_defaulters": len(defaulters),
                    "columns": columns,
                    "sample_names": sample_names
                }
            }
        
        # Search for customer by name (case-insensitive partial match)
        if not name_col:
            return {
                "status": "error",
                "message": f"The file does not contain a 'name' column. Available columns: {columns}"
            }
        
        # Perform case-insensitive search
        matching_customers = []
        for row in rows:
            row_name = row.get(name_col, '')
            if customer_name.lower() in row_name.lower():
                matching_customers.append(row)
        
        if len(matching_customers) == 0:
            sample_names = [row[name_col] for row in rows[:20] if name_col in row]
            return {
                "status": "not_found",
                "message": f"No customer found with name containing '{customer_name}'. Please check the spelling or try a different name.",
                "available_names_sample": sample_names
            }
        
        if len(matching_customers) == 1:
            customer = matching_customers[0]
            
            # Replace empty values with "N/A" for proper JSON serialization
            customer_clean = {}
            for key, value in customer.items():
                if not value or value.strip() == '':
                    customer_clean[key] = "N/A"
                else:
                    customer_clean[key] = str(value).strip()
            
            # Check if customer is a defaulter
            customer_status = customer_clean.get(status_col, customer_clean.get('Status', customer_clean.get('status', ''))).lower()
            
            return {
                "status": "success",
                "customer_found": True,
                "is_defaulter": customer_status == 'defaulter',
                "customer_profile": customer_clean,
                "message": f"Customer '{customer_clean.get(name_col)}' found."
            }
        
        # Multiple matches found
        match_names = [{"Name": row.get(name_col, 'N/A')} for row in matching_customers]
        return {
            "status": "multiple_matches",
            "message": f"Found {len(matching_customers)} customers matching '{customer_name}'. Please be more specific.",
            "matching_customers": match_names
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reading file: {str(e)}"
        }


# Create the read profile agent
read_profile = Agent(
    model=GEMINI_MODEL,
    name="read_profile",
    description=READ_PROFILE_DESCRIPTION,
    instruction=READ_PROFILE_INSTRUCTION,
    tools=[read_customer_data],
)