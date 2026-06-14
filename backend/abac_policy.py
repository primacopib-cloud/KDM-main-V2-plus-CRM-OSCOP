"""
KDMARCHE × O'SCOP - ABAC Policy Engine (Python Native)
Implements OPA-equivalent logic for B2B access control

Key Rules:
- Pricing visible only if: org APPROVED + subscription ACTIVE + partner ACCESS_ENABLED + zone entitled
- Orders allowed only if: above + role is OWNER/BUYER + EXW incoterm for OM zones
- Wallet consumption: org APPROVED + subscription ACTIVE + wallet ACTIVE + sufficient balance
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from schema_v2 import (
    OrgStatus, SubscriptionStatus, PartnerProvisionStatus, 
    WalletStatus, CustomerRole, OscopRole, KdmRole, ZoneKind
)


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


# ============== CONVENIENCE FUNCTIONS ==============
#
# NOTE: The previous helpers `check_pricing_access`, `check_order_access` and
# `check_wallet_consume` were removed in 2026-02 — they were never called from
# anywhere in the codebase (verified via grep). Routes call
# `ABACPolicyEngine().evaluate(input, data)` directly with the typed
# `PolicyInput` / `PolicyData` dataclasses, which keeps callsites explicit
# and avoids long positional argument lists (the previous helpers had 9–13
# positional args, which the code review flagged as error-prone).
#
# If a future caller needs a thin wrapper, prefer building a small
# `OrderAccessContext` / `PricingAccessContext` dataclass at the call site
# rather than reintroducing a wide-signature function.


# ============== PREP OPTIONS POLICY (OPA/REGO STYLE) ==============

class PrepOptionsPolicy:
    """
    OPA/Rego-style policy for preparation options
    
    Rule: Option préparation autorisée uniquement si enabled=true pour la zone
    
    Example input:
    {
      "action": "kdm.prep_options.apply",
      "resource": {
        "org_id": "o1",
        "zone_id": "GUADELOUPE",
        "selections": [
          {"code":"PREP_PALLET","qty":2},
          {"code":"PREP_CONTAINER","qty":1}
        ]
      },
      "subject": {"org_id":"o1","roles":["CUSTOMER_ORG_BUYER"]}
    }
    """
    
    def __init__(self, zones_config: Dict[str, Any]):
        self.zones_config = zones_config
    
    def evaluate(self, action: str, resource: Dict, subject: Dict) -> Dict:
        """Evaluate policy for given input"""
        deny_reasons = []
        warnings = []
        
        if action != "kdm.prep_options.apply":
            return {"allow": True, "warnings": ["Action non concernée"]}
        
        zone_id = resource.get("zone_id")
        selections = resource.get("selections", [])
        
        # Rule 1: Zone must exist
        if not self._zone_exists(zone_id):
            return {"allow": False, "deny_reasons": ["ZONE_UNKNOWN_FOR_PREP_OPTIONS"]}
        
        zone_config = self.zones_config.get(zone_id, {})
        prep_options = zone_config.get("prep_options", {})
        
        # Evaluate each selection
        for selection in selections:
            code = selection.get("code")
            qty = selection.get("qty", 0)
            
            if code not in prep_options:
                deny_reasons.append(f"PREP_OPTION_UNKNOWN:{code}")
                continue
            
            option_config = prep_options.get(code, {})
            
            if not option_config.get("enabled", False):
                deny_reasons.append(f"PREP_OPTION_DISABLED_FOR_ZONE:{code}")
                continue
            
            min_qty = option_config.get("min_qty", 0)
            max_qty = option_config.get("max_qty", 999999)
            if not (min_qty <= qty <= max_qty):
                deny_reasons.append(f"PREP_OPTION_QTY_OUT_OF_RANGE:{code}")
        
        return {
            "allow": len(deny_reasons) == 0,
            "deny_reasons": deny_reasons,
            "warnings": warnings
        }
    
    def _zone_exists(self, zone_id: str) -> bool:
        if not zone_id:
            return False
        zone = self.zones_config.get(zone_id)
        return zone is not None and zone.get("prep_options") is not None


class KDMarcheAccessPolicyV2:
    """
    Policy principale KDMARCHE V2 avec intégration des sous-policies
    """
    
    ALLOWED_ROLES = [
        "CUSTOMER_ORG_BUYER", "CUSTOMER_ORG_ADMIN",
        "KDM_B2B_ADMIN", "KDM_FINANCE", "KDM_WAREHOUSE", "SUPER_ADMIN"
    ]
    
    def __init__(self, zones_config: Dict[str, Any], allowed_zones: Optional[List[str]] = None):
        self.zones_config = zones_config
        self.allowed_zones = allowed_zones
        self.prep_policy = PrepOptionsPolicy(zones_config)
    
    def evaluate(self, action: str, resource: Dict, subject: Dict) -> Dict:
        deny_reasons = []
        
        # Check base access
        roles = subject.get("roles", [])
        if not any(r in self.ALLOWED_ROLES for r in roles):
            deny_reasons.append("BASE_ACCESS_DENIED")
        
        # Check zone is allowed
        zone_id = resource.get("zone_id")
        if zone_id and self.allowed_zones and zone_id not in self.allowed_zones:
            deny_reasons.append(f"ZONE_NOT_ALLOWED:{zone_id}")
        
        # For prep_options.apply action, delegate to prep policy
        if action == "kdm.prep_options.apply":
            prep_result = self.prep_policy.evaluate(action, resource, subject)
            deny_reasons.extend(prep_result.get("deny_reasons", []))
        
        return {
            "allow": len(deny_reasons) == 0,
            "deny_reasons": deny_reasons
        }


def build_zones_config_from_db(zones: List[Dict], options: List[Dict]) -> Dict[str, Any]:
    """Build zones_config JSON from database records"""
    config = {}
    
    options_by_zone = {}
    for opt in options:
        zone_code = opt.get("zone_code")
        if zone_code not in options_by_zone:
            options_by_zone[zone_code] = {}
        
        code = opt.get("code")
        options_by_zone[zone_code][code] = {
            "enabled": opt.get("enabled", False),
            "min_qty": opt.get("min_qty", 1),
            "max_qty": opt.get("max_qty", 999999),
            "pricing_mode": opt.get("pricing_mode"),
            "unit_price_ht_cents": opt.get("price_ht_cents"),
            "tva_rate": opt.get("tva_rate"),
            "tva_exonerated": opt.get("tva_exonerated", False),
        }
    
    for zone in zones:
        code = zone.get("code")
        config[code] = {
            "label": zone.get("label"),
            "kind": zone.get("kind"),
            "vat_rate": zone.get("vat_rate"),
            "is_active": zone.get("is_active", True),
            "prep_options": options_by_zone.get(code, {})
        }
    
    return config


def export_zones_config_to_json(zones_config: Dict) -> Dict:
    """Export zones_config to standardized JSON format"""
    return {
        "version": "1.0",
        "default_zone": list(zones_config.keys())[0] if zones_config else None,
        "zones": zones_config,
        "exported_at": datetime.utcnow().isoformat()
    }

