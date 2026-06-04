#!/usr/bin/env bash
# Install gitleaks, syft, and grype for the SCR pipeline.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${SCR_TOOLS_BIN:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"

install_gitleaks() {
  if command -v gitleaks >/dev/null 2>&1; then
    echo "gitleaks already installed: $(gitleaks version 2>/dev/null | head -1 || true)"
    return
  fi
  echo "Installing gitleaks..."
  curl -sSfL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_x64.tar.gz \
    | tar -xz -C /tmp
  install -m 755 /tmp/gitleaks "$BIN_DIR/gitleaks"
}

install_syft() {
  if command -v syft >/dev/null 2>&1; then
    echo "syft already installed: $(syft version 2>/dev/null | head -1 || true)"
    return
  fi
  echo "Installing syft..."
  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b "$BIN_DIR"
}

install_grype() {
  if command -v grype >/dev/null 2>&1; then
    echo "grype already installed: $(grype version 2>/dev/null | head -1 || true)"
    return
  fi
  echo "Installing grype..."
  curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b "$BIN_DIR"
}

install_gitleaks
install_syft
install_grype

echo ""
echo "Installed to $BIN_DIR — ensure it is on PATH:"
echo "  export PATH=\"$BIN_DIR:\$PATH\""
echo ""
command -v gitleaks && command -v syft && command -v grype && echo "All SCR tools available."
