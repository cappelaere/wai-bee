# Operation ID Guidelines for LLM Compatibility

## Problem

Some API endpoints have operation IDs exceeding 34 characters, which can cause issues with LLM token limits and API documentation tools.

## Current Issues

### Operation IDs > 34 Characters

| Operation ID | Length | Endpoint | Recommendation |
|--------------|--------|----------|----------------|
| `regenerate_agent_criteria_with_llm_admin__scholarship__criteria__agent_name__regenerate_post` | 92 | POST /admin/{scholarship}/criteria/{agent_name}/regenerate | `regen_criteria` |
| `download_text_attachment_attachments_text__scholarship___wai_number___filename__get` | 83 | GET /attachments/text/{scholarship}/{wai_number}/{filename} | `get_text_attachment` |
| `download_attachment_attachments__scholarship___wai_number___filename__get` | 73 | GET /attachments/{scholarship}/{wai_number}/{filename} | `get_attachment` |
| `update_agent_criteria_admin__scholarship__criteria__agent_name__put` | 67 | PUT /admin/{scholarship}/criteria/{agent_name} | `update_criteria` |
| `get_single_recommendation_analysis_recommendation__rec_number__get` | 66 | GET /recommendation/{rec_number} | `get_recommendation` |
| `get_agent_criteria_admin__scholarship__criteria__agent_name__get` | 64 | GET /admin/{scholarship}/criteria/{agent_name} | `get_criteria` |
| `update_scholarship_weights_admin__scholarship__weights_put` | 58 | PUT /admin/{scholarship}/weights | `update_weights` |
| `get_criteria_file_criteria__scholarship___filename__get` | 55 | GET /criteria/{scholarship}/{filename} | `get_criteria_file` |
| `get_scholarship_weights_admin__scholarship__weights_get` | 55 | GET /admin/{scholarship}/weights | `get_weights` |
| `get_single_essay_analysis_essay__essay_number__get` | 50 | GET /essay/{essay_number} | `get_essay` |
| `get_recommendation_analysis_recommendation_get` | 46 | GET /recommendation | `list_recommendations` |
| `get_criteria_criteria__criteria_type__get` | 41 | GET /criteria/{criteria_type} | `get_criteria_by_type` |
| `get_application_analysis_application_get` | 40 | GET /application | `get_application` |
| `get_agent_config_agents__agent_name__get` | 40 | GET /agents/{agent_name} | `get_agent` |

## Solution: Use `operation_id` Parameter

FastAPI allows you to explicitly set operation IDs using the `operation_id` parameter in route decorators.

### Example Fix

**Before (auto-generated, 92 chars):**
```python
@router.post("/admin/{scholarship}/criteria/{agent_name}/regenerate")
async def regenerate_agent_criteria_with_llm(...):
    ...
```

**After (explicit, 14 chars):**
```python
@router.post(
    "/admin/{scholarship}/criteria/{agent_name}/regenerate",
    operation_id="regen_criteria"
)
async def regenerate_agent_criteria_with_llm(...):
    ...
```

## Recommended Operation IDs (≤34 chars)

### Admin Endpoints
```python
# bee_agents/api_routers/admin.py
@router.get("/admin/{scholarship}/weights", operation_id="get_weights")
@router.put("/admin/{scholarship}/weights", operation_id="update_weights")
@router.get("/admin/{scholarship}/criteria/{agent_name}", operation_id="get_criteria")
@router.put("/admin/{scholarship}/criteria/{agent_name}", operation_id="update_criteria")
@router.post("/admin/{scholarship}/criteria/{agent_name}/regenerate", operation_id="regen_criteria")
```

### Analysis Endpoints
```python
# bee_agents/api_routers/analysis.py
@router.get("/application", operation_id="get_application")
@router.get("/academic/{wai_number}", operation_id="get_academic")
@router.get("/essay/{essay_number}", operation_id="get_essay")
@router.get("/recommendation/{rec_number}", operation_id="get_recommendation")
@router.get("/recommendation", operation_id="list_recommendations")
```

### Criteria Endpoints
```python
# bee_agents/api_routers/criteria.py
@router.get("/criteria", operation_id="list_criteria")
@router.get("/criteria/{criteria_type}", operation_id="get_criteria_by_type")
@router.get("/criteria/{scholarship}/{filename}", operation_id="get_criteria_file")
```

### Attachment Endpoints
```python
# bee_agents/api_routers/attachments.py (if exists)
@router.get("/attachments/{scholarship}/{wai_number}/{filename}", operation_id="get_attachment")
@router.get("/attachments/text/{scholarship}/{wai_number}/{filename}", operation_id="get_text_attachment")
```

### Scores Endpoints
```python
# bee_agents/api_routers/scores.py
@router.get("/top_scores", operation_id="get_top_scores")
@router.get("/score", operation_id="get_score")
@router.get("/statistics", operation_id="get_statistics")
```

### Health Endpoints
```python
# bee_agents/api_routers/health.py
@router.get("/", operation_id="root")
@router.get("/health", operation_id="health_check")
```

## Implementation Steps

1. **Update each router file** with explicit `operation_id` parameters
2. **Keep IDs ≤34 characters** for LLM compatibility
3. **Use clear, descriptive names** (e.g., `get_`, `list_`, `update_`, `delete_`)
4. **Avoid redundancy** (don't repeat the path in the ID)
5. **Test the changes** - run tests to ensure no breaking changes

## Verification

After implementing, verify operation IDs:

```bash
python -c "from bee_agents.api import app; schema = app.openapi(); ops = [(op.get('operationId'), len(op.get('operationId', ''))) for methods in schema['paths'].values() for op in methods.values() if 'operationId' in op]; long_ops = [(id, length) for id, length in ops if length > 34]; print(f'Operation IDs > 34 chars: {len(long_ops)}'); [print(f'  {id} ({length} chars)') for id, length in long_ops]"
```

Expected output after fix:
```
Operation IDs > 34 chars: 0
```

## Benefits

1. **LLM Compatibility** - Shorter IDs fit within token limits
2. **Better Documentation** - Clearer, more readable API docs
3. **Easier Integration** - Simpler for API clients to use
4. **Consistent Naming** - Standardized operation ID patterns

## Naming Conventions

- **GET (single):** `get_{resource}` (e.g., `get_score`, `get_agent`)
- **GET (list):** `list_{resources}` (e.g., `list_criteria`, `list_attachments`)
- **POST:** `create_{resource}` or `{action}_{resource}` (e.g., `regen_criteria`)
- **PUT:** `update_{resource}` (e.g., `update_weights`)
- **DELETE:** `delete_{resource}` (e.g., `delete_agent`)

## Priority

**High** - Should be implemented before production deployment for optimal LLM integration.

---

*Created: 2025-12-16*
*Author: Code Review Process*