"""Access control middleware for scholarship multi-tenancy.

This module provides middleware for enforcing scholarship-based access control,
ensuring users can only access data for their assigned scholarships.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-09
Version: 1.0.0
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from .logging_config import setup_logging

# Configure logging
logger = setup_logging('middleware')

class ScholarshipAccessMiddleware:
    """Middleware to enforce scholarship-based access control."""
    
    def __init__(self, token_data: dict):
        """Initialize middleware with user token data.
        
        Args:
            token_data: Dictionary containing username, role, scholarships, and permissions
        """
        self.username = token_data.get("username")
        self.role = token_data.get("role")
        self.scholarships = token_data.get("scholarships", [])
        self.permissions = token_data.get("permissions", [])
        
        logger.info(
            f"Access control initialized for {self.username}",
            extra={
                "username": self.username,
                "role": self.role,
                "scholarships": self.scholarships
            }
        )
    
    def can_access_scholarship(self, scholarship: str) -> bool:
        """Check if user can access a specific scholarship.
        
        Args:
            scholarship: Scholarship identifier to check
            
        Returns:
            True if user has access, False otherwise
        """
        # Admin has access to all scholarships
        if "*" in self.scholarships:
            return True
        
        # Check if scholarship is in user's assigned list
        has_access = scholarship in self.scholarships
        
        logger.info(
            f"Access check: {self.username} -> {scholarship}",
            extra={
                "username": self.username,
                "scholarship": scholarship,
                "allowed": has_access
            }
        )
        
        return has_access
    
    def filter_scholarships(self, scholarships: List[str]) -> List[str]:
        """Filter scholarship list based on user access.
        
        Args:
            scholarships: List of scholarship identifiers
            
        Returns:
            Filtered list containing only accessible scholarships
        """
        if "*" in self.scholarships:
            return scholarships
        
        filtered = [s for s in scholarships if s in self.scholarships]
        
        logger.debug(
            f"Filtered scholarships for {self.username}",
            extra={
                "username": self.username,
                "original_count": len(scholarships),
                "filtered_count": len(filtered)
            }
        )
        
        return filtered
    
    def get_data_folder(self, scholarship: str) -> str:
        """Get data folder path for a scholarship.
        
        Args:
            scholarship: Scholarship identifier
            
        Returns:
            Path to scholarship data folder
            
        Raises:
            PermissionError: If user doesn't have access to the scholarship
        """
        if not self.can_access_scholarship(scholarship):
            logger.warning(
                f"Access denied: {self.username} attempted to access {scholarship}",
                extra={
                    "username": self.username,
                    "scholarship": scholarship,
                    "action": "get_data_folder"
                }
            )
            raise PermissionError(f"Access denied to {scholarship}")
        
        # Load scholarship configuration
        from .auth import load_user_config
        config = load_user_config()
        
        if scholarship not in config["scholarships"]:
            raise ValueError(f"Unknown scholarship: {scholarship}")
        
        return config["scholarships"][scholarship]["data_folder"]
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.
        
        Args:
            permission: Permission to check (read, write, admin)
            
        Returns:
            True if user has the permission, False otherwise
        """
        return permission in self.permissions
    
    def validate_path(self, scholarship: str, requested_path: str) -> bool:
        """Validate that a requested path is within the scholarship folder.
        
        Prevents path traversal attacks by ensuring the resolved path
        is within the scholarship's data folder.
        
        Args:
            scholarship: Scholarship identifier
            requested_path: Path to validate
            
        Returns:
            True if path is valid and within scholarship folder
        """
        try:
            scholarship_folder = self.get_data_folder(scholarship)
            resolved_path = Path(requested_path).resolve()
            scholarship_path = Path(scholarship_folder).resolve()
            
            is_valid = resolved_path.is_relative_to(scholarship_path)
            
            if not is_valid:
                logger.warning(
                    f"Path traversal attempt detected",
                    extra={
                        "username": self.username,
                        "scholarship": scholarship,
                        "requested_path": requested_path,
                        "resolved_path": str(resolved_path)
                    }
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False
    
    def get_accessible_scholarships(self) -> List[Dict[str, str]]:
        """Get list of scholarships accessible to the user.
        
        Returns:
            List of scholarship dictionaries with id, name, and short_name
        """
        from .auth import load_user_config
        config = load_user_config()
        
        all_scholarships = config["scholarships"]
        
        if "*" in self.scholarships:
            # Admin sees all enabled scholarships
            return [
                {
                    "id": key,
                    "name": value["name"],
                    "short_name": value["short_name"]
                }
                for key, value in all_scholarships.items()
                if value.get("enabled", True)
            ]
        
        # Regular users see only their assigned scholarships
        return [
            {
                "id": key,
                "name": all_scholarships[key]["name"],
                "short_name": all_scholarships[key]["short_name"]
            }
            for key in self.scholarships
            if key in all_scholarships and all_scholarships[key].get("enabled", True)
        ]


def log_access_attempt(
    username: str,
    scholarship: str,
    action: str,
    allowed: bool,
    resource: Optional[str] = None
):
    """Log access attempts for audit trail.
    
    Args:
        username: Username attempting access
        scholarship: Scholarship being accessed
        action: Action being performed
        allowed: Whether access was granted
        resource: Optional specific resource being accessed
    """
    from datetime import datetime
    
    log_data = {
        "username": username,
        "scholarship": scholarship,
        "action": action,
        "allowed": allowed,
        "resource": resource,
        "timestamp": datetime.now().isoformat()
    }
    
    if allowed:
        logger.info("Access granted", extra=log_data)
    else:
        logger.warning("Access denied", extra=log_data)


# Made with Bob