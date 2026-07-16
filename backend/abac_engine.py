"""KDMARCHE ABAC — Policy dataclasses & engine (split from abac_policy.py)."""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

from schema_v2 import (
    OrgStatus, SubscriptionStatus, WalletStatus, KdmRole, OscopRole, CustomerRole, PartnerProvisionStatus, ZoneKind,
)

logger = logging.getLogger(__name__)

# ============== POLICY INPUT/OUTPUT ==============

@dataclass
class PolicySubject:
    """Who is making the request"""
    user_id: str
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    org_id: Optional[str] = None


@dataclass
class PolicyResource:
    """What resource/action is being accessed"""
    org_id: Optional[str] = None
    zone_id: Optional[str] = None
    incoterm: Optional[str] = None
    pickup_location_id: Optional[str] = None
    amount_credits: Optional[int] = None
    order_total_exw_cents: Optional[int] = None


@dataclass
class PolicyContext:
    """Additional context"""
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    now: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyInput:
    """Complete policy input"""
    action: str
    subject: PolicySubject
    resource: PolicyResource
    context: PolicyContext = field(default_factory=PolicyContext)


@dataclass
class PolicyData:
    """Data loaded from database"""
    org: Optional[Dict[str, Any]] = None
    subscription: Optional[Dict[str, Any]] = None
    partner_account: Optional[Dict[str, Any]] = None
    entitlements: List[str] = field(default_factory=list)  # Zone IDs
    wallet: Optional[Dict[str, Any]] = None
    zone: Optional[Dict[str, Any]] = None


@dataclass
class PolicyResult:
    """Policy evaluation result"""
    allow: bool
    deny_reasons: List[str] = field(default_factory=list)
    show_price: bool = False
    can_order: bool = False
    can_consume_credits: bool = False
    exw_required: bool = False
    incoterm_allowed: bool = False


# ============== ABAC POLICY ENGINE ==============

class ABACPolicyEngine:
    """
    ABAC Policy Engine implementing OPA-equivalent rules
    """
    
    # Admin roles
    ADMIN_ROLES = [
        OscopRole.OSCOP_SUPER_ADMIN.value,
        OscopRole.OSCOP_COMPLIANCE_ADMIN.value,
        OscopRole.OSCOP_BILLING_ADMIN.value,
    ]
    
    # Customer roles that can buy
    BUYER_ROLES = [
        CustomerRole.CUSTOMER_ORG_OWNER.value,
        CustomerRole.CUSTOMER_ORG_BUYER.value,
    ]
    
    # All customer roles
    CUSTOMER_ROLES = [
        CustomerRole.CUSTOMER_ORG_OWNER.value,
        CustomerRole.CUSTOMER_ORG_BUYER.value,
        CustomerRole.CUSTOMER_ORG_VIEWER.value,
    ]
    
    def __init__(self):
        self.deny_reasons: List[str] = []
    
    def evaluate(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """
        Main evaluation entry point
        """
        self.deny_reasons = []
        result = PolicyResult(allow=False)
        
        # Route to specific action handler
        action_handlers = {
            "kdm.pricing.view": self._evaluate_pricing_view,
            "kdm.order.create": self._evaluate_order_create,
            "kdm.shipping.quote": self._evaluate_shipping_quote,
            "wallet.consume": self._evaluate_wallet_consume,
            "oscop.application.decision": self._evaluate_admin_action,
            "oscop.org.suspend": self._evaluate_admin_action,
            "oscop.subscription.manage": self._evaluate_billing_admin,
        }
        
        handler = action_handlers.get(input.action)
        if handler:
            result = handler(input, data)
        else:
            result.deny_reasons = ["UNKNOWN_ACTION"]
        
        result.deny_reasons = self.deny_reasons
        return result
    
    # ============== HELPERS ==============
    
    def _has_role(self, subject: PolicySubject, role: str) -> bool:
        return role in subject.roles
    
    def _has_any_role(self, subject: PolicySubject, roles: List[str]) -> bool:
        return any(r in subject.roles for r in roles)
    
    def _is_admin(self, subject: PolicySubject) -> bool:
        return self._has_any_role(subject, self.ADMIN_ROLES)
    
    def _is_same_org(self, subject: PolicySubject, resource: PolicyResource) -> bool:
        return subject.org_id is not None and subject.org_id == resource.org_id
    
    def _check_org_status(self, data: PolicyData) -> bool:
        """Check organization status"""
        if not data.org:
            self.deny_reasons.append("ORG_NOT_FOUND")
            return False
        
        status = data.org.get("status")
        
        if status == OrgStatus.REJECTED.value:
            self.deny_reasons.append("ORG_REJECTED")
            return False
        
        if status == OrgStatus.SUSPENDED.value:
            self.deny_reasons.append("ORG_SUSPENDED")
            return False
        
        if status == OrgStatus.CLOSED.value:
            self.deny_reasons.append("ORG_CLOSED")
            return False
        
        if status != OrgStatus.APPROVED.value:
            self.deny_reasons.append("ORG_NOT_APPROVED")
            return False
        
        return True
    
    def _check_subscription_status(self, data: PolicyData) -> bool:
        """Check subscription status"""
        if not data.subscription:
            self.deny_reasons.append("SUBSCRIPTION_NOT_FOUND")
            return False
        
        status = data.subscription.get("status")
        
        if status == SubscriptionStatus.CANCELED.value:
            self.deny_reasons.append("SUBSCRIPTION_CANCELED")
            return False
        
        if status == SubscriptionStatus.PAST_DUE.value:
            self.deny_reasons.append("SUBSCRIPTION_PAST_DUE")
            return False
        
        if status == SubscriptionStatus.GRACE_PERIOD.value:
            self.deny_reasons.append("SUBSCRIPTION_GRACE_PERIOD")
            return False
        
        if status != SubscriptionStatus.ACTIVE.value:
            self.deny_reasons.append("SUBSCRIPTION_NOT_ACTIVE")
            return False
        
        return True
    
    def _check_partner_access(self, data: PolicyData) -> bool:
        """Check KDMARCHE partner access"""
        if not data.partner_account:
            self.deny_reasons.append("PARTNER_ACCOUNT_NOT_FOUND")
            return False
        
        status = data.partner_account.get("status")
        
        if status == PartnerProvisionStatus.ACCESS_DISABLED.value:
            self.deny_reasons.append("PARTNER_ACCESS_DISABLED")
            return False
        
        if status != PartnerProvisionStatus.ACCESS_ENABLED.value:
            self.deny_reasons.append("PARTNER_ACCESS_NOT_ENABLED")
            return False
        
        return True
    
    def _check_zone_entitled(self, resource: PolicyResource, data: PolicyData) -> bool:
        """Check if zone is entitled for org"""
        if not resource.zone_id:
            self.deny_reasons.append("ZONE_NOT_SELECTED")
            return False
        
        if resource.zone_id not in data.entitlements:
            self.deny_reasons.append("ZONE_NOT_ENTITLED")
            return False
        
        return True
    
    def _check_wallet_status(self, data: PolicyData, amount: int = 0) -> bool:
        """Check wallet status and balance"""
        if not data.wallet:
            self.deny_reasons.append("WALLET_NOT_FOUND")
            return False
        
        if data.wallet.get("status") == WalletStatus.FROZEN.value:
            self.deny_reasons.append("WALLET_FROZEN")
            return False
        
        if amount > 0:
            balance = data.wallet.get("balance_credits", 0)
            if amount > balance:
                self.deny_reasons.append("INSUFFICIENT_CREDITS")
                return False
        
        return True
    
    def _check_base_access(self, data: PolicyData) -> bool:
        """Check all base access conditions"""
        org_ok = self._check_org_status(data)
        sub_ok = self._check_subscription_status(data)
        partner_ok = self._check_partner_access(data)
        
        return org_ok and sub_ok and partner_ok
    
    def _check_exw_incoterm(self, resource: PolicyResource, data: PolicyData) -> Tuple[bool, bool]:
        """
        Check EXW incoterm rules
        Returns: (exw_required, incoterm_allowed)
        """
        zone = data.zone
        
        if not zone:
            self.deny_reasons.append("ZONE_UNKNOWN")
            return False, False
        
        exw_required = zone.get("exw_only", True)
        
        incoterm = (resource.incoterm or "").upper()
        
        if exw_required:
            if incoterm != "EXW":
                self.deny_reasons.append("INCOTERM_NOT_ALLOWED_EXW_ONLY")
                return exw_required, False
            
            # Check pickup location for EXW
            if zone.get("pickup_required", True):
                if not resource.pickup_location_id:
                    self.deny_reasons.append("PICKUP_LOCATION_REQUIRED_FOR_EXW")
                    return exw_required, False
        
        # EXW strict everywhere (as requested)
        if incoterm != "EXW":
            self.deny_reasons.append("INCOTERM_NOT_ALLOWED_EXW_ONLY")
            return exw_required, False
        
        return exw_required, True
    
    # ============== ACTION HANDLERS ==============
    
    def _evaluate_pricing_view(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """Evaluate kdm.pricing.view action"""
        result = PolicyResult(allow=False)
        
        # Check role
        is_customer = self._has_any_role(input.subject, self.CUSTOMER_ROLES)
        is_admin = self._is_admin(input.subject)
        
        if not (is_customer or is_admin):
            self.deny_reasons.append("ROLE_NOT_AUTHORIZED")
            return result
        
        # Check same org
        if not self._is_same_org(input.subject, input.resource) and not is_admin:
            self.deny_reasons.append("ORG_MISMATCH")
            return result
        
        # Check base access
        if not self._check_base_access(data):
            return result
        
        # Check zone entitled
        if not self._check_zone_entitled(input.resource, data):
            return result
        
        result.allow = True
        result.show_price = True
        return result
    
    def _evaluate_order_create(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """Evaluate kdm.order.create action"""
        result = PolicyResult(allow=False)
        
        # Check role (must be buyer)
        is_buyer = self._has_any_role(input.subject, self.BUYER_ROLES)
        is_admin = self._is_admin(input.subject)
        
        if not (is_buyer or is_admin):
            self.deny_reasons.append("ROLE_NOT_AUTHORIZED_TO_ORDER")
            return result
        
        # Check same org
        if not self._is_same_org(input.subject, input.resource) and not is_admin:
            self.deny_reasons.append("ORG_MISMATCH")
            return result
        
        # Check base access
        if not self._check_base_access(data):
            return result
        
        # Check zone entitled
        if not self._check_zone_entitled(input.resource, data):
            return result
        
        # Check EXW incoterm
        exw_required, incoterm_allowed = self._check_exw_incoterm(input.resource, data)
        result.exw_required = exw_required
        result.incoterm_allowed = incoterm_allowed
        
        if not incoterm_allowed:
            return result
        
        # Optional: Order limit check
        order_total = input.resource.order_total_exw_cents or 0
        if order_total > 5000000 and not is_admin:  # 50,000€ limit
            self.deny_reasons.append("ORDER_LIMIT_EXCEEDED")
            return result
        
        result.allow = True
        result.can_order = True
        return result
    
    def _evaluate_shipping_quote(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """Evaluate kdm.shipping.quote action (pre-check for incoterm)"""
        result = PolicyResult(allow=False)
        
        if not data.zone:
            self.deny_reasons.append("ZONE_UNKNOWN")
            return result
        
        exw_required, incoterm_allowed = self._check_exw_incoterm(input.resource, data)
        result.exw_required = exw_required
        result.incoterm_allowed = incoterm_allowed
        result.allow = incoterm_allowed
        
        return result
    
    def _evaluate_wallet_consume(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """Evaluate wallet.consume action"""
        result = PolicyResult(allow=False)
        
        # Check role
        is_buyer = self._has_any_role(input.subject, self.BUYER_ROLES)
        is_admin = self._is_admin(input.subject)
        
        if not (is_buyer or is_admin):
            self.deny_reasons.append("ROLE_NOT_AUTHORIZED_TO_CONSUME")
            return result
        
        # Check same org
        if not self._is_same_org(input.subject, input.resource) and not is_admin:
            self.deny_reasons.append("ORG_MISMATCH")
            return result
        
        # Check org status (but not full base access - wallet ops don't need KDM)
        if not self._check_org_status(data):
            return result
        
        if not self._check_subscription_status(data):
            return result
        
        # Check wallet
        amount = input.resource.amount_credits or 0
        if amount <= 0:
            self.deny_reasons.append("INVALID_AMOUNT")
            return result
        
        if not self._check_wallet_status(data, amount):
            return result
        
        result.allow = True
        result.can_consume_credits = True
        return result
    
    def _evaluate_admin_action(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """Evaluate admin-only actions"""
        result = PolicyResult(allow=False)
        
        if self._is_admin(input.subject):
            result.allow = True
        else:
            self.deny_reasons.append("ADMIN_REQUIRED")
        
        return result
    
    def _evaluate_billing_admin(self, input: PolicyInput, data: PolicyData) -> PolicyResult:
        """Evaluate billing admin actions"""
        result = PolicyResult(allow=False)
        
        billing_roles = [
            OscopRole.OSCOP_BILLING_ADMIN.value,
            OscopRole.OSCOP_SUPER_ADMIN.value,
        ]
        
        if self._has_any_role(input.subject, billing_roles):
            result.allow = True
        else:
            self.deny_reasons.append("BILLING_ADMIN_REQUIRED")
        
        return result


