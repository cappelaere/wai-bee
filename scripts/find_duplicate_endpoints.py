#!/usr/bin/env python3
"""Find duplicate endpoint definitions between api.py and routers.

This script compares endpoints defined in api.py with those in the routers
to identify duplicates that should be removed.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import re
from pathlib import Path


def extract_endpoints(file_path: Path) -> list:
    """Extract endpoint definitions from a Python file."""
    endpoints = []
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Match @router.get/post/put/delete or @app.get/post/put/delete
    pattern = r'@(?:router|app)\.(get|post|put|delete)\(["\']([^"\']+)["\']'
    matches = re.findall(pattern, content)
    
    for method, path in matches:
        endpoints.append({
            'method': method.upper(),
            'path': path,
            'file': file_path.name
        })
    
    return endpoints


def main():
    """Main entry point."""
    base_path = Path(__file__).parent.parent
    
    # Get endpoints from routers
    router_endpoints = []
    router_dir = base_path / 'bee_agents' / 'api_routers'
    for router_file in router_dir.glob('*.py'):
        if router_file.name != '__init__.py':
            router_endpoints.extend(extract_endpoints(router_file))
    
    # Get endpoints from api.py
    api_file = base_path / 'bee_agents' / 'api.py'
    api_endpoints = extract_endpoints(api_file)
    
    # Find duplicates
    duplicates = []
    for api_ep in api_endpoints:
        for router_ep in router_endpoints:
            # Match if same method and path pattern (ignoring parameter names)
            api_path_normalized = re.sub(r'\{[^}]+\}', '{}', api_ep['path'])
            router_path_normalized = re.sub(r'\{[^}]+\}', '{}', router_ep['path'])
            
            if (api_ep['method'] == router_ep['method'] and 
                api_path_normalized == router_path_normalized):
                duplicates.append({
                    'method': api_ep['method'],
                    'path': api_ep['path'],
                    'router': router_ep['file']
                })
                break
    
    # Print results
    print(f"📊 Endpoint Analysis")
    print(f"=" * 80)
    print(f"Router endpoints: {len(router_endpoints)}")
    print(f"API.py endpoints: {len(api_endpoints)}")
    print(f"Duplicates found: {len(duplicates)}")
    print()
    
    if duplicates:
        print(f"⚠️  DUPLICATE ENDPOINTS (defined in both api.py and routers):")
        print(f"=" * 80)
        for dup in sorted(duplicates, key=lambda x: (x['router'], x['method'], x['path'])):
            print(f"  {dup['method']:6} {dup['path']:50} -> {dup['router']}")
        print()
    
    # Find unique endpoints in api.py
    unique_api = []
    for api_ep in api_endpoints:
        is_duplicate = False
        for router_ep in router_endpoints:
            api_path_normalized = re.sub(r'\{[^}]+\}', '{}', api_ep['path'])
            router_path_normalized = re.sub(r'\{[^}]+\}', '{}', router_ep['path'])
            
            if (api_ep['method'] == router_ep['method'] and 
                api_path_normalized == router_path_normalized):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_api.append(api_ep)
    
    if unique_api:
        print(f"✅ UNIQUE ENDPOINTS (only in api.py, should be kept or moved to routers):")
        print(f"=" * 80)
        for ep in sorted(unique_api, key=lambda x: (x['method'], x['path'])):
            print(f"  {ep['method']:6} {ep['path']}")
        print()


if __name__ == '__main__':
    main()

# Made with Bob
