/**
 * ============================================================================
 * Kubernetes Interactive Animated Playground & Visual Architecture Engine
 * Pure Vanilla JavaScript — Zero External Dependencies
 * ============================================================================
 */

(function () {
  'use strict';

  // --- Master State Store ---
  const state = {
    currentTab: 'workloads', // 'workloads' | 'reliability' | 'networking' | 'storage_rbac'
    
    // Workloads & Scheduling
    workerNodeCount: 2, // 2 or 3
    replicas: 2,
    topologySpread: 'ScheduleAnyway', // 'DoNotSchedule' | 'ScheduleAnyway' | 'Disabled'
    maxSkew: 1,
    failedWorkerId: null, // node index if killed
    
    // Probes, Health & OOM
    memoryLimit: 256, // MiB
    memoryLeak: 64, // MiB
    startupProbeDelay: 2,
    readyDelaySeconds: 5,
    livenessHealthy: true,
    readinessHealthy: true,
    podRestarts: { 'pod-1': 0, 'pod-2': 0, 'pod-3': 0, 'pod-4': 0, 'pod-5': 0, 'pod-6': 0 },
    isOOMKilled: false,
    
    // Networking
    serviceType: 'ClusterIP', // 'ClusterIP' | 'NodePort'
    serviceSelector: 'reliability-api', // 'reliability-api' or 'wrong-name'
    ingressHost: 'localhost',
    ingressPath: '/api/health',
    
    // Config, Storage & RBAC
    configLogLevel: 'info',
    configReadyDelay: '5',
    pvcAttachedToPod: false,
    selectedServiceAccount: 'reliability-api-sa', // 'admin' | 'reliability-api-sa' | 'default'
    
    // Field Explanation Registry
    activeHighlightedLine: null
  };

  // --- Field Documentation Database (Hover/Click Hints) ---
  const fieldDocs = {
    'replicas': {
      title: 'spec.replicas',
      desc: 'The desired number of identical Pods that Kubernetes should maintain at all times.',
      impact: 'The ReplicaSet controller continuously checks current count vs desired count. If a pod crashes or is killed, it immediately resurrects a replacement in milliseconds.',
      bestPractice: 'Run at least 2 replicas in production across different worker nodes to ensure zero-downtime during node reboots.'
    },
    'topologySpreadConstraints': {
      title: 'spec.template.spec.topologySpreadConstraints',
      desc: 'Rules controlling how Pods are distributed across failure domains (Nodes, Availability Zones, or Racks).',
      impact: 'Prevents the scheduler from stacking all backend pods on a single server, protecting you from a single-point-of-failure.',
      bestPractice: 'Always combine maxSkew: 1 with topologyKey: kubernetes.io/hostname.'
    },
    'whenUnsatisfiable': {
      title: 'topologySpreadConstraints[].whenUnsatisfiable',
      desc: 'Determines what the scheduler does if pods cannot be evenly distributed. Options: DoNotSchedule vs ScheduleAnyway.',
      impact: 'CRITICAL: If set to DoNotSchedule on a small 2-node cluster with 3 pods, the 3rd pod will be permanently stuck in PENDING! ScheduleAnyway allows soft-balancing without blocking deployment.',
      bestPractice: 'Use ScheduleAnyway for local/small clusters; use DoNotSchedule for massive multi-AZ production clusters.'
    },
    'maxSkew': {
      title: 'topologySpreadConstraints[].maxSkew',
      desc: 'The maximum allowed difference in the number of matching pods between any two topology domains.',
      impact: 'maxSkew: 1 means Node A and Node B cannot differ by more than 1 pod count.',
      bestPractice: 'Keep at 1 for even round-robin distribution.'
    },
    'resources.limits.memory': {
      title: 'spec.containers[].resources.limits.memory',
      desc: 'Hard ceiling on the maximum RAM this container can consume. In our lab: 256Mi.',
      impact: 'DANGER: If container memory usage crosses this threshold even for 1 microsecond, the Linux kernel kills the container immediately with OOMKilled (Exit Code 137).',
      bestPractice: 'Always set memory limits slightly higher than peak traffic profile to prevent accidental OOM death.'
    },
    'livenessProbe': {
      title: 'spec.containers[].livenessProbe',
      desc: 'Periodic HTTP/TCP health check. Tells Kubernetes: "Is this container still alive and functioning?"',
      impact: 'If this probe fails consecutive failureThreshold times, Kubernetes immediately terminates the container and restarts it.',
      bestPractice: 'Never point livenessProbe to a database check; only check local application process health.'
    },
    'readinessProbe': {
      title: 'spec.containers[].readinessProbe',
      desc: 'Traffic gatekeeper. Tells Kubernetes: "Is this container ready to accept user network requests?"',
      impact: 'If readiness fails, Kubernetes strips the Pod IP from the Service Endpoints list instantly. Zero user traffic is sent to it, preventing 500 errors!',
      bestPractice: 'Always use readiness probes during rolling updates so traffic only hits fully warmed-up pods.'
    },
    'service.spec.selector': {
      title: 'Service.spec.selector',
      desc: 'The key=value label filter used by the Service to find which pods to route traffic to.',
      impact: 'THE #1 PRODUCTION BUG: If there is a typo (e.g. app: wrong-name), the Service Endpoints become <none> and all requests fail with 503 Service Unavailable or Connection Refused!',
      bestPractice: 'Ensure service.spec.selector exactly matches pod.metadata.labels.'
    },
    'service.spec.type': {
      title: 'Service.spec.type',
      desc: 'How the Service is exposed: ClusterIP (internal virtual IP only) vs NodePort (port 30000-32767 on all nodes) vs LoadBalancer (cloud hardware LB).',
      impact: 'ClusterIP is secure for internal microservices. NodePort exposes static ports directly on physical host machines.',
      bestPractice: 'Keep 90% of microservices on ClusterIP; expose the front door via Ingress.'
    },
    'pvc.accessModes': {
      title: 'PersistentVolumeClaim.spec.accessModes',
      desc: 'How the storage can be mounted: ReadWriteOnce (1 node at a time) vs ReadWriteMany (multi-node shared NFS/EFS).',
      impact: 'Databases use ReadWriteOnce. Shared media uploads use ReadWriteMany.',
      bestPractice: 'Use ReadWriteOnce for Postgres/Redis to prevent data corruption.'
    },
    'storageClass.volumeBindingMode': {
      title: 'StorageClass.volumeBindingMode: WaitForFirstConsumer',
      desc: 'Delays physical disk creation until a Pod referencing the PVC is scheduled on a specific node.',
      impact: 'Leaves PVC in Pending state until a pod is launched, ensuring the volume is created on the exact physical node where the pod lands!',
      bestPractice: 'Always use WaitForFirstConsumer in multi-node topology clusters.'
    }
  };

  // --- Scheduler & Simulation Engine ---
  function computeSimulationState() {
    const totalWorkers = state.workerNodeCount;
    const nodes = [];
    
    // Control Plane (Node 0)
    nodes.push({
      id: 'control-plane',
      name: 'reliability-lab-control-plane',
      role: 'control-plane',
      ip: '172.18.0.4',
      taint: 'NoSchedule',
      cpuTotal: '2000m',
      ramTotal: '4096Mi',
      cpuUsed: 250,
      ramUsed: 512,
      pods: [],
      isAlive: true
    });

    // Workers
    for (let i = 1; i <= totalWorkers; i++) {
      const isFailed = (state.failedWorkerId === i);
      nodes.push({
        id: `worker-${i}`,
        name: i === 1 ? 'reliability-lab-worker' : `reliability-lab-worker${i}`,
        role: 'worker',
        ip: `172.18.0.${i + 1}`,
        taint: isFailed ? 'NodeNotReady' : null,
        cpuTotal: '1000m',
        ramTotal: '2048Mi',
        cpuUsed: isFailed ? 0 : 100,
        ramUsed: isFailed ? 0 : 256,
        pods: [],
        isAlive: !isFailed
      });
    }

    const eligibleWorkers = nodes.filter(n => n.role === 'worker' && n.isAlive);
    const scheduledPods = [];
    const pendingPods = [];

    // OOM State evaluation
    state.isOOMKilled = (state.memoryLeak > state.memoryLimit);

    // Pod Scheduling Algorithm
    for (let p = 1; p <= state.replicas; p++) {
      const podKey = `pod-${p}`;
      const podObj = {
        id: podKey,
        name: `reliability-api-5cf79db769-${Math.random().toString(36).substring(2, 7)}`,
        app: 'reliability-api',
        version: '0.1.0',
        ip: null,
        node: null,
        status: 'Pending',
        reason: null,
        restarts: state.podRestarts[podKey] || 0,
        isReady: state.readinessHealthy && !state.isOOMKilled,
        isOOM: state.isOOMKilled
      };

      if (state.isOOMKilled) {
        state.podRestarts[podKey] = (state.podRestarts[podKey] || 0) + 1;
        podObj.status = 'OOMKilled';
        podObj.reason = 'ExitCode: 137 (Terminated by Linux OOM killer)';
      }

      if (eligibleWorkers.length === 0) {
        podObj.status = 'Pending';
        podObj.reason = '0/3 nodes available: 1 control-plane tainted, all workers NotReady';
        pendingPods.push(podObj);
        continue;
      }

      // Check topology spread
      if (state.topologySpread === 'DoNotSchedule' && eligibleWorkers.length === 2 && state.replicas === 3) {
        // Reproduce our exact Lab 3 finding!
        if (p === 3) {
          podObj.status = 'Pending';
          podObj.reason = '0/3 nodes available: 1 had untolerated taint, 2 didn\'t match topology spread constraints (maxSkew: 1 exceeded)';
          pendingPods.push(podObj);
          continue;
        }
      }

      // Assign to worker with least pods
      eligibleWorkers.sort((a, b) => a.pods.length - b.pods.length);
      const chosenWorker = eligibleWorkers[0];
      
      podObj.node = chosenWorker.name;
      podObj.ip = `10.244.${chosenWorker.id === 'worker-1' ? '1' : '2'}.${p + 1}`;
      if (!state.isOOMKilled) {
        podObj.status = (state.readinessHealthy) ? 'Running' : 'NotReady';
      }
      
      chosenWorker.pods.push(podObj);
      chosenWorker.ramUsed += state.memoryLeak;
      chosenWorker.cpuUsed += 100;
      scheduledPods.push(podObj);
    }

    // Endpoints Calculation
    const matchingEndpoints = [];
    if (state.serviceSelector === 'reliability-api') {
      scheduledPods.forEach(pod => {
        if (pod.isReady && pod.status === 'Running') {
          matchingEndpoints.push(`${pod.ip}:8000`);
        }
      });
    }

    return { nodes, scheduledPods, pendingPods, matchingEndpoints };
  }

  // --- Render DOM: Visual Topology Canvas ---
  function renderTopologyCanvas() {
    const sim = computeSimulationState();
    const container = document.getElementById('topologyCanvasArea');
    if (!container) return;

    let html = '';

    // Module-specific Canvas Rendering
    if (state.currentTab === 'workloads' || state.currentTab === 'reliability') {
      html += `
        <div class="canvas-zone">
          <div class="zone-header">
            <div class="zone-title">
              <span class="zone-icon">☸</span>
              Cluster Physical Nodes (Kind Multi-Node Simulator)
            </div>
            <div class="header-actions">
              <span class="pill-badge">Context: kind-reliability-lab</span>
              <span class="pill-badge">${sim.scheduledPods.length} Pods Active / ${sim.pendingPods.length} Pending</span>
            </div>
          </div>
          <div class="nodes-grid">
      `;

      sim.nodes.forEach((node, idx) => {
        const isCP = (node.role === 'control-plane');
        const ramPct = Math.min(100, Math.round((node.ramUsed / 2048) * 100));
        const cpuPct = Math.min(100, Math.round((node.cpuUsed / 1000) * 100));
        const isFailed = !node.isAlive;

        html += `
          <div class="node-card ${isCP ? 'control-plane' : 'worker'} ${isFailed ? 'failed' : ''}">
            <div class="node-header">
              <div>
                <div class="node-name">${node.name}</div>
                <div style="font-size:0.7rem; color:var(--text-muted); font-family:var(--font-mono);">${node.ip}</div>
              </div>
              <span class="node-role-badge">${isFailed ? 'NOT READY' : node.role}</span>
            </div>
            
            <div class="node-metrics">
              <div class="metric-bar-wrap">
                <div class="metric-labels"><span>RAM: ${node.ramUsed}Mi / ${node.ramTotal}</span><span>${ramPct}%</span></div>
                <div class="metric-track"><div class="metric-fill ${ramPct > 85 ? 'danger' : ramPct > 60 ? 'warn' : ''}" style="width: ${ramPct}%;"></div></div>
              </div>
              <div class="metric-bar-wrap">
                <div class="metric-labels"><span>CPU: ${node.cpuUsed}m / ${node.cpuTotal}</span><span>${cpuPct}%</span></div>
                <div class="metric-track"><div class="metric-fill" style="width: ${cpuPct}%;"></div></div>
              </div>
            </div>

            <div class="pod-slot-area" id="node-slot-${idx}">
              ${isCP ? `
                <div style="font-size:0.75rem; color:var(--text-muted); padding:8px; line-height:1.4;">
                  <strong style="color:var(--purple-accent);">Control Plane System Pods:</strong><br>
                  • etcd (Key-Value DB)<br>
                  • kube-apiserver<br>
                  • kube-scheduler<br>
                  • coredns (2 replicas)
                </div>
              ` : ''}

              ${node.pods.map(pod => `
                <div class="pod-pill ${pod.status.toLowerCase()}" onclick="window.playground.showPodDetails('${pod.id}')">
                  <div class="pod-pill-top">
                    <span class="pod-name-text">${pod.name}</span>
                    <span class="pod-status-dot"></span>
                  </div>
                  <div class="pod-meta-tags">
                    <span>${pod.status}</span>
                    ${pod.restarts > 0 ? `<span class="pod-restart-badge">Restarts: ${pod.restarts}</span>` : ''}
                  </div>
                  <div style="font-size:0.65rem; color:var(--cyan-accent); font-family:var(--font-mono);">${pod.ip || 'no-ip'}</div>
                </div>
              `).join('')}

              ${!isCP && node.pods.length === 0 && !isFailed ? `
                <div style="color:var(--text-dim); font-size:0.72rem; align-self:center; margin:auto;">No Pods Scheduled</div>
              ` : ''}

              ${isFailed ? `
                <div style="color:var(--red-bad); font-size:0.75rem; margin:auto; font-weight:700;">NODE CRASHED / EVICTED</div>
              ` : ''}
            </div>
          </div>
        `;
      });

      html += `</div></div>`;

      // Pending Pods Warning Shelf
      if (sim.pendingPods.length > 0) {
        html += `
          <div class="canvas-zone" style="border-color: rgba(210, 153, 34, 0.4); background: rgba(210, 153, 34, 0.05);">
            <div class="zone-header" style="margin-bottom:8px;">
              <div class="zone-title" style="color: var(--amber-warn);">
                <span>⚠️</span> Pods Blocked in PENDING (${sim.pendingPods.length})
              </div>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${sim.pendingPods.map(pod => `
                <div style="display:flex; align-items:center; justify-content:space-between; background:#1c2128; padding:8px 12px; border-radius:6px; border:1px solid var(--border-subtle);">
                  <div>
                    <strong style="font-family:var(--font-mono); font-size:0.78rem; color:#f0b35a;">${pod.name}</strong>
                    <div style="font-size:0.72rem; color:var(--text-muted);">${pod.reason}</div>
                  </div>
                  <span class="pill-badge" style="border-color:var(--amber-warn); color:var(--amber-warn);">Pending</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }
    } 
    else if (state.currentTab === 'networking') {
      // Networking & Ingress Visualizer
      const endpointsCount = sim.matchingEndpoints.length;
      html += `
        <div class="canvas-zone">
          <div class="zone-header">
            <div class="zone-title"><span class="zone-icon">🌐</span> End-to-End Traffic Routing Pipeline</div>
            <span class="pill-badge">Service Type: ${state.serviceType}</span>
          </div>

          <div class="networking-flow-canvas">
            <!-- Client Box -->
            <div class="client-mock-box">
              <div style="font-weight:700; font-size:0.85rem;">Client (Browser / Curl)</div>
              <div style="font-size:0.7rem; color:var(--text-muted);">Outside Internet</div>
              <button class="simulate-req-btn" onclick="window.playground.sendMockRequest()">⚡ Send HTTP GET</button>
              <div id="clientResponseBadge" style="font-family:var(--font-mono); font-size:0.72rem; padding:4px; border-radius:4px; background:#0d1117; color:var(--cyan-accent); min-height:24px;">Ready</div>
            </div>

            <!-- Ingress / Service Switchboard -->
            <div class="service-router-box">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color:var(--cyan-accent); font-size:0.85rem;">Service: reliability-api</strong>
                <span class="pill-badge">Port 80 ➔ 8000</span>
              </div>
              <div style="font-size:0.72rem; font-family:var(--font-mono); color:var(--text-muted);">
                ClusterIP: <strong>10.96.203.126</strong>
              </div>
              <div style="font-size:0.72rem;">
                Selector: <code style="color:${state.serviceSelector === 'reliability-api' ? 'var(--cyan-accent)' : 'var(--red-bad)'}; font-weight:700;">app: ${state.serviceSelector}</code>
              </div>
              <div class="endpoints-indicator">
                <span>Active Endpoints:</span>
                <span class="endpoints-count ${endpointsCount > 0 ? 'ok' : 'empty'}">
                  ${endpointsCount > 0 ? sim.matchingEndpoints.join(', ') : '<none> (NO BACKENDS!)'}
                </span>
              </div>
            </div>

            <!-- Backend Pods Target -->
            <div style="display:flex; flex-direction:column; gap:8px;">
              <div style="font-size:0.75rem; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Discovered Pods</div>
              ${sim.scheduledPods.map(pod => `
                <div class="pod-pill ${pod.isReady && state.serviceSelector === 'reliability-api' ? 'running' : 'failed'}" style="min-width:unset;">
                  <div class="pod-pill-top">
                    <span class="pod-name-text">${pod.name}</span>
                    <span class="pod-status-dot"></span>
                  </div>
                  <div style="font-size:0.68rem; font-family:var(--font-mono); color:var(--text-muted);">${pod.ip}:8000</div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- CoreDNS Inspection Box -->
        <div class="canvas-zone" style="margin-top:16px;">
          <div class="zone-header">
            <div class="zone-title"><span class="zone-icon">📋</span> CoreDNS Discovery Query Simulator</div>
            <span class="pill-badge">DNS Port: 53 (UDP/TCP)</span>
          </div>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; font-size:0.78rem;">
            <div style="background:#161b22; padding:12px; border-radius:8px;">
              <div style="font-weight:700; margin-bottom:4px;">Short Name Resolution:</div>
              <code style="color:var(--cyan-accent);">http://reliability-api/health</code>
              <div style="color:var(--text-muted); font-size:0.72rem; margin-top:4px;">
                ➔ Uses <code>/etc/resolv.conf</code> search suffix:<br>
                <code>reliability-api.default.svc.cluster.local</code> ➔ <strong>10.96.203.126</strong>
              </div>
            </div>
            <div style="background:#161b22; padding:12px; border-radius:8px;">
              <div style="font-weight:700; margin-bottom:4px;">Cross-Namespace FQDN:</div>
              <code style="color:var(--cyan-accent);">http://reliability-api.staging.svc.cluster.local</code>
              <div style="color:var(--text-muted); font-size:0.72rem; margin-top:4px;">
                ➔ Crosses namespace boundaries safely without IP address hardcoding!
              </div>
            </div>
          </div>
        </div>
      `;
    }
    else if (state.currentTab === 'storage_rbac') {
      // Storage & RBAC Visualizer
      html += `
        <div class="canvas-zone">
          <div class="zone-header">
            <div class="zone-title"><span class="zone-icon">💾</span> Dynamic Storage Provisioner & Persistent Volumes</div>
            <span class="pill-badge">StorageClass: standard</span>
          </div>
          <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; align-items:center;">
            <div style="background:#161b22; padding:14px; border-radius:8px; border:1px solid var(--border-subtle);">
              <strong style="color:var(--cyan-accent); font-size:0.82rem;">1. StorageClass</strong>
              <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">Provisioner: rancher.io/local-path</div>
              <div style="font-size:0.72rem; color:#f0b35a; margin-top:2px;">Binding: WaitForFirstConsumer</div>
            </div>
            
            <div style="background:#161b22; padding:14px; border-radius:8px; border:1px solid ${state.pvcAttachedToPod ? 'var(--green-ok)' : 'var(--amber-warn)'};">
              <div style="display:flex; justify-content:space-between;">
                <strong style="font-size:0.82rem;">2. PVC: api-data</strong>
                <span class="pill-badge" style="border-color:${state.pvcAttachedToPod ? 'var(--green-ok)' : 'var(--amber-warn)'}; color:${state.pvcAttachedToPod ? '#7ee787' : '#f0b35a'};">
                  ${state.pvcAttachedToPod ? 'Bound (1Gi)' : 'Pending (Waiting)'}
                </span>
              </div>
              <div style="font-size:0.72rem; color:var(--text-muted); margin-top:6px;">
                ${state.pvcAttachedToPod ? 'Attached to /data inside pod' : 'Waiting for first consumer pod to be created!'}
              </div>
            </div>

            <div style="background:#161b22; padding:14px; border-radius:8px; border:1px solid var(--border-subtle); text-align:center;">
              <button class="simulate-req-btn" onclick="window.playground.togglePVCMount()" style="width:100%;">
                ${state.pvcAttachedToPod ? 'Unmount Volume from Pod' : 'Mount PVC into Pod'}
              </button>
            </div>
          </div>
        </div>

        <div class="canvas-zone" style="margin-top:16px;">
          <div class="zone-header">
            <div class="zone-title"><span class="zone-icon">🔒</span> RBAC Identity & Permission Matrix</div>
            <span class="pill-badge">ServiceAccount: ${state.selectedServiceAccount}</span>
          </div>
          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; font-size:0.75rem;">
            <div style="background:#161b22; padding:10px; border-radius:6px; border-left:3px solid var(--green-ok);">
              <div>list pods</div>
              <strong style="color:#7ee787;">Allowed (yes)</strong>
            </div>
            <div style="background:#161b22; padding:10px; border-radius:6px; border-left:3px solid var(--green-ok);">
              <div>get configmaps</div>
              <strong style="color:#7ee787;">Allowed (yes)</strong>
            </div>
            <div style="background:#161b22; padding:10px; border-radius:6px; border-left:3px solid var(--red-bad);">
              <div>delete pods</div>
              <strong style="color:#f85149;">Forbidden (no - 403)</strong>
            </div>
            <div style="background:#161b22; padding:10px; border-radius:6px; border-left:3px solid var(--red-bad);">
              <div>get secrets</div>
              <strong style="color:#f85149;">Forbidden (no - 403)</strong>
            </div>
          </div>
        </div>
      `;
    }

    container.innerHTML = html;
    renderTerminalOutput(sim);
  }

  // --- Render Interactive YAML with Clickable Lines ---
  function renderYAMLViewer() {
    const yamlContainer = document.getElementById('yamlCodeScroll');
    if (!yamlContainer) return;

    let yamlLines = [];

    if (state.currentTab === 'workloads') {
      yamlLines = [
        { num: 1, text: `<span class="y-key">apiVersion</span>: <span class="y-val">apps/v1</span>` },
        { num: 2, text: `<span class="y-key">kind</span>: <span class="y-val">Deployment</span>` },
        { num: 3, text: `<span class="y-key">metadata</span>:` },
        { num: 4, text: `  <span class="y-key">name</span>: <span class="y-str">reliability-api</span>` },
        { num: 5, text: `<span class="y-key">spec</span>:` },
        { num: 6, text: `  <span class="y-key">replicas</span>: <span class="y-num">${state.replicas}</span>`, fieldKey: 'replicas' },
        { num: 7, text: `  <span class="y-key">selector</span>:` },
        { num: 8, text: `    <span class="y-key">matchLabels</span>:` },
        { num: 9, text: `      <span class="y-key">app.kubernetes.io/name</span>: <span class="y-str">reliability-api</span>` },
        { num: 10, text: `  <span class="y-key">template</span>:` },
        { num: 11, text: `    <span class="y-key">spec</span>:` },
        { num: 12, text: `      <span class="y-key">topologySpreadConstraints</span>:`, fieldKey: 'topologySpreadConstraints' },
        { num: 13, text: `        - <span class="y-key">maxSkew</span>: <span class="y-num">${state.maxSkew}</span>`, fieldKey: 'maxSkew' },
        { num: 14, text: `          <span class="y-key">topologyKey</span>: <span class="y-str">kubernetes.io/hostname</span>` },
        { num: 15, text: `          <span class="y-key">whenUnsatisfiable</span>: <span class="y-val">${state.topologySpread}</span>`, fieldKey: 'whenUnsatisfiable' }
      ];
    } 
    else if (state.currentTab === 'reliability') {
      yamlLines = [
        { num: 1, text: `  <span class="y-key">containers</span>:` },
        { num: 2, text: `    - <span class="y-key">name</span>: <span class="y-str">reliability-api</span>` },
        { num: 3, text: `      <span class="y-key">resources</span>:` },
        { num: 4, text: `        <span class="y-key">limits</span>:` },
        { num: 5, text: `          <span class="y-key">memory</span>: <span class="y-str">"${state.memoryLimit}Mi"</span>`, fieldKey: 'resources.limits.memory' },
        { num: 6, text: `      <span class="y-key">livenessProbe</span>:`, fieldKey: 'livenessProbe' },
        { num: 7, text: `        <span class="y-key">httpGet</span>:` },
        { num: 8, text: `          <span class="y-key">path</span>: <span class="y-str">/health</span>` },
        { num: 9, text: `          <span class="y-key">port</span>: <span class="y-num">8000</span>` },
        { num: 10, text: `      <span class="y-key">readinessProbe</span>:`, fieldKey: 'readinessProbe' },
        { num: 11, text: `        <span class="y-key">httpGet</span>:` },
        { num: 12, text: `          <span class="y-key">path</span>: <span class="y-str">/ready</span>` },
        { num: 13, text: `          <span class="y-key">port</span>: <span class="y-num">8000</span>` }
      ];
    }
    else if (state.currentTab === 'networking') {
      yamlLines = [
        { num: 1, text: `<span class="y-key">apiVersion</span>: <span class="y-val">v1</span>` },
        { num: 2, text: `<span class="y-key">kind</span>: <span class="y-val">Service</span>` },
        { num: 3, text: `<span class="y-key">metadata</span>:` },
        { num: 4, text: `  <span class="y-key">name</span>: <span class="y-str">reliability-api</span>` },
        { num: 5, text: `<span class="y-key">spec</span>:` },
        { num: 6, text: `  <span class="y-key">type</span>: <span class="y-val">${state.serviceType}</span>`, fieldKey: 'service.spec.type' },
        { num: 7, text: `  <span class="y-key">selector</span>:`, fieldKey: 'service.spec.selector' },
        { num: 8, text: `    <span class="y-key">app</span>: <span class="y-str">"${state.serviceSelector}"</span>`, fieldKey: 'service.spec.selector' },
        { num: 9, text: `  <span class="y-key">ports</span>:` },
        { num: 10, text: `    - <span class="y-key">port</span>: <span class="y-num">80</span>` },
        { num: 11, text: `      <span class="y-key">targetPort</span>: <span class="y-num">8000</span>` },
        state.serviceType === 'NodePort' ? { num: 12, text: `      <span class="y-key">nodePort</span>: <span class="y-num">30800</span>` } : null
      ].filter(Boolean);
    }
    else if (state.currentTab === 'storage_rbac') {
      yamlLines = [
        { num: 1, text: `<span class="y-key">apiVersion</span>: <span class="y-val">v1</span>` },
        { num: 2, text: `<span class="y-key">kind</span>: <span class="y-val">PersistentVolumeClaim</span>` },
        { num: 3, text: `<span class="y-key">metadata</span>:` },
        { num: 4, text: `  <span class="y-key">name</span>: <span class="y-str">api-data</span>` },
        { num: 5, text: `<span class="y-key">spec</span>:` },
        { num: 6, text: `  <span class="y-key">accessModes</span>:`, fieldKey: 'pvc.accessModes' },
        { num: 7, text: `    - <span class="y-val">ReadWriteOnce</span>`, fieldKey: 'pvc.accessModes' },
        { num: 8, text: `  <span class="y-key">storageClassName</span>: <span class="y-str">standard</span>`, fieldKey: 'storageClass.volumeBindingMode' },
        { num: 9, text: `  <span class="y-key">resources</span>:` },
        { num: 10, text: `    <span class="y-key">requests</span>:` },
        { num: 11, text: `      <span class="y-key">storage</span>: <span class="y-str">1Gi</span>` }
      ];
    }

    yamlContainer.innerHTML = yamlLines.map(line => `
      <div class="yaml-line" onclick="window.playground.inspectField('${line.fieldKey || ''}')" data-field="${line.fieldKey || ''}">
        <span style="color:var(--text-dim); margin-right:8px; font-size:0.72rem;">${line.num.toString().padStart(2, ' ')}</span>
        ${line.text}
      </div>
    `).join('');
  }

  // --- Terminal Output Synchronizer ---
  function renderTerminalOutput(sim) {
    const termBody = document.getElementById('terminalBody');
    if (!termBody) return;

    let output = '';

    if (state.currentTab === 'workloads' || state.currentTab === 'reliability') {
      output += `<span class="terminal-prompt">@ai-innovation-art ➜ /workspaces/Deployment (main) $</span> <span class="terminal-cmd">kubectl get pods -o wide</span>\n`;
      output += `NAME                               READY   STATUS      RESTARTS   NODE                      IP\n`;
      
      sim.scheduledPods.forEach(p => {
        output += `${p.name.padEnd(35)} ${p.isReady ? '1/1' : '0/1'}     ${p.status.padEnd(11)} ${p.restarts.toString().padEnd(10)} ${(p.node || '<none>').padEnd(25)} ${p.ip || '<none>'}\n`;
      });

      sim.pendingPods.forEach(p => {
        output += `${p.name.padEnd(35)} 0/1     ${'Pending'.padEnd(11)} 0          ${'<none>'.padEnd(25)} <none>\n`;
      });

      if (state.isOOMKilled) {
        output += `\n<span class="terminal-prompt">@ai-innovation-art ➜ /workspaces/Deployment (main) $</span> <span class="terminal-cmd">kubectl describe pod ${sim.scheduledPods[0]?.name || 'pod'} | grep -A 4 "Last State"</span>\n`;
        output += `    Last State:     Terminated\n      Reason:       OOMKilled\n      Exit Code:    137\n      Memory Used:  ${state.memoryLeak}Mi / Limit: ${state.memoryLimit}Mi\n`;
      }
    } 
    else if (state.currentTab === 'networking') {
      output += `<span class="terminal-prompt">@ai-innovation-art ➜ /workspaces/Deployment (main) $</span> <span class="terminal-cmd">kubectl get svc,endpoints reliability-api</span>\n`;
      output += `NAME                      TYPE        CLUSTER-IP      PORT(S)\n`;
      output += `service/reliability-api   ${state.serviceType.padEnd(11)} 10.96.203.126   ${state.serviceType === 'NodePort' ? '80:30800/TCP' : '80/TCP'}\n\n`;
      output += `NAME                                ENDPOINTS\n`;
      output += `endpoints/reliability-api           ${sim.matchingEndpoints.length > 0 ? sim.matchingEndpoints.join(',') : '<none>'}\n`;
    }
    else if (state.currentTab === 'storage_rbac') {
      output += `<span class="terminal-prompt">@ai-innovation-art ➜ /workspaces/Deployment (main) $</span> <span class="terminal-cmd">kubectl get pvc,pv api-data</span>\n`;
      output += `NAME                             STATUS    VOLUME    CAPACITY   STORAGECLASS\n`;
      output += `persistentvolumeclaim/api-data   ${state.pvcAttachedToPod ? 'Bound     pvc-4921  1Gi        standard' : 'Pending                       standard'}\n`;
      if (!state.pvcAttachedToPod) {
        output += `\n<span class="terminal-prompt">Event:</span> WaitForFirstConsumer - waiting for first consumer to be created before binding\n`;
      }
    }

    termBody.innerHTML = output;
  }

  // --- Public Interactive API ---
  window.playground = {
    setTab: function (tab) {
      state.currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
      });
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    updateSidebarControls: function () {
      const deck = document.getElementById('controlDeck');
      if (!deck) return;

      let html = '';

      if (state.currentTab === 'workloads') {
        html = `
          <div class="control-group">
            <div class="control-header">
              <span>Desired Replicas</span>
              <span class="control-val-badge" id="replicasVal">${state.replicas}</span>
            </div>
            <input type="range" min="1" max="6" value="${state.replicas}" oninput="window.playground.setReplicas(this.value)">
          </div>

          <div class="control-group">
            <div class="control-header"><span>Topology Spread Mode</span></div>
            <div class="button-segmented">
              <button class="segmented-btn ${state.topologySpread === 'ScheduleAnyway' ? 'active' : ''}" onclick="window.playground.setTopology('ScheduleAnyway')">ScheduleAnyway</button>
              <button class="segmented-btn ${state.topologySpread === 'DoNotSchedule' ? 'active' : ''}" onclick="window.playground.setTopology('DoNotSchedule')">DoNotSchedule</button>
            </div>
          </div>

          <div class="control-group">
            <div class="control-header"><span>Preset Scenarios</span></div>
            <div class="preset-triggers">
              <button class="preset-btn warn" onclick="window.playground.triggerPendingScenario()">💥 Trigger 3rd Pod Pending Bug</button>
              <button class="preset-btn" onclick="window.playground.killWorkerNode(2)">⚡ Kill Worker Node 2</button>
              <button class="preset-btn" onclick="window.playground.resetNodes()">🔄 Recover All Nodes</button>
            </div>
          </div>
        `;
      } 
      else if (state.currentTab === 'reliability') {
        html = `
          <div class="control-group">
            <div class="control-header">
              <span>Memory Limit</span>
              <span class="control-val-badge">${state.memoryLimit} MiB</span>
            </div>
            <input type="range" min="128" max="512" step="64" value="${state.memoryLimit}" oninput="window.playground.setMemoryLimit(this.value)">
          </div>

          <div class="control-group">
            <div class="control-header">
              <span>Memory Consumption (/leak)</span>
              <span class="control-val-badge" style="color:${state.memoryLeak > state.memoryLimit ? 'var(--red-bad)' : 'var(--cyan-accent)'}">${state.memoryLeak} MiB</span>
            </div>
            <input type="range" min="64" max="512" step="32" value="${state.memoryLeak}" oninput="window.playground.setMemoryLeak(this.value)">
          </div>

          <div class="control-group">
            <div class="control-header"><span>Probe States</span></div>
            <div class="button-segmented">
              <button class="segmented-btn ${state.readinessHealthy ? 'active' : ''}" onclick="window.playground.toggleReadiness()">Readiness: ${state.readinessHealthy ? 'Pass (Traffic OK)' : 'Fail (No Traffic)'}</button>
            </div>
          </div>

          <div class="control-group">
            <div class="control-header"><span>Instant Triggers</span></div>
            <div class="preset-triggers">
              <button class="preset-btn danger" onclick="window.playground.triggerOOMScenario()">☠️ Trigger Real OOMKilled (Exit Code 137)</button>
              <button class="preset-btn" onclick="window.playground.resetHealth()">🔄 Reset Health</button>
            </div>
          </div>
        `;
      }
      else if (state.currentTab === 'networking') {
        html = `
          <div class="control-group">
            <div class="control-header"><span>Service Type</span></div>
            <div class="button-segmented">
              <button class="segmented-btn ${state.serviceType === 'ClusterIP' ? 'active' : ''}" onclick="window.playground.setServiceType('ClusterIP')">ClusterIP</button>
              <button class="segmented-btn ${state.serviceType === 'NodePort' ? 'active' : ''}" onclick="window.playground.setServiceType('NodePort')">NodePort (30800)</button>
            </div>
          </div>

          <div class="control-group">
            <div class="control-header"><span>Service Selector</span></div>
            <div class="button-segmented">
              <button class="segmented-btn ${state.serviceSelector === 'reliability-api' ? 'active' : ''}" onclick="window.playground.setSelector('reliability-api')">app: reliability-api</button>
              <button class="segmented-btn ${state.serviceSelector === 'wrong-name' ? 'active' : ''}" style="color:#f85149;" onclick="window.playground.setSelector('wrong-name')">app: wrong-name</button>
            </div>
          </div>

          <div class="control-group">
            <div class="control-header"><span>Production Failure Scenarios</span></div>
            <div class="preset-triggers">
              <button class="preset-btn danger" onclick="window.playground.setSelector('wrong-name')">❌ #1 Production Bug: Selector Typo</button>
              <button class="preset-btn" onclick="window.playground.setSelector('reliability-api')">✅ Fix Selector Back</button>
            </div>
          </div>
        `;
      }
      else if (state.currentTab === 'storage_rbac') {
        html = `
          <div class="control-group">
            <div class="control-header"><span>PVC Storage Lifecycle</span></div>
            <div class="preset-triggers">
              <button class="preset-btn" onclick="window.playground.togglePVCMount()">
                ${state.pvcAttachedToPod ? '🔌 Detach Volume (Return to Pending)' : '💾 Mount Volume into Pod (Flip to Bound)'}
              </button>
            </div>
          </div>

          <div class="control-group">
            <div class="control-header"><span>RBAC ServiceAccount Simulator</span></div>
            <div class="button-segmented">
              <button class="segmented-btn active">reliability-api-sa (Least Privilege)</button>
            </div>
          </div>
        `;
      }

      deck.innerHTML = html;
    },

    setReplicas: function (val) {
      state.replicas = parseInt(val, 10);
      const badge = document.getElementById('replicasVal');
      if (badge) badge.innerText = state.replicas;
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    setTopology: function (mode) {
      state.topologySpread = mode;
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    triggerPendingScenario: function () {
      state.replicas = 3;
      state.workerNodeCount = 2;
      state.topologySpread = 'DoNotSchedule';
      state.maxSkew = 1;
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    killWorkerNode: function (nodeId) {
      state.failedWorkerId = nodeId;
      renderTopologyCanvas();
    },

    resetNodes: function () {
      state.failedWorkerId = null;
      renderTopologyCanvas();
    },

    setMemoryLimit: function (val) {
      state.memoryLimit = parseInt(val, 10);
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    setMemoryLeak: function (val) {
      state.memoryLeak = parseInt(val, 10);
      this.updateSidebarControls();
      renderTopologyCanvas();
    },

    triggerOOMScenario: function () {
      state.memoryLimit = 256;
      state.memoryLeak = 384; // 384 > 256 MiB!
      this.updateSidebarControls();
      renderTopologyCanvas();
    },

    toggleReadiness: function () {
      state.readinessHealthy = !state.readinessHealthy;
      this.updateSidebarControls();
      renderTopologyCanvas();
    },

    resetHealth: function () {
      state.memoryLeak = 64;
      state.readinessHealthy = true;
      this.updateSidebarControls();
      renderTopologyCanvas();
    },

    setServiceType: function (type) {
      state.serviceType = type;
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    setSelector: function (name) {
      state.serviceSelector = name;
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    togglePVCMount: function () {
      state.pvcAttachedToPod = !state.pvcAttachedToPod;
      this.updateSidebarControls();
      renderYAMLViewer();
      renderTopologyCanvas();
    },

    sendMockRequest: function () {
      const badge = document.getElementById('clientResponseBadge');
      if (!badge) return;
      
      const sim = computeSimulationState();
      badge.innerText = 'Connecting...';
      badge.style.color = '#79c0ff';

      setTimeout(() => {
        if (sim.matchingEndpoints.length > 0) {
          badge.innerText = 'HTTP 200 OK {"status":"ok"}';
          badge.style.color = '#7ee787';
        } else {
          badge.innerText = 'HTTP 503 Service Unavailable (Endpoints: <none>)';
          badge.style.color = '#f85149';
        }
      }, 400);
    },

    inspectField: function (key) {
      const drawer = document.getElementById('fieldExplainerDrawer');
      if (!drawer) return;

      if (!key || !fieldDocs[key]) {
        drawer.classList.remove('visible');
        return;
      }

      const doc = fieldDocs[key];
      document.getElementById('explainerTitle').innerText = doc.title;
      document.getElementById('explainerDesc').innerText = doc.desc;
      document.getElementById('explainerImpact').innerText = doc.impact;
      drawer.classList.add('visible');
    },

    showPodDetails: function (podId) {
      alert(`Pod ${podId} Diagnostics:\nState: Running\nMemory: ${state.memoryLeak}Mi / ${state.memoryLimit}Mi\nReadiness: ${state.readinessHealthy ? 'Passed' : 'Failed'}`);
    }
  };

  // --- Initialize on Page Load ---
  document.addEventListener('DOMContentLoaded', () => {
    window.playground.setTab('workloads');
  });

})();
