"""
Demo Mode Data Isolation Utility

This module provides utilities to ensure complete isolation of demo data from live data.
Demo users should ONLY see data marked with is_demo=True.
Live users should NEVER see data marked with is_demo=True.
"""

from fastapi import HTTPException

DEMO_USER_ID = "demo_user_privity"

def is_demo_user(current_user: dict) -> bool:
    """Check if the current user is a demo user"""
    if not current_user:
        return False
    return (
        current_user.get("is_demo", False) or 
        current_user.get("id") == DEMO_USER_ID or
        current_user.get("email") == "demo@privity.com"
    )

def get_demo_filter(current_user: dict) -> dict:
    """
    Get the appropriate MongoDB filter for demo/live data isolation.
    
    - Demo users: Only see is_demo=True data
    - Live users: Only see is_demo != True data (includes missing field)
    """
    if is_demo_user(current_user):
        # Demo user - only show demo data
        return {"is_demo": True}
    else:
        # Live user - exclude demo data
        return {"is_demo": {"$ne": True}}

def add_demo_filter(query: dict, current_user: dict) -> dict:
    """
    Add demo isolation filter to an existing MongoDB query.
    
    Args:
        query: Existing MongoDB query dict
        current_user: Current user dict from authentication
        
    Returns:
        Modified query with demo filter applied
    """
    demo_filter = get_demo_filter(current_user)
    
    # If query already has $and, append to it
    if "$and" in query:
        query["$and"].append(demo_filter)
    else:
        # Merge the demo filter with existing query
        query.update(demo_filter)
    
    return query

def mark_as_demo(data: dict, current_user: dict) -> dict:
    """
    Mark data as demo if created by a demo user.
    
    Args:
        data: Data dict to potentially mark as demo
        current_user: Current user dict
        
    Returns:
        Data dict with is_demo flag if applicable
    """
    if is_demo_user(current_user):
        data["is_demo"] = True
    return data

def validate_demo_access(entity: dict, current_user: dict) -> bool:
    """
    Validate that a user has access to a specific entity.
    
    - Demo users can only access demo entities
    - Live users can only access non-demo entities
    
    Args:
        entity: The entity being accessed
        current_user: Current user dict
        
    Returns:
        True if access is allowed, False otherwise
    """
    entity_is_demo = entity.get("is_demo", False)
    user_is_demo = is_demo_user(current_user)
    
    # Demo users can only access demo data
    if user_is_demo and not entity_is_demo:
        return False
    
    # Live users cannot access demo data
    if not user_is_demo and entity_is_demo:
        return False
    
    return True

def require_demo_access(entity: dict, current_user: dict):
    """
    Raise HTTPException if user doesn't have access to entity.
    """
    if not validate_demo_access(entity, current_user):
        if is_demo_user(current_user):
            raise HTTPException(
                status_code=403, 
                detail="Demo users can only access demo data"
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail="Entity not found"  # Don't reveal demo data exists
            )
