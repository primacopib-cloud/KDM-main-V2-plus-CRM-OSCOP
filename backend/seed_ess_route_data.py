#!/usr/bin/env python3
"""
KDMARCHE — seed_ess_route_data.py
Script pour initialiser les collections MongoDB route_policy et route_capacity
pour le support des Tournées Mutualisées ESS.

Collections créées:
- kdm_route_policy: Policy ESS Route par zone
- kdm_route_priority_rules: Règles de priorisation par zone
- kdm_route_capacity: Capacité des tournées

Usage:
    python seed_ess_route_data.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    print("ERROR: motor not installed. Run: pip install motor")
    sys.exit(1)

# Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ESS Route Policy Data
ROUTE_POLICIES = [
    {
        "zone_code": "GUADELOUPE",
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 120,
        "is_active": True
    },
    {
        "zone_code": "MARTINIQUE",
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 100,
        "is_active": True
    },
    {
        "zone_code": "GUYANE",
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 50,
        "max_daily_capacity": 60,
        "is_active": True
    },
    {
        "zone_code": "REUNION",
        "ess_route_enabled": True,
        "window_required": True,
        "min_reliability_score": 60,
        "max_daily_capacity": 80,
        "is_active": True
    },
    {
        "zone_code": "MAYOTTE",
        "ess_route_enabled": False,  # Not available yet
        "window_required": True,
        "min_reliability_score": 50,
        "max_daily_capacity": 40,
        "is_active": True
    }
]


# Priority Rules Data
PRIORITY_RULES = [
    # Guadeloupe
    {"zone_code": "GUADELOUPE", "code": "COMPLIANCE_OK", "weight": 40, "sort_order": 1},
    {"zone_code": "GUADELOUPE", "code": "RELIABLE_PICKUPS", "weight": 30, "sort_order": 2},
    {"zone_code": "GUADELOUPE", "code": "LOW_INCIDENTS", "weight": 20, "sort_order": 3},
    {"zone_code": "GUADELOUPE", "code": "RECENT_LATE_CANCEL", "weight": -30, "sort_order": 4},
    
    # Martinique
    {"zone_code": "MARTINIQUE", "code": "COMPLIANCE_OK", "weight": 40, "sort_order": 1},
    {"zone_code": "MARTINIQUE", "code": "RELIABLE_PICKUPS", "weight": 30, "sort_order": 2},
    {"zone_code": "MARTINIQUE", "code": "LOW_INCIDENTS", "weight": 20, "sort_order": 3},
    {"zone_code": "MARTINIQUE", "code": "RECENT_LATE_CANCEL", "weight": -30, "sort_order": 4},
    
    # Guyane
    {"zone_code": "GUYANE", "code": "COMPLIANCE_OK", "weight": 40, "sort_order": 1},
    {"zone_code": "GUYANE", "code": "RELIABLE_PICKUPS", "weight": 30, "sort_order": 2},
    {"zone_code": "GUYANE", "code": "LOW_INCIDENTS", "weight": 20, "sort_order": 3},
    
    # Réunion
    {"zone_code": "REUNION", "code": "COMPLIANCE_OK", "weight": 40, "sort_order": 1},
    {"zone_code": "REUNION", "code": "RELIABLE_PICKUPS", "weight": 30, "sort_order": 2},
    {"zone_code": "REUNION", "code": "LOW_INCIDENTS", "weight": 20, "sort_order": 3},
    
    # Mayotte (no rules since ESS Route is disabled)
]


def generate_sample_tours(zone_code: str, zone_prefix: str, max_capacity: int, days_ahead: int = 14):
    """Generate sample tour capacities for a zone"""
    tours = []
    today = datetime.now(timezone.utc).date()
    
    windows = [
        ("AM", "08:00", "12:00"),
        ("PM", "14:00", "18:00")
    ]
    
    for day_offset in range(1, days_ahead + 1):
        tour_date = today + timedelta(days=day_offset)
        
        # Skip weekends
        if tour_date.weekday() >= 5:
            continue
        
        week_num = tour_date.isocalendar()[1]
        day_abbr = tour_date.strftime("%a").upper()[:3]
        
        for window_code, start, end in windows:
            tour_id = f"TOUR-{zone_prefix}-{tour_date.year}W{week_num:02d}-{day_abbr}-{window_code}"
            
            # Simulate some bookings (random between 20-70% capacity) using cryptographic randomness
            import secrets as _secrets
            lower = int(max_capacity * 0.2)
            upper = max(1, int(max_capacity * 0.7) - lower + 1)
            booked = lower + _secrets.randbelow(upper)
            
            tours.append({
                "zone_code": zone_code,
                "tour_id": tour_id,
                "capacity": max_capacity,
                "booked": booked,
                "window_start": f"{tour_date.isoformat()}T{start}:00Z",
                "window_end": f"{tour_date.isoformat()}T{end}:00Z",
                "is_active": True
            })
    
    return tours


async def main():
    print("=" * 60)
    print("KDMARCHE — ESS Route Data Seeder (MongoDB)")
    print("=" * 60)
    
    # Connect to MongoDB
    print("\n[1/5] Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print(f"  ✓ Connected to {DB_NAME}")
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        sys.exit(1)
    
    now = datetime.now(timezone.utc)
    
    # Create indexes
    print("\n[2/5] Creating indexes...")
    await db.kdm_route_policy.create_index("zone_code", unique=True)
    await db.kdm_route_priority_rules.create_index([("zone_code", 1), ("code", 1)], unique=True)
    await db.kdm_route_capacity.create_index([("zone_code", 1), ("tour_id", 1)], unique=True)
    await db.kdm_route_capacity.create_index("tour_id")
    print("  ✓ Indexes created")
    
    # Seed route_policy
    print("\n[3/5] Seeding kdm_route_policy...")
    for policy in ROUTE_POLICIES:
        policy["created_at"] = now
        policy["updated_at"] = now
        
        await db.kdm_route_policy.update_one(
            {"zone_code": policy["zone_code"]},
            {"$set": policy},
            upsert=True
        )
        status = "enabled" if policy["ess_route_enabled"] else "disabled"
        print(f"  ✓ {policy['zone_code']}: ESS Route {status}, capacity={policy['max_daily_capacity']}")
    
    # Seed priority_rules
    print("\n[4/5] Seeding kdm_route_priority_rules...")
    for rule in PRIORITY_RULES:
        rule["is_active"] = True
        rule["created_at"] = now
        rule["updated_at"] = now
        
        await db.kdm_route_priority_rules.update_one(
            {"zone_code": rule["zone_code"], "code": rule["code"]},
            {"$set": rule},
            upsert=True
        )
    print(f"  ✓ {len(PRIORITY_RULES)} priority rules created")
    
    # Seed route_capacity (sample tours)
    print("\n[5/5] Seeding kdm_route_capacity (sample tours)...")
    
    zone_configs = [
        ("GUADELOUPE", "GP", 60),
        ("MARTINIQUE", "MQ", 50),
        ("GUYANE", "GF", 30),
        ("REUNION", "RE", 40),
    ]
    
    total_tours = 0
    for zone_code, prefix, capacity in zone_configs:
        tours = generate_sample_tours(zone_code, prefix, capacity)
        for tour in tours:
            tour["created_at"] = now
            tour["updated_at"] = now
            
            await db.kdm_route_capacity.update_one(
                {"zone_code": tour["zone_code"], "tour_id": tour["tour_id"]},
                {"$set": tour},
                upsert=True
            )
        
        total_tours += len(tours)
        print(f"  ✓ {zone_code}: {len(tours)} tours created")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ ESS Route data seeding complete!")
    print("=" * 60)
    
    # Verify counts
    policy_count = await db.kdm_route_policy.count_documents({})
    rules_count = await db.kdm_route_priority_rules.count_documents({})
    capacity_count = await db.kdm_route_capacity.count_documents({})
    
    print("\nCollections:")
    print(f"  - kdm_route_policy: {policy_count} documents")
    print(f"  - kdm_route_priority_rules: {rules_count} documents")
    print(f"  - kdm_route_capacity: {capacity_count} documents")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
