# Podman Notes

*Container engine alternative to Docker — understanding tradeoffs and migration*

---

## What Podman is

Podman (Pod Manager) is a container engine developed by Red Hat that does essentially the same job as Docker — builds images, runs containers, manages local image storage — but with a fundamentally different architecture underneath. The name isn't accidental: it was built from the ground up to understand Kubernetes' pod concept natively, not just individual containers.

---

## The key architectural difference: daemonless

This is the single most important distinction.

Docker requires a background daemon (`dockerd`) running continuously as root — everything you do with the `docker` CLI is a request to that daemon. That daemon runs as root the entire time, which means if something exploits the Docker daemon, it has root access to your entire machine.

Podman has no daemon. When you run `podman run nginx`, it directly starts the container process as a child of your own shell — no intermediary service involved. When the command finishes, nothing keeps running in the background.

**Security implication**: containers run as your own user (non-root) by default — called "rootless containers." A compromised container can't escalate to root because it never had root in the first place. This matters enormously in enterprise and security-regulated environments.

**Reliability implication**: if Docker's daemon crashes, every container it manages goes down with it. With Podman, each container is its own independent process — one crashing doesn't affect others.

---

## How similar are they in practice?

Extremely similar from a day-to-day usage perspective. Podman was deliberately designed as a drop-in replacement — most commands are identical:

```bash
# Docker                          # Podman equivalent
docker run nginx                  podman run nginx
docker build -t myapp .           podman build -t myapp .
docker ps                         podman ps
docker images                     podman images
docker push                       podman push
```

You can literally alias `docker` to `podman` on many systems and most workflows continue working unchanged:
```bash
alias docker=podman
```

Both use the same OCI (Open Container Initiative) image format — images built with Docker run on Podman and vice versa, and both pull from the same registries (Docker Hub, etc.).

---

## Where they diverge

**Compose**: Docker has Docker Compose for defining multi-container applications. Podman has `podman-compose` (a separate community project) and `podman play kube` (which runs Kubernetes YAML directly). Neither is as seamless as Docker Compose yet, though improving.

**Desktop experience**: Docker Desktop is a polished, well-supported product with a GUI, resource controls, and good Mac/Windows integration. Podman Desktop exists but is less mature. For learning and development on a Mac, Docker Desktop is still the smoother experience.

**Ecosystem and tooling**: Docker has a larger ecosystem, more tutorials, and more third-party tool integrations simply because it's been around longer. If you hit a problem with Docker, Stack Overflow has ten answers. Podman's community is smaller, though growing fast particularly in enterprise Linux environments.

**kind compatibility**: kind was built assuming Docker as the container runtime. Podman can work with kind but requires extra configuration (`KIND_EXPERIMENTAL_PROVIDER=podman`) and has known quirks on macOS. For kind-based Kubernetes development, Docker Desktop is the right choice.

---

## Tradeoff summary

| | Docker | Podman |
|---|---|---|
| Architecture | Daemon-based (root) | Daemonless (rootless) |
| Security model | Root daemon, more attack surface | Non-root by default, smaller attack surface |
| Mac/Windows experience | Excellent (Docker Desktop) | Still maturing |
| Command compatibility | The original | Near-identical, drop-in replacement |
| Ecosystem/community | Larger, more tutorials | Smaller but growing fast |
| Enterprise Linux | Less common | Default on RHEL/CentOS 8+ |
| kind compatibility | Native | Requires extra config |
| Kubernetes alignment | Separate tool | Natively understands pods |
| Auto-start on boot | Docker daemon handles it | Requires systemd unit files |

---

## Migration: Docker to Podman

The migration story is one of Podman's strongest selling points. For most workloads it's surprisingly straightforward because of the deliberate compatibility decisions Podman's team made. But there are real gotchas worth knowing about for production environments.

### Why migration is simpler than you'd expect

The OCI image format is shared — existing Docker images don't need to be rebuilt. Podman pulls and runs them directly from the same registries. Dockerfiles are identical; `podman build` reads the same file. Scripts, CI/CD pipelines, and runbooks written for Docker often run unmodified under Podman.

### Step 1: Inventory what you're running

Before touching anything, understand scope:
```bash
docker ps -a          # all running and stopped containers
docker images         # all local images
docker volume ls      # persistent volumes
docker network ls     # custom networks
```

### Step 2: Install Podman alongside Docker (don't remove Docker yet)

Run both side by side during transition — nothing forces a big-bang cutover.

On Mac:
```bash
brew install podman
brew install podman-desktop    # optional GUI
podman machine init            # creates Podman's VM (similar to Docker Desktop's VM)
podman machine start
```

On RHEL/CentOS (where Docker may not even be installed):
```bash
sudo dnf install podman        # already default on RHEL 8+
```

### Step 3: Validate your images run on Podman

Pull or transfer existing images and test them:
```bash
podman pull your-image:tag
podman run your-image:tag
```

For images that only exist locally in Docker's store, export and import:
```bash
# export from Docker
docker save my-app:v3 -o my-app-v3.tar

# import into Podman
podman load -i my-app-v3.tar
```

### Step 4: Handle the daemon-dependent pieces

This is where the real migration work lives. Several things that worked transparently under Docker's daemon need explicit handling in Podman's daemonless model.

**Auto-start on boot**: Docker containers restart automatically because the daemon starts at boot. With Podman, generate systemd service files instead:
```bash
podman generate systemd --name my-container --files --new
```
Creates a proper systemd unit file that starts the container at boot — actually cleaner from an enterprise Linux perspective since systemd already manages everything else on the server.

**Docker Compose files**: if you're using `docker-compose.yml`, options are:
- Use `podman-compose` (community project)
- Use `podman play kube` with a Kubernetes YAML equivalent (better long-term if heading toward Kubernetes anyway)
- Use `podman kube generate` to convert running containers into Kubernetes YAML automatically

**Docker socket**: some tools (CI/CD systems, monitoring agents) connect to Docker's socket at `/var/run/docker.sock`. Podman can expose a compatible socket:
```bash
podman system service --time=0 unix:///var/run/docker.sock
```
Makes Podman impersonate Docker's socket so existing tools continue working without modification.

### Step 5: Rootless consideration

This requires the most thought in a production migration. Podman runs rootless by default — the security win, but containers no longer have root access to the host. Most well-written containers handle this fine, but containers built assuming root (binding to ports below 1024, writing to system directories, etc.) need updates.

**Real-world example**: the nginx `USER nginx` fix done during Kubernetes practice is exactly the kind of change needed for containers that assumed root — pre-creating and chown-ing directories the process needs before switching to a non-root user.

### Where migration gets genuinely complicated

**Volumes with root-owned data**: if Docker containers wrote data as root into volumes, those files are root-owned. A rootless Podman container running as your user won't have permission to read them. Fix with `chown` or configure user namespace mapping.

**Privileged containers**: anything running with `--privileged` in Docker needs careful review. Some privileges compensated for Docker's root daemon — they may not be needed in Podman, or may need different handling.

### The production migration strategy that actually works

Rather than a big-bang cutover:

1. New workloads go on Podman from day one
2. Existing workloads migrate opportunistically — when a container needs an update anyway, rebuild and validate on Podman at the same time
3. Run Docker and Podman in parallel during transition (they don't conflict)
4. Remove Docker once everything confirmed working on Podman

This is essentially what Red Hat did when making Podman the default on RHEL 8 — they made it the path forward for new work and let existing Docker users migrate on their own timeline.

---

## Where Podman is winning

Red Hat made Podman the default container engine in RHEL 8 and later — meaning any enterprise environment running Red Hat Linux uses Podman by default. OpenShift (Red Hat's Kubernetes distribution, widely used in enterprise) is built around Podman concepts. In security-regulated environments (finance, government, healthcare), Podman's rootless-by-default model makes it easier to pass security audits.

---

## Explaining Docker and Kubernetes to a non-technical person

### One sentence version
"Docker and Kubernetes solve the problem of 'it works on my machine but not in production' — Docker packages an application so it runs identically anywhere, and Kubernetes manages thousands of those packages running reliably at scale."

### The shipping container analogy
Before shipping containers existed, loading goods onto a ship meant handling every box, barrel, and crate individually — each a different shape, requiring custom handling, slow and error-prone. The shipping container changed that: no matter what's inside, it's the same standard box, so any crane, truck, or ship can move it without caring about the contents.

**Docker is the shipping container for software.** Instead of saying "here's my code, plus a list of libraries you need to install, plus the exact OS version it needs," you package the application and everything it depends on into one standard unit. That unit runs identically on your laptop, a test server, or a data center.

**Kubernetes is the shipping port and logistics system.** Once you have thousands of containers that need to run reliably — across many machines, scaling up and down with demand, recovering automatically when something fails — you need something to manage all of that. Kubernetes decides which machine each container runs on, restarts it automatically if it crashes, spreads traffic across multiple copies, and rolls out updates without taking the whole system down.

### The business case
Without this, companies needed an engineer to manually configure each server, babysit it, and fix things by hand when they broke — slow, expensive, and it didn't scale. Docker and Kubernetes together let a small team reliably run an application across hundreds or thousands of machines, with much of the recovery and scaling automated rather than manual.

---

## Enterprise relevance

Many enterprise Linux environments (RHEL and derivatives) default to Podman, so understanding the architectural differences with Docker is broadly useful platform-engineering context, not just interview material. Being able to articulate the daemonless/rootless security model and what a migration involves shows ecosystem awareness rather than knowledge of just one tool.

**A solid answer on Docker vs Podman migration covers three things:**
1. OCI image format compatibility makes migration technically straightforward for most workloads
2. Real effort is in daemon-dependent pieces (auto-start, socket compatibility, compose files)
3. Rootless default is a security improvement but requires auditing containers built assuming root access

The business case for migrating is strongest in security-regulated environments where Docker's root daemon is a compliance concern, and in Red Hat/RHEL shops where Podman is already the standard.

---

## Troubleshooting Log (Podman-specific)

| Problem | Cause | Fix |
|---|---|---|
| Container can't bind to port 80 after switching to rootless Podman | Ports below 1024 require root; rootless containers can't bind them | Use port 8080 internally and map externally, or configure `net.ipv4.ip_unprivileged_port_start=80` on Linux |
| Container can't read volume data after migration from Docker | Volume data written as root by Docker; rootless Podman runs as your user | `chown -R $USER:$USER /path/to/volume` or configure user namespace mapping |
| Existing tool can't connect to container runtime after switching | Tool hardcoded to Docker socket at `/var/run/docker.sock` | Run `podman system service --time=0 unix:///var/run/docker.sock` to expose compatible socket |
| kind doesn't work with Podman on Mac | kind assumes Docker by default | Set `KIND_EXPERIMENTAL_PROVIDER=podman`; note known networking quirks on macOS — Docker Desktop remains smoother for kind |

---

*Last updated: August 27, 2026 (reviewed/consolidated after DDN offer accepted; general reference going forward)*
*Repo: github.com/haywooda1/ai_practice*