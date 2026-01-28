"""
High-Concurrency Booking Stress Test

This script tests the system's ability to handle multiple simultaneous booking requests
for the same stock without creating race conditions or overselling inventory.
"""
import asyncio
import aiohttp
import json
import time
from typing import List, Tuple
import sys

API_URL = "https://privity-booking.preview.emergentagent.com"

async def login(session: aiohttp.ClientSession) -> str:
    """Get authentication token."""
    async with session.post(
        f"{API_URL}/api/auth/login",
        json={"email": "pedesk@smifs.com", "password": "Kutta@123"}
    ) as resp:
        data = await resp.json()
        return data.get("token", "")

async def get_inventory(session: aiohttp.ClientSession, token: str, stock_id: str) -> dict:
    """Get current inventory for a stock."""
    async with session.get(
        f"{API_URL}/api/inventory",
        headers={"Authorization": f"Bearer {token}"}
    ) as resp:
        data = await resp.json()
        for inv in data:
            if inv.get("stock_id") == stock_id:
                return inv
        return {}

async def create_booking(
    session: aiohttp.ClientSession,
    token: str,
    client_id: str,
    stock_id: str,
    quantity: int,
    booking_num: int
) -> Tuple[bool, str, int]:
    """
    Attempt to create a booking.
    Returns: (success, message, booking_num)
    """
    try:
        async with session.post(
            f"{API_URL}/api/bookings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "client_id": client_id,
                "stock_id": stock_id,
                "quantity": quantity,
                "selling_price": 150.0,
                "booking_date": "2026-01-28",
                "booking_type": "client",
                "status": "pending"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return True, f"Created {data.get('booking_number', 'unknown')}", booking_num
            else:
                return False, data.get("detail", "Unknown error"), booking_num
    except Exception as e:
        return False, str(e), booking_num

async def run_concurrent_bookings(
    num_bookings: int,
    quantity_per_booking: int,
    client_id: str,
    stock_id: str
) -> List[Tuple[bool, str, int]]:
    """Run multiple booking requests concurrently."""
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        if not token:
            print("Failed to login")
            return []
        
        # Get initial inventory
        initial_inv = await get_inventory(session, token, stock_id)
        initial_available = initial_inv.get("available_quantity", 0)
        print(f"\nInitial inventory available: {initial_available}")
        print(f"Attempting {num_bookings} concurrent bookings of {quantity_per_booking} units each")
        print(f"Total requested: {num_bookings * quantity_per_booking} units")
        print("-" * 50)
        
        # Create concurrent booking tasks
        tasks = [
            create_booking(session, token, client_id, stock_id, quantity_per_booking, i+1)
            for i in range(num_bookings)
        ]
        
        # Execute all at once
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        print(f"\nCompleted {num_bookings} requests in {elapsed:.2f} seconds")
        
        # Analyze results
        successes = [r for r in results if r[0]]
        failures = [r for r in results if not r[0]]
        
        print(f"\nResults:")
        print(f"  Successful bookings: {len(successes)}")
        print(f"  Failed bookings: {len(failures)}")
        
        # Show details
        if successes:
            print(f"\n  Successful booking numbers:")
            for success, msg, num in successes[:10]:
                print(f"    #{num}: {msg}")
            if len(successes) > 10:
                print(f"    ... and {len(successes) - 10} more")
        
        if failures:
            print(f"\n  Failure reasons:")
            failure_reasons = {}
            for fail, msg, num in failures:
                if msg not in failure_reasons:
                    failure_reasons[msg] = 0
                failure_reasons[msg] += 1
            for reason, count in failure_reasons.items():
                print(f"    {count}x: {reason[:80]}...")
        
        # Get final inventory
        final_inv = await get_inventory(session, token, stock_id)
        final_available = final_inv.get("available_quantity", 0)
        
        print(f"\nInventory changes:")
        print(f"  Initial available: {initial_available}")
        print(f"  Final available: {final_available}")
        print(f"  Units consumed: {initial_available - final_available}")
        print(f"  Expected (based on successes): {len(successes) * quantity_per_booking}")
        
        # Verify no overselling
        units_consumed = initial_available - final_available
        expected_consumed = len(successes) * quantity_per_booking
        
        if units_consumed == expected_consumed:
            print(f"\n✅ PASS: Inventory correctly tracked (no race condition)")
        else:
            print(f"\n❌ FAIL: Inventory mismatch! Consumed {units_consumed} but {expected_consumed} expected")
        
        return results

async def main():
    # Test parameters
    # Using existing test data
    client_id = "fad25d59-f0d9-473d-8b7e-dde3363817a7"  # Test Client Ltd
    stock_id = "3e29a141-4509-4340-8971-5ea82609608b"   # TEST stock
    
    # First check current inventory
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        inv = await get_inventory(session, token, stock_id)
        available = inv.get("available_quantity", 0)
        
        if available < 10:
            print(f"Not enough inventory for stress test. Available: {available}")
            print("Need at least 10 units. Please add more purchases first.")
            return
    
    print("=" * 60)
    print("HIGH-CONCURRENCY BOOKING STRESS TEST")
    print("=" * 60)
    
    # Test 1: 5 concurrent bookings of 10 units each (should handle correctly)
    print("\n\nTEST 1: 5 concurrent bookings of 10 units each")
    print("=" * 60)
    await run_concurrent_bookings(
        num_bookings=5,
        quantity_per_booking=10,
        client_id=client_id,
        stock_id=stock_id
    )
    
    print("\n\nStress test complete!")

if __name__ == "__main__":
    asyncio.run(main())
