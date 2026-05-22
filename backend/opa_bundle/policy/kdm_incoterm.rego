package oscop.kdm.incoterm

default allow := false
default deny := []

zone_code := upper(input.resource.zone_code)
policy := data.zones_policy[zone_code]

zone_known { policy != null }
exw_required { zone_known; policy.exw_only == true }

deny[msg] {
  input.action == "kdm.order.create"
  not zone_known
  msg := "ZONE_UNKNOWN"
}

deny[msg] {
  input.action == "kdm.order.create"
  exw_required
  upper(input.resource.incoterm) != "EXW"
  msg := "INCOTERM_NOT_ALLOWED_EXW_ONLY"
}

deny[msg] {
  input.action == "kdm.order.create"
  zone_known
  policy.pickup_required == true
  (not input.resource.pickup_location_id) or input.resource.pickup_location_id == ""
  msg := "PICKUP_LOCATION_REQUIRED_FOR_EXW"
}

allow {
  input.action == "kdm.order.create"
  zone_known
  (not exw_required) or upper(input.resource.incoterm) == "EXW"
  (policy.pickup_required == false) or (input.resource.pickup_location_id != "")
}
