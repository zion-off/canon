#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Colors ──────────────────────────────────────────────────────────
if [ -t 1 ]; then
  BOLD="\033[1m"; DIM="\033[2m"
  RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"
  BLUE="\033[34m"; CYAN="\033[36m"
  RESET="\033[0m"
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""
  BLUE=""; CYAN=""; RESET=""
fi

say()    { printf "%b%s%b\n" "$1" "$2" "$RESET"; }
header() { say "$BOLD$BLUE" "$1"; }
step()   { say "$CYAN" "  → $1"; }
ok()     { say "$GREEN" "  ✓ $1"; }
err()    { say "$RED" "  ✗ $1"; }

missing=()

# ── Python ──────────────────────────────────────────────────────────
REQUIRED_PYTHON="3.14"

if command -v python3 &>/dev/null; then
  py_ver="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  if printf '%s\n%s\n' "$REQUIRED_PYTHON" "$py_ver" | sort -V -C 2>/dev/null || \
     [ "$(printf '%s\n%s\n' "$REQUIRED_PYTHON" "$py_ver" | sort -V | head -1)" = "$REQUIRED_PYTHON" ]; then
    ok "python3 $py_ver (need ≥$REQUIRED_PYTHON)"
  else
    err "python3 $py_ver — need ≥$REQUIRED_PYTHON"
    missing+=("python3 ≥$REQUIRED_PYTHON")
  fi
else
  err "python3 not found"
  missing+=("python3 ≥$REQUIRED_PYTHON")
fi

# ── Node ────────────────────────────────────────────────────────────
REQUIRED_NODE="18"

if command -v node &>/dev/null; then
  node_ver="$(node -v | sed 's/^v//')"
  node_major="$(echo "$node_ver" | cut -d. -f1)"
  if [ "$node_major" -ge "$REQUIRED_NODE" ] 2>/dev/null; then
    ok "node $node_ver (need ≥$REQUIRED_NODE)"
  else
    err "node $node_ver — need ≥$REQUIRED_NODE"
    missing+=("node ≥$REQUIRED_NODE")
  fi
else
  err "node not found"
  missing+=("node ≥$REQUIRED_NODE")
fi

# ── uv ──────────────────────────────────────────────────────────────
if command -v uv &>/dev/null; then
  uv_ver="$(uv --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  ok "uv ${uv_ver:-installed}"
else
  err "uv not found"
  missing+=("uv (https://docs.astral.sh/uv/)")
fi

# ── pnpm ────────────────────────────────────────────────────────────
if command -v pnpm &>/dev/null; then
  pnpm_ver="$(pnpm --version 2>/dev/null)"
  ok "pnpm $pnpm_ver"
else
  err "pnpm not found"
  missing+=("pnpm (https://pnpm.io/installation)")
fi

# ── Docker ──────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
  docker_ver="$(docker --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  ok "docker ${docker_ver:-installed}"
else
  err "docker not found"
  missing+=("docker (https://docs.docker.com/get-docker/)")
fi

# ── gcloud credentials ─────────────────────────────────────────────
GCLOUD_CREDS="$HOME/.config/gcloud/application_default_credentials.json"
if [ -f "$GCLOUD_CREDS" ]; then
  ok "gcloud ADC found at $GCLOUD_CREDS"
else
  err "gcloud ADC not found at $GCLOUD_CREDS"
  missing+=("gcloud ADC (run: gcloud auth application-default login)")
fi

if [ ${#missing[@]} -gt 0 ]; then
  echo ""
  say "$BOLD$RED" "Missing prerequisites:"
  for m in "${missing[@]}"; do
    say "$YELLOW" "  • $m"
  done
  exit 1
fi

# ── .env ────────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  step "Creating .env from .env.example..."
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  ok ".env created (edit with your secrets)"
else
  ok ".env already exists — skipping"
fi

echo ""

# ── Backend venv ────────────────────────────────────────────────────
header "Backend"
step "Syncing backend dependencies..."
cd "$PROJECT_ROOT/backend"
uv sync
ok "Backend venv ready"

# ── MCP venv ────────────────────────────────────────────────────────
header "MCP Server"
step "Syncing MCP dependencies..."
cd "$PROJECT_ROOT/mcp"
uv sync
ok "MCP venv ready"

# ── Frontend ────────────────────────────────────────────────────────
header "Frontend"
step "Installing frontend dependencies..."
cd "$PROJECT_ROOT/frontend"
pnpm install --frozen-lockfile
ok "Frontend packages installed"

# ── Banner ──────────────────────────────────────────────────────────
echo ""
say "$BOLD$GREEN" "✓ All dependencies installed."
echo ""
say "$DIM" "────────────────────────────────────────────"
say "$BOLD$YELLOW" "Next steps:"
echo ""
say "$YELLOW" "  1. Install the gcloud CLI:"
say "$DIM"      "     https://cloud.google.com/sdk/docs/install"
echo ""
say "$YELLOW" "  2. Set up Application Default Credentials:"
say "$DIM"      "     gcloud auth application-default login"
echo ""
say "$DIM" "────────────────────────────────────────────"
