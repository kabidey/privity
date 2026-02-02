"""
Hierarchy Service
Manages organizational hierarchy for users (Employee → Manager → Zonal Head → Regional Manager → Business Head)
"""
from typing import List, Optional, Set
from database import db

# Hierarchy Levels
HIERARCHY_LEVELS = {
    1: "Employee",
    2: "Manager", 
    3: "Zonal Head",
    4: "Regional Manager",
    5: "Business Head"
}

async def get_user_hierarchy_level(user_id: str) -> int:
    """Get hierarchy level for a user (default to Employee=1)"""
    user = await db.users.find_one({"id": user_id}, {"hierarchy_level": 1})
    return user.get("hierarchy_level", 1) if user else 1


async def get_reports_to(user_id: str) -> Optional[str]:
    """Get the manager (reports_to) for a user"""
    user = await db.users.find_one({"id": user_id}, {"reports_to": 1})
    return user.get("reports_to") if user else None


async def get_direct_reports(manager_id: str) -> List[str]:
    """Get list of user IDs that directly report to this manager"""
    users = await db.users.find(
        {"reports_to": manager_id},
        {"id": 1}
    ).to_list(1000)
    return [u["id"] for u in users]


async def get_all_subordinates(manager_id: str, visited: Set[str] = None) -> List[str]:
    """
    Recursively get all subordinates (direct and indirect) under a manager.
    Returns list of user IDs including all levels below.
    """
    if visited is None:
        visited = set()
    
    # Prevent infinite loops
    if manager_id in visited:
        return []
    visited.add(manager_id)
    
    subordinates = []
    direct_reports = await get_direct_reports(manager_id)
    
    for report_id in direct_reports:
        subordinates.append(report_id)
        # Recursively get subordinates of this report
        sub_subordinates = await get_all_subordinates(report_id, visited)
        subordinates.extend(sub_subordinates)
    
    return subordinates


async def get_team_user_ids(user_id: str, include_self: bool = True) -> List[str]:
    """
    Get all user IDs in a user's team (self + all subordinates).
    For Employees, returns only their own ID.
    For Managers+, returns self + all people under them.
    """
    user = await db.users.find_one({"id": user_id}, {"hierarchy_level": 1})
    hierarchy_level = user.get("hierarchy_level", 1) if user else 1
    
    # Employees only see themselves
    if hierarchy_level <= 1:
        return [user_id] if include_self else []
    
    # Managers and above see their team
    subordinates = await get_all_subordinates(user_id)
    
    if include_self:
        return [user_id] + subordinates
    return subordinates


async def can_view_user_data(viewer_id: str, target_user_id: str) -> bool:
    """
    Check if viewer can view target user's data.
    - Users can always view their own data
    - Managers+ can view data of their subordinates
    - PE Level can view everyone
    """
    if viewer_id == target_user_id:
        return True
    
    viewer = await db.users.find_one({"id": viewer_id}, {"role": 1, "hierarchy_level": 1})
    if not viewer:
        return False
    
    # PE Level can view everyone
    if viewer.get("role") in [1, 2]:
        return True
    
    # Check if target is a subordinate
    subordinates = await get_all_subordinates(viewer_id)
    return target_user_id in subordinates


async def can_edit_user_data(editor_id: str, target_user_id: str) -> bool:
    """
    Check if editor can edit target user's data.
    - Users can only edit their own data (not subordinates')
    - PE Level can edit everyone
    """
    if editor_id == target_user_id:
        return True
    
    editor = await db.users.find_one({"id": editor_id}, {"role": 1})
    if not editor:
        return False
    
    # Only PE Level can edit others' data
    return editor.get("role") in [1, 2]


async def get_hierarchy_tree(root_user_id: str = None) -> List[dict]:
    """
    Get the full hierarchy tree starting from root (or all Business Heads if no root).
    Returns nested structure with user info and their reports.
    """
    if root_user_id:
        # Get tree starting from specific user
        user = await db.users.find_one({"id": root_user_id}, {"_id": 0, "password": 0})
        if not user:
            return []
        
        direct_reports = await db.users.find(
            {"reports_to": root_user_id},
            {"_id": 0, "password": 0}
        ).to_list(1000)
        
        user["direct_reports"] = []
        for report in direct_reports:
            report_tree = await get_hierarchy_tree(report["id"])
            if report_tree:
                user["direct_reports"].append(report_tree[0])
            else:
                user["direct_reports"].append(report)
        
        return [user]
    else:
        # Get all users without a manager (top level)
        top_users = await db.users.find(
            {"$or": [{"reports_to": None}, {"reports_to": {"$exists": False}}]},
            {"_id": 0, "password": 0}
        ).to_list(1000)
        
        result = []
        for user in top_users:
            tree = await get_hierarchy_tree(user["id"])
            result.extend(tree)
        
        return result


async def get_manager_chain(user_id: str) -> List[dict]:
    """
    Get the chain of managers above a user (up to Business Head).
    Returns list from immediate manager to top.
    """
    chain = []
    current_id = user_id
    visited = set()
    
    while current_id and current_id not in visited:
        visited.add(current_id)
        user = await db.users.find_one({"id": current_id}, {"_id": 0, "password": 0})
        if not user:
            break
        
        reports_to = user.get("reports_to")
        if reports_to:
            manager = await db.users.find_one({"id": reports_to}, {"_id": 0, "password": 0})
            if manager:
                chain.append(manager)
            current_id = reports_to
        else:
            break
    
    return chain


async def update_user_hierarchy(user_id: str, reports_to: Optional[str], hierarchy_level: int) -> bool:
    """
    Update a user's hierarchy settings.
    Only PE Level should call this.
    """
    # Validate hierarchy_level
    if hierarchy_level not in HIERARCHY_LEVELS:
        return False
    
    # Prevent circular references
    if reports_to:
        # Check if reports_to user exists
        manager = await db.users.find_one({"id": reports_to})
        if not manager:
            return False
        
        # Check for circular reference
        chain = await get_manager_chain(reports_to)
        if any(m["id"] == user_id for m in chain):
            return False
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "reports_to": reports_to,
            "hierarchy_level": hierarchy_level
        }}
    )
    
    return result.modified_count > 0


async def get_unmapped_clients_query() -> dict:
    """
    Get MongoDB query for unmapped clients (clients not assigned to any employee).
    These should only be visible to PE Desk/Manager.
    """
    return {
        "$or": [
            {"assigned_to": None},
            {"assigned_to": {"$exists": False}},
            {"assigned_to": ""}
        ]
    }


async def get_team_clients_query(user_id: str) -> dict:
    """
    Get MongoDB query for clients visible to a user based on hierarchy.
    - Employee: Only clients they created or are assigned to them
    - Manager+: Clients of self + all subordinates
    - PE Level: All clients
    """
    user = await db.users.find_one({"id": user_id}, {"role": 1, "hierarchy_level": 1})
    if not user:
        return {"created_by": user_id}
    
    # PE Level sees all
    if user.get("role") in [1, 2]:
        return {}
    
    hierarchy_level = user.get("hierarchy_level", 1)
    
    # Employee (level 1): Only their own clients
    if hierarchy_level <= 1:
        return {
            "$or": [
                {"created_by": user_id},
                {"assigned_to": user_id}
            ]
        }
    
    # Manager+ (level 2+): Team clients
    team_ids = await get_team_user_ids(user_id, include_self=True)
    return {
        "$or": [
            {"created_by": {"$in": team_ids}},
            {"assigned_to": {"$in": team_ids}}
        ]
    }


async def get_team_bookings_query(user_id: str) -> dict:
    """
    Get MongoDB query for bookings visible to a user based on hierarchy.
    - Employee: Only bookings they created
    - Manager+: Bookings of self + all subordinates
    - PE Level: All bookings
    """
    user = await db.users.find_one({"id": user_id}, {"role": 1, "hierarchy_level": 1})
    if not user:
        return {"created_by": user_id}
    
    # PE Level sees all
    if user.get("role") in [1, 2]:
        return {}
    
    hierarchy_level = user.get("hierarchy_level", 1)
    
    # Employee (level 1): Only their own bookings
    if hierarchy_level <= 1:
        return {"created_by": user_id}
    
    # Manager+ (level 2+): Team bookings
    team_ids = await get_team_user_ids(user_id, include_self=True)
    return {"created_by": {"$in": team_ids}}
