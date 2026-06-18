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

## Troubleshooting Log (Kubernetes-specific)

| Problem | Cause | Fix |
|---|---|---|
| `kind create cluster` fails with "Cannot connect to the Docker daemon" | Docker Desktop not installed or not running | `brew install --cask docker`, then `open -a Docker`, wait for whale icon to settle, confirm with `docker ps` |
| `port-forward` shows only one pod name in logs no matter how many times you curl | port-forward bypasses the Service's load balancer, tunnels to one pod for the whole session | Use `kubectl run tmp-curl ... -- sh` and `curl hello` from inside the cluster instead |
| Pod stuck in `ImagePullBackOff` / `ErrImagePull` | Image name doesn't exist or typo in `--image=` | Verify with `docker pull <image>` manually first |
| Forgot which cluster kubectl is pointed at | Multiple contexts saved, wrong one is "current" | `kubectl config current-context` before anything destructive |

---

*Last updated: June 2026*
*Repo: github.com/haywooda1/ai_practice*
