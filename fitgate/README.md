# FitGate — Per-backend conformance attestations for GGUF / llama.cpp serving

> Status: **IDEA — approved with changes by Finder/Validator review (29 Oct 2026)**. Nothing built yet.
> Builds on: the DevOps course notes in `../notes/` (read-only, finalized) and `../devops_kubernetes_study_and_build_guide.md`.

## One-line pitch
A quantized model can serve on a Kubernetes node **only if** that exact `(model digest + llama.cpp engine build + runtime flags + chat template)` has a **signed, CI-generated proof** that it answers correctly **and** meets its latency SLO **on that node's hardware backend**.

## The problem (evidence)
- **Broken models ship from official registries.** arXiv 2609.05881 "Broken on Arrival": 7 of 305 official Ollama GGUF tags (2.3%) are non-functional (low-bit q2_K–q3_K_L quants of ≤4B models, solved ≤6/15 HumanEval+ screen tasks). They stayed published for two months; perplexity didn't flag them. Rebuilding with an imatrix fixed them. https://arxiv.org/abs/2609.05881 · tool: https://github.com/aditi-p31/quantcheck
- **Correctness depends on the backend.** The same file can work on one backend and fail on another:
  - llama.cpp #11256: Llama-3.2-1B-Instruct-Q4_K_M gives garbage on Vulkan (MoltenVK, M1) but works on Metal and CPU. https://github.com/ggml-org/llama.cpp/issues/11256
  - #21450: Metal fails mixed q8_0/q4_0 KV cache without Flash Attention, so the result depends on flags. https://github.com/ggml-org/llama.cpp/issues/21450
  - #20081: engine-build drift, from a CUDA + Vulkan mmproj split. Weaker evidence; use only as a build-drift example. https://github.com/ggml-org/llama.cpp/issues/20081
- **Today's gates verify identity, not function.**
  - Sigstore Model Validation Operator checks signatures only.
  - Jozu gates on signatures, scans and compliance.
  - KitOps does no evaluation.

## What FitGate does (validated framing)
1. **Differential backend conformance** (the core check):
   - Compare the target backend's output against a CPU reference run of the *same digest*, using token / top-k logit agreement (e.g. KL divergence) over a fixed prompt set.
   - Also run an absolute check: golden prompts plus a ~15-task EvalPlus screen, scored by threshold.
   - Also measure a perf envelope: goodput under a TTFT/ITL SLO, measured with AIPerf / inference-perf.
2. **Signed predicate `serving-fitness/v1`.** An in-toto statement that extends or references the in-toto **Test Result** predicate. It covers model digest, engine image digest, flags, chat-template hash and backend/hardware class. It is signed with cosign keyless (GitHub OIDC) and pushed to GHCR.
3. **Admission enforcement.** A Kyverno policy, or GitHub Attestations + OPA Gatekeeper:
   - Deny a pod with no passing attestation for its node class.
   - Mutate `nodeAffinity` so the pod lands only on qualified classes.
4. **Automatic re-qualification.** An engine image bump (Renovate), a new node class or changed flags invalidates attestations and triggers the qualify job. Admission is denied until it passes.
5. **Perf-envelope producer.** This is the former "QuantPilot" idea folded in: sweep quant × KV-quant × n-gpu-layers × slots and emit Helm values, KEDA thresholds and alert rules.
6. **Thin canary demo.** An Argo Rollouts AnalysisTemplate (Prometheus goodput + a golden-probe Job) with auto-rollback. **Not a headline feature**, because this pattern already exists.
7. **Interoperates** with Socair and Sigstore identity attestations rather than duplicating them.

## Why it doesn't exist (closest prior art, overlap 0–10)
| Tool | Overlap | What it lacks |
|---|---|---|
| **Socair** (defilantech, same org as LLMKube) https://github.com/defilantech/socair | **6** | Signs GGUF attestations and has Kyverno admission plus promotion. But checks are static/security only: no functional eval, no perf, no hardware/engine binding. **WATCH:** its roadmap lists "Tier 2 GPU-based measurements"; issue #200. |
| NVIDIA NeMo Evaluator `nel gate` https://docs.nvidia.com/nemo/evaluator/nightly/tutorials/quality-gate | 5 | CI GO/NO-GO only. No admission, no hardware binding, no signed digest-bound predicate. |
| thejoecrabtree/llm-eval-gate | 4 | Golden-set CI gate. No K8s, signing, perf or hardware binding. |
| quantcheck | 4 | Screening logic only, as a research harness. |
| Jozu Hub, Sigstore MVO | 3 | Identity/scan/compliance only. |
| Confident AI gate, GH Attestations + Gatekeeper | 2 | Governance-policy checks (Confident AI) and a generic attestation primitive (Gatekeeper). FitGate can use the latter. |

**The gap:** nothing binds *functional + perf* results to *(model, engine build, flags, chat template, backend class)* and enforces them per node class at admission.

## Course mapping
| Course module | FitGate piece |
|---|---|
| M01–02 Linux/Docker | llama-server and eval-runner images, reproducible builds |
| M03–06 K8s, kind, Helm | Test cluster, umbrella Helm chart, webhook/policy deployment |
| M07 Observability | SLO dashboards, burn-rate alerts (TTFT/ITL/goodput, gate latency) |
| M08 Scaling/load/failure | KEDA on `llamacpp:requests_deferred`, k6, Chaos Mesh |
| M09 CI/CD | Qualify pipeline, SBOM (syft), Trivy, cosign, SLSA provenance, attestations |
| M10–11 Terraform/GKE | Short GKE L4 bursts as the CUDA hardware class, destroyed after each run |
| M12 AI inference | AIPerf/inference-perf goodput, prefill/decode metrics |
| M13 Troubleshooting | Runbooks, experiments, evidence discipline |
| **New beyond course** | Kyverno (attestation policies), Argo Rollouts (thin), in-toto predicates |

## Production-level requirements
- **SLOs:**
  - Gate: admission p99 < 200 ms; webhook availability 99.9% with a documented `failurePolicy`.
  - Model: TTFT/ITL p95 and goodput.
  - Canary: MTTD < 10 min.
- **CI/CD:** kind e2e on every PR, Trivy, syft SBOM, cosign-signed images, SLSA provenance, Renovate.
- **Security:** least-privilege RBAC, cert-manager TLS, External Secrets, NetworkPolicies, a written threat model.
- **Release:** semver, Helm chart published to an OCI registry, CHANGELOG.
- **Runbooks:** gate down, attestation missing or expired, canary rolled back, node-class drift.

## Experiments that prove the claim
1. **Broken-artifact corpus:** the 7 broken tags plus ≥20 known-good tags.
   - Plain KServe/LLMKube and the Sigstore MVO are expected to admit 7/7 broken tags.
   - FitGate target: block 7/7 with ≤1 false positive.
2. **Cross-backend:** reproduce a #11256-style divergence. FitGate admits on the good backend and denies or redirects on the bad one.
3. **Bad engine upgrade or flags** (`-ngl 0`, low `-np`): the perf envelope fails before deploy. If that is bypassed, the canary should roll back; measure MTTD.
4. **Chaos:** kill a node mid-canary and compare error-budget burn against a plain Deployment.

## Scope and plan
- **MVP (~8–9 weeks):** CPU class on kind.
  - Qualify job, signed attestation, admission allow/deny, Grafana SLO dashboard.
  - Demo: the 7 broken tags are blocked.
- **v1 (~16–22 weeks):**
  - CPU + CUDA (GKE L4) classes.
  - Differential conformance, auto re-qualification, perf envelope.
  - Chaos tests, thin canary, published Helm chart, runbooks, v1.0 release.
- **Stretch:**
  - Vulkan class.
  - Metal class: Docker/kind on macOS cannot reach the Metal GPU, so this needs a native llama-server joined as an external endpoint.
  - Public fitness ledger.
  - Upstream the predicate to in-toto, ModelPack and Socair.
  - vLLM/AWQ support.

| Weeks | Modules | Build |
|---|---|---|
| 1–2 | M01–02 | Images; **week-1 check: can the 7 broken tags still be fetched by digest?** |
| 3–5 | M03–06 | kind + Helm, llama-server pool, Kyverno policy |
| 6–7 | M07 | SLOs, dashboards, alerts |
| 8–9 | M09 | Qualify pipeline + signing → **MVP demo** |
| 10–12 | M08 + M12 | KEDA, k6, AIPerf perf envelope, Chaos Mesh |
| 13–15 | — | Differential conformance, auto re-qualify, thin Argo canary |
| 16–18 | M10–11 | Terraform GKE L4 class, self-hosted runner |
| 19–22 | M13 | Experiments, runbooks, v1.0, write-up |

## Risks and kill criteria
- **KILL / pivot:**
  - Socair, LLMKube, Jozu or OpenShift AI ships functional, per-backend attestation enforcement first. **Recheck monthly** (Socair roadmap and #200).
- **Risks:**
  - **Broken tags re-pushed or removed.** Mitigation: pin sha256 blobs from quantcheck's provenance, or rebuild without imatrix (the paper shows the tensors match).
  - **Evals flaky across backends.** Mitigation: threshold scoring, not exact match.
  - **CPU evals slow.** Mitigation: use the 15-task screen; the models are small.
  - **Unverified detail:** whether current llama.cpp still exports `kv_cache_usage_ratio`.

## Review scores (Validator)
Novelty **6/10** · Feasibility **7/10** · Production value **7/10**

## Rejected alternatives (for the record)
- **EdgePool** (llama.cpp in the Gateway API Inference Extension): already works. Kubermatic documents a llama-cpp InferencePool picker, and LLMKube covers heterogeneous routing.
- **QuantPilot** (quant Pareto profiler): mostly exists (quant-sim, CanIRun). Folded into FitGate as the perf-envelope producer.
- **Also already covered:**
  - Per-token cost: OpenCost 1.121.
  - Heterogeneous GPU autoscaling: llm-d WVA, AIBrix.
  - llama.cpp K8s operator: LLMKube.
  - Client LLM chaos: LLMock.
  - AI SRE agents: HolmesGPT, k8sgpt.
  - Multi-provider gateway: LiteLLM, Envoy AI Gateway.
  - SLO GPU profiler: NVIDIA Dynamo.

## Next steps when we continue
1. Week-1 feasibility check: fetch the 7 broken Ollama tags by digest, or confirm the rebuild path.
2. Read the Socair repo and roadmap in detail; decide the interop format (in-toto Test Result extension).
3. Draft the `serving-fitness/v1` predicate schema.
4. Turn the milestone table into a week-by-week task plan.
