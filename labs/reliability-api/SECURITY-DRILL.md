# 🛡️ Special Drill: Container Security & Privilege Boundary (Root vs Non-Root)

> **Core Lesson:** Containers share the host Linux kernel. Running a container process as `root` (UID 0) removes the primary defense barrier protecting your infrastructure from host-level takeover, DNS spoofing, and runtime malware execution.

---

## 1. The Anatomy of the Test Command

```bash
docker run --rm reliability-api:naive sh -c "echo '1.2.3.4 evil-hacker.com' >> /etc/hosts && cat /etc/hosts"
```

### Detailed Component Breakdown

| Token | Component | Purpose & Underlying Linux Behavior |
| :--- | :--- | :--- |
| `docker run` | Container Execution | Allocates isolated Linux namespaces (`pid`, `net`, `mnt`, `uts`, `ipc`) and attaches cgroups. |
| `--rm` | Ephemeral Lifecycle | Tells the Docker daemon to automatically delete the container metadata and writable layer as soon as the process terminates. |
| `reliability-api:naive` | Target Image | Single-stage image built without `USER` directive (defaults to `root`, `UID 0`). |
| `sh` | Shell Binary | Overrides the default entrypoint (`CMD ["uvicorn"...]`) to execute the standard POSIX shell (`/bin/sh`). |
| `-c` | Command String Flag | Tells `sh` to read and execute the adjacent quoted string non-interactively, then immediately exit. |
| `" ... "` | Execution Payload | The compound shell payload executed inside the container environment. |

### Shell Payload Breakdown

* **`echo '1.2.3.4 evil-hacker.com'`**: Emits the IP-to-hostname mapping to standard output (`stdout`).
* **`>>` (Append Operator)**: 
  * `>` would wipe out and overwrite the target file from scratch.
  * `>>` preserves existing contents and appends the new line at the bottom.
* **`/etc/hosts`**: The local operating system static DNS mapping table. Any query for `evil-hacker.com` will resolve to `1.2.3.4` before public DNS servers (e.g. `8.8.8.8`) are consulted.
* **`&&` (Logical AND Chaining)**: Executes the second command (`cat /etc/hosts`) **only if** the preceding command returns exit status code `0` (Success). If the first command fails (e.g., `Permission denied`), execution halts immediately.
* **`cat /etc/hosts`**: Concatenates and streams the file contents to `stdout` to verify file modification.

---

## 2. Live Test Comparison: Naive vs Production

### Test A: Naive Container (Root - UID 0)
```bash
docker run --rm reliability-api:naive sh -c "echo '1.2.3.4 evil-hacker.com' >> /etc/hosts && cat /etc/hosts"
```

#### Real Output:
```text
127.0.0.1       localhost
::1             localhost ip6-localhost ip6-loopback
fe00::          ip6-localnet
ff00::          ip6-mcastprefix
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
172.17.0.2      161d7e1054de
1.2.3.4 evil-hacker.com   <── EXPLOIT SUCCEEDED!
```
> **Vulnerability Confirmed:** Because the container was started as `root`, the process has full write access to core system files. An attacker with arbitrary code execution can manipulate DNS records, install unauthorized binaries, or replace system libraries.

---

### Test B: Production Container (Unprivileged - UID 10001)
```bash
docker run --rm kumawatsunil/reliability-api sh -c "echo '1.2.3.4 evil-hacker.com' >> /etc/hosts"
```

#### Real Output:
```text
sh: 1: cannot create /etc/hosts: Permission denied
```
> **Defense Verified:** The container process runs as user `app` (`UID 10001`). The Linux kernel enforces POSIX file permission checks: `/etc/hosts` is owned by `root:root (0644)`. User `10001` has read-only access. The write request is denied at the kernel syscall boundary.

---

## 3. The Logic Behind User ID `10001`

Why did we choose UID `10001` in the production `Dockerfile`?

```dockerfile
RUN groupadd --system --gid 10001 appuser && \
    useradd --system --uid 10001 --gid 10001 --no-create-home appuser
USER 10001:10001
```

### Linux UID Allocation Hierarchy

```text
UID Range              Designation / Typical Owner
────────────────────────────────────────────────────────────────────────────────
0                      root (Superuser / Kernel Admin)
1 – 999                System Daemons (Reserved by Linux distributions: sshd, mail, etc.)
1000                   Primary Human Host User (Default on Ubuntu, Debian, Codespaces)
1001 – 9999            Additional Human Users / Host Service Accounts
10000+                 Cloud Application / Container Sandbox Space
```

### 3 Key Architectural Reasons for `10001`:

1. **Host Human User Collision Prevention:**
   * On cloud VMs and developer workstations, the default human account is almost universally assigned `UID 1000`.
   * If a container process runs as `UID 1000` and a host directory is volume-mounted (`-v /host/dir:/data`), the container process has identical read/write ownership as the host developer.
   * Selecting `10001` guarantees the container user is an unrecognized stranger to host files.

2. **System Service Space Protection:**
   * `UID 1 - 999` are statically or dynamically assigned to base Linux system packages (`www-data`, `systemd-resolve`, `nobody`).
   * Using a high number avoids clashing with distribution-level system accounts.

3. **Kubernetes CIS & PodSecurityStandards Compliance:**
   * Enterprise Kubernetes security policies (Kyverno, OPA Gatekeeper, OpenShift SCC) enforce `MustRunAsNonRoot: true`.
   * OpenShift and corporate clusters often randomize or enforce UIDs in high ranges ($\ge 10000$) to guarantee zero root privilege inheritance.
