#!/usr/bin/env python3
"""Find duplicate endpoint definitions in both api.py and chat_api.py.

This script compares endpoints defined in main files with those in the routers
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
    
    # Match @router.get/post/put/delete/websocket or @app.get/post/put/delete/websocket
    pattern = r'@(?:router|app)\.(get|post|put|delete|websocket)\(["\']([^"\']+)["\']'
    matches = re.findall(pattern, content)
    
    for method, path in matches:
        endpoints.append({
            'method': method.upper(),
            'path': path,
            'file': file_path.name
        })
    
    return endpoints


def normalize_path(path: str) -> str:
    """Normalize path by replacing parameter names with placeholders."""
    return re.sub(r'\{[^}]+\}', '{}', path)


def main():
    """Main entry point."""
    base_path = Path(__file__).parent.parent
    
    # Get endpoints from API routers
    api_router_endpoints = []
    api_router_dir = base_path / 'bee_agents' / 'api_routers'
    for router_file in api_router_dir.glob('*.py'):
        if router_file.name != '__init__.py':
            api_router_endpoints.extend(extract_endpoints(router_file))
    
    # Get endpoints from chat routers
    chat_router_endpoints = []
    chat_router_dir = base_path / 'bee_agents' / 'chat_routers'
    for router_file in chat_router_dir.glob('*.py'):
        if router_file.name != '__init__.py':
            chat_router_endpoints.extend(extract_endpoints(router_file))
    
    # Get endpoints from api.py
    api_file = base_path / 'bee_agents' / 'api.py'
    api_endpoints = extract_endpoints(api_file)
    
    # Get endpoints from chat_api.py
    chat_api_file = base_path / 'bee_agents' / 'chat_api.py'
    chat_api_endpoints = extract_endpoints(chat_api_file)
    
    # Find duplicates in api.py
    api_duplicates = []
    for api_ep in api_endpoints:
        for router_ep in api_router_endpoints:
            if (api_ep['method'] == router_ep['method'] and 
                normalize_path(api_ep['path']) == normalize_path(router_ep['path'])):
                api_duplicates.append({
                    'method': api_ep['method'],
                    'path': api_ep['path'],
                    'router': router_ep['file']
                })
                break
    
    # Find duplicates in chat_api.py
    chat_duplicates = []
    for chat_ep in chat_api_endpoints:
        for router_ep in chat_router_endpoints:
            if (chat_ep['method'] == router_ep['method'] and 
                normalize_path(chat_ep['path']) == normalize_path(router_ep['path'])):
                chat_duplicates.append({
                    'method': chat_ep['method'],
                    'path': chat_ep['path'],
                    'router': router_ep['file']
                })
                break
    
    # Print results
    print(f"📊 Endpoint Analysis")
    print(f"=" * 80)
    print(f"API Router endpoints: {len(api_router_endpoints)}")
    print(f"Chat Router endpoints: {len(chat_router_endpoints)}")
    print(f"api.py endpoints: {len(api_endpoints)}")
    print(f"chat_api.py endpoints: {len(chat_api_endpoints)}")
    print()
    
    total_duplicates = len(api_duplicates) + len(chat_duplicates)
    
    if api_duplicates:
        print(f"⚠️  DUPLICATES IN api.py ({len(api_duplicates)} found):")
        print(f"=" * 80)
        for dup in sorted(api_duplicates, key=lambda x: (x['router'], x['method'], x['path'])):
            print(f"  {dup['method']:6} {dup['path']:50} -> {dup['router']}")
        print()
    
    if chat_duplicates:
        print(f"⚠️  DUPLICATES IN chat_api.py ({len(chat_duplicates)} found):")
        print(f"=" * 80)
        for dup in sorted(chat_duplicates, key=lambda x: (x['router'], x['method'], x['path'])):
            print(f"  {dup['method']:6} {dup['path']:50} -> {dup['router']}")
        print()
    
    if total_duplicates == 0:
        print(f"✅ NO DUPLICATES FOUND!")
        print()
    
    # Find unique endpoints
    unique_api = []
    for api_ep in api_endpoints:
        is_duplicate = False
        for router_ep in api_router_endpoints:
            if (api_ep['method'] == router_ep['method'] and 
                normalize_path(api_ep['path']) == normalize_path(router_ep['path'])):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_api.append(api_ep)
    
    unique_chat = []
    for chat_ep in chat_api_endpoints:
        is_duplicate = False
        for router_ep in chat_router_endpoints:
            if (chat_ep['method'] == router_ep['method'] and 
                normalize_path(chat_ep['path']) == normalize_path(router_ep['path'])):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_chat.append(chat_ep)
    
    if unique_api:
        print(f"✅ UNIQUE ENDPOINTS in api.py ({len(unique_api)} found):")
        print(f"=" * 80)
        for ep in sorted(unique_api, key=lambda x: (x['method'], x['path'])):
            print(f"  {ep['method']:6} {ep['path']}")
        print()
    
    if unique_chat:
        print(f"✅ UNIQUE ENDPOINTS in chat_api.py ({len(unique_chat)} found):")
        print(f"=" * 80)
        for ep in sorted(unique_chat, key=lambda x: (x['method'], x['path'])):
            print(f"  {ep['method']:6} {ep['path']}")
        print()
    
    print(f"📊 SUMMARY:")
    print(f"=" * 80)
    print(f"Total duplicates found: {total_duplicates}")
    print(f"  - In api.py: {len(api_duplicates)}")
    print(f"  - In chat_api.py: {len(chat_duplicates)}")
    print()


if __name__ == '__main__':
    main()

# Made with Bob
