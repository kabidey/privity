#!/usr/bin/env python3
"""
Test script to verify the updated Client models work correctly
"""

import sys
import os
sys.path.append('/app')

from backend.server import Client, ClientDocument, ClientCreate
from datetime import datetime

def test_client_models():
    """Test the updated client models"""
    
    # Test ClientDocument with new fields
    doc = ClientDocument(
        doc_type="pan_card",
        filename="pan_123.pdf",
        file_path="/uploads/client123/pan_123.pdf",
        upload_date=datetime.now().isoformat(),
        ocr_data={
            "pan_number": "ABCDE1234F",
            "name": "John Doe"
        }
    )
    print("✓ ClientDocument model works with new fields")
    print(f"  - doc_type: {doc.doc_type}")
    print(f"  - file_path: {doc.file_path}")
    print(f"  - ocr_data: {doc.ocr_data}")
    
    # Test ClientCreate (unchanged)
    client_create = ClientCreate(
        name="John Doe",
        email="john@example.com",
        pan_number="ABCDE1234F",
        dp_id="12345678"
    )
    print("\n✓ ClientCreate model works")
    
    # Test Client with new fields
    client = Client(
        id="client-123",
        otc_ucc="OTC20241201ABCD1234",
        name="John Doe",
        email="john@example.com",
        pan_number="ABCDE1234F",
        dp_id="12345678",
        documents=[doc],
        created_at=datetime.now().isoformat(),
        created_by="user-123",
        mapped_employee_id="emp-456",
        mapped_employee_name="Jane Smith"
    )
    print("\n✓ Client model works with new fields")
    print(f"  - otc_ucc: {client.otc_ucc}")
    print(f"  - mapped_employee_id: {client.mapped_employee_id}")
    print(f"  - mapped_employee_name: {client.mapped_employee_name}")
    print(f"  - documents count: {len(client.documents)}")
    
    print("\n🎉 All model tests passed!")

if __name__ == "__main__":
    test_client_models()