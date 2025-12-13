# Multi-Tenancy Quick Reference Guide

## User Roles

| Role | Access Level | Permissions | Use Case |
|------|-------------|-------------|----------|
| **admin** | All scholarships (`*`) | read, write, admin | System administrators, full access |
| **manager** | Assigned scholarships | read, write | Scholarship program managers |
| **reviewer** | Assigned scholarships | read | Read-only reviewers, auditors |

## Configuration Files

### Primary Configuration
- **Location**: `config/users.json`
- **Purpose**: User accounts, roles, and scholarship assignments
- **Format**: JSON

### Environment Variables
- **Location**: `.env`
- **Purpose**: Passwords and system settings
- **Security**: Never commit to version control

## Key Components

### 1. Authentication (`bee_agents/auth.py`)
```python
# Load user configuration
config = load_user_config()

# Check user access
has_access = has_scholarship_access(username, "Delaney_Wings")

# Get user scholarships
scholarships = get_user_scholarships(username)

# Create token with context
token_data = create_token(username)
```

### 2. Middleware (`bee_agents/middleware.py`)
```python
# Initialize middleware
access_control = ScholarshipAccessMiddleware(token_data)

# Check scholarship access
if access_control.can_access_scholarship("Delaney_Wings"):
    # Access granted
    pass

# Get data folder
folder = access_control.get_data_folder("Delaney_Wings")

# Validate file path
is_valid = access_control.validate_path("Delaney_Wings", file_path)
```

### 3. API Integration (`bee_agents/chat_api.py`)
```python
# Authenticate WebSocket
token_data = await authenticate_websocket(websocket)

# Process with access control
access_control = ScholarshipAccessMiddleware(token_data)
scholarships = access_control.get_accessible_scholarships()
```

## Common Tasks

### Adding a New User

1. **Update `config/users.json`**:
```json
{
  "new_user": {
    "password_env": "NEW_USER_PASSWORD",
    "role": "manager",
    "scholarships": ["Delaney_Wings"],
    "permissions": ["read", "write"],
    "email": "user@example.com",
    "full_name": "New User",
    "enabled": true
  }
}
```

2. **Add password to `.env`**:
```bash
NEW_USER_PASSWORD="secure_password_here"
```

3. **Restart the application**

### Adding a New Scholarship

1. **Update `config/users.json`**:
```json
{
  "scholarships": {
    "New_Scholarship": {
      "name": "New Scholarship Program",
      "short_name": "New",
      "data_folder": "data/New_Scholarship",
      "enabled": true,
      "description": "Description here"
    }
  }
}
```

2. **Create data folder**:
```bash
mkdir -p data/New_Scholarship/Applications
```

3. **Assign users to scholarship** in their user config

### Disabling a User

Update `config/users.json`:
```json
{
  "username": {
    "enabled": false
  }
}
```

### Changing User Permissions

Update `config/users.json`:
```json
{
  "username": {
    "role": "reviewer",
    "permissions": ["read"]
  }
}
```

## API Endpoints

### Authentication
- `POST /login` - User login with credentials
- `POST /logout` - User logout
- `GET /api/user/profile` - Get current user profile
- `GET /api/user/scholarships` - Get accessible scholarships

### WebSocket
- `WS /ws` - Real-time chat communication (requires auth token in cookie)

### Health Check
- `GET /health` - System health status

## Security Checklist

- [ ] All passwords stored in environment variables
- [ ] User config file has correct permissions (600)
- [ ] HTTPS enabled in production
- [ ] Audit logging enabled
- [ ] Token expiry configured appropriately
- [ ] Regular password rotation policy
- [ ] Access logs monitored regularly

## Troubleshooting Commands

### Check Configuration
```bash
# Validate JSON syntax
python -c "import json; json.load(open('config/users.json'))"

# List all users
python -c "from bee_agents.auth import load_user_config; config = load_user_config(); print(list(config['users'].keys()))"

# Check user scholarships
python -c "from bee_agents.auth import get_user_scholarships; print(get_user_scholarships('delaney_manager'))"
```

### Check Logs
```bash
# View access audit log
tail -f logs/access_audit.log

# View application log
tail -f logs/wai_processing.log

# Search for access denials
grep "Access denied" logs/access_audit.log
```

### Test Authentication
```bash
# Test user login (requires running server)
curl -X POST http://localhost:8100/login \
  -H "Content-Type: application/json" \
  -d '{"username":"delaney_manager","password":"password"}'
```

## File Structure

```
project/
├── config/
│   └── users.json              # User and scholarship configuration
├── bee_agents/
│   ├── auth.py                 # Authentication with multi-tenancy
│   ├── middleware.py           # Access control middleware
│   ├── chat_api.py             # API with scholarship filtering
│   └── templates/
│       ├── login.html          # Login page
│       └── chat.html           # Chat interface
├── data/
│   ├── Delaney_Wings/          # Delaney scholarship data
│   └── Evans_Wings/            # Evans scholarship data
├── logs/
│   ├── access_audit.log        # Access control audit log
│   └── wai_processing.log      # Application log
└── docs/
    ├── multi_tenancy_design.md # Architecture design
    ├── implementation_guide.md # Implementation steps
    └── quick_reference.md      # This file
```

## Environment Variables Reference

```bash
# Authentication
ADMIN_PASSWORD="admin_password"
DELANEY_PASSWORD="delaney_password"
EVANS_PASSWORD="evans_password"

# Configuration
USER_CONFIG_FILE="config/users.json"
TOKEN_EXPIRY_HOURS=24

# Logging
ENABLE_AUDIT_LOG=true
AUDIT_LOG_FILE="logs/access_audit.log"
LOG_LEVEL=INFO

# Security
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
```

## Token Structure

```json
{
  "token": "abc123...",
  "username": "delaney_manager",
  "role": "manager",
  "scholarships": ["Delaney_Wings"],
  "permissions": ["read", "write"],
  "created": "2025-12-09T21:00:00Z"
}
```

## Access Control Flow

```
User Login
    ↓
Verify Credentials
    ↓
Load User Config
    ↓
Create Token with Scholarship Context
    ↓
User Makes Request
    ↓
Verify Token
    ↓
Initialize Middleware
    ↓
Check Scholarship Access
    ↓
Filter Data by Scholarship
    ↓
Return Results
    ↓
Log Access Attempt
```

## Best Practices

1. **Always use middleware** for scholarship access checks
2. **Never bypass** access control in code
3. **Log all access attempts** for audit trail
4. **Validate file paths** to prevent traversal attacks
5. **Use environment variables** for sensitive data
6. **Test with different roles** before deploying
7. **Monitor logs regularly** for suspicious activity
8. **Rotate passwords** on a regular schedule
9. **Keep config backups** before making changes
10. **Document all changes** to user assignments

## Support Contacts

- **Technical Issues**: Check logs and documentation
- **User Management**: System administrator
- **Security Concerns**: Security team
- **Access Requests**: Scholarship program managers

## Related Documentation

- [Multi-Tenancy Design](multi_tenancy_design.md) - Complete architecture
- [Implementation Guide](implementation_guide.md) - Step-by-step setup
- [API Documentation](../bee_agents/openapi.json) - API reference