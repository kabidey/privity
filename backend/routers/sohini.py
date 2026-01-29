"""
Sohini AI Assistant Router
AI-powered assistant to help users navigate and understand the Privity app
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

from database import db
from utils.auth import get_current_user

load_dotenv()

router = APIRouter(prefix="/sohini", tags=["AI Assistant"])

# System prompt for Sohini - comprehensive knowledge about Privity
SOHINI_SYSTEM_PROMPT = """You are Sohini, a friendly and knowledgeable AI assistant for the Privity Private Equity System. You are a female assistant with a warm, professional demeanor.

## About Privity
Privity is a comprehensive Share Booking Management System designed for private equity operations. It helps organizations manage:
- Client onboarding and management
- Stock purchases and inventory
- Booking transactions (buying/selling shares)
- Payment tracking and finance
- Referral Partners (RPs) and Business Partners (BPs)
- Revenue tracking and dashboards

## User Roles in Privity
1. **PE Desk (Role 1)** - Super admin with full system access, approvals, user management
2. **PE Manager (Role 2)** - Senior management with most admin capabilities
3. **Zonal Manager (Role 3)** - Regional oversight, team management
4. **Manager (Role 4)** - Team management, client/booking oversight
5. **Employee (Role 5)** - Day-to-day operations, client handling
6. **Client (Role 6)** - External clients viewing their portfolio
7. **Finance (Role 7)** - Payment tracking, financial reports
8. **Business Partner (Role 8)** - External partners with revenue sharing
9. **Partners Desk (Role 9)** - Manages business partners

## Key Features You Can Help With

### Clients & Vendors
- Creating new clients (requires PAN verification, document uploads)
- Client approval workflow (PE Level approves new clients)
- Mapping clients to employees and referral partners
- Vendor management for stock procurement

### Stocks & Inventory
- Adding new stocks with face value and lot size
- Managing stock status (active, delisted, suspended)
- Tracking inventory levels and values
- Recording dividends and corporate actions

### Bookings
- Creating buy/sell bookings for clients
- Understanding booking statuses: open, closed, cancelled
- Approval workflow: pending → approved/rejected
- Loss bookings require special PE Level approval
- Recording payments against bookings

### Finance
- Payment tracking for client bookings
- Vendor payment management
- Refund requests and processing
- Financial reports and exports

### Reports & Dashboards
- Role-specific dashboards (PE, Finance, Employee, Client)
- Revenue dashboards (RP Revenue, Team Revenue)
- Audit trail for tracking all activities
- Analytics and booking reports

### Referral Partners (RPs)
- Creating and managing RPs with revenue share %
- Mapping RPs to employees
- Tracking RP performance and commissions
- Document management for RPs

### Business Partners (BPs)
- OTP-based login system
- Revenue sharing arrangements
- Document uploads and verification

## Navigation Help
- **Dashboard** - Overview of key metrics
- **Clients** - Manage client records
- **Stocks** - Stock master data
- **Bookings** - Transaction management
- **Finance** - Payment tracking
- **Reports** - Various reports and exports
- **Referral Partners** - RP management
- **Audit Trail** - Activity logs (PE Level only)

## How to Respond
1. Be friendly and use "I" when referring to yourself
2. Keep responses concise but helpful
3. If you don't know something specific to the user's data, guide them to the right page
4. Use bullet points for listing features or steps
5. Offer to explain more if the user seems confused
6. Remember you're Sohini - a helpful female AI assistant

## Important Notes
- For technical issues or bugs, suggest contacting PE Desk
- For payment issues, guide users to the Finance section
- For approval delays, suggest checking with PE Level users
- Always be helpful and patient with users
"""


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_sohini(
    chat_message: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """Chat with Sohini AI assistant"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI assistant not configured")
    
    user_id = current_user.get("id")
    user_name = current_user.get("name", "User")
    user_role = current_user.get("role", 6)
    
    # Get or create session
    session_id = chat_message.session_id or str(uuid.uuid4())
    
    # Get chat history for this session
    chat_history = await db.sohini_chats.find_one(
        {"session_id": session_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not chat_history:
        chat_history = {
            "session_id": session_id,
            "user_id": user_id,
            "user_name": user_name,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    # Add user context to the system message
    role_names = {
        1: "PE Desk", 2: "PE Manager", 3: "Zonal Manager", 4: "Manager",
        5: "Employee", 6: "Client", 7: "Finance", 8: "Business Partner", 9: "Partners Desk"
    }
    user_context = f"\n\nCurrent user context:\n- Name: {user_name}\n- Role: {role_names.get(user_role, 'Unknown')}"
    
    try:
        # Initialize LLM chat
        llm_chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=SOHINI_SYSTEM_PROMPT + user_context
        ).with_model("openai", "gpt-4o")
        
        # Build conversation history for context
        for msg in chat_history.get("messages", [])[-10:]:  # Last 10 messages for context
            if msg["role"] == "user":
                await llm_chat.send_message(UserMessage(text=msg["content"]), store_only=True)
            else:
                llm_chat.add_assistant_message(msg["content"])
        
        # Send new message
        user_message = UserMessage(text=chat_message.message)
        response = await llm_chat.send_message(user_message)
        
        # Store the conversation
        chat_history["messages"].append({
            "role": "user",
            "content": chat_message.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        chat_history["messages"].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        chat_history["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Save to database
        await db.sohini_chats.update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": chat_history},
            upsert=True
        )
        
        return ChatResponse(response=response, session_id=session_id)
        
    except Exception as e:
        # Return a friendly error message
        return ChatResponse(
            response=f"I apologize, but I'm having a little trouble right now. Please try again in a moment. If the issue persists, please contact PE Desk for assistance.",
            session_id=session_id
        )


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat history for a session"""
    user_id = current_user.get("id")
    
    chat_history = await db.sohini_chats.find_one(
        {"session_id": session_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not chat_history:
        return {"messages": [], "session_id": session_id}
    
    return {
        "messages": chat_history.get("messages", []),
        "session_id": session_id
    }


@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Clear chat history for a session"""
    user_id = current_user.get("id")
    
    await db.sohini_chats.delete_one(
        {"session_id": session_id, "user_id": user_id}
    )
    
    return {"message": "Chat history cleared"}
