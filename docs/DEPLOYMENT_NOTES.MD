# Deployment Notes for Multi-Tenancy Implementation

## Environment Setup

### Virtual Environment
- **Python Version**: 3.12
- **Virtual Environment**: `venv`
- **Activation Script**: `activate_venv.sh`

### Activation
```bash
# Activate virtual environment
source activate_venv.sh

# Verify Python version
python --version  # Should show Python 3.12.x
```

## Pre-Implementation Checklist

Before implementing the multi-tenancy system:

- [ ] Virtual environment is activated
- [ ] All dependencies are installed
- [ ] Current system is backed up
- [ ] `.env` file is configured
- [ ] Test environment is available

## Implementation Order

### Phase 1: Configuration Setup (No Code Changes)
1. Create `config/` directory
2. Create `config/users.json` with initial users
3. Update `.env` with new environment variables
4. Test configuration loading

**Commands**:
```bash
source activate_venv.sh
mkdir -p config logs
# Create users.json (see implementation guide)
# Update .env (see implementation guide)
```

### Phase 2: Core Components (Code Changes)
1. Create `bee_agents/middleware.py`
2. Update `bee_agents/auth.py`
3. Update `bee_agents/chat_api.py`
4. Test authentication and access control

**Commands**:
```bash
source activate_venv.sh
# Create middleware.py
# Update auth.py
# Update chat_api.py
python -m pytest tests/  # Run tests
```

### Phase 3: API Integration
1. Update WebSocket authentication
2. Add scholarship filtering to agents
3. Add new API endpoints
4. Test end-to-end flow

### Phase 4: UI Updates
1. Update login page to show scholarship info
2. Add scholarship context to chat interface
3. Test with different user roles

### Phase 5: Testing & Validation
1. Run unit tests
2. Run integration tests
3. Test with each user role
4. Verify data isolation
5. Check audit logs

## Dependencies

The multi-tenancy implementation requires no additional Python packages beyond what's already installed. It uses only standard library modules:
- `json` - Configuration file parsing
- `pathlib` - Path validation
- `logging` - Audit logging
- `typing` - Type hints

## Testing Strategy

### Unit Tests
```bash
source activate_venv.sh
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_middleware.py -v
```

### Integration Tests
```bash
source activate_venv.sh
python -m pytest tests/test_integration.py -v
```

### Manual Testing
```bash
source activate_venv.sh

# Start the server
python bee_agents/chat_api.py --port 8100

# In another terminal, test login
curl -X POST http://localhost:8100/login \
  -H "Content-Type: application/json" \
  -d '{"username":"delaney_manager","password":"delaney_password"}'
```

## Rollback Plan

If issues occur during implementation:

### Quick Rollback
```bash
# Restore from backup
git checkout -- bee_agents/auth.py
git checkout -- bee_agents/chat_api.py
rm bee_agents/middleware.py

# Restart server
python bee_agents/chat_api.py --port 8100
```

### Gradual Rollback
1. Keep new configuration files but disable in code
2. Use feature flags to toggle multi-tenancy
3. Fall back to original authentication

## Monitoring

### Log Files to Monitor
- `logs/access_audit.log` - Access control events
- `logs/wai_processing.log` - Application logs
- Server console output - Real-time errors

### Key Metrics
- Login success/failure rates
- Access denial frequency
- Token expiration events
- Scholarship access patterns

## Security Considerations

### File Permissions
```bash
# Secure configuration file
chmod 600 config/users.json

# Secure log directory
chmod 700 logs/

# Secure environment file
chmod 600 .env
```

### Environment Variables
```bash
# Never commit these files
echo "config/users.json" >> .gitignore
echo ".env" >> .gitignore
echo "logs/*.log" >> .gitignore
```

## Performance Impact

The multi-tenancy implementation has minimal performance impact:
- **Configuration Loading**: Cached in memory, loaded once at startup
- **Token Verification**: O(1) dictionary lookup
- **Access Control**: O(1) set membership check
- **Path Validation**: O(1) path resolution

Expected overhead: < 1ms per request

## Backup Strategy

### Before Implementation
```bash
# Backup current code
git add -A
git commit -m "Pre-multi-tenancy backup"
git tag pre-multi-tenancy

# Backup configuration
cp .env .env.backup
```

### During Implementation
```bash
# Commit after each phase
git add -A
git commit -m "Phase 1: Configuration setup"
```

## Troubleshooting

### Issue: Module Import Errors
```bash
# Ensure virtual environment is activated
source activate_venv.sh

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Issue: Configuration Not Loading
```bash
# Check file exists
ls -la config/users.json

# Validate JSON
python -c "import json; json.load(open('config/users.json'))"

# Check environment variable
echo $USER_CONFIG_FILE
```

### Issue: Permission Denied
```bash
# Check file permissions
ls -la config/users.json

# Fix if needed
chmod 600 config/users.json
```

## Post-Implementation Validation

### Checklist
- [ ] All users can log in successfully
- [ ] Admin can access all scholarships
- [ ] Managers can only access assigned scholarships
- [ ] Reviewers have read-only access
- [ ] Cross-scholarship access is blocked
- [ ] Audit logs are being created
- [ ] UI shows correct scholarship context
- [ ] API endpoints filter data correctly
- [ ] WebSocket connections work with new auth
- [ ] No errors in application logs

### Validation Commands
```bash
source activate_venv.sh

# Test each user role
python tests/validate_multi_tenancy.py

# Check logs
tail -n 100 logs/access_audit.log

# Verify no errors
grep ERROR logs/wai_processing.log
```

## Production Deployment

### Pre-Deployment
1. Test in staging environment
2. Review all configuration files
3. Verify all passwords are secure
4. Enable HTTPS
5. Set up monitoring alerts

### Deployment Steps
```bash
# 1. Activate environment
source activate_venv.sh

# 2. Pull latest code
git pull origin main

# 3. Install any new dependencies (if added)
pip install -r requirements.txt

# 4. Update configuration
cp config/users.json.template config/users.json
# Edit users.json with production values

# 5. Update environment variables
# Edit .env with production values

# 6. Run tests
python -m pytest tests/ -v

# 7. Restart server
# Use your process manager (systemd, supervisor, etc.)
sudo systemctl restart scholarship-chat
```

### Post-Deployment
1. Monitor logs for errors
2. Test login with each user role
3. Verify scholarship access control
4. Check performance metrics
5. Review audit logs

## Maintenance

### Regular Tasks
- **Daily**: Review audit logs for suspicious activity
- **Weekly**: Check for failed login attempts
- **Monthly**: Rotate passwords
- **Quarterly**: Review user access rights

### User Management
```bash
# Add new user
# 1. Edit config/users.json
# 2. Add password to .env
# 3. Restart server (or reload config if hot-reload implemented)

# Disable user
# 1. Set "enabled": false in config/users.json
# 2. Restart server

# Change user permissions
# 1. Update "permissions" in config/users.json
# 2. Restart server
```

## Support

### Documentation
- [Multi-Tenancy Design](multi_tenancy_design.md)
- [Implementation Guide](implementation_guide.md)
- [Quick Reference](quick_reference.md)

### Getting Help
1. Check logs: `logs/access_audit.log` and `logs/wai_processing.log`
2. Review documentation
3. Check configuration files
4. Verify environment variables
5. Test with different user roles

## Version History

- **v1.0** - Initial multi-tenancy implementation
  - Organization-based access control
  - Role-based permissions
  - Audit logging
  - Configuration-based user management