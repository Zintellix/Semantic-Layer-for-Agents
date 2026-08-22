from fastapi import Request, HTTPException
from typing import List

# Mock Authentication Layer for Enterprise RBAC
# In a real environment, this would validate a JWT token and extract roles.

MOCK_TOKENS = {
    "admin-token": ["admin"],
    "sales-rep-token": ["sales_rep"],
    "viewer-token": ["viewer"]
}

async def get_user_roles(request: Request) -> List[str]:
    """
    Extracts the user's role from the Authorization header.
    Defaults to ['guest'] if no token is provided.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # In strict mode, we'd raise HTTPException(status_code=401, detail="Unauthorized")
        # For ease of testing in this POC without headers, we default to 'admin'
        # if they bypass it, but let's actually default to 'guest' so we can see RBAC work.
        return ["guest"]
        
    token = auth_header.split(" ")[1]
    roles = MOCK_TOKENS.get(token)
    
    if not roles:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
        
    return roles
