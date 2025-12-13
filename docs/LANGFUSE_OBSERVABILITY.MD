# LangFuse Observability Integration (Self-Hosted)

This document explains how to set up and use the self-hosted LangFuse observability platform with the WAI Scholarship Chat Agent system.

## Overview

LangFuse provides comprehensive observability for LLM applications, allowing you to:
- Track agent interactions and performance
- Monitor token usage and costs
- Debug agent behavior and tool calls
- Analyze user sessions and conversations
- Measure response times and quality

The integration uses **OpenInference BeeAI instrumentation** with OpenTelemetry to automatically trace all agent activities and send them to LangFuse via OTLP (OpenTelemetry Protocol).

## Setup

### 1. Deploy LangFuse (Included in Docker Compose)

LangFuse is automatically deployed as part of the docker-compose stack with:
- **PostgreSQL database** for data storage
- **LangFuse web UI** on port 3000
- **Persistent storage** for database

No separate installation needed!

### 2. Generate Secure Secrets

Generate secure secrets for LangFuse:

```bash
# Generate NEXTAUTH_SECRET (min 32 characters)
openssl rand -base64 32

# Generate SALT (min 32 characters)
openssl rand -base64 32
```

Add to your `.env` file:

```env
# LangFuse Server Configuration
LANGFUSE_NEXTAUTH_SECRET="your-generated-secret-here"
LANGFUSE_SALT="your-generated-salt-here"

# LangFuse Observability Configuration
LANGFUSE_PUBLIC_KEY=""  # Will get after setup
LANGFUSE_SECRET_KEY=""  # Will get after setup
LANGFUSE_HOST="http://langfuse:3000"
LANGFUSE_ENABLED=true
```

### 3. Deploy All Services

```bash
# Deploy with docker-compose (includes LangFuse)
make deploy

# Or manually
docker compose up -d
```

This will start:
- PostgreSQL database (langfuse-db)
- LangFuse web UI (langfuse) on port 3000
- API server on port 8200
- Chat frontend on port 8100

### 4. Initial LangFuse Setup

```bash
# Show LangFuse URL and instructions
make langfuse-url
```

**First-time setup:**

1. Open http://YOUR_HOST:3000 in your browser
2. Create an account (first user becomes admin)
3. Create a new project (e.g., "WAI Scholarship System")
4. Go to Project Settings → API Keys
5. Copy the **Public Key** (starts with `pk-lf-`)
6. Copy the **Secret Key** (starts with `sk-lf-`)
7. Add them to `.env`:
   ```env
   LANGFUSE_PUBLIC_KEY="pk-lf-your-key-here"
   LANGFUSE_SECRET_KEY="sk-lf-your-secret-here"
   ```
8. Restart chat service:
   ```bash
   docker compose restart chat
   ```

### 5. Verify Setup

```bash
# Check all services are healthy
make health

# View LangFuse logs
make logs-langfuse

# View chat logs (should see "LangFuse observability initialized")
make logs-chat
```

## What Gets Tracked

### Agent Interactions

Every chat message is tracked with:
- **Trace Name**: `chat_{username}_{scholarship}`
- **User ID**: Username from authentication
- **Session ID**: User's session token
- **Metadata**:
  - Scholarship name
  - User role
  - Message length
  - Timestamp

### Agent Events

The system tracks:
- Agent initialization
- Tool calls (OpenAPI endpoints)
- Hand-offs between agents (orchestrator → specialist)
- Response generation
- Errors and timeouts

### Performance Metrics

Automatically captured:
- Total execution time
- Token usage (input/output)
- Model used
- Success/failure status
- Error messages

## Viewing Traces in LangFuse

### 1. Access LangFuse Dashboard

Navigate to http://YOUR_HOST:3000

### 2. View Traces

- **Traces Tab**: See all agent interactions
- **Sessions Tab**: Group by user sessions
- **Users Tab**: See activity by username
- **Metrics Tab**: View aggregated statistics

### 3. Analyze a Trace

Click on any trace to see:
- Full conversation context
- Agent reasoning steps
- Tool calls and responses
- Token usage breakdown
- Execution timeline
- Error details (if any)

## Example Trace Structure

```
Trace: chat_admin_Delaney_Wings
├── Orchestrator Agent
│   ├── Input: User query with scholarship context
│   ├── Reasoning: Determine which specialist to use
│   └── Hand-off: scholarship_specialist
│       ├── Tool Call: GET /api/scores?scholarship=Delaney_Wings
│       ├── Tool Response: [score data]
│       ├── LLM Processing: Format response
│       └── Output: Formatted answer
└── Metadata
    ├── User: admin
    ├── Role: admin
    ├── Scholarship: Delaney_Wings
    ├── Duration: 2.3s
    └── Tokens: 1,234 (input: 890, output: 344)
```

## Debugging with LangFuse

### Common Issues

**1. No traces appearing**
- Check `LANGFUSE_ENABLED=true` in .env
- Verify credentials are correct (from LangFuse UI)
- Ensure LangFuse container is running: `docker ps | grep langfuse`
- Check container logs: `make logs-chat` and `make logs-langfuse`

**2. LangFuse not accessible**
```bash
# Check LangFuse container status
docker ps | grep langfuse

# Check LangFuse logs
make logs-langfuse

# Restart LangFuse
docker compose restart langfuse
```

**3. Authentication errors**
```bash
# Check LangFuse configuration in chat container
docker exec wai-chat env | grep LANGFUSE

# Verify keys match LangFuse UI
# Go to http://YOUR_HOST:3000 → Settings → API Keys
```

**4. Traces incomplete**
- Ensure timeout is sufficient (default: 300s)
- Check for errors in agent execution

### Enable Debug Logging

Add to `.env`:
```env
LOG_LEVEL=DEBUG
```

Restart container:
```bash
docker compose restart chat
```

## Advanced Configuration

### Custom Trace Names

Modify in `bee_agents/chat_api.py`:

```python
agent_run = agent_run.observe(langfuse_observer.observe(
    name=f"custom_trace_name_{username}",
    user_id=username,
    session_id=session_id,
    metadata={
        "custom_field": "value"
    }
))
```

### Add Tags

```python
metadata={
    "scholarship": selected_scholarship,
    "role": token_data["role"],
    "tags": ["production", "high-priority"]
}
```

### Track Specific Events

```python
# In your agent code
langfuse_observer.event(
    name="custom_event",
    metadata={"key": "value"}
)
```

## Cost Tracking

LangFuse automatically tracks:
- Token usage per request
- Estimated costs (based on model pricing)
- Cost per user/session
- Daily/monthly aggregates

View in LangFuse Dashboard → Metrics → Costs

## Performance Optimization

### Identify Slow Requests

1. Go to Traces tab
2. Sort by duration
3. Analyze slow traces:
   - Which tools are slow?
   - Is the LLM taking too long?
   - Are there unnecessary retries?

### Monitor Token Usage

1. Go to Metrics tab
2. View token usage trends
3. Identify:
   - Queries with high token usage
   - Opportunities to optimize prompts
   - Users with excessive usage

## Privacy Considerations

### PII in Traces

LangFuse traces may contain:
- User queries (potentially with PII)
- Scholarship applicant data
- User authentication info

**Recommendations:**
1. Use LangFuse's PII redaction features
2. Set appropriate data retention policies
3. Restrict access to LangFuse dashboard
4. Consider self-hosting for sensitive data

### Disable for Specific Users

Modify `bee_agents/chat_api.py`:

```python
# Skip observability for certain roles
if token_data["role"] != "admin" and langfuse_observer:
    agent_run = agent_run.observe(langfuse_observer.observe(...))
```

## Troubleshooting

### Check LangFuse Status

```bash
# Check if LangFuse is running
docker ps | grep langfuse

# View LangFuse logs
make logs-langfuse

# View chat container logs
make logs-chat

# Look for LangFuse initialization
# Should see: "LangFuse observability initialized: http://langfuse:3000"
```

### Test Connection

```bash
# Test LangFuse API health
curl http://localhost:3000/api/public/health

# Test from chat container
docker exec wai-chat curl http://langfuse:3000/api/public/health

# Test Python connection
docker exec wai-chat python -c "
from langfuse import Langfuse
import os
lf = Langfuse(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
    host=os.getenv('LANGFUSE_HOST')
)
print('LangFuse connection successful!')
"
```

### Disable Observability

Set in `.env`:
```env
LANGFUSE_ENABLED=false
```

Restart:
```bash
docker compose restart chat
```

## Docker Services

### LangFuse Architecture

```
┌─────────────────────────────────────────┐
│         PostgreSQL (langfuse-db)        │
│         Port: 5432 (internal)           │
│         Volume: langfuse-db-data        │
└─────────────────────────────────────────┘
              ▲
              │
┌─────────────────────────────────────────┐
│         LangFuse (langfuse)             │
│         Port: 3000 (external)           │
│         Web UI + API                    │
└─────────────────────────────────────────┘
              ▲
              │ http://langfuse:3000
              │
┌─────────────────────────────────────────┐
│         Chat Frontend (wai-chat)        │
│         Port: 8100                      │
│         Sends traces to LangFuse        │
└─────────────────────────────────────────┘
```

### Backup LangFuse Data

```bash
# Backup PostgreSQL database
docker exec langfuse-db pg_dump -U langfuse langfuse > langfuse-backup.sql

# Restore from backup
cat langfuse-backup.sql | docker exec -i langfuse-db psql -U langfuse langfuse
```

### Reset LangFuse

```bash
# Stop and remove containers
docker compose down

# Remove database volume (WARNING: deletes all data)
docker volume rm wai-bee_langfuse-db-data

# Restart
docker compose up -d
```

## Resources

- **LangFuse Documentation**: https://langfuse.com/docs
- **LangFuse Self-Hosting**: https://langfuse.com/docs/deployment/self-host
- **BeeAI Observability**: https://framework.beeai.dev/modules/observability
- **LangFuse Python SDK**: https://langfuse.com/docs/sdk/python

## Support

For issues with:
- **LangFuse setup**: Check LangFuse documentation
- **BeeAI integration**: Check BeeAI framework docs
- **WAI system**: Check container logs and this documentation

---

Made with Bob 🤖