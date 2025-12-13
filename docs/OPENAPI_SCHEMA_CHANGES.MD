# OpenAPI Schema Changes for Multi-Tenancy

## Overview

To support multi-tenancy, the OpenAPI schema must be updated to include a `scholarship` parameter in all endpoints that query scholarship-specific data. This allows the BeeAI agent to properly pass scholarship context when making API calls.

## Required Changes

### Current Schema Issues

The current OpenAPI schema (`bee_agents/openapi.json`) does NOT include scholarship parameters, meaning:
- ❌ Agent cannot specify which scholarship to query
- ❌ API returns data from all scholarships (no filtering)
- ❌ No way to enforce data isolation

### Required Updates

**Every endpoint that returns scholarship-specific data must add a `scholarship` parameter.**

## Endpoint-by-Endpoint Changes

### 1. GET /scholarship

**Current:**
```json
{
  "paths": {
    "/scholarship": {
      "get": {
        "summary": "Get Scholarship Info",
        "description": "Get scholarship information and details",
        "operationId": "get_scholarship_info_scholarship_get",
        "responses": {
          "200": {
            "description": "Successful Response"
          }
        }
      }
    }
  }
}
```

**Updated (Add scholarship parameter):**
```json
{
  "paths": {
    "/scholarship": {
      "get": {
        "summary": "Get Scholarship Info",
        "description": "Get scholarship information and details for a specific scholarship",
        "operationId": "get_scholarship_info_scholarship_get",
        "parameters": [
          {
            "name": "scholarship",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "enum": ["Delaney_Wings", "Evans_Wings"],
              "description": "Scholarship identifier"
            },
            "description": "The scholarship to retrieve information for"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "scholarship_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"}
                  }
                }
              }
            }
          },
          "403": {
            "description": "Access denied to this scholarship"
          },
          "404": {
            "description": "Scholarship not found"
          }
        }
      }
    }
  }
}
```

### 2. GET /top_scores

**Current:**
```json
{
  "paths": {
    "/top_scores": {
      "get": {
        "summary": "Get Top Scores",
        "description": "Get top scoring applications",
        "operationId": "get_top_scores_top_scores_get",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 100,
              "minimum": 1,
              "default": 10
            }
          }
        ]
      }
    }
  }
}
```

**Updated (Add scholarship parameter):**
```json
{
  "paths": {
    "/top_scores": {
      "get": {
        "summary": "Get Top Scores",
        "description": "Get top scoring applications for a specific scholarship",
        "operationId": "get_top_scores_top_scores_get",
        "parameters": [
          {
            "name": "scholarship",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "enum": ["Delaney_Wings", "Evans_Wings"],
              "description": "Scholarship identifier"
            },
            "description": "The scholarship to query top scores for"
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 100,
              "minimum": 1,
              "default": 10
            },
            "description": "Number of top scores to return"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "scholarship": {"type": "string"},
                    "applications": {
                      "type": "array",
                      "items": {"type": "object"}
                    }
                  }
                }
              }
            }
          },
          "403": {
            "description": "Access denied to this scholarship"
          }
        }
      }
    }
  }
}
```

### 3. GET /applications (if exists)

**Add scholarship parameter:**
```json
{
  "paths": {
    "/applications": {
      "get": {
        "summary": "Get Applications",
        "description": "Get applications for a specific scholarship",
        "operationId": "get_applications_applications_get",
        "parameters": [
          {
            "name": "scholarship",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "enum": ["Delaney_Wings", "Evans_Wings"]
            },
            "description": "Scholarship identifier"
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 100
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 0
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response"
          },
          "403": {
            "description": "Access denied"
          }
        }
      }
    }
  }
}
```

### 4. GET /application/{application_id}

**Add scholarship parameter:**
```json
{
  "paths": {
    "/application/{application_id}": {
      "get": {
        "summary": "Get Application Details",
        "description": "Get details for a specific application",
        "operationId": "get_application_application__application_id__get",
        "parameters": [
          {
            "name": "application_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "scholarship",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "enum": ["Delaney_Wings", "Evans_Wings"]
            },
            "description": "Scholarship the application belongs to"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response"
          },
          "403": {
            "description": "Access denied"
          },
          "404": {
            "description": "Application not found"
          }
        }
      }
    }
  }
}
```

## Complete Updated Schema Template

### Scholarship Parameter Definition (Reusable)

```json
{
  "components": {
    "parameters": {
      "ScholarshipParam": {
        "name": "scholarship",
        "in": "query",
        "required": true,
        "schema": {
          "type": "string",
          "enum": ["Delaney_Wings", "Evans_Wings"],
          "description": "Scholarship identifier"
        },
        "description": "The scholarship to query data for. Users can only access scholarships they are assigned to."
      }
    },
    "schemas": {
      "Scholarship": {
        "type": "string",
        "enum": ["Delaney_Wings", "Evans_Wings"],
        "description": "Available scholarship identifiers"
      }
    }
  }
}
```

### Using the Reusable Parameter

```json
{
  "paths": {
    "/top_scores": {
      "get": {
        "parameters": [
          {
            "$ref": "#/components/parameters/ScholarshipParam"
          },
          {
            "name": "limit",
            "in": "query",
            "schema": {"type": "integer", "default": 10}
          }
        ]
      }
    }
  }
}
```

## API Server Implementation Changes

### Before (No Scholarship Filtering)

```python
@app.get("/top_scores")
async def get_top_scores(limit: int = 10):
    """Returns top scores from ALL scholarships - WRONG!"""
    all_applications = []
    
    # Loads from all scholarship folders
    for folder in ["data/Delaney_Wings", "data/Evans_Wings"]:
        apps = load_applications(folder)
        all_applications.extend(apps)
    
    # Returns mixed data - security issue!
    return sorted(all_applications, key=lambda x: x['score'])[:limit]
```

### After (With Scholarship Filtering)

```python
@app.get("/top_scores")
async def get_top_scores(
    scholarship: str = Query(
        ...,
        description="Scholarship identifier",
        regex="^(Delaney_Wings|Evans_Wings)$"
    ),
    limit: int = Query(10, ge=1, le=100)
):
    """Returns top scores for SPECIFIC scholarship - CORRECT!"""
    
    # Validate scholarship
    if scholarship not in ["Delaney_Wings", "Evans_Wings"]:
        raise HTTPException(404, f"Scholarship not found: {scholarship}")
    
    # Load from specific scholarship folder only
    data_folder = f"data/{scholarship}"
    applications = load_applications(data_folder)
    
    # Return filtered data
    return {
        "scholarship": scholarship,
        "applications": sorted(applications, key=lambda x: x['score'])[:limit]
    }
```

## Dynamic Scholarship Enum

For maintainability, generate the enum dynamically:

```python
# In API server startup
def get_available_scholarships() -> list[str]:
    """Get list of available scholarships from config"""
    config = load_user_config()
    return [
        key for key, value in config["scholarships"].items()
        if value.get("enabled", True)
    ]

# Update OpenAPI schema dynamically
def update_openapi_schema():
    """Update OpenAPI schema with current scholarships"""
    scholarships = get_available_scholarships()
    
    # Update the enum in the schema
    for path in app.openapi()["paths"].values():
        for operation in path.values():
            if "parameters" in operation:
                for param in operation["parameters"]:
                    if param.get("name") == "scholarship":
                        param["schema"]["enum"] = scholarships

# Call on startup
@app.on_event("startup")
async def startup_event():
    update_openapi_schema()
```

## Testing the Changes

### Test 1: Verify Parameter is Required

```bash
# Should fail - no scholarship parameter
curl http://localhost:8200/top_scores
# Expected: 422 Unprocessable Entity

# Should succeed
curl "http://localhost:8200/top_scores?scholarship=Delaney_Wings"
# Expected: 200 OK with Delaney data
```

### Test 2: Verify Enum Validation

```bash
# Should fail - invalid scholarship
curl "http://localhost:8200/top_scores?scholarship=Invalid_Scholarship"
# Expected: 422 Unprocessable Entity or 404 Not Found

# Should succeed
curl "http://localhost:8200/top_scores?scholarship=Evans_Wings"
# Expected: 200 OK with Evans data
```

### Test 3: Agent Tool Usage

```python
# Test that BeeAI agent can use the updated schema
from beeai_framework.tools.openapi import OpenAPITool

# Load updated schema
with open("bee_agents/openapi.json") as f:
    schema = json.load(f)

tools = OpenAPITool.from_schema(schema)

# Agent should now be able to pass scholarship parameter
result = await tools['get_top_scores'].execute(
    scholarship="Delaney_Wings",
    limit=10
)
```

## Migration Checklist

- [ ] Update `bee_agents/openapi.json` with scholarship parameters
- [ ] Update API server endpoints to require scholarship parameter
- [ ] Add scholarship validation in API server
- [ ] Update API server to filter data by scholarship
- [ ] Test each endpoint with scholarship parameter
- [ ] Verify agent can use updated schema
- [ ] Update API documentation
- [ ] Test with different user roles
- [ ] Verify data isolation between scholarships

## Example: Complete Updated Endpoint

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Scholarship Analysis API",
    "version": "2.0.0",
    "description": "Multi-tenant API for scholarship application analysis"
  },
  "paths": {
    "/top_scores": {
      "get": {
        "tags": ["Scores"],
        "summary": "Get Top Scores",
        "description": "Get top scoring applications for a specific scholarship. Users can only access scholarships they are assigned to.",
        "operationId": "get_top_scores_top_scores_get",
        "parameters": [
          {
            "name": "scholarship",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "enum": ["Delaney_Wings", "Evans_Wings"],
              "description": "Scholarship identifier"
            },
            "description": "The scholarship to query top scores for",
            "example": "Delaney_Wings"
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 1,
              "maximum": 100,
              "default": 10
            },
            "description": "Number of top scores to return"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "scholarship": {
                      "type": "string",
                      "description": "Scholarship identifier"
                    },
                    "count": {
                      "type": "integer",
                      "description": "Number of applications returned"
                    },
                    "applications": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "application_id": {"type": "string"},
                          "score": {"type": "number"},
                          "applicant_name": {"type": "string"}
                        }
                      }
                    }
                  }
                },
                "example": {
                  "scholarship": "Delaney_Wings",
                  "count": 10,
                  "applications": [
                    {
                      "application_id": "12345",
                      "score": 95.5,
                      "applicant_name": "John Doe"
                    }
                  ]
                }
              }
            }
          },
          "403": {
            "description": "Access denied to this scholarship",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "detail": {"type": "string"}
                  }
                },
                "example": {
                  "detail": "Access denied to Evans_Wings scholarship"
                }
              }
            }
          },
          "404": {
            "description": "Scholarship not found"
          },
          "422": {
            "description": "Validation Error - Invalid scholarship parameter"
          }
        }
      }
    }
  }
}
```

## Summary

**Critical Changes Required:**

1. ✅ Add `scholarship` parameter to ALL endpoints that query scholarship data
2. ✅ Make `scholarship` parameter **required** (not optional)
3. ✅ Use enum to restrict to valid scholarship identifiers
4. ✅ Update API server to validate and use scholarship parameter
5. ✅ Update response schemas to include scholarship identifier
6. ✅ Add proper error responses (403 for access denied, 404 for not found)

**Without these OpenAPI changes:**
- ❌ Agent cannot specify which scholarship to query
- ❌ API returns mixed data from all scholarships
- ❌ No data isolation
- ❌ Multi-tenancy doesn't work

**With these OpenAPI changes:**
- ✅ Agent explicitly passes scholarship in every request
- ✅ API filters data by scholarship
- ✅ Complete data isolation
- ✅ Multi-tenancy works correctly