#!/usr/bin/env bash
# =====================================================================
#  resume.sh: get back to a known checkpoint with ONE command.
#
#    ./scripts/resume.sh            -> checkpoint "app"   (cluster + full QuickBite running)
#    ./scripts/resume.sh cluster    -> checkpoint "cluster" (empty 3-node cluster, for Chapter 1)
#
#  Works for all three situations:
#    1. Brand-new Codespace       -> installs tools, creates cluster, deploys
#    2. Codespace was stopped     -> restarts the kind node containers, re-deploys
#    3. Everything already running -> just re-applies (no-op) and prints status
#  Images come from Docker Hub (kumawatsunil/*), so nothing is rebuilt.
# =====================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

CHECKPOINT=${1:-app}
CLUSTER=quickbite
NS=quickbite

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

step "1/4 tools"
bash scripts/install-tools.sh >/dev/null && echo "kind, kubectl, helm present"

step "2/4 cluster '$CLUSTER'"
if kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  stopped=$(docker ps -a --filter "label=io.x-k8s.kind.cluster=$CLUSTER" --filter status=exited -q)
  if [ -n "$stopped" ]; then
    echo "node containers were stopped (Codespace restart) -> starting them"
    docker start $stopped >/dev/null
  fi
  kubectl config use-context "kind-$CLUSTER" >/dev/null
  echo "waiting for the API server..."
  if ! timeout 120 bash -c 'until kubectl get --raw=/readyz >/dev/null 2>&1; do sleep 2; done'; then
    echo "API server did not come back -> recreating the cluster"
    kind delete cluster --name "$CLUSTER"
    kind create cluster --config k8s/cluster/kind-3node.yaml
  fi
else
  kind create cluster --config k8s/cluster/kind-3node.yaml
fi
kubectl wait --for=condition=Ready nodes --all --timeout=180s

if [ "$CHECKPOINT" = "cluster" ]; then
  step "3/4 checkpoint 'cluster': removing QuickBite if present"
  kubectl delete namespace "$NS" --ignore-not-found --wait=true
  step "4/4 status"
  kubectl get nodes -o wide
  exit 0
fi

step "3/4 checkpoint 'app': deploying QuickBite (kubectl apply -k k8s/base)"
kubectl apply -k k8s/base
echo "waiting for workloads to become ready..."
kubectl -n "$NS" rollout status statefulset/postgres --timeout=180s
for d in redis menu-api orders-api notifier web; do
  kubectl -n "$NS" rollout status "deployment/$d" --timeout=240s
done

step "4/4 status"
kubectl get nodes
kubectl -n "$NS" get pods -o wide
echo
echo "QuickBite is up: open the PORTS tab in VS Code -> port 8080 (or: curl -s localhost:8080/api/version)"
