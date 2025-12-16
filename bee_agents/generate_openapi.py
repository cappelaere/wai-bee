#!/usr/bin/env python3
"""Generate OpenAPI specification file.

This script generates the OpenAPI (Swagger) specification for the
Scholarship Analysis API and saves it as a YAML file.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import yaml
import json
import logging
from pathlib import Path
from .api import app, initialize_services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_openapi_spec(output_file: str = "bee_agents/openapi.yml"):
    """Generate OpenAPI specification and save to file.
    
    Args:
        output_file: Path to output YAML file
    """
    logger.info("Generating OpenAPI specification", extra={"output_file": output_file})
    
    # Initialize all scholarships to get the full spec
    try:
        initialize_services()
        logger.info("Services initialized successfully")
    except Exception as e:
        # If initialization fails, continue anyway - we just want the spec structure
        logger.warning(f"Service initialization failed, continuing with spec generation: {e}")
    
    # Get OpenAPI schema from FastAPI
    openapi_schema = app.openapi()
    
    # Save as YAML
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(openapi_schema, f, default_flow_style=False, sort_keys=False)
    
    logger.info("OpenAPI specification generated", extra={
        "output_path": str(output_path),
        "title": openapi_schema['info']['title'],
        "version": openapi_schema['info']['version'],
        "endpoint_count": len(openapi_schema['paths'])
    })
    
    print(f"✓ OpenAPI specification generated: {output_path}")
    print(f"  Title: {openapi_schema['info']['title']}")
    print(f"  Version: {openapi_schema['info']['version']}")
    print(f"  Endpoints: {len(openapi_schema['paths'])}")
    
    # Also save as JSON for convenience
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(openapi_schema, f, indent=2)
    
    logger.info(f"Also saved as JSON: {json_path}")
    print(f"✓ Also saved as JSON: {json_path}")


def main():
    """Main entry point."""
    logger.info("Starting OpenAPI specification generation")
    print("Generating OpenAPI specification...")
    print()
    generate_openapi_spec()
    print()
    print("You can now:")
    print("  - View the spec: cat bee_agents/openapi.yml")
    print("  - Import into Postman, Insomnia, or other API tools")
    print("  - Use with code generators (openapi-generator, swagger-codegen)")
    logger.info("OpenAPI specification generation complete")


if __name__ == "__main__":
    main()

# Made with Bob
