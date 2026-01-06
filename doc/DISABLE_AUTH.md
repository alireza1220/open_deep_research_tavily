# How to Disable Authentication

If you don't want to set up Supabase authentication, you have a few options:

## Option 1: Remove Auth from langgraph.json (Simplest)

Edit `langgraph.json` and remove the `auth` section:

```json
{
    "dockerfile_lines": [],
    "graphs": {
      "Deep Researcher": "./src/open_deep_research/deep_researcher.py:deep_researcher"
    },
    "python_version": "3.11",
    "env": "./.env",
    "dependencies": [
      "."
    ]
}
```

**Note**: Remove the entire `"auth": { "path": "./src/security/auth.py:auth" }` section.

After this change, restart the LangGraph server. All API endpoints will be accessible without authentication.

## Option 2: Make Auth Optional (Modify auth.py)

If you want to keep the auth file but make it optional (allow requests without Supabase), modify `src/security/auth.py`:

```python
@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Check if the user's JWT token is valid using Supabase."""
    
    # If Supabase is not configured, allow all requests (no auth required)
    if not supabase:
        # Return a default user identity for unauthenticated requests
        return {
            "identity": "anonymous",
        }
    
    # If Supabase is configured, require authentication
    if not authorization:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Authorization header missing"
        )
    
    # ... rest of the authentication logic
```

This way:
- If `SUPABASE_URL` and `SUPABASE_KEY` are not set → All requests allowed (no auth)
- If Supabase is configured → Authentication required

## Option 3: Use LangGraph Studio UI (No Code Changes)

You can always use the LangGraph Studio UI which bypasses authentication:

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

The Studio UI uses `StudioUser` which bypasses all authentication checks.

## Current Behavior Without Supabase

**Without Supabase configured:**
- ❌ Direct API calls fail (401 or 500 errors)
- ✅ LangGraph Studio UI works (no auth needed)

**After disabling auth (Option 1):**
- ✅ Direct API calls work (no auth required)
- ✅ LangGraph Studio UI works (no auth needed)

## Security Considerations

⚠️ **Warning**: Disabling authentication means:
- Anyone with access to your API can use it
- No user isolation (all users share the same data)
- No access control

**Recommended for:**
- Local development
- Testing
- Internal networks only
- Single-user deployments

**Not recommended for:**
- Production deployments
- Public APIs
- Multi-user scenarios
- Any environment where security matters

