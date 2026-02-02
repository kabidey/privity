"""
Research Reports Router
Handles research report uploads, listing, and AI-powered stock research
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import os
import aiofiles

from database import db
from routers.auth import get_current_user
from config import is_pe_level
from services.file_storage import upload_file_to_gridfs, get_file_url

router = APIRouter(prefix="/research", tags=["Research"])

# Upload directory (for backward compatibility)
RESEARCH_UPLOADS_DIR = "/app/uploads/research"
os.makedirs(RESEARCH_UPLOADS_DIR, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class ResearchReportCreate(BaseModel):
    stock_id: str
    title: str
    description: Optional[str] = None
    report_type: str = "general"  # general, quarterly, annual, analysis, recommendation


class ResearchReportResponse(BaseModel):
    id: str
    stock_id: str
    stock_symbol: Optional[str] = None
    stock_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    report_type: str
    file_url: str
    file_name: str
    file_size: int
    uploaded_by: str
    uploaded_by_name: str
    created_at: str


# ============== Upload Research Report ==============
@router.post("/reports")
async def upload_research_report(
    stock_id: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    report_type: str = Form("general"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a research report for a stock (PE Desk/Manager only)"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can upload research reports")
    
    # Validate stock exists
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "symbol": 1, "name": 1})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
    
    # Generate unique filename
    report_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{stock['symbol']}_{timestamp}_{report_id[:8]}{file_ext}"
    
    # Upload to GridFS for persistent storage
    file_id = await upload_file_to_gridfs(
        content,
        safe_filename,
        file.content_type or "application/octet-stream",
        {
            "category": "research_reports",
            "entity_id": stock_id,
            "report_id": report_id,
            "stock_symbol": stock.get("symbol"),
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name")
        }
    )
    
    # Also save locally for backward compatibility
    file_path = os.path.join(RESEARCH_UPLOADS_DIR, safe_filename)
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
    except Exception as e:
        print(f"Warning: Local file save failed: {e}")
    
    # Create report record with GridFS file_id
    report = {
        "id": report_id,
        "stock_id": stock_id,
        "stock_symbol": stock.get("symbol"),
        "stock_name": stock.get("name"),
        "title": title,
        "description": description,
        "report_type": report_type,
        "file_id": file_id,  # GridFS file ID for persistent access
        "file_url": get_file_url(file_id),  # GridFS URL
        "file_name": file.filename,
        "file_size": file_size,
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.research_reports.insert_one(report)
    
    # Log audit
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "RESEARCH_REPORT_UPLOADED",
        "entity_type": "research_report",
        "entity_id": report_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": user_role,
        "details": {
            "stock_symbol": stock.get("symbol"),
            "title": title,
            "file_name": file.filename
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Research report uploaded successfully",
        "report": {k: v for k, v in report.items() if k != "_id"}
    }


# ============== List Research Reports ==============
@router.get("/reports")
async def list_research_reports(
    stock_id: Optional[str] = None,
    report_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List all research reports (accessible to all users)"""
    query = {}
    
    if stock_id:
        query["stock_id"] = stock_id
    if report_type:
        query["report_type"] = report_type
    
    reports = await db.research_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    return reports


# ============== Get Reports by Stock ==============
@router.get("/reports/stock/{stock_id}")
async def get_stock_reports(
    stock_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all research reports for a specific stock"""
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    reports = await db.research_reports.find(
        {"stock_id": stock_id}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "stock": stock,
        "reports": reports,
        "total_reports": len(reports)
    }


# ============== Delete Research Report ==============
@router.delete("/reports/{report_id}")
async def delete_research_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a research report (PE Desk/Manager only)"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can delete research reports")
    
    report = await db.research_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Delete file
    file_path = f"/app{report['file_url']}"
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete record
    await db.research_reports.delete_one({"id": report_id})
    
    # Log audit
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "RESEARCH_REPORT_DELETED",
        "entity_type": "research_report",
        "entity_id": report_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": user_role,
        "details": {
            "title": report.get("title"),
            "stock_symbol": report.get("stock_symbol")
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Research report deleted successfully"}


# ============== AI Stock Research ==============
@router.post("/ai-research")
async def ai_stock_research(
    query: str = Form(...),
    stock_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """AI-powered stock research assistant"""
    from emergentintegrations.llm.chat import LlmChat
    
    # Get stock context if provided
    stock_context = ""
    if stock_id:
        stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
        if stock:
            stock_context = f"""
Stock Information:
- Symbol: {stock.get('symbol')}
- Name: {stock.get('name')}
- Sector: {stock.get('sector', 'N/A')}
- Current Price: ₹{stock.get('current_price', 'N/A')}
- Face Value: ₹{stock.get('face_value', 'N/A')}
- Lot Size: {stock.get('lot_size', 'N/A')}
- ISIN: {stock.get('isin', 'N/A')}
"""
    
    # Build system prompt
    system_prompt = f"""You are a professional stock research assistant for PRIVITY, a private equity share booking system. 
Your role is to provide helpful, accurate, and professional analysis about stocks and investments.

Guidelines:
- Provide factual information about stocks, markets, and investment concepts
- When discussing specific stocks, use available data and general market knowledge
- Always include appropriate disclaimers about investment risks
- Be concise but thorough in your analysis
- If you don't have specific information, say so clearly
- Focus on fundamental analysis, market trends, and investment considerations

{stock_context}

Remember: This is for informational purposes only and should not be considered as financial advice."""

    try:
        from emergentintegrations.llm.chat import UserMessage
        
        # Generate unique session ID for this query
        session_id = f"research_{current_user['id']}_{uuid.uuid4().hex[:8]}"
        
        llm = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=session_id,
            system_message=system_prompt
        )
        
        msg = UserMessage(text=query)
        response = await llm.send_message(msg)
        
        # Log the research query
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "AI_RESEARCH_QUERY",
            "entity_type": "ai_research",
            "entity_id": stock_id or "general",
            "user_id": current_user["id"],
            "user_name": current_user["name"],
            "user_role": current_user.get("role", 5),
            "details": {
                "query": query[:200],  # Truncate for storage
                "stock_id": stock_id
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "response": response,
            "stock_id": stock_id,
            "disclaimer": "This information is for educational purposes only and should not be considered as financial advice. Please consult a qualified financial advisor before making investment decisions."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI research failed: {str(e)}")


# ============== Get Research Stats ==============
@router.get("/stats")
async def get_research_stats(current_user: dict = Depends(get_current_user)):
    """Get research section statistics"""
    total_reports = await db.research_reports.count_documents({})
    
    # Get reports by type
    pipeline = [
        {"$group": {"_id": "$report_type", "count": {"$sum": 1}}}
    ]
    by_type = await db.research_reports.aggregate(pipeline).to_list(100)
    type_counts = {item["_id"]: item["count"] for item in by_type}
    
    # Get stocks with most reports
    pipeline = [
        {"$group": {"_id": "$stock_symbol", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_stocks = await db.research_reports.aggregate(pipeline).to_list(5)
    
    # Get recent uploads
    recent = await db.research_reports.find(
        {}, {"_id": 0, "id": 1, "title": 1, "stock_symbol": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    return {
        "total_reports": total_reports,
        "by_type": type_counts,
        "top_stocks": top_stocks,
        "recent_uploads": recent
    }
