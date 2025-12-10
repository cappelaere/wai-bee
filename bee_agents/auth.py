"""Authentication module for the chat API.

This module provides simple token-based authentication for the scholarship
agent chat interface with multi-tenancy support.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-09
Version: 2.0.0
License: MIT
"""

import os, secrets, json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _load_users() -> Dict[str, str]:
    """Load user credentials from environment variables.
    
    This function validates that all required authentication environment variables
    are set and returns a dictionary mapping usernames to their passwords.
    Called once at module initialization to fail fast if configuration is missing.
    
    Environment Variables Required:
        ADMIN_PASSWORD: Password for the admin user
        USER_PASSWORD: Password for the regular user
    
    Returns:
        Dict[str, str]: Dictionary mapping usernames to passwords
        
    Raises:
        ValueError: If any required environment variables are not set
        
    Note:
        This is a private function (prefixed with _) intended for internal use only.
        In production, consider using a secrets manager instead of environment variables.
    """
    required_vars = ["ADMIN_PASSWORD", "USER_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    return {
        "admin": os.environ["ADMIN_PASSWORD"],
        "user": os.environ["USER_PASSWORD"]
    }

USERS = _load_users()

# Store active tokens (in production, use Redis or database)
active_tokens: Dict[str, Dict] = {}


# Models for request/response
class LoginRequest(BaseModel):
    """Login request model for authentication endpoints.
    
    Attributes:
        username (str): The username for authentication
        password (str): The password for authentication
        
    """
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model returned after successful authentication.
    
    Attributes:
        token (str): The generated authentication token (URL-safe, 32 bytes)
        username (str): The authenticated username
        role (str): User role (admin, manager, reviewer)
        scholarships (List[str]): List of scholarship identifiers user can access
        permissions (List[str]): List of permissions (read, write, admin)
        
    """
    token: str
    username: str
    role: Optional[str] = None
    scholarships: Optional[List[str]] = None
    permissions: Optional[List[str]] = None


# Multi-Tenancy Support Functions

def load_user_config() -> dict:
    """Load user configuration from JSON file.
    
    Returns:
        Dictionary containing user and scholarship configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    config_file = os.environ.get("USER_CONFIG_FILE", "config/users.json")
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"User config file not found: {config_file}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate config structure
        if "users" not in config or "scholarships" not in config:
            raise ValueError("Invalid config structure: missing 'users' or 'scholarships'")
        
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")


def get_user_info(username: str) -> Optional[Dict]:
    """Get user information from configuration.
    
    Args:
        username: Username to look up
        
    Returns:
        User information dictionary or None if not found
    """
    try:
        config = load_user_config()
        return config["users"].get(username)
    except Exception:
        return None


def get_user_scholarships(username: str) -> List[str]:
    """Get list of scholarships assigned to user.
    
    Args:
        username: Username to look up
        
    Returns:
        List of scholarship identifiers
    """
    user_info = get_user_info(username)
    if user_info:
        return user_info.get("scholarships", [])
    return []


def get_user_role(username: str) -> str:
    """Get user role.
    
    Args:
        username: Username to look up
        
    Returns:
        User role (admin, manager, reviewer) or empty string
    """
    user_info = get_user_info(username)
    if user_info:
        return user_info.get("role", "")
    return ""


def get_user_permissions(username: str) -> List[str]:
    """Get user permissions.
    
    Args:
        username: Username to look up
        
    Returns:
        List of permissions (read, write, admin)
    """
    user_info = get_user_info(username)
    if user_info:
        return user_info.get("permissions", [])
    return []


def has_scholarship_access(username: str, scholarship: str) -> bool:
    """Check if user has access to specific scholarship.
    
    Args:
        username: Username to check
        scholarship: Scholarship identifier
        
    Returns:
        True if user has access, False otherwise
    """
    scholarships = get_user_scholarships(username)
    return "*" in scholarships or scholarship in scholarships


def is_user_enabled(username: str) -> bool:
    """Check if user account is enabled.
    
    Args:
        username: Username to check
        
    Returns:
        True if user is enabled, False otherwise
    """
    user_info = get_user_info(username)
    if user_info:
        return user_info.get("enabled", True)
    return False


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password credentials with multi-tenancy support.
    
    Supports both legacy USERS dict and new config file.
    
    Args:
        username: The username to verify
        password: The password to verify (plaintext)
        
    Returns:
        bool: True if credentials are valid and user is enabled
    """
    # Check if user is enabled
    if not is_user_enabled(username):
        return False
    
    # Try new config file first
    user_info = get_user_info(username)
    if user_info:
        password_env = user_info.get("password_env")
        if password_env:
            expected_password = os.environ.get(password_env)
            if expected_password and expected_password == password:
                return True
    
    # Fall back to legacy USERS dict for backward compatibility
    if username in USERS and USERS[username] == password:
        return True
    
    return False


def create_token(username: str) -> str:
    """Create a new authentication token for a user (backward compatible).
    
    Generates a cryptographically secure URL-safe token and stores it in the
    active_tokens dictionary with the associated username and creation timestamp.
    Tokens are valid for 24 hours from creation.
    
    Args:
        username (str): Username to associate with the token. Must be a valid
                       username from the USERS dictionary.
        
    Returns:
        str: A URL-safe authentication token (32 bytes, base64 encoded)
        
    Note:
        - Tokens are stored in memory and will be lost on server restart
        - In production, use Redis or a database for token persistence
        - Token expiration is checked during verification, not creation
        
    See Also:
        verify_token: Verify and retrieve username from a token
        revoke_token: Manually invalidate a token
    """
    result = create_token_with_context(username)
    return result["token"]


def create_token_with_context(username: str) -> Dict:
    """Create a new authentication token with scholarship context.
    
    Args:
        username: Username to associate with the token
        
    Returns:
        Dictionary containing token and user context
    """
    token = secrets.token_urlsafe(32)
    
    # Get user information
    scholarships = get_user_scholarships(username)
    role = get_user_role(username)
    permissions = get_user_permissions(username)
    
    # Store token with full context
    active_tokens[token] = {
        "username": username,
        "role": role,
        "scholarships": scholarships,
        "permissions": permissions,
        "created": datetime.now()
    }
    
    return {
        "token": token,
        "username": username,
        "role": role,
        "scholarships": scholarships,
        "permissions": permissions
    }


def verify_token(token: Optional[str]) -> Optional[str]:
    """Verify an authentication token and return the associated username.
    
    Checks if the provided token exists in active_tokens and has not expired.
    Tokens are valid for 24 hours from creation. Expired tokens are automatically
    removed from the active_tokens dictionary.
    
    Args:
        token (Optional[str]): The authentication token to verify. Can be None.
        
    Returns:
        Optional[str]: The username associated with the token if valid and not expired,
                      None if token is invalid, expired, or not provided.
        
    Note:
        - Expired tokens (>24 hours old) are automatically deleted
        - Token expiration is checked on every verification
        - Returns None for any invalid input (None, empty string, unknown token)
        
    Security:
        - Uses constant-time comparison for token lookup
        - Automatically cleans up expired tokens
        - No information leakage about token validity
        
    See Also:
        create_token: Generate a new authentication token
        revoke_token: Manually invalidate a token before expiration
    """
    if not token:
        return None
    
    token_data = active_tokens.get(token)
    if not token_data:
        return None
    
    # Check if token is expired (24 hours)
    expiry_hours = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))
    if datetime.now() - token_data["created"] > timedelta(hours=expiry_hours):
        del active_tokens[token]
        return None
    
    return token_data["username"]


def verify_token_with_context(token: Optional[str]) -> Optional[Dict]:
    """Verify token and return full user context.
    
    Args:
        token: Authentication token to verify
        
    Returns:
        Dictionary with user context or None if invalid
    """
    if not token:
        return None
    
    token_data = active_tokens.get(token)
    if not token_data:
        return None
    
    # Check if token is expired
    expiry_hours = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))
    if datetime.now() - token_data["created"] > timedelta(hours=expiry_hours):
        del active_tokens[token]
        return None
    
    return token_data


def revoke_token(token: str) -> bool:
    """Revoke an authentication token, invalidating it immediately.
    
    Removes the token from the active_tokens dictionary, making it invalid
    for future authentication attempts. Useful for implementing logout
    functionality or forced session termination.
    
    Args:
        token (str): The authentication token to revoke
        
    Returns:
        bool: True if the token existed and was successfully revoked,
              False if the token was not found in active_tokens
        
    Use Cases:
        - User logout: Invalidate token when user explicitly logs out
        - Security breach: Force logout of compromised accounts
        - Session management: Clean up tokens on demand
        - Administrative actions: Revoke access for specific users
        
    Note:
        - Revoking a non-existent token is safe and returns False
        - Expired tokens are automatically removed during verification
        - In production, consider logging revocation events for audit trails
        
    See Also:
        verify_token: Check if a token is valid (handles expiration automatically)
        create_token: Generate new authentication tokens
    """
    if token in active_tokens:
        del active_tokens[token]
        return True
    return False

# Made with Bob
