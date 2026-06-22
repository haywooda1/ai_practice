# Kubernetes & GitOps Fluency Notes

*For NVIDIA DGX Cloud EM role prep*

## Why this file exists
DGX Cloud EM role calls for Kubernetes operability, automation, GitOps, observability. Goal is interview-level fluency and hands-on familiarity — not operational mastery. Practicing on a local kind cluster, not production Kubernetes.

---

## Core concept: reconciliation

Kubernetes' control plane continuously compares desired state (what you declared) against actual state (what's really running) and nudges reality to match. Same idea as a storage controller continuously checking RAID health against a target config. This same reconciliation pattern repeats at every layer: the Deployment controller reconciles pods, and (later) ArgoCD reconciles the whole cluster against Git.

---

## Vocabulary, mapped to storage/SAN background

- **Pod** — smallest deployable unit (1+ containers). Like a LUN, but ephemeral — expected to die and be replaced, not nursed back to health.
- **Node** — a machine (physical, VM, or in kind's case a Docker container) running pods.
- **Deployment** — controller managing a set of identical pods; handles rolling updates and self-healing.
- **Service** — stable network identity/load balancer in front of a changing set of pods. Solves "pod IPs constantly change, but consumers need one stable address." Finds pods via **label selectors**, not pod names — so new matching pods are picked up automatically with zero reconfiguration.
- **Namespace** — logical partition, like a storage pool or tenant boundary.
- **etcd** — distributed key-value store holding all cluster state; the "brain."
- **kubectl** — CLI client only. Does not run any cluster components itself — sends API requests to whatever cluster is set as the "current context," reads connection info from `~/.kube/config`.

---

## GitOps concept

Deployment philosophy: desired cluster state lives as files in a Git repo. A controller (ArgoCD or Flux) running inside the cluster continuously watches the repo and reconciles the live cluster to match — no engineer running `kubectl apply` by hand. The PR becomes the change-control/audit-trail mechanism.

**Interview pitch line**: "GitOps is change control as code — same rigor as release readiness gates, expressed as a reconciliation loop instead of a manual gate."

---

## Local cluster setup (kind)

Prerequisite — Docker Desktop must be installed AND running before kind will work. kind does not bundle Docker; it calls Docker's existing API/socket, the same one the `docker` CLI uses.

```bash
# one-time installs
brew install kind
brew install kubectl
brew install --cask docker     # installs the Docker Desktop app
open -a Docker                 # launch it; wait for whale icon to stop animating
docker ps                      # confirms daemon is up (empty table = good)

# create and verify cluster
kind create cluster --name dgx-practice
kubectl cluster-info --context kind-dgx-practice
kubectl get nodes
```

---

## Client/daemon pattern (shows up at every layer)

`docker` CLI talks to the Docker daemon (`dockerd`), which on Mac runs inside Docker Desktop's background Linux VM (Mac can't run Linux containers natively). Same shape as `kubectl` talking to the Kubernetes API server. Thin client sends request → background service does the work → response streamed back.

Check both client and server versions are visibly separate:
```bash
docker version
```

---

## Image name resolution (Docker and Kubernetes share this)

Short names like `nginx` or `hello-world` expand using default rules: no registry → `docker.io`, no namespace → `library` (means "official image"), no tag → `:latest`. Full resolved name: `docker.io/library/nginx:latest`. Kubernetes reuses this same OCI/registry convention — `kubectl create deployment hello --image=nginx` resolves the image the same way `docker pull nginx` would.

---

## kubectl contexts (multi-cluster management)

```bash
kubectl config get-contexts          # list all saved contexts; * marks current
kubectl config use-context <name>    # switch default cluster
kubectl config current-context       # confirm what's active
```

Contexts persist in `~/.kube/config`, apply across all terminals (not per-shell). Real-world risk: forgetting which context is "current" and running a destructive command against the wrong cluster (e.g. prod instead of test). Professional habit: check `current-context` before anything destructive, or use `kubectx`/`kubens` for shell-visible context. Directly relevant to DGX Cloud JD's NCP + on-prem multi-environment scope.

---

## Deployments, scaling, self-healing

```bash
kubectl create deployment hello --image=nginx
kubectl get pods
kubectl scale deployment hello --replicas=3
kubectl delete pod <pod-name>        # watch it — a NEW pod (new name) appears immediately
kubectl get pods
```

Deleted pods are never resurrected — always replaced by a brand-new instance (new name, fresh state). This is the reconciliation loop made visible.

---

## Services and load balancing

```bash
kubectl expose deployment hello --port=80 --type=NodePort
kubectl get service hello            # shows PORT(S) like 80:31669/TCP
```

80 = Service's internal cluster port. 31669 = NodePort (random 30000-32767 range), meant to be reachable from outside the cluster.

**kind-specific wrinkle**: NodePort isn't directly reachable from the Mac because the "node" is just a Docker container with its own network namespace.

**Important gotcha**: `kubectl port-forward service/hello 8080:80` does NOT go through the Service's load balancer — it tunnels directly to one single pod for the whole session, bypassing kube-proxy entirely. It's a debugging convenience, not representative of real traffic. Confirmed by watching logs: every request showed the same pod name and source IP `127.0.0.1` (looks locally-sourced because it's tunneled).

To see real load balancing, send traffic from inside the cluster's network instead:

```bash
kubectl run tmp-curl --image=curlimages/curl --rm -it --restart=Never -- sh
# inside the temp pod:
curl hello      # Service name resolves via cluster-internal DNS
curl hello
curl hello
exit            # --rm means the temp pod self-deletes on exit
```

Watch with:
```bash
kubectl logs -l app=hello --prefix -f
```
(the `-l app=hello` label selector is the same mechanism the Service itself uses to find pods)

Confirmed: requests genuinely spread across different pod names, with real pod source IPs (10.244.x.x pod CIDR range) instead of 127.0.0.1. Distribution isn't strict round-robin — closer to random per-connection, so small sample sizes can look uneven.

---

## Building and deploying a custom image

This is the real-world pattern — building your own application image rather than deploying someone else's pre-built one.

### Project structure

```
k8s_webapp/
  Dockerfile      # recipe for building the image (capital D, no extension)
  index.html      # your custom content
```

### Dockerfile — working hardened version (v3)

```dockerfile
FROM nginx:latest

COPY index.html /usr/share/nginx/html/index.html

RUN chown nginx:nginx /usr/share/nginx/html/index.html

RUN chown -R nginx:nginx /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx
```

**Why each line matters:**
- `FROM nginx:latest` — starts from the official nginx image as a base layer; your changes stack on top
- `COPY` — runs during build as root; copies your HTML into nginx's web root
- First `RUN chown` — fixes ownership of your copied file
- Second `RUN chown -R` — pre-creates and fixes ownership of nginx's cache directories and PID file *before* switching user; this is the critical fix (see troubleshooting below)
- `USER nginx` — switches the runtime process to non-root; everything after this point runs as nginx

### Build, test locally, then deploy to kind

```bash
# build
docker build -t my-k8s-app:v3 .

# test with plain Docker FIRST — isolates image issues from Kubernetes issues
docker run --rm -d -p 8081:80 --name test-v3 my-k8s-app:v3
docker run --rm my-k8s-app:v3 whoami    # should return "nginx" not "root"
curl localhost:8081                      # should return your custom HTML
docker rm -f test-v3

# load into kind node (required — kind cluster can't see Mac's Docker image store directly)
kind load docker-image my-k8s-app:v3 --name dgx-practice

# deploy
kubectl create deployment my-app --image=my-k8s-app:v3
kubectl get pods                         # watch for 1/1 Running, zero restarts
kubectl expose deployment my-app --port=80 --type=NodePort
```

### Image store separation — critical concept

There are two completely separate image inventories:

```
Mac's Docker store    →  docker images             (what you've built/pulled locally)
kind node's cache     →  crictl images (inside node) (what Kubernetes can actually deploy)
```

`kind load docker-image` is the explicit copy step between them — nothing flows through automatically. Every new image version needs both `docker build` AND `kind load` before Kubernetes can use it.

```bash
# see Mac's Docker store
docker images

# see kind node's internal cache
docker exec -it dgx-practice-control-plane crictl images
```

### Rolling updates (updating a running deployment)

Don't create a new deployment for each version — update the existing one:

```bash
# first confirm exact container name (not the same as deployment name)
kubectl describe deployment my-app | grep -A2 "Containers:"

# rolling update — replaces pods one at a time, keeps service available throughout
kubectl set image deployment/my-app my-k8s-app=my-k8s-app:v3
kubectl rollout status deployment/my-app

# verify which image pods are actually running
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"  ->  "}{.spec.containers[*].image}{"\n"}{end}'

# verify running user inside the live pod
kubectl exec deployment/my-app -- whoami

# roll back if something broke
kubectl rollout undo deployment/my-app
```

**Container name gotcha**: `kubectl set image` requires the *container's* name (left side of `=`), not the deployment name. When you run `kubectl create deployment my-app --image=my-k8s-app:v3`, Kubernetes names the container after the *image* (`my-k8s-app`), not the deployment (`my-app`). Always confirm with `kubectl describe deployment <name> | grep -A2 "Containers:"` before running `set image`.

### Inspect image filesystem

```bash
# list files in a specific directory inside the image
docker run --rm my-k8s-app:v3 ls -la /usr/share/nginx/html/

# interactive shell inside the image (exits and auto-removes when done)
docker run --rm -it my-k8s-app:v3 sh

# check architecture of a built image
docker inspect my-k8s-app:v3 --format '{{.Architecture}}'
```

### Docker storage and space management

```bash
docker system df                  # breakdown of image/container/volume/cache usage
docker system prune               # remove stopped containers, dangling images, unused cache
docker image rm my-k8s-app:v1    # remove a specific image
```

Docker Desktop's VM disk ceiling is set in GUI: Settings → Resources → Advanced → Virtual disk limit. Default is usually 64GB; grows on demand up to that ceiling, doesn't pre-allocate.

---

## Architecture transition: Intel → ARM (Apple Silicon)

### What happened
Migrating a Mac from Intel (x86_64/amd64) to ARM (Apple Silicon/arm64) breaks existing kind clusters and tool installations because: Docker images are compiled for a specific CPU architecture, Homebrew installs to a different path on ARM (`/opt/homebrew/bin` vs Intel's `/usr/local/bin`), and kind/kubectl binaries need to be ARM-native.

### Symptoms
- `kind` and `kubectl` not found after migration (Homebrew PATH issue or tools not reinstalled for ARM)
- kind cluster starts but Kubernetes API server never comes up (`connection refused` on kubectl commands)
- Pod errors related to cgroups, `/sys` remounting, or privileged operations
- `docker logs dgx-practice-control-plane` shows `INFO: starting init` as the last line with nothing following

### Diagnosis commands
```bash
docker info | grep Architecture          # confirm Docker is running ARM-native
docker inspect <image> --format '{{.Architecture}}'  # check a specific image's arch
which kind || echo "not found"           # confirm kind is on PATH
which kubectl || echo "not found"        # confirm kubectl is on PATH
echo $PATH                               # check Homebrew path is included
docker logs dgx-practice-control-plane  # check node container startup
```

### Fix: clean reinstall after architecture transition

```bash
# 1. remove zombie container if kind delete cluster failed to clean up
docker rm -f dgx-practice-control-plane

# 2. clean up stale kubectl context
kind delete cluster --name dgx-practice   # may partially fail, that's fine

# 3. reinstall tools (Homebrew will pull ARM-native binaries)
brew install kind
brew install kubectl

# 4. confirm versions
kind version
kubectl version --client

# 5. recreate cluster fresh (kind auto-pulls ARM-native node image)
kind create cluster --name dgx-practice
kubectl get nodes                         # should show Ready
```

### Key insight
"Container is Up" (per `docker ps`) and "Kubernetes API server is running" are two different things. The kind node container can show as `Up` while the Kubernetes processes inside it (API server, etcd, scheduler) never started. Always verify with `kubectl get nodes` returning `Ready`, not just `docker ps` showing `Up`.

### Two kindest/node images showing in docker images
```
kindest/node:v1.36.1                    (human-readable tag)
kindest/node@sha256:3489c767...         (pulled by digest)
```
Same image, same ID, two references — not double storage. Docker deduplicates by layer content; the `DISK USAGE` column in `docker system df` reflects real usage, not per-tag double-counting.

---

## Cleanup

```bash
pkill -f "port-forward"               # kill a dangling port-forward if left running
ps aux | grep port-forward            # confirm it's gone
kind delete cluster --name dgx-practice
```

---

## GitOps next steps (ArgoCD) — in progress

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd            # wait for server, repo-server, application-controller, redis, dex to go Running
```

Concept: ArgoCD watches a Git repo and reconciles the *whole cluster* against it — same reconciliation pattern as the Deployment controller, one layer up. Git repo becomes the source of truth instead of engineers running kubectl apply by hand.

---

## End-to-end runbook: Docker running → app live in Kubernetes

Starting point: Docker Desktop is open and the whale icon is steady.

### Step 1: Confirm Docker is actually up
```bash
docker ps
```
Empty table = Docker daemon is running and ready. If you get a connection error, open Docker Desktop from Applications and wait for the whale icon to stop animating.

### Step 2: Create your cluster
```bash
kind create cluster --name dgx-practice
```
Spins up a single Docker container acting as a full Kubernetes node — control plane, reconciliation loop, and all — and automatically writes connection info into `~/.kube/config`.

Verify it's genuinely alive (not just "container is Up"):
```bash
kubectl get nodes
```
Must return `Ready`. That's the API server responding — not just Docker reporting the container is running. Two different things.

### Step 3: Build your application image
```bash
cd ~/DEV_Space/ai_practice/k8s_webapp
docker build -t my-k8s-app:v3 .
```
The `.` at the end is not optional — it tells Docker where the build context lives. Capital `D` on `Dockerfile`, no extension.

### Step 4: Test the image locally with plain Docker first
Always do this before touching Kubernetes — isolates "is my image broken" from "is my Kubernetes config broken":
```bash
docker run --rm -d -p 8081:80 --name test-app my-k8s-app:v3
curl localhost:8081                       # should return your custom HTML
docker run --rm my-k8s-app:v3 whoami    # should return "nginx" not "root"
docker rm -f test-app
```

### Step 5: Load your image into the kind node
The kind node is a separate, isolated environment — it cannot see your Mac's Docker image store directly. You must explicitly copy the image across:
```bash
kind load docker-image my-k8s-app:v3 --name dgx-practice
```
Confirm it landed inside the node:
```bash
docker exec -it dgx-practice-control-plane crictl images
```

### Step 6: Deploy to Kubernetes
```bash
kubectl create deployment my-app --image=my-k8s-app:v3
kubectl get pods
```
Watch for `1/1 Running` with zero restarts. If you see `Error` or `CrashLoopBackOff`, check logs immediately:
```bash
kubectl logs <pod-name>
kubectl logs <pod-name> --previous    # if it's already cycled through restarts
```

### Step 7: Expose it via a Service
```bash
kubectl expose deployment my-app --port=80 --type=NodePort
kubectl get service my-app
```
Creates the stable front-end that load-balances across pods using label selectors. Output shows a port mapping like `80:31xxx/TCP` — the number after the colon is the NodePort.

### Step 8: Confirm traffic is actually flowing
NodePort isn't directly reachable from your Mac due to kind's networking. Use a temporary pod inside the cluster network instead:
```bash
kubectl run tmp-curl --image=curlimages/curl --rm -it --restart=Never -- sh
# inside that shell:
curl my-app
exit
```
Your custom HTML coming back confirms the full chain: image → kind load → Deployment → Service → real traffic.

### Step 9: Update to a new version (rolling update)
When you make changes and rebuild:
```bash
docker build -t my-k8s-app:v4 .
kind load docker-image my-k8s-app:v4 --name dgx-practice
kubectl set image deployment/my-app my-k8s-app=my-k8s-app:v4
kubectl rollout status deployment/my-app
```
Kubernetes replaces pods one at a time — the Service stays available throughout. Roll back instantly if something breaks:
```bash
kubectl rollout undo deployment/my-app
```

### Step 10: Tear down when done
```bash
kind delete cluster --name dgx-practice
```
Clusters are disposable — cheap to destroy, cheap to recreate. Don't leave them running when not in use.

**Mental model across all of this**: Docker is the engine. kind uses Docker to fake a real server. Kubernetes runs inside that fake server and manages your pods. kubectl is your remote control talking to Kubernetes' API from the outside. Every other concept — Services, rolling updates, label selectors — is detail layered on top of that foundation.

---

## ArgoCD & GitOps — installation and configuration

### What ArgoCD is and why it matters
ArgoCD is a GitOps controller that runs *inside* your Kubernetes cluster and watches a Git repo. When the repo changes, ArgoCD automatically reconciles the cluster to match — replacing manual `kubectl apply` commands with a continuous, automated sync loop. Git becomes the single source of truth; ArgoCD is the engine that enforces it.

The full GitOps flow:
```
You edit YAML → push to GitHub → ArgoCD detects change → applies it to cluster
```
Vs. the manual flow you started with:
```
You run kubectl create / kubectl set image → cluster changes
```

**Interview pitch**: "GitOps replaces imperative kubectl commands with declarative Git-driven reconciliation — same change control discipline as release readiness gates, but enforced automatically by a controller rather than a manual process."

---

### Where to find Kubernetes tooling
The authoritative resource for the cloud-native ecosystem is the **CNCF Landscape**: `landscape.cncf.io`. The Cloud Native Computing Foundation governs Kubernetes and most tools built around it. Tools are organized by category (CI/CD, observability, storage, security) and tiered by maturity:
- **Graduated** — production-proven, widely adopted (Kubernetes, Prometheus, ArgoCD)
- **Incubating** — growing adoption, still maturing
- **Sandbox** — early stage, experimental

For production infrastructure, always prefer Graduated or well-established Incubating projects. ArgoCD and Flux are the two dominant GitOps controllers — both Graduated. ArgoCD has broader adoption and a more mature UI, making it the better starting point.

For any specific tool: search CNCF Landscape for the category → find the GitHub repo → README has install instructions.

---

### Installing ArgoCD into the cluster

ArgoCD runs as pods in its own namespace — a logical partition inside the cluster, not a new container or node:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

The install URL comes from ArgoCD's official getting started docs: `argo-cd.readthedocs.io/en/stable/getting_started/`. The `stable` in the path always points to the latest stable release. Before running `kubectl apply -f <url>` in production, open the URL in a browser first and read what it creates — it's applying cluster-level resources and you should understand what they are.

Watch pods come up (takes 2-3 minutes on first install):
```bash
kubectl get pods -n argocd --watch
```

Expected pods — all should reach `Running`:
- `argocd-server` — the API server and UI
- `argocd-repo-server` — clones and reads Git repos
- `argocd-application-controller` — the reconciliation engine
- `argocd-redis` — caching layer
- `argocd-dex-server` — SSO/authentication
- `argocd-applicationset-controller` — manages sets of applications
- `argocd-notifications-controller` — handles alerting

**Expected behavior on first install**: `dex-server` and `applicationset-controller` commonly show `Error` or `CrashLoopBackOff` briefly on startup due to dependency race conditions (dex needs Redis fully ready before it can initialize). Both self-heal within a few minutes — same reconciliation loop as everything else in Kubernetes. Only investigate if they stay in `CrashLoopBackOff` for more than 5 minutes.

---

### Namespaces — important concept

A namespace is a **logical boundary** inside Kubernetes, not a container or node. No new compute spins up when you create one — it's purely organizational, like a folder. Resources in different namespaces are isolated from each other within the same cluster.

```bash
kubectl get pods                    # only shows default namespace
kubectl get pods -n argocd          # shows argocd namespace
kubectl get pods --all-namespaces   # shows everything
```

ArgoCD itself lives in the `argocd` namespace. Your application (`my-app`) lives in `default`. These are intentionally separate — ArgoCD is the manager in its own office, reaching out to manage workers on a different floor. In production you'd deploy into namespaces like `production`, `staging`, or team-specific partitions, keeping GitOps tooling cleanly separated from workloads.

---

### Accessing the ArgoCD UI

```bash
# port-forward to reach the UI from your Mac (occupies the terminal)
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Get the auto-generated admin password (stored as a Kubernetes Secret):
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Breaking that command down:
- `get secret argocd-initial-admin-secret` — retrieves the Secret object ArgoCD created during install
- `-o jsonpath="{.data.password}"` — extracts just the password field from the full JSON object
- `| base64 -d` — decodes it from base64 (Kubernetes Secrets store values base64-encoded, not encrypted — real security comes from RBAC and etcd encryption at rest)

Open `https://localhost:8080` in browser. Accept the certificate warning (self-signed cert in a local cluster, expected). Login: `admin` / <password from above>.

---

### Kubernetes manifest files (replacing kubectl commands with YAML)

Instead of `kubectl create deployment` and `kubectl expose`, you declare the same desired state as YAML files that ArgoCD reads from Git:

**`k8s-manifests/deployment.yaml`**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-k8s-app
        image: my-k8s-app:v3
        ports:
        - containerPort: 80
```

**`k8s-manifests/service.yaml`**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 80
  type: NodePort
```

These files live in the repo at `k8s-manifests/` — ArgoCD watches that specific folder, not the whole repo.

---

### Connecting ArgoCD to GitHub (UI method)

In the ArgoCD dashboard → **+ New App**:

| Field | Value | Why |
|---|---|---|
| Application Name | `my-app` | identifies this app in ArgoCD |
| Project | `default` | ArgoCD's own grouping concept |
| Sync Policy | `Automatic` | ArgoCD applies Git changes without manual intervention |
| Self Heal | checked | reverts any manual kubectl drift back to Git state |
| Repository URL | `https://github.com/haywooda1/ai_practice` | where to watch |
| Revision | `HEAD` | always track latest commit on default branch |
| Path | `k8s-manifests` | specific folder to watch, not whole repo |
| Cluster URL | `https://kubernetes.default.svc` | deploy into the same cluster ArgoCD runs in |
| Namespace | `default` | where YOUR app's resources go (not where ArgoCD lives) |

**The namespace distinction**: ArgoCD lives in `argocd` namespace. The destination namespace (`default`) is where ArgoCD deploys *your* application resources. These are always separate — ArgoCD's home vs. where it manages work.

---

### ArgoCD status indicators

- **Synced** — what's in Git matches what's in the cluster
- **OutOfSync** — Git and cluster have drifted (change detected but not yet applied)
- **Healthy** — the actual resources are running correctly
- **Degraded** — resources exist but aren't functioning correctly

With `Automatic` sync + `Self Heal` enabled, `OutOfSync` should be transient — ArgoCD applies the change and returns to `Synced` automatically.

---

### Proving the GitOps loop works

Make a change in Git and watch ArgoCD apply it without any kubectl commands:

```bash
# edit k8s-manifests/deployment.yaml — change replicas: 1 to replicas: 2
git add k8s-manifests/deployment.yaml
git commit -m "Scale my-app to 2 replicas"
git push origin main
```

In the ArgoCD UI, click **Refresh** to force an immediate sync (default poll interval is 3 minutes). Watch the app card go `OutOfSync` → `Synced`, and the visual graph update from 1 pod to 2.

Confirm from terminal:
```bash
kubectl get pods
```

Two pods appear — one old, one new (43 seconds old in practice) — without a single kubectl command after the push. That's the GitOps loop confirmed.

**Interview summary**: "I edited a YAML file, pushed it to GitHub, and ArgoCD detected the change and reconciled the cluster to match — scaling from 1 to 2 replicas automatically. No manual kubectl commands after the initial setup."

---

### Understanding the ArgoCD visual graph

The ArgoCD UI shows a visual graph of every resource it manages. Here's what each layer means for `my-app`:

```
ArgoCD Application (my-app)
  ├── Service (my-app-svc)          — peer of Deployment, not below it
  └── Deployment (my-app)          — desired state declaration
        ├── ReplicaSet rev1         — previous version, 0 pods, kept for rollback
        └── ReplicaSet rev2         — current version, 2 pods running
              ├── Pod 1
              └── Pod 2
```

**ArgoCD Application** — the top-level object is ArgoCD's own construct, not a Kubernetes resource. It represents "I am responsible for watching this repo and managing everything below this point."

**Service** — shown as a sibling of the Deployment, not below it, because they're peers in Kubernetes — neither owns the other. The Service selects the same pods the Deployment manages via label selectors. ArgoCD shows them as siblings because both came from the same Git folder, managed by the same Application.

**Deployment** — the familiar object that declares desired state: "I want N replicas of this container image running." Importantly, the Deployment doesn't manage pods directly — it manages ReplicaSets, which in turn manage pods.

**ReplicaSets (rev1, rev2)** — the layer most people don't realize exists. A ReplicaSet is the object that actually owns and manages pods directly. Every rolling update creates a brand new ReplicaSet for the new version and gradually scales it up while scaling the old one down. The old ReplicaSet (rev1) stays around at **zero replicas** as a rollback safety net — `kubectl rollout undo` just scales rev1 back up and rev2 back down, which is why rollbacks are near-instant. Nothing is rebuilt; Kubernetes just shifts which ReplicaSet is active.

**Pods** — only appear under the current active ReplicaSet (rev2). rev1 sits at zero pods but is retained specifically for rollback capability.

**Why this matters for interviews**: If asked "how do rolling updates work in Kubernetes," the complete answer involves ReplicaSets: "Kubernetes creates a new ReplicaSet for each version, scales it up while scaling the old one down, and retains the old ReplicaSet at zero replicas to enable instant rollback." This is stronger than "it replaces pods one at a time" — which is true but incomplete.

**Settings → Repositories in ArgoCD UI** — your repo doesn't appear here because it's public. ArgoCD fetched it anonymously without needing stored credentials. Settings → Repositories is where you register **private** repos with credentials (SSH key, GitHub token) so ArgoCD can authenticate. In production, repos are almost always private and would be registered here. For public repos, ArgoCD uses the URL embedded in the app spec directly without a formal registered connection.

---

### Git repo hygiene for ArgoCD

ArgoCD refuses to process repos containing out-of-bounds symlinks (symlinks pointing outside the repo boundary) — it flags these as a security concern to prevent path traversal attacks.

Common culprit: symlinks to local Mac files used by Python scripts (e.g. `fidelity_export.csv -> /Users/Adam/Documents/...`). Fix: remove from Git tracking without deleting the actual file:

```bash
# check what's tracked
git ls-files

# remove symlinks from tracking (keeps the file on disk)
git rm --cached fidelity_export.csv
git rm --cached capitalgroup.csv

# prevent re-adding
echo "fidelity_export.csv" >> .gitignore
echo "capitalgroup.csv" >> .gitignore
echo ".DS_Store" >> .gitignore

git add .gitignore
git commit -m "Remove out-of-bounds symlinks from git tracking"
git push origin main
```

The `--cached` flag is critical — removes from Git without touching the filesystem. Python scripts that depend on those symlinks continue working unchanged.

---

## Troubleshooting Log (Kubernetes-specific)

| Problem | Cause | Fix |
|---|---|---|
| `kind create cluster` fails with "Cannot connect to the Docker daemon" | Docker Desktop not installed or not running | `brew install --cask docker`, then `open -a Docker`, wait for whale icon to settle, confirm with `docker ps` |
| `port-forward` shows only one pod name in logs no matter how many times you curl | port-forward bypasses the Service's load balancer, tunnels to one pod for the whole session | Use `kubectl run tmp-curl ... -- sh` and `curl hello` from inside the cluster instead |
| Pod stuck in `ImagePullBackOff` / `ErrImagePull` | Image name doesn't exist, typo in `--image=`, or image not loaded into kind node | Verify with `docker pull <image>` first; confirm `kind load docker-image` completed |
| Forgot which cluster kubectl is pointed at | Multiple contexts saved, wrong one is "current" | `kubectl config current-context` before anything destructive |
| `kubectl set image` returns "unable to find container named X" | Container name inside deployment ≠ deployment name; Kubernetes names container after the image, not the deployment | Run `kubectl describe deployment <name> | grep -A2 "Containers:"` to get real container name |
| Pod in `Error` / `CrashLoopBackOff` after adding `USER nginx` to Dockerfile | nginx base image assumes root startup to create cache dirs; `USER nginx` bypasses that | Pre-create and chown `/var/cache/nginx`, `/var/run`, and nginx.pid before `USER nginx` directive (see hardened Dockerfile above) |
| `mkdir() "/var/cache/nginx/client_temp" failed (13: Permission denied)` in pod logs | Same as above — nginx can't create its working directories as non-root | Apply the full `RUN chown -R nginx:nginx /var/cache/nginx /var/run` fix in Dockerfile |
| `kind create cluster` fails with "container name already in use" | Previous cluster deletion failed, leaving zombie container | `docker rm -f dgx-practice-control-plane` then retry `kind create cluster` |
| `kubectl get nodes` returns `connection refused` after architecture migration | kind node container is Up but Kubernetes API server inside it never started — architecture mismatch or cgroup issue | Delete zombie container, reinstall kind/kubectl via Homebrew for ARM, recreate cluster fresh |
| `kind` or `kubectl` not found after Intel → ARM migration | Homebrew PATH changed (`/opt/homebrew/bin` on ARM vs `/usr/local/bin` on Intel) or tools not reinstalled | `brew install kind && brew install kubectl`; confirm with `which kind` |
| `docker build` fails with "requires 1 argument" | Missing build context path (the trailing `.`) | Always end `docker build -t name:tag .` with a space and `.` for current directory, or provide explicit path |

---

*Last updated: June 2026*
*Repo: github.com/haywooda1/ai_practice*
