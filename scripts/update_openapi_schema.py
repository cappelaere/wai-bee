#!/usr/bin/env python3
"""Update OpenAPI schema to add scholarship parameters for multi-tenancy.

This script updates the OpenAPI schema to include scholarship parameters
in all relevant endpoints for multi-tenancy support.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-09
Version: 1.0.0
License: MIT
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_scholarship_parameter():
    """Create the reusable scholarship parameter definition."""
    return {
        "name": "scholarship",
        "in": "query",
        "required": True,
        "schema": {
            "type": "string",
            "enum": ["Delaney_Wings", "Evans_Wings"],
            "description": "Scholarship identifier"
        },
        "description": "The scholarship to query data for. Users can only access scholarships they are assigned to.",
        "example": "Delaney_Wings"
    }


def add_scholarship_parameter_to_endpoint(endpoint_def):
    """Add scholarship parameter to an endpoint definition."""
    if "parameters" not in endpoint_def:
        endpoint_def["parameters"] = []
    
    # Check if scholarship parameter already exists
    has_scholarship = any(
        p.get("name") == "scholarship" 
        for p in endpoint_def["parameters"]
    )
    
    if not has_scholarship:
        # Add scholarship parameter as first parameter
        endpoint_def["parameters"].insert(0, create_scholarship_parameter())
        return True
    
    return False


def add_error_responses(endpoint_def):
    """Add 403 and 404 error responses for scholarship access."""
    if "responses" not in endpoint_def:
        endpoint_def["responses"] = {}
    
    # Add 403 Forbidden response
    if "403" not in endpoint_def["responses"]:
        endpoint_def["responses"]["403"] = {
            "description": "Access denied to this scholarship",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string"}
                        }
                    },
                    "example": {
                        "detail": "Access denied to Evans_Wings scholarship"
                    }
                }
            }
        }
    
    # Add 404 Not Found response if not exists
    if "404" not in endpoint_def["responses"]:
        endpoint_def["responses"]["404"] = {
            "description": "Scholarship not found"
        }


def update_openapi_schema(schema_path: str, backup: bool = True):
    """Update the OpenAPI schema with scholarship parameters.
    
    Args:
        schema_path: Path to the OpenAPI schema file
        backup: Whether to create a backup before updating
    """
    print(f"📖 Reading OpenAPI schema from: {schema_path}")
    
    # Read the schema
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    # Create backup if requested
    if backup:
        backup_path = f"{schema_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"💾 Creating backup: {backup_path}")
        with open(backup_path, 'w') as f:
            json.dump(schema, f, indent=2)
    
    # Update version
    schema["info"]["version"] = "2.0.0"
    schema["info"]["description"] = "REST API for accessing scholarship application analysis data with multi-tenancy support"
    
    # Track changes
    endpoints_updated = []
    
    # Endpoints that need scholarship parameter
    endpoints_to_update = [
        "/scholarship",
        "/top_scores",
        "/application"
    ]
    
    # Update each endpoint
    for path, path_item in schema.get("paths", {}).items():
        if path in endpoints_to_update:
            for method, endpoint_def in path_item.items():
                if method in ["get", "post", "put", "delete"]:
                    print(f"🔧 Updating {method.upper()} {path}")
                    
                    # Add scholarship parameter
                    if add_scholarship_parameter_to_endpoint(endpoint_def):
                        endpoints_updated.append(f"{method.upper()} {path}")
                    
                    # Add error responses
                    add_error_responses(endpoint_def)
                    
                    # Update description to mention multi-tenancy
                    if "description" in endpoint_def:
                        if "multi-tenancy" not in endpoint_def["description"].lower():
                            endpoint_def["description"] += " Supports multi-tenancy with scholarship-based access control."
    
    # Add components section if it doesn't exist
    if "components" not in schema:
        schema["components"] = {}
    
    # Add reusable parameter definition
    if "parameters" not in schema["components"]:
        schema["components"]["parameters"] = {}
    
    schema["components"]["parameters"]["ScholarshipParam"] = {
        "name": "scholarship",
        "in": "query",
        "required": True,
        "schema": {
            "type": "string",
            "enum": ["Delaney_Wings", "Evans_Wings"],
            "description": "Scholarship identifier"
        },
        "description": "The scholarship to query data for. Users can only access scholarships they are assigned to."
    }
    
    # Add scholarship schema
    if "schemas" not in schema["components"]:
        schema["components"]["schemas"] = {}
    
    schema["components"]["schemas"]["Scholarship"] = {
        "type": "string",
        "enum": ["Delaney_Wings", "Evans_Wings"],
        "description": "Available scholarship identifiers"
    }
    
    # Write updated schema
    print(f"💾 Writing updated schema to: {schema_path}")
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    # Print summary
    print(f"\n✅ OpenAPI schema updated successfully!")
    print(f"   Version: {schema['info']['version']}")
    print(f"   Endpoints updated: {len(endpoints_updated)}")
    for endpoint in endpoints_updated:
        print(f"     • {endpoint}")
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update OpenAPI schema for multi-tenancy support"
    )
    parser.add_argument(
        "--schema",
        type=str,
        default="bee_agents/openapi.json",
        help="Path to OpenAPI schema file"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup before updating"
    )
    
    args = parser.parse_args()
    
    try:
        success = update_openapi_schema(args.schema, backup=not args.no_backup)
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

# Made with Bob