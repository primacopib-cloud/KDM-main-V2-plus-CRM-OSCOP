#!/usr/bin/env bash
# ============================================================
# KDMARCHE — build_opa_bundle.sh (MongoDB version)
# - Exporte opa_data_json depuis MongoDB via Python/FastAPI
# - Écrit bundle/data.json
# - Copie les policies Rego
# - Génère bundle.tar.gz (structure standard OPA)
#
# Prérequis:
#   - bash, curl, tar, jq (optional)
#   - Backend FastAPI en cours d'exécution
#   - Variables d'environnement:
#       API_BASE_URL  (default: http://localhost:8001)
#
# Utilisation:
#   chmod +x build_opa_bundle.sh
#   ./build_opa_bundle.sh
#
# Options:
#   API_BASE_URL=http://localhost:8001
#   BUNDLE_DIR=./bundle
#   POLICY_SRC_DIR=./opa_bundle/policy
#   OUT_TGZ=./bundle.tar.gz
# ============================================================

set -euo pipefail

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8001}"
BUNDLE_DIR="${BUNDLE_DIR:-./bundle}"
POLICY_SRC_DIR="${POLICY_SRC_DIR:-./opa_bundle/policy}"
OUT_TGZ="${OUT_TGZ:-./bundle.tar.gz}"
DATA_FILE="${BUNDLE_DIR}/data.json"
POLICY_DST_DIR="${BUNDLE_DIR}/policy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ---- sanity checks ----
if ! command -v curl >/dev/null 2>&1; then
  log_error "curl not found. Install curl."
  exit 1
fi
if ! command -v tar >/dev/null 2>&1; then
  log_error "tar not found."
  exit 1
fi

if [ ! -d "${POLICY_SRC_DIR}" ]; then
  log_error "POLICY_SRC_DIR '${POLICY_SRC_DIR}' not found."
  log_error "Create it and place your .rego files inside (kdm_incoterm.rego, kdm_prep_options.rego, kdm_delivery.rego, kdm_order_create.rego)."
  exit 1
fi

# ---- create bundle dirs ----
log_info "Creating bundle directories..."
mkdir -p "${BUNDLE_DIR}"
mkdir -p "${POLICY_DST_DIR}"

# ---- Export data.json from MongoDB via API ----
log_info "Exporting OPA data.json from MongoDB via API (${API_BASE_URL}/api/opa/bundle/data.json)..."

HTTP_CODE=$(curl -s -w "%{http_code}" -o "${DATA_FILE}" "${API_BASE_URL}/api/opa/bundle/data.json")

if [ "$HTTP_CODE" != "200" ]; then
  log_error "Failed to fetch data.json from API (HTTP $HTTP_CODE)"
  log_error "Make sure the backend is running and accessible at ${API_BASE_URL}"
  cat "${DATA_FILE}" 2>/dev/null || true
  exit 1
fi

# Basic validation
if [ ! -s "${DATA_FILE}" ]; then
  log_error "data.json export failed (empty file)."
  exit 1
fi

# Validate JSON structure
if command -v jq >/dev/null 2>&1; then
  if ! jq empty "${DATA_FILE}" 2>/dev/null; then
    log_error "data.json is not valid JSON."
    exit 1
  fi
  
  # Show summary
  ZONES_CONFIG=$(jq -r '.zones_config | keys | length' "${DATA_FILE}" 2>/dev/null || echo "?")
  ZONES_POLICY=$(jq -r '.zones_policy | keys | length' "${DATA_FILE}" 2>/dev/null || echo "?")
  DELIVERY_POLICY=$(jq -r '.delivery_policy | keys | length' "${DATA_FILE}" 2>/dev/null || echo "?")
  VERSION=$(jq -r '.version // "unknown"' "${DATA_FILE}" 2>/dev/null || echo "?")
  
  log_info "data.json summary:"
  echo "   - Version: ${VERSION}"
  echo "   - zones_config: ${ZONES_CONFIG} zones"
  echo "   - zones_policy: ${ZONES_POLICY} zones"
  echo "   - delivery_policy: ${DELIVERY_POLICY} zones"
else
  log_warn "jq not installed, skipping JSON validation"
fi

# ---- copy policies ----
log_info "Copying policies from ${POLICY_SRC_DIR} -> ${POLICY_DST_DIR} ..."

# Copy only .rego files
find "${POLICY_SRC_DIR}" -maxdepth 1 -type f -name "*.rego" -print0 | while IFS= read -r -d '' f; do
  cp -f "$f" "${POLICY_DST_DIR}/"
  log_info "  Copied: $(basename "$f")"
done

# Ensure required policies exist
REQ_POLICIES=("kdm_incoterm.rego" "kdm_prep_options.rego" "kdm_delivery.rego" "kdm_order_create.rego")
missing=0
for p in "${REQ_POLICIES[@]}"; do
  if [ ! -f "${POLICY_DST_DIR}/${p}" ]; then
    log_warn "Missing policy file in bundle: ${p}"
    missing=1
  fi
done

if [ "${missing}" -eq 1 ]; then
  log_error "One or more required .rego files are missing. Add them to ${POLICY_SRC_DIR} and rerun."
  exit 1
fi

# ---- create .manifest for OPA ----
log_info "Creating OPA manifest..."
cat > "${BUNDLE_DIR}/.manifest" << EOF
{
  "revision": "$(date +%Y%m%d%H%M%S)",
  "roots": ["zones_config", "zones_policy", "delivery_policy"]
}
EOF

# ---- create tar.gz (bundle root) ----
log_info "Creating ${OUT_TGZ} ..."

# Tar the contents of BUNDLE_DIR as bundle root (data.json + policy/ + .manifest)
tar -czf "${OUT_TGZ}" -C "${BUNDLE_DIR}" .

# Show bundle contents
log_info "Bundle contents:"
tar -tzf "${OUT_TGZ}" | sed 's/^/   /'

# Calculate size
BUNDLE_SIZE=$(du -h "${OUT_TGZ}" | cut -f1)

echo ""
log_info "✅ Done."
echo "   - data.json: ${DATA_FILE}"
echo "   - policies:  ${POLICY_DST_DIR}"
echo "   - bundle:    ${OUT_TGZ} (${BUNDLE_SIZE})"
echo ""
log_info "To use with OPA:"
echo "   opa run --server --bundle ${OUT_TGZ}"
echo ""
log_info "Or download directly from API:"
echo "   curl -o bundle.tar.gz ${API_BASE_URL}/api/opa/bundle/download"
