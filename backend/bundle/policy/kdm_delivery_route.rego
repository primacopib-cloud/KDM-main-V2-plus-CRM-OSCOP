package oscop.kdm.route

# ESS Route (Tournées Mutualisées) Policy
# Rules for ESS_ROUTE delivery mode: capacity, priority, eligibility

default allow := false
default deny := []

# Input structure expected:
# {
#   "action": "kdm.delivery.quote",
#   "resource": {
#     "zone_code": "GUADELOUPE",
#     "delivery_mode": "ESS_ROUTE",
#     "delivery_window": {"start": "08:00", "end": "12:00"},
#     "tour_id": "TOUR-GP-2026W03-THU-AM"
#   },
#   "subject": {
#     "org_id": "org_123",
#     "reliability_score": 85,
#     "roles": ["CUSTOMER_ORG_BUYER"]
#   }
# }

# Zone and policy lookup
zone := upper(input.resource.zone_code)
pol := data.route_policy[zone]

# Checks
zone_known { pol != null }

is_ess_route { upper(input.resource.delivery_mode) == "ESS_ROUTE" }

# Optional org reliability score passed by gateway/app
org_score := input.subject.reliability_score

# ============== DENY RULES ==============

# Zone unknown for ESS Route
deny[msg] {
  input.action == "kdm.delivery.quote"
  is_ess_route
  not zone_known
  msg := "ESS_ROUTE_ZONE_UNKNOWN"
}

# ESS Route disabled for zone
deny[msg] {
  input.action == "kdm.delivery.quote"
  is_ess_route
  zone_known
  pol.ess_route_enabled != true
  msg := "ESS_ROUTE_DISABLED_FOR_ZONE"
}

# Delivery window required for ESS Route
deny[msg] {
  input.action == "kdm.delivery.quote"
  is_ess_route
  zone_known
  pol.window_required == true
  not input.resource.delivery_window.start
  msg := "ESS_ROUTE_DELIVERY_WINDOW_REQUIRED"
}

deny[msg] {
  input.action == "kdm.delivery.quote"
  is_ess_route
  zone_known
  pol.window_required == true
  not input.resource.delivery_window.end
  msg := "ESS_ROUTE_DELIVERY_WINDOW_REQUIRED"
}

# Priority score too low
deny[msg] {
  input.action == "kdm.delivery.quote"
  is_ess_route
  zone_known
  org_score < pol.min_reliability_score
  msg := "ESS_ROUTE_PRIORITY_SCORE_TOO_LOW"
}

# Capacity check if tour_id provided
deny[msg] {
  input.action == "kdm.delivery.quote"
  is_ess_route
  zone_known
  tid := input.resource.tour_id
  tid != ""
  cap := data.route_capacity[zone][tid]
  cap.booked >= cap.capacity
  msg := "ESS_ROUTE_TOUR_CAPACITY_FULL"
}

# ============== ALLOW RULES ==============

# Allow ESS Route if all conditions met
allow {
  input.action == "kdm.delivery.quote"
  is_ess_route
  zone_known
  pol.ess_route_enabled == true
  count(deny) == 0
}

# For non-ESS_ROUTE delivery mode, this policy does not apply
allow {
  input.action == "kdm.delivery.quote"
  not is_ess_route
}

# ============== PRIORITY CALCULATION ==============
# Calculates priority score for tour placement

priority_score := score {
  is_ess_route
  zone_known
  rules := pol.priority_rules
  base := org_score
  
  # Calculate weighted score from priority rules
  weighted_sum := sum([r.weight | r := rules[_]; r.code == "COMPLIANCE_OK"; org_score >= pol.min_reliability_score])
  
  score := base + weighted_sum
}

# Priority reason code for audit trail
priority_reason_code := code {
  is_ess_route
  zone_known
  count(deny) == 0
  code := "COMPLIANCE_OK"
}

priority_reason_code := code {
  is_ess_route
  zone_known
  count(deny) > 0
  code := deny[0]
}
