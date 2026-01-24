"""
Database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def get_db():
    """Get database instance"""
    return db

def get_client():
    """Get MongoDB client"""
    return client
