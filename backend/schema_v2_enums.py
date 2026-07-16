"""KDMARCHE × O'SCOP — Schema V2 enums & RBAC roles (split from schema_v2.py)."""
from enum import Enum

# ============== ENUMS (Production Schema) ==============

class OrgStatus(str, Enum):
    """Organization status state machine"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class ApplicationStatus(str, Enum):
    """B2B Application status"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SubscriptionStatus(str, Enum):
    """Subscription billing status"""
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    GRACE_PERIOD = "GRACE_PERIOD"
    CANCELED = "CANCELED"


class PartnerProvisionStatus(str, Enum):
    """KDMARCHE partner provisioning status"""
    NOT_PROVISIONED = "NOT_PROVISIONED"
    PROVISIONED = "PROVISIONED"
    ACCESS_ENABLED = "ACCESS_ENABLED"
    ACCESS_DISABLED = "ACCESS_DISABLED"
    DEPROVISIONED = "DEPROVISIONED"


class LedgerStatus(str, Enum):
    """Wallet ledger entry status"""
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    CANCELED = "CANCELED"


class LedgerDirection(str, Enum):
    """Wallet ledger direction"""
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class WalletStatus(str, Enum):
    """Wallet status"""
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"


class DocType(str, Enum):
    """Application document types"""
    REGISTRATION_DOC = "REGISTRATION_DOC"  # KBIS, extrait RCS
    ID_SIGNATORY = "ID_SIGNATORY"          # Pièce d'identité signataire
    PROOF_ADDRESS = "PROOF_ADDRESS"        # Justificatif adresse
    OTHER = "OTHER"


class DocStatus(str, Enum):
    """Document verification status"""
    UPLOADED = "UPLOADED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ZoneKind(str, Enum):
    """Zone type"""
    OM = "OM"        # Outre-mer
    EXPORT = "EXPORT"


class BillingPeriod(str, Enum):
    """Billing period"""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class InvoiceType(str, Enum):
    """Invoice type"""
    SUBSCRIPTION = "SUBSCRIPTION"
    CREDITS_TOPUP = "CREDITS_TOPUP"


class InvoiceStatus(str, Enum):
    """Invoice status"""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    FAILED = "FAILED"
    VOID = "VOID"


class DeliveryMode(str, Enum):
    """Delivery mode for logistics"""
    DIRECT = "DIRECT"        # Standard LOGI'SCOP delivery
    ESS_ROUTE = "ESS_ROUTE"  # Tournées Mutualisées ESS


class FulfillmentMode(str, Enum):
    """Fulfillment mode for orders"""
    EXW = "EXW"                        # Customer pickup
    LOGISCOP_DELIVERY = "LOGISCOP_DELIVERY"  # LOGI'SCOP delivery


class TourStatus(str, Enum):
    """ESS Tour status"""
    OPEN = "open"          # Accepting bookings
    FULL = "full"          # Capacity reached
    IN_PROGRESS = "in_progress"  # Currently running
    COMPLETED = "completed"       # Tour finished


class ESSBookingStatus(str, Enum):
    """ESS Route booking status"""
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"
    NO_SHOW = "no_show"


class EntitlementSource(str, Enum):
    """Zone entitlement source"""
    INCLUDED = "INCLUDED"  # Included in plan
    OPTION = "OPTION"      # Purchased addon


class EntitlementStatus(str, Enum):
    """Zone entitlement status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# ============== RBAC ROLES ==============

class OscopRole(str, Enum):
    """O'SCOP internal roles"""
    OSCOP_SUPER_ADMIN = "OSCOP_SUPER_ADMIN"
    OSCOP_COMPLIANCE_ADMIN = "OSCOP_COMPLIANCE_ADMIN"
    OSCOP_BILLING_ADMIN = "OSCOP_BILLING_ADMIN"
    OSCOP_SUPPORT_AGENT = "OSCOP_SUPPORT_AGENT"


class KdmRole(str, Enum):
    """KDMARCHE roles"""
    KDM_B2B_ADMIN = "KDM_B2B_ADMIN"
    KDM_B2B_SALES = "KDM_B2B_SALES"
    KDM_WAREHOUSE = "KDM_WAREHOUSE"
    KDM_FINANCE = "KDM_FINANCE"


class CustomerRole(str, Enum):
    """Customer organization roles"""
    CUSTOMER_ORG_OWNER = "CUSTOMER_ORG_OWNER"
    CUSTOMER_ORG_BUYER = "CUSTOMER_ORG_BUYER"
    CUSTOMER_ORG_VIEWER = "CUSTOMER_ORG_VIEWER"


