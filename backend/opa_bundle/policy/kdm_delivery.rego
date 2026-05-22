package oscop.kdm.delivery

# LOGI'SCOP Delivery Policy
# Règles pour la sélection du mode de livraison (EXW local vs LOGI'SCOP delivery)

default allow := false
default deny := []

# Input structure expected:
# {
#   "action": "kdm.delivery.select",
#   "resource": {
#     "zone_code": "GUADELOUPE",
#     "fulfillment_mode": "EXW" | "DELIVERY",
#     "pickup_location_id": "PU-971-01",  # Required if EXW
#     "delivery_address": {...},           # Required if DELIVERY
#     "delivery_slot": "AM" | "PM" | "EXPRESS" | "RDV",
#     "weight_kg": 50,
#     "volume_m3": 0.5,
#     "goods_value_cents": 150000
#   },
#   "subject": {
#     "org_id": "org_123",
#     "roles": ["CUSTOMER_ORG_BUYER"]
#   }
# }

# Zone and policy lookup
zone_code := upper(input.resource.zone_code)
delivery_policy := data.delivery_policy[zone_code]

# Checks
zone_known { delivery_policy != null }
fulfillment_mode := upper(input.resource.fulfillment_mode)
is_exw { fulfillment_mode == "EXW" }
is_delivery { fulfillment_mode == "DELIVERY" }

# Delivery availability check
delivery_available { 
  zone_known
  delivery_policy.delivery_enabled == true 
}

# Minimum weight for delivery
min_weight_ok {
  zone_known
  input.resource.weight_kg >= delivery_policy.min_weight_kg
}

# Maximum weight for delivery
max_weight_ok {
  zone_known
  input.resource.weight_kg <= delivery_policy.max_weight_kg
}

# Minimum value for delivery (some zones require minimum order value)
min_value_ok {
  zone_known
  not delivery_policy.min_value_cents
}

min_value_ok {
  zone_known
  input.resource.goods_value_cents >= delivery_policy.min_value_cents
}

# ============== DENY RULES ==============

# Zone unknown
deny[msg] {
  input.action == "kdm.delivery.select"
  not zone_known
  msg := "ZONE_UNKNOWN"
}

# DELIVERY mode selected but not available in zone
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  zone_known
  not delivery_available
  msg := "DELIVERY_NOT_AVAILABLE_FOR_ZONE"
}

# DELIVERY mode: minimum weight not met
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  delivery_available
  not min_weight_ok
  msg := "DELIVERY_MIN_WEIGHT_NOT_MET"
}

# DELIVERY mode: maximum weight exceeded
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  delivery_available
  not max_weight_ok
  msg := "DELIVERY_MAX_WEIGHT_EXCEEDED"
}

# DELIVERY mode: minimum order value not met
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  delivery_available
  delivery_policy.min_value_cents
  not min_value_ok
  msg := "DELIVERY_MIN_VALUE_NOT_MET"
}

# DELIVERY mode: delivery address required but missing
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  not input.resource.delivery_address
  msg := "DELIVERY_ADDRESS_REQUIRED"
}

deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  input.resource.delivery_address
  not input.resource.delivery_address.street
  msg := "DELIVERY_ADDRESS_INCOMPLETE"
}

deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  input.resource.delivery_address
  not input.resource.delivery_address.city
  msg := "DELIVERY_ADDRESS_INCOMPLETE"
}

deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  input.resource.delivery_address
  not input.resource.delivery_address.postal_code
  msg := "DELIVERY_ADDRESS_INCOMPLETE"
}

# EXW mode: pickup location required but missing
deny[msg] {
  input.action == "kdm.delivery.select"
  is_exw
  zone_known
  delivery_policy.pickup_required == true
  not input.resource.pickup_location_id
  msg := "PICKUP_LOCATION_REQUIRED_FOR_EXW"
}

deny[msg] {
  input.action == "kdm.delivery.select"
  is_exw
  zone_known
  delivery_policy.pickup_required == true
  input.resource.pickup_location_id == ""
  msg := "PICKUP_LOCATION_REQUIRED_FOR_EXW"
}

# Invalid delivery slot
valid_slots := ["AM", "PM", "EXPRESS", "RDV"]
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  slot := upper(input.resource.delivery_slot)
  not valid_slots[_] == slot
  msg := "INVALID_DELIVERY_SLOT"
}

# EXPRESS slot: check if enabled for zone
deny[msg] {
  input.action == "kdm.delivery.select"
  is_delivery
  upper(input.resource.delivery_slot) == "EXPRESS"
  zone_known
  delivery_policy.express_enabled == false
  msg := "EXPRESS_DELIVERY_NOT_AVAILABLE"
}

# ============== ALLOW RULE ==============

allow {
  input.action == "kdm.delivery.select"
  zone_known
  not deny[_]
}
