"""KDMARCHE × O'SCOP — Schema Catalogue : enums (split from schema_catalog.py)."""
from enum import Enum

# ============== ENUMS ==============

class ProductStatus(str, Enum):
    """Product availability status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    DISCONTINUED = "DISCONTINUED"


class PriceType(str, Enum):
    """Price type"""
    STANDARD = "STANDARD"
    PROMO = "PROMO"
    FLASH = "FLASH"


class UnitType(str, Enum):
    """Unit of measurement"""
    PIECE = "PIECE"
    KG = "KG"
    LITRE = "LITRE"
    CARTON = "CARTON"
    PALETTE = "PALETTE"


class OrderStatus(str, Enum):
    """Order status"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    INVOICED = "INVOICED"
    PAID = "PAID"
    CANCELED = "CANCELED"


class CartStatus(str, Enum):
    """Cart status"""
    ACTIVE = "ACTIVE"
    CONVERTED = "CONVERTED"
    ABANDONED = "ABANDONED"


