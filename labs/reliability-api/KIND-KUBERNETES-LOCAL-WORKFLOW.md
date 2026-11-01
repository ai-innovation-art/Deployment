# ☸️ Special Guide: Local Kubernetes Cluster with Kind & Offline Image Loading

> **Core Lesson:** Kubernetes runs in its own containerized runtime (`containerd`). By default, it always attempts to fetch images from public registries over the internet (`docker.io`, `ghcr.io`). To run locally built images without pushing them to the public internet, you must inject them directly into the cluster node using `kind load` and specify `imagePullPolicy: Never` (or `IfNotPresent`).

---

## 1. Environment Setup: Installing Kind & Verifying Kubectl

### Step 1.1: Download & Install Kind Binary (Linux AMD64)
```bash
# Download official Kind binary v0.25.0
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64

# Grant execute permissions
chmod +x ./kind

# Move binary into system PATH
sudo mv ./kind /usr/local/bin/kind

# Verify installation
kind --version
```

### Step 1.2: Verify Kubectl Client
```bash
kubectl version --client
```

---

## 2. Cluster Creation & Architecture

### Step 2.1: Spin Up the Kind Cluster
```bash
kind create cluster --name reliability-lab
```

#### What Kind Does Behind the Scenes:
1. Pulls the multi-arch node base image: `kindest/node:v1.31.2`.
2. Starts a Docker container named `reliability-lab-control-plane` to emulate a physical/virtual Linux node.
3. Generates the Kubernetes PKI certificates and cluster configuration.
4. Starts the core control plane components:
   * **`etcd`**: Key-value state storage.
   * **`kube-apiserver`**: The REST API gateway.
   * **`kube-controller-manager`**: Reconciles cluster state (node lifecycle, replica counts).
   * **`kube-scheduler`**: Assigns Pods to healthy nodes.
5. Installs the Container Network Interface (CNI - `kindnet`) for Pod-to-Pod networking.
6. Installs a local dynamic `StorageClass` (Rancher `local-path-provisioner`).
7. Updates your local `~/.kube/config` and sets context to `kind-reliability-lab`.

### Step 2.2: Verify Cluster Nodes
```bash
kubectl get nodes
```
* Status will initially show `NotReady` for ~10–15 seconds while CNI network bridges initialize, then transition to **`Ready`**.

---

## 3. Injecting Local Images (`kind load`)

### The Architecture Problem:
```text
[ Host Machine (Codespace) ]
  ├── Docker Daemon (Holds local image: reliability-api:0.1.0)
  │
  └── [ Docker Container: reliability-lab-control-plane ]
        └── containerd Daemon (Separate image store isolated from host!)
```
Kubernetes pods do not have direct access to your host machine's Docker daemon.

### Step 3.1: Ensure Local Image Exists with Matching Tag
```bash
docker tag kumawatsunil/reliability-api:latest reliability-api:0.1.0
```

### Step 3.2: Load Image into the Kind Node
```bash
kind load docker-image reliability-api:0.1.0 --name reliability-lab
```

### Step 3.3: Inspect the Node's containerd Cache
Prove the image exists inside the Kubernetes node using `crictl` (Container Runtime Interface CLI):
```bash
docker exec -it reliability-lab-control-plane crictl images | grep reliability-api
```
Output confirms the presence of `docker.io/library/reliability-api:0.1.0` inside containerd.

---

## 4. Running Your First Kubernetes Workload (Pod)

### Step 4.1: Launch Pod with `Never` Pull Policy
```bash
kubectl run my-first-pod --image=reliability-api:0.1.0 --image-pull-policy=Never
```

| Flag | Why it is Critical |
| :--- | :--- |
| `--image=reliability-api:0.1.0` | Points to the image name we loaded into the node. |
| `--image-pull-policy=Never` | Strictly commands kubelet: **Do NOT query Docker Hub / internet**. Use the local containerd cache. If omitted with tag `:latest`, default policy is `Always`, causing `ErrImagePull`! |

### Step 4.2: Inspect Running Pods
```bash
kubectl get pods
```

To see real-time startup details and health events:
```bash
kubectl describe pod my-first-pod
```

To view live container logs:
```bash
kubectl logs my-first-pod
```

### Step 4.3: Port-Forward to Test Endpoint Locally
```bash
kubectl port-forward pod/my-first-pod 8080:8000
```
In a separate terminal:
```bash
curl http://localhost:8080/health
```

---

## 5. Cleanup Commands

```bash
# Delete the test pod
kubectl delete pod my-first-pod

# Delete the entire Kind cluster and all resources
kind delete cluster --name reliability-lab
```
