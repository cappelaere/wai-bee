# Multi-Tenancy Implementation Guide

## Quick Start

This guide provides step-by-step instructions for implementing the organization-based multi-tenancy system for scholarship management.

## Prerequisites

- Python 3.8+
- Existing scholarship system with authentication
- Access to modify code and configuration files

## Implementation Steps

### Step 1: Create Configuration Directory and Files

#### 1.1 Create the config directory structure

```bash
mkdir -p config
mkdir -p logs
```

#### 1.2 Create `config/users.json`

```json
{
  "version": "1.0",
  "description": "User and scholarship configuration for multi-tenancy",
  "users": {
    "admin": {
      "password_env": "ADMIN_PASSWORD",
      "role": "admin",
      "scholarships": ["*"],
      "permissions": ["read", "write", "admin"],
      "email": "admin@example.com",
      "full_name": "System Administrator",
      "enabled": true
    },
    "delaney_manager": {
      "password_env": "DELANEY_PASSWORD",
      "role": "manager",
      "scholarships": ["Delaney_Wings"],
      "permissions": ["read", "write"],
      "email": "delaney.manager@example.com",
      "full_name": "Delaney Scholarship Manager",
      "enabled": true
    },
    "evans_manager": {
      "password_env": "EVANS_PASSWORD",
      "role": "manager",
      "scholarships": ["Evans_Wings"],
      "permissions": ["read", "write"],
      "email": "evans.manager@example.com",
      "full_name": "Evans Scholarship Manager",
      "enabled": true
    },
    "delaney_reviewer": {
      "password_env": "DELANEY_REVIEWER_PASSWORD",
      "role": "reviewer",
      "scholarships": ["Delaney_Wings"],
      "permissions": ["read"],
      "email": "delaney.reviewer@example.com",
      "full_name": "Delaney Scholarship Reviewer",
      "enabled": true
    }
  },
  "scholarships": {
    "Delaney_Wings": {
      "name": "Delaney Wings Scholarship",
      "short_name": "Delaney",
      "data_folder": "data/Delaney_Wings",
      "enabled": true,
      "description": "Delaney Wings Scholarship Program",
      "contact_email": "delaney@example.com"
    },
    "Evans_Wings": {
      "name": "Evans Wings Scholarship",
      "short_name": "Evans",
      "data_folder": "data/Evans_Wings",
      "enabled": true,
      "description": "Evans Wings Scholarship Program",
      "contact_email": "evans@example.com"
    }
  },
  "roles": {
    "admin": {
      "description": "Full system access, can manage all scholarships",
      "default_permissions": ["read", "write", "admin"]
    },
    "manager": {
      "description": "Can read and write to assigned scholarships",
      "default_permissions": ["read", "write"]
    },
    "reviewer": {
      "description": "Read-only access to assigned scholarships",
      "default_permissions": ["read"]
    }
  }
}
```

#### 1.3 Update `.env` file

Add these new environment variables:

```bash
# Existing variables...
ADMIN_PASSWORD="your_secure_admin_password"
USER_PASSWORD="wai2025"  # Keep for backward compatibility

# New user passwords for multi-tenancy
DELANEY_PASSWORD="delaney_secure_password"
EVANS_PASSWORD="evans_secure_password"
DELANEY_REVIEWER_PASSWORD="reviewer_password"

# Multi-tenancy configuration
USER_CONFIG_FILE="config/users.json"
TOKEN_EXPIRY_HOURS=24
ENABLE_AUDIT_LOG=true
AUDIT_LOG_FILE="logs/access_audit.log"

# Security settings
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
```

### Step 2: Create Middleware Module

Create `bee_agents/middleware.py`:

```python
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

logger = logging.getLogger(__name__)


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
```

### Step 3: Update Authentication Module

Modify `bee_agents/auth.py` to add these functions:

```python
# Add these imports at the top
import json
from pathlib import Path
from typing import Dict, List, Optional

# Add after the existing USERS definition

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
    except Exception as e:
        logger.error(f"Error loading user info: {e}")
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


# Update the verify_credentials function
def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password credentials.
    
    Now supports both legacy USERS dict and new config file.
    
    Args:
        username: The username to verify
        password: The password to verify (plaintext)
        
    Returns:
        bool: True if credentials are valid and user is enabled
    """
    # Check if user is enabled
    if not is_user_enabled(username):
        logger.warning(f"Login attempt for disabled user: {username}")
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


# Update the create_token function
def create_token(username: str) -> dict:
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


# Update verify_token to return full context
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
    
    # Check if token is expired (24 hours)
    expiry_hours = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))
    if datetime.now() - token_data["created"] > timedelta(hours=expiry_hours):
        del active_tokens[token]
        return None
    
    return token_data
```

### Step 4: Update Chat API

Modify `bee_agents/chat_api.py`:

```python
# Add import at the top
from .middleware import ScholarshipAccessMiddleware, log_access_attempt
from .auth import verify_token_with_context

# Update authenticate_websocket function
async def authenticate_websocket(websocket: WebSocket) -> Optional[dict]:
    """Authenticate WebSocket connection and return full token data.
    
    Args:
        websocket: The WebSocket connection to authenticate
        
    Returns:
        Token data dictionary if authentication successful, None otherwise
    """
    cookie_header = websocket.headers.get("cookie", "")
    auth_token = extract_auth_token_from_cookies(cookie_header)
    token_data = verify_token_with_context(auth_token)
    
    if not token_data:
        await websocket.close(code=1008, reason="Unauthorized")
        return None
    
    logger.info(
        f"WebSocket authenticated: {token_data['username']}",
        extra={
            "username": token_data["username"],
            "role": token_data["role"],
            "scholarships": token_data["scholarships"]
        }
    )
    
    return token_data


# Update process_chat_message function
async def process_chat_message(websocket: WebSocket, message_data: dict, token_data: dict) -> None:
    """Process a chat message with scholarship access control.
    
    Args:
        websocket: The WebSocket connection
        message_data: The parsed message data from the client
        token_data: The authenticated user's token data with scholarship context
    """
    if message_data.get("type") != "message":
        return
    
    user_message = message_data.get("content", "")
    
    # Create access control middleware
    access_control = ScholarshipAccessMiddleware(token_data)
    
    # Get accessible scholarships for context
    accessible_scholarships = access_control.get_accessible_scholarships()
    scholarship_names = [s["name"] for s in accessible_scholarships]
    
    # Add scholarship context to agent instructions
    scholarship_context = f"""
User Context:
- Username: {token_data['username']}
- Role: {token_data['role']}
- Assigned Scholarships: {', '.join(scholarship_names)}
- Permissions: {', '.join(token_data['permissions'])}

You can only access and provide information about the scholarships listed above.
If the user asks about other scholarships, politely inform them they don't have access.
"""
    
    # Structured logging with context
    log_context = {
        "username": token_data["username"],
        "role": token_data["role"],
        "scholarships": token_data["scholarships"],
        "message_length": len(user_message),
        "timestamp": time.time()
    }
    logger.info(f"Processing message from {token_data['username']}", extra=log_context)
    
    # Rest of the function remains similar...
    # Add scholarship_context to the agent's system prompt or instructions
```

### Step 5: Add New API Endpoints

Add these endpoints to `bee_agents/chat_api.py`:

```python
@app.get("/api/user/profile")
async def get_user_profile(auth_token: Optional[str] = Cookie(None)):
    """Get current user's profile information."""
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    access_control = ScholarshipAccessMiddleware(token_data)
    scholarships = access_control.get_accessible_scholarships()
    
    return {
        "username": token_data["username"],
        "role": token_data["role"],
        "scholarships": scholarships,
        "permissions": token_data["permissions"]
    }


@app.get("/api/user/scholarships")
async def get_user_scholarships(auth_token: Optional[str] = Cookie(None)):
    """Get scholarships accessible to current user."""
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    access_control = ScholarshipAccessMiddleware(token_data)
    return {
        "scholarships": access_control.get_accessible_scholarships()
    }
```

### Step 6: Update Login Response

Modify the login endpoint in `bee_agents/chat_api.py`:

```python
@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Handle login requests with scholarship context."""
    # Verify credentials
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create token with full context
    token_response = create_token(request.username)
    logger.info(
        f"User logged in: {request.username}",
        extra={
            "username": request.username,
            "role": token_response["role"],
            "scholarships": token_response["scholarships"]
        }
    )
    
    return LoginResponse(**token_response)
```

### Step 7: Testing

#### 7.1 Test User Configuration

```bash
# Test loading configuration
python -c "from bee_agents.auth import load_user_config; import json; print(json.dumps(load_user_config(), indent=2))"
```

#### 7.2 Test Authentication

```python
# test_auth.py
from bee_agents.auth import (
    verify_credentials,
    create_token,
    get_user_scholarships,
    has_scholarship_access
)

# Test admin user
assert verify_credentials("admin", "your_admin_password")
token_data = create_token("admin")
assert token_data["role"] == "admin"
assert "*" in token_data["scholarships"]

# Test manager user
assert verify_credentials("delaney_manager", "delaney_password")
token_data = create_token("delaney_manager")
assert token_data["role"] == "manager"
assert "Delaney_Wings" in token_data["scholarships"]
assert has_scholarship_access("delaney_manager", "Delaney_Wings")
assert not has_scholarship_access("delaney_manager", "Evans_Wings")

print("All tests passed!")
```

#### 7.3 Test Middleware

```python
# test_middleware.py
from bee_agents.middleware import ScholarshipAccessMiddleware

# Test manager access
token_data = {
    "username": "delaney_manager",
    "role": "manager",
    "scholarships": ["Delaney_Wings"],
    "permissions": ["read", "write"]
}

middleware = ScholarshipAccessMiddleware(token_data)
assert middleware.can_access_scholarship("Delaney_Wings")
assert not middleware.can_access_scholarship("Evans_Wings")

# Test admin access
admin_token = {
    "username": "admin",
    "role": "admin",
    "scholarships": ["*"],
    "permissions": ["read", "write", "admin"]
}

admin_middleware = ScholarshipAccessMiddleware(admin_token)
assert admin_middleware.can_access_scholarship("Delaney_Wings")
assert admin_middleware.can_access_scholarship("Evans_Wings")

print("Middleware tests passed!")
```

### Step 8: Deployment Checklist

- [ ] Create `config/users.json` with all users
- [ ] Update `.env` with all password environment variables
- [ ] Create `bee_agents/middleware.py`
- [ ] Update `bee_agents/auth.py` with new functions
- [ ] Update `bee_agents/chat_api.py` with middleware integration
- [ ] Test authentication with different user roles
- [ ] Test scholarship access control
- [ ] Verify data isolation between scholarships
- [ ] Check audit logs are being created
- [ ] Test WebSocket connections with different users
- [ ] Update UI to show scholarship context
- [ ] Document user management procedures
- [ ] Train users on new login process

## Troubleshooting

### Issue: Config file not found

**Solution**: Ensure `config/users.json` exists and `USER_CONFIG_FILE` environment variable is set correctly.

### Issue: User can't log in

**Solution**: 
1. Check user is enabled in config
2. Verify password environment variable is set
3. Check logs for authentication errors

### Issue: User sees wrong scholarships

**Solution**:
1. Verify user's scholarship assignments in config
2. Check token contains correct scholarship list
3. Clear browser cookies and re-login

### Issue: Access denied errors

**Solution**:
1. Check user has correct permissions
2. Verify scholarship is enabled in config
3. Check middleware is properly initialized

## Security Best Practices

1. **Password Management**
   - Use strong, unique passwords for each user
   - Store passwords in environment variables, never in code
   - Rotate passwords regularly

2. **Token Security**
   - Use HTTPS in production
   - Set appropriate token expiry times
   - Implement token refresh mechanism

3. **Audit Logging**
   - Enable audit logging in production
   - Regularly review access logs
   - Set up alerts for suspicious activity

4. **Data Isolation**
   - Never bypass middleware checks
   - Validate all file paths
   - Test cross-scholarship access attempts

## Next Steps

After implementing basic multi-tenancy:

1. **Add Admin UI** for user management
2. **Implement Database** for scalable user storage
3. **Add OAuth/SAML** for enterprise SSO
4. **Create Reports** for access analytics
5. **Add MFA** for enhanced security

## Support

For questions or issues:
- Review the main design document: `docs/multi_tenancy_design.md`
- Check logs in `logs/` directory
- Contact system administrator