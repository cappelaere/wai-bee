#!/usr/bin/env python3
"""Verify that all OpenAPI operation IDs are ≤34 characters for LLM compatibility.

This script checks the generated OpenAPI schema to ensure all operation IDs
meet the length requirement for optimal LLM integration.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import sys
import json
from pathlib import Path


def check_operation_ids(openapi_file: Path) -> tuple[list, list]:
    """Check operation IDs in OpenAPI schema.
    
    Args:
        openapi_file: Path to openapi.json file
        
    Returns:
        Tuple of (valid_ids, invalid_ids) where invalid_ids are > 34 chars
    """
    with open(openapi_file, 'r') as f:
        schema = json.load(f)
    
    valid_ids = []
    invalid_ids = []
    
    # Check all paths and their operations
    for path, methods in schema.get('paths', {}).items():
        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                operation_id = operation.get('operationId', '')
                length = len(operation_id)
                
                entry = {
                    'path': path,
                    'method': method.upper(),
                    'operation_id': operation_id,
                    'length': length
                }
                
                if length > 34:
                    invalid_ids.append(entry)
                else:
                    valid_ids.append(entry)
    
    return valid_ids, invalid_ids


def main():
    """Main entry point."""
    # Find openapi.json in bee_agents directory
    openapi_file = Path(__file__).parent.parent / 'bee_agents' / 'openapi.json'
    
    if not openapi_file.exists():
        print(f"❌ OpenAPI schema not found: {openapi_file}")
        print("   Run the API server first to generate the schema.")
        sys.exit(1)
    
    print(f"📋 Checking operation IDs in: {openapi_file}")
    print()
    
    valid_ids, invalid_ids = check_operation_ids(openapi_file)
    
    # Print results
    print(f"✅ Valid operation IDs (≤34 chars): {len(valid_ids)}")
    print(f"❌ Invalid operation IDs (>34 chars): {len(invalid_ids)}")
    print()
    
    if invalid_ids:
        print("⚠️  INVALID OPERATION IDs (exceeding 34 character limit):")
        print("=" * 80)
        for entry in sorted(invalid_ids, key=lambda x: x['length'], reverse=True):
            print(f"  {entry['method']:6} {entry['path']}")
            print(f"         ID: {entry['operation_id']} ({entry['length']} chars)")
            print()
        
        print("=" * 80)
        print()
        print("📖 See docs/OPERATION_ID_GUIDELINES.md for fixing these issues.")
        sys.exit(1)
    else:
        print("🎉 All operation IDs are within the 34 character limit!")
        print()
        
        # Show some statistics
        if valid_ids:
            lengths = [e['length'] for e in valid_ids]
            print(f"📊 Statistics:")
            print(f"   Total endpoints: {len(valid_ids)}")
            print(f"   Shortest ID: {min(lengths)} chars")
            print(f"   Longest ID: {max(lengths)} chars")
            print(f"   Average length: {sum(lengths) / len(lengths):.1f} chars")
        
        sys.exit(0)


if __name__ == '__main__':
    main()

# Made with Bob
