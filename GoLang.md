# Go Learning Notes — DDN Infinia Prep

Tracking notes while building conceptual + hands-on familiarity with Go ahead of DDN Senior Engineering Manager (Platform Engineering / Infinia) interviews.

**Environment:** Intel Mac, native `x86_64` Go install at `/usr/local/bin/go`, Homebrew at `/usr/local`.
**Project location:** `~/DEV_Space/go-learning/filescan`

---

## Why Go, and why infra/storage teams use it

- Built at Google specifically for large distributed systems and network services.
- **Simplicity as a feature**: small language spec, no inheritance, no exceptions — easier for large teams to stay consistent.
- **Built-in concurrency**: goroutines (lightweight threads) + channels (typed pipes) make concurrent I/O far more approachable than thread/lock models.
- **Compiled, statically typed, single static binary** — no runtime/interpreter dependency, which matters for firmware/hardware bring-up and deployment across heterogeneous environments (vs. Python's "which venv is this" problem).
- **Ecosystem tell**: Docker, Kubernetes, Terraform, Prometheus, Etcd are all Go. If Infinia touches orchestration, consensus, or telemetry, Go is likely the default *because* the ecosystem it integrates with is Go-native.

### Quotable lines for interviews
- "Share memory by communicating" (channels) rather than "communicate by sharing memory" (locks).
- Go isn't object-oriented in the classical sense — no classes, no inheritance — but achieves similar goals through **structs**, **interfaces**, and **composition**. Deliberate choice to avoid deep inheritance hierarchy complexity in large codebases.

### Honest framing of my own gap
"I lead platform/quality engineering at the systems level — I read code fluently, understand distributed systems and CI/CD deeply, and I'm building hands-on Go familiarity specifically to review designs and hold technical credibility with the team, not to write production Go myself."

---

## Core concepts

| Concept | What it is | Python analog |
|---|---|---|
| `package main` + `func main()` | Marks file as an executable program with an entry point | `if __name__ == "__main__":` (but mandatory, not conditional) |
| Struct | Named type grouping fields together, data only | `@dataclass` |
| Goroutine (`go func(){}()`) | Lightweight thread managed by Go runtime, not the OS — cheap to spin up thousands | `threading.Thread` / `asyncio` task, but much cheaper |
| Channel (`chan T`) | Typed pipe for passing values between goroutines safely | `queue.Queue` (roughly) |
| `sync.WaitGroup` | Counter tracking outstanding goroutines (`Add`/`Done`/`Wait`) | `threading.join()` on multiple threads |
| `(result, error)` return pattern | Explicit, visible error checking (`if err != nil`) instead of exceptions | try/except, but error is a normal return value |
| `defer` | Schedules a call to run when the enclosing function returns, regardless of exit path | `finally` block |
| Interface | A set of method signatures; any type implementing them satisfies it automatically (no `implements` keyword) | Duck typing / structural typing |
| Exported vs unexported | Capitalized identifier = exported/public; lowercase = package-private. No `public`/`private` keywords. | `_leading_underscore` convention, but enforced by compiler in Go |
| `:=` | Declare + assign in one step, type inferred | `x = value` (Python has no static type to infer, but same shorthand feel) |
| `nil` | Go's `None`/`null` | `None` |

### Standard library packages used so far
- `fmt` — formatting/printing (`Println`, `Printf`, `Errorf`) — like Python's `print()` + string formatting combined.
- `os` — OS interface: `os.Args` (CLI args), `os.Exit`, env vars, file handles — like Python's `os` + `sys` combined.
- `path/filepath` — portable path handling + `filepath.Walk` for recursive directory traversal — like `os.walk` + `pathlib`.

### Where to look things up (not memorized — nobody memorizes stdlib)
- [pkg.go.dev/std](https://pkg.go.dev/std) — official standard library reference.
- `go doc <package>.<Function>` — e.g. `go doc fmt.Println` — same lookup, from the terminal.
- Recognize-by-repetition packages: `fmt`, `os`, `strings`, `errors`, `time`, `context`, `sync`, `net/http`.

---

## Project: `filescan` — concurrent directory scanner

**Why this project:** touches goroutines, channels, WaitGroups, file I/O, and the (result, error) pattern in one small tool — directly echoes "platform bring-up" style work, and gives an honest, specific answer to "what have you built while learning Go."

### v1 — sequential (working, tested)

Scans a directory tree recursively and reports file count + total size.

```go
package main

import (
	"fmt"
	"os"
	"path/filepath"
)

type DirStats struct {
	Path      string
	FileCount int
	TotalSize int64
}

func scanDir(path string) (DirStats, error) {
	stats := DirStats{Path: path}

	err := filepath.Walk(path, func(p string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			stats.FileCount++
			stats.TotalSize += info.Size()
		}
		return nil
	})

	return stats, err
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("usage: filescan <directory>")
		os.Exit(1)
	}

	stats, err := scanDir(os.Args[1])
	if err != nil {
		fmt.Println("error:", err)
		os.Exit(1)
	}

	fmt.Printf("%s: %d files, %d bytes\n", stats.Path, stats.FileCount, stats.TotalSize)
}
```

**Test result:** `go run . ~/DEV_Space` → `10809 files, 187808282 bytes` ✅

### Line-by-line notes (v1)

- `DirStats{Path: path}` — constructs struct, unset fields (`FileCount`, `TotalSize`) default to zero values (`0`), not undefined — Go always initializes, unlike Python where an unset attribute wouldn't exist.
- `filepath.Walk(path, func(...) error {...})` — `Walk` takes a **callback** (anonymous function), called once per file/folder found — vs. Python's `os.walk()` returning an iterator to loop over.
- The anonymous callback is a **closure**: it reads/modifies the outer `stats` variable directly, without it being passed in — same concept as Python's `nonlocal`.
- `int64` used explicitly for `TotalSize` (not plain `int`) because plain `int` is platform-dependent width; `int64` guarantees 64 bits for a value that needs to reliably hold large numbers.
- Repeated pattern across the whole file: **do something → get back (result, error) → check error → proceed or bail.** This is the core idiom of the language.

### v2 — concurrent (next step)

Scans each top-level subdirectory concurrently using goroutines + a channel + a WaitGroup, instead of one sequential walk. Not yet run/tested — pending.

```go
// (pending — will paste in once tested)
```

**Concepts to focus on once testing v2:**
- `go func(dir string) {...}(subdir)` — launches goroutine
- `results := make(chan DirStats, len(entries))` — buffered channel
- `wg.Add(1)` / `defer wg.Done()` / `wg.Wait()` — coordination
- `close(results)` + `for stats := range results` — draining a channel

### Stretch goal (optional, time permitting)
Add a `-workers N` flag to cap concurrency via a **worker pool** pattern instead of one goroutine per directory — more production-realistic (avoids hammering disk I/O with unbounded goroutines), and a common Go infra interview/discussion topic.

---

## Open questions / things to revisit
- (add as they come up)

## Session log
- Installed Go (Intel, `x86_64`, `/usr/local`), confirmed clean install.
- Set up `~/DEV_Space/go-learning/filescan`, ran `go mod init filescan`.
- Wrote and successfully ran v1 (sequential scanner).
- Walked v1 line-by-line: package/import, struct, function signature, closures, error pattern.
- Next: build and test v2 (concurrent version).
