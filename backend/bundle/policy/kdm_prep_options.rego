package oscop.kdm.prep

default allow := false
default deny := []

zone_code := upper(input.resource.zone_code)
zone := data.zones_config[zone_code]

zone_exists { zone != null }
opt_cfg(code) := zone.prep_options[code]

option_exists(code) { opt_cfg(code) != null }
option_enabled(code) { opt_cfg(code).enabled == true }

qty_ok(code, qty) {
  min := opt_cfg(code).min_qty
  max := opt_cfg(code).max_qty
  qty >= min
  qty <= max
}

deny[msg] {
  input.action == "kdm.order.create"
  not zone_exists
  msg := "ZONE_UNKNOWN_FOR_PREP_OPTIONS"
}

deny[msg] {
  input.action == "kdm.order.create"
  some i
  sel := input.resource.prep_selections[i]
  not option_exists(sel.code)
  msg := sprintf("PREP_OPTION_UNKNOWN:%s", [sel.code])
}

deny[msg] {
  input.action == "kdm.order.create"
  some i
  sel := input.resource.prep_selections[i]
  option_exists(sel.code)
  not option_enabled(sel.code)
  msg := sprintf("PREP_OPTION_DISABLED_FOR_ZONE:%s", [sel.code])
}

deny[msg] {
  input.action == "kdm.order.create"
  some i
  sel := input.resource.prep_selections[i]
  option_exists(sel.code)
  option_enabled(sel.code)
  not qty_ok(sel.code, sel.qty)
  msg := sprintf("PREP_OPTION_QTY_OUT_OF_RANGE:%s", [sel.code])
}

allow {
  input.action == "kdm.order.create"
  zone_exists
  not deny[_]
}
