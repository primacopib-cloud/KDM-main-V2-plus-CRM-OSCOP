package oscop.kdm.order

import data.oscop.kdm.incoterm
import data.oscop.kdm.prep
import data.oscop.kdm.delivery

default allow := false
default deny := []

# Deny from incoterm policy
deny[msg] {
  input.action == "kdm.order.create"
  not incoterm.allow
  msg := incoterm.deny[_]
}

# Deny from prep options policy
deny[msg] {
  input.action == "kdm.order.create"
  not prep.allow
  msg := prep.deny[_]
}

# Deny from delivery policy (if delivery mode selected)
deny[msg] {
  input.action == "kdm.order.create"
  input.resource.fulfillment_mode
  upper(input.resource.fulfillment_mode) == "DELIVERY"
  not delivery.allow
  msg := delivery.deny[_]
}

# Allow if no deny reasons
allow {
  input.action == "kdm.order.create"
  not deny[_]
}
