#!/usr/bin/env bash
# Installs kind, kubectl and helm if missing. Safe to run many times.
set -euo pipefail

KIND_VERSION=v0.24.0
KUBECTL_VERSION=v1.31.0
ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH=amd64; [ "$ARCH" = "aarch64" ] && ARCH=arm64

have() { command -v "$1" >/dev/null 2>&1; }

if ! have kind; then
  echo ">> installing kind $KIND_VERSION"
  curl -fsSLo /tmp/kind "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${ARCH}"
  sudo install -m 0755 /tmp/kind /usr/local/bin/kind
fi

# kubectl must be within ONE minor version of the cluster (v1.31 here), so check the
# version, not just whether kubectl exists. Codespaces often preinstall a newer one.
want_minor=$(echo "$KUBECTL_VERSION" | cut -d. -f2)
have_minor=$(kubectl version --client -o json 2>/dev/null | grep -m1 '"minor"' | tr -dc '0-9')
if ! have kubectl || [ "$have_minor" != "$want_minor" ]; then
  echo ">> installing kubectl $KUBECTL_VERSION (found minor: ${have_minor:-none})"
  curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl"
  sudo install -m 0755 /tmp/kubectl /usr/local/bin/kubectl
fi

if ! have helm; then
  echo ">> installing helm"
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# Quality of life: `k` alias + tab completion (added once)
if ! grep -q "quickbite-k8s-aliases" ~/.bashrc 2>/dev/null; then
  cat >> ~/.bashrc <<'RC'
# quickbite-k8s-aliases
source <(kubectl completion bash)
alias k=kubectl
complete -o default -F __start_kubectl k
export KUBE_EDITOR=nano
RC
fi

echo ">> tools ready:"
echo "   kind    $(kind version | awk '{print $2}')"
echo "   kubectl $(kubectl version --client -o json | grep -m1 gitVersion | cut -d'"' -f4)"
echo "   helm    $(helm version --short)"
