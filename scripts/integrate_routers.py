#!/usr/bin/env python3
"""Script to integrate modular routers into api.py.

This script demonstrates how to integrate the new router structure.
For production use, manually review and apply changes.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import re
from pathlib import Path


def backup_file(file_path: Path) -> Path:
    """Create a backup of the file."""
    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    backup_path.write_text(file_path.read_text())
    print(f"✓ Created backup: {backup_path}")
    return backup_path


def add_router_imports(content: str) -> str:
    """Add router imports after existing imports."""
    # Find the logging_config import line
    import_marker = "from .logging_config import setup_logging"
    
    if import_marker in content:
        router_imports = """
# Import modular routers
from .api_routers import (
    health_router,
    scores_router,
    analysis_router,
    criteria_router,
    admin_router
)
"""
        content = content.replace(
            import_marker,
            import_marker + router_imports
        )
        print("✓ Added router imports")
    else:
        print("⚠ Could not find import marker")
    
    return content


def add_router_includes(content: str) -> str:
    """Add router includes after CORS middleware."""
    # Find the CORS middleware section
    cors_marker = "app.add_middleware(\n    CORSMiddleware,"
    
    if cors_marker in content:
        # Find the end of the CORS middleware block
        cors_end = content.find(")", content.find(cors_marker)) + 1
        
        router_includes = """


# Include modular routers
app.include_router(health_router)
app.include_router(scores_router)
app.include_router(analysis_router)
app.include_router(criteria_router)
app.include_router(admin_router)

logger.info("Modular routers integrated successfully")
"""
        content = content[:cors_end] + router_includes + content[cors_end:]
        print("✓ Added router includes")
    else:
        print("⚠ Could not find CORS middleware marker")
    
    return content


def comment_out_duplicate_endpoints(content: str) -> str:
    """Comment out endpoints that are now in routers."""
    
    # List of endpoint patterns to comment out
    endpoints_to_remove = [
        (r'@app\.get\("/", tags=\["Health"\]\)', 'root endpoint'),
        (r'@app\.get\("/health"', 'health check'),
        (r'@app\.get\("/score"', 'individual score'),
        (r'@app\.get\("/top_scores"', 'top scores'),
        (r'@app\.get\("/statistics"', 'statistics'),
        (r'@app\.get\("/application"', 'application analysis'),
        (r'@app\.get\("/academic"', 'academic analysis'),
        (r'@app\.get\("/essay"', 'essay analysis'),
        (r'@app\.get\("/recommendation"', 'recommendation analysis'),
        (r'@app\.get\("/criteria"', 'criteria list'),
        (r'@app\.get\("/criteria/\{scholarship\}/\{filename\}"', 'criteria file'),
        (r'@app\.get\("/admin/\{scholarship\}/weights"', 'get weights'),
        (r'@app\.put\("/admin/\{scholarship\}/weights"', 'update weights'),
        (r'@app\.get\("/admin/\{scholarship\}/criteria/\{agent_name\}"', 'get criteria'),
        (r'@app\.put\("/admin/\{scholarship\}/criteria/\{agent_name\}"', 'update criteria'),
        (r'@app\.post\("/admin/\{scholarship\}/criteria/\{agent_name\}/regenerate"', 'regenerate criteria'),
    ]
    
    commented_count = 0
    
    for pattern, description in endpoints_to_remove:
        if re.search(pattern, content):
            # Find the function definition
            match = re.search(pattern, content)
            if match:
                # Find the start of the decorator
                start = match.start()
                
                # Find the end of the function (next @app or def at same indentation level)
                # This is a simplified approach - in production, use proper AST parsing
                next_decorator = content.find('\n@app.', start + 1)
                next_function = content.find('\ndef ', start + 1)
                
                if next_decorator == -1:
                    next_decorator = len(content)
                if next_function == -1:
                    next_function = len(content)
                
                end = min(next_decorator, next_function)
                
                # Comment out the section
                section = content[start:end]
                commented_section = f"\n# MOVED TO ROUTER: {description}\n# " + section.replace('\n', '\n# ')
                content = content[:start] + commented_section + content[end:]
                commented_count += 1
                print(f"✓ Commented out: {description}")
    
    print(f"✓ Commented out {commented_count} duplicate endpoints")
    return content


def integrate_routers(api_file: Path, dry_run: bool = True):
    """Integrate routers into api.py."""
    print(f"\n{'='*60}")
    print("Router Integration Script")
    print(f"{'='*60}\n")
    
    if not api_file.exists():
        print(f"✗ File not found: {api_file}")
        return False
    
    print(f"Processing: {api_file}")
    
    # Read current content
    content = api_file.read_text()
    original_lines = len(content.splitlines())
    print(f"Original file: {original_lines} lines")
    
    if not dry_run:
        # Create backup
        backup_file(api_file)
    
    # Apply transformations
    content = add_router_imports(content)
    content = add_router_includes(content)
    
    # Note: Commenting out endpoints is complex and risky
    # Better to do manually with proper review
    print("\n⚠ Skipping automatic endpoint removal (do manually)")
    print("  See docs/API_REFACTORING_GUIDE.md for list of endpoints to remove")
    
    new_lines = len(content.splitlines())
    print(f"\nModified file: {new_lines} lines")
    print(f"Change: +{new_lines - original_lines} lines")
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No changes written")
        print("="*60)
        print("\nTo apply changes, run with --apply flag:")
        print(f"  python {__file__} --apply")
        
        # Show preview of changes
        print("\n" + "="*60)
        print("Preview of changes:")
        print("="*60)
        print("\n[Router imports would be added after logging_config import]")
        print("[Router includes would be added after CORS middleware]")
        print("\nSee docs/API_REFACTORING_GUIDE.md for complete instructions")
    else:
        # Write changes
        api_file.write_text(content)
        print("\n" + "="*60)
        print("✓ Changes applied successfully")
        print("="*60)
        print(f"\nBackup saved to: {api_file}.backup")
        print("\nNext steps:")
        print("1. Review the changes")
        print("2. Manually remove duplicate endpoints (see guide)")
        print("3. Test the API: python -m bee_agents.api")
        print("4. Run tests: pytest tests/")
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integrate modular routers into api.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview changes)
  python scripts/integrate_routers.py
  
  # Apply changes
  python scripts/integrate_routers.py --apply
  
  # Custom file path
  python scripts/integrate_routers.py --file bee_agents/api.py --apply

For complete instructions, see: docs/API_REFACTORING_GUIDE.md
        """
    )
    
    parser.add_argument(
        '--file',
        type=Path,
        default=Path('bee_agents/api.py'),
        help='Path to api.py file (default: bee_agents/api.py)'
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (default is dry run)'
    )
    
    args = parser.parse_args()
    
    success = integrate_routers(args.file, dry_run=not args.apply)
    
    if not success:
        exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
