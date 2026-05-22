#!/usr/bin/env python3
"""
KDMARCHE — build_opa_bundle.py (MongoDB version)
Script Python pour générer le bundle OPA directement depuis MongoDB.

Utilisation:
    python build_opa_bundle.py

Options (via variables d'environnement):
    MONGO_URL       MongoDB connection URL
    DB_NAME         Database name (default: kdmarche)
    BUNDLE_DIR      Output directory (default: ./bundle)
    OUT_TGZ         Output tarball (default: ./bundle.tar.gz)
"""

import asyncio
import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    print("ERROR: motor not installed. Run: pip install motor")
    sys.exit(1)


# Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")  # Match .env default
BUNDLE_DIR = Path(os.environ.get("BUNDLE_DIR", "./bundle"))
POLICY_SRC_DIR = Path(os.environ.get("POLICY_SRC_DIR", "./opa_bundle/policy"))
OUT_TGZ = Path(os.environ.get("OUT_TGZ", "./bundle.tar.gz"))

# Zone code mapping (text -> numeric DOM codes)
CODE_MAPPING = {
    "GUADELOUPE": "971",
    "MARTINIQUE": "972",
    "GUYANE": "973",
    "REUNION": "974",
    "MAYOTTE": "976"
}

# Required policy files
REQUIRED_POLICIES = [
    "kdm_incoterm.rego",
    "kdm_prep_options.rego",
    "kdm_delivery.rego",
    "kdm_delivery_route.rego",
    "kdm_order_create.rego"
]


async def generate_zones_config(db) -> Dict[str, Any]:
    """Generate zones_config from MongoDB"""
    zones_config = {}
    
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    options = await db.zone_preparation_options.find({"enabled": True}, {"_id": 0}).to_list(500)
    
    # Group options by zone
    options_by_zone = {}
    for opt in options:
        zone_code = opt.get("zone_code", "")
        if zone_code not in options_by_zone:
            options_by_zone[zone_code] = {}
        options_by_zone[zone_code][opt.get("code", "")] = {
            "enabled": opt.get("enabled", True),
            "min_qty": opt.get("min_qty", 1),
            "max_qty": opt.get("max_qty", 100),
            "pricing_mode": opt.get("pricing_mode", "FIXED")
        }
    
    for zone in zones:
        zone_code = zone.get("code", "")
        zones_config[zone_code] = {
            "prep_options": options_by_zone.get(zone_code, {})
        }
    
    return zones_config


async def generate_zones_policy(db) -> Dict[str, Any]:
    """Generate zones_policy from MongoDB"""
    zones_policy = {}
    
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    
    for zone in zones:
        zone_code = zone.get("code", "")
        zones_policy[zone_code] = {
            "exw_only": zone.get("exw_only", True),
            "pickup_required": zone.get("pickup_required", True),
            "vat_rate": zone.get("vat_rate", 8.5),
            "vat_exonerated": zone.get("vat_exonerated", False),
            "kind": zone.get("kind", "OM"),
            "currency": "EUR"
        }
    
    return zones_policy


async def generate_delivery_policy(db) -> Dict[str, Any]:
    """Generate delivery_policy from MongoDB"""
    delivery_policy = {}
    
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    
    for zone in zones:
        zone_code = zone.get("code", "")
        numeric_code = CODE_MAPPING.get(zone_code.upper(), zone_code)
        
        delivery_policy[numeric_code] = {
            "zone_name": zone.get("name", zone_code),
            "logiscop_delivery_enabled": zone.get("logiscop_delivery_enabled", False),
            "delivery_enabled": zone.get("logiscop_delivery_enabled", False),
            "pickup_required": zone.get("pickup_required", True),
            "min_cartons": zone.get("delivery_min_cartons", 1),
            "max_cartons": zone.get("delivery_max_cartons", 100),
            "vat_rate": zone.get("vat_rate", 8.5),
            "vat_exonerated": zone.get("vat_exonerated", False)
        }
    
    return delivery_policy


async def generate_route_policy(db) -> Dict[str, Any]:
    """Generate route_policy (ESS Route) from MongoDB"""
    route_policy = {}
    
    # Get zones
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    
    # Get route policies
    policies = await db.kdm_route_policy.find({}, {"_id": 0}).to_list(100)
    policies_by_zone = {p.get("zone_code", ""): p for p in policies}
    
    # Get priority rules
    rules = await db.kdm_route_priority_rules.find({"is_active": True}, {"_id": 0}).to_list(500)
    rules_by_zone = {}
    for rule in rules:
        zone_code = rule.get("zone_code", "")
        if zone_code not in rules_by_zone:
            rules_by_zone[zone_code] = []
        rules_by_zone[zone_code].append({
            "code": rule.get("code", ""),
            "weight": rule.get("weight", 0)
        })
    
    for zone in zones:
        zone_code = zone.get("code", "").upper()
        if not zone_code:
            continue
        
        policy = policies_by_zone.get(zone_code, {})
        zone_rules = rules_by_zone.get(zone_code, [])
        zone_rules.sort(key=lambda x: x.get("weight", 0), reverse=True)
        
        route_policy[zone_code] = {
            "ess_route_enabled": policy.get("ess_route_enabled", False),
            "window_required": policy.get("window_required", True),
            "min_reliability_score": policy.get("min_reliability_score", 0),
            "max_daily_capacity": policy.get("max_daily_capacity", 0),
            "priority_rules": zone_rules
        }
    
    return route_policy


async def generate_route_capacity(db) -> Dict[str, Any]:
    """Generate route_capacity from MongoDB"""
    route_capacity = {}
    
    # Get zones
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    
    # Get capacities
    capacities = await db.kdm_route_capacity.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    # Group by zone
    capacity_by_zone = {}
    for cap in capacities:
        zone_code = cap.get("zone_code", "").upper()
        if zone_code not in capacity_by_zone:
            capacity_by_zone[zone_code] = {}
        
        tour_id = cap.get("tour_id", "")
        if tour_id:
            capacity_by_zone[zone_code][tour_id] = {
                "capacity": cap.get("capacity", 0),
                "booked": cap.get("booked", 0),
                "window_start": cap.get("window_start"),
                "window_end": cap.get("window_end")
            }
    
    for zone in zones:
        zone_code = zone.get("code", "").upper()
        if zone_code:
            route_capacity[zone_code] = capacity_by_zone.get(zone_code, {})
    
    return route_capacity


async def generate_data_json(db) -> Dict[str, Any]:
    """Generate complete data.json for OPA bundle"""
    zones_config = await generate_zones_config(db)
    zones_policy = await generate_zones_policy(db)
    delivery_policy = await generate_delivery_policy(db)
    route_policy = await generate_route_policy(db)
    route_capacity = await generate_route_capacity(db)
    
    return {
        "zones_config": zones_config,
        "zones_policy": zones_policy,
        "delivery_policy": delivery_policy,
        "route_policy": route_policy,
        "route_capacity": route_capacity,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.3.0"
    }


def copy_policies(src_dir: Path, dst_dir: Path) -> bool:
    """Copy .rego policy files"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    missing = []
    
    for policy_file in REQUIRED_POLICIES:
        src = src_dir / policy_file
        if src.exists():
            dst = dst_dir / policy_file
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  ✓ Copied: {policy_file}")
        else:
            missing.append(policy_file)
            print(f"  ✗ Missing: {policy_file}")
    
    return len(missing) == 0


def create_manifest(bundle_dir: Path) -> None:
    """Create OPA .manifest file"""
    manifest = {
        "revision": datetime.now().strftime("%Y%m%d%H%M%S"),
        "roots": ["zones_config", "zones_policy", "delivery_policy", "route_policy", "route_capacity"]
    }
    (bundle_dir / ".manifest").write_text(json.dumps(manifest, indent=2))


def create_tarball(bundle_dir: Path, out_tgz: Path) -> None:
    """Create bundle.tar.gz"""
    with tarfile.open(out_tgz, "w:gz") as tar:
        for item in bundle_dir.iterdir():
            arcname = item.name
            if item.is_dir():
                for sub in item.rglob("*"):
                    tar.add(sub, arcname=f"{arcname}/{sub.relative_to(item)}")
            else:
                tar.add(item, arcname=arcname)


async def main():
    print("=" * 60)
    print("KDMARCHE — OPA Bundle Generator (MongoDB)")
    print("=" * 60)
    
    # Connect to MongoDB
    print(f"\n[1/5] Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Test connection
        await db.command("ping")
        print(f"  ✓ Connected to {DB_NAME}")
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        sys.exit(1)
    
    # Create bundle directory
    print(f"\n[2/5] Creating bundle directories...")
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    policy_dst = BUNDLE_DIR / "policy"
    policy_dst.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Created {BUNDLE_DIR}")
    
    # Generate data.json
    print(f"\n[3/5] Generating data.json from MongoDB...")
    try:
        data = await generate_data_json(db)
        data_file = BUNDLE_DIR / "data.json"
        data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        
        print(f"  ✓ Generated data.json (v{data['version']})")
        print(f"    - zones_config: {len(data['zones_config'])} zones")
        print(f"    - zones_policy: {len(data['zones_policy'])} zones")
        print(f"    - delivery_policy: {len(data['delivery_policy'])} zones")
        print(f"    - route_policy: {len(data['route_policy'])} zones")
        print(f"    - route_capacity: {len(data['route_capacity'])} zones")
    except Exception as e:
        print(f"  ✗ Failed to generate data.json: {e}")
        sys.exit(1)
    
    # Copy policies
    print(f"\n[4/5] Copying policy files...")
    if not copy_policies(POLICY_SRC_DIR, policy_dst):
        print("  ✗ Some policy files are missing!")
        sys.exit(1)
    
    # Create manifest
    create_manifest(BUNDLE_DIR)
    print("  ✓ Created .manifest")
    
    # Create tarball
    print(f"\n[5/5] Creating bundle tarball...")
    create_tarball(BUNDLE_DIR, OUT_TGZ)
    size = OUT_TGZ.stat().st_size / 1024
    print(f"  ✓ Created {OUT_TGZ} ({size:.1f} KB)")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Bundle generation complete!")
    print("=" * 60)
    print(f"\nFiles:")
    print(f"  - data.json: {BUNDLE_DIR / 'data.json'}")
    print(f"  - policies:  {policy_dst}")
    print(f"  - bundle:    {OUT_TGZ}")
    print(f"\nTo use with OPA:")
    print(f"  opa run --server --bundle {OUT_TGZ}")
    
    # Cleanup
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
