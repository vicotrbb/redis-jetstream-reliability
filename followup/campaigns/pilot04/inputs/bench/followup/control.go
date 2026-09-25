// The control server runs only inside an isolated homelab benchmark pod.
package main

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/unix"
)

func mono() int64 {
	var t unix.Timespec
	if e := unix.ClockGettime(unix.CLOCK_MONOTONIC, &t); e != nil {
		panic(e)
	}
	return t.Nano()
}
func contents(p string) string {
	b, e := os.ReadFile(p)
	if e != nil {
		return "ERROR: " + e.Error()
	}
	return string(b)
}
func cpu() map[string]int64 {
	v := map[string]int64{}
	for _, s := range strings.Split(contents("/sys/fs/cgroup/cpu.stat"), "\n") {
		var k string
		var n int64
		if _, e := fmt.Sscan(s, &k, &n); e == nil {
			v[k] = n
		}
	}
	return v
}
func sample() map[string]any {
	return map[string]any{"start_ns": mono(), "wall_ns": time.Now().UnixNano(), "cpu": cpu(), "memory_current": contents("/sys/fs/cgroup/memory.current"), "memory_events": contents("/sys/fs/cgroup/memory.events"), "io_stat": contents("/sys/fs/cgroup/io.stat"), "cpu_pressure": contents("/sys/fs/cgroup/cpu.pressure"), "io_pressure": contents("/sys/fs/cgroup/io.pressure"), "host_cpu_stat": contents("/proc/stat"), "host_loadavg": contents("/proc/loadavg"), "end_ns": mono()}
}
func flags(p string, disable bool) (uint32, error) {
	f, e := os.Open(p)
	if e != nil {
		return 0, e
	}
	defer f.Close()
	var v uint32
	_, _, errno := syscall.Syscall(syscall.SYS_IOCTL, f.Fd(), 0x80086601, uintptr(unsafe.Pointer(&v)))
	if errno != 0 {
		return v, errno
	}
	if disable {
		v &^= 0x4 // Btrfs forbids simultaneous COMPRESS and NOCOMPRESS.
		v |= 0x400
		_, _, errno = syscall.Syscall(syscall.SYS_IOCTL, f.Fd(), 0x40086602, uintptr(unsafe.Pointer(&v)))
		if errno != 0 {
			return v, errno
		}
		_, _, errno = syscall.Syscall(syscall.SYS_IOCTL, f.Fd(), 0x80086601, uintptr(unsafe.Pointer(&v)))
		if errno != 0 {
			return v, errno
		}
		if v&0x400 == 0 {
			return v, fmt.Errorf("no-compression flag not applied")
		}
	}
	return v, nil
}

type control struct {
	mu      sync.Mutex
	engine  string
	command *exec.Cmd
	done    chan error
	log     *os.File
	dir     string
	config  string
	start   map[string]any
}

func (c *control) startTrial(t Trial) (map[string]any, error) {
	if c.command != nil {
		return nil, fmt.Errorf("a broker is already active")
	}
	if !regexp.MustCompile(`^[A-Za-z0-9_]{1,80}$`).MatchString(t.ID) {
		return nil, fmt.Errorf("invalid trial ID")
	}
	if t.Engine != c.engine {
		return nil, fmt.Errorf("engine mismatch")
	}
	port := "6379"
	if c.engine == "nats" {
		port = "4222"
	}
	if connection, err := net.DialTimeout("tcp", "127.0.0.1:"+port, 100*time.Millisecond); err == nil {
		connection.Close()
		return nil, fmt.Errorf("broker port was already listening before reset")
	}
	c.dir = filepath.Join("/data", t.ID)
	if e := os.Mkdir(c.dir, 0755); e != nil {
		return nil, e
	}
	f, e := flags(c.dir, t.Compression == "off")
	if e != nil {
		return nil, e
	}
	data := filepath.Join(c.dir, "store")
	if e = os.Mkdir(data, 0755); e != nil {
		return nil, e
	}
	if t.Engine == "redis" {
		c.config = fmt.Sprintf("bind 0.0.0.0\nprotected-mode no\nport 6379\nsave \"\"\ndir %s\nmaxmemory 2gb\nmaxmemory-policy noeviction\nauto-aof-rewrite-percentage 0\nno-appendfsync-on-rewrite no\n", data)
		if t.Profile == "memory" {
			c.config += "appendonly no\n"
		} else {
			mode := "everysec"
			if t.Profile == "always" {
				mode = "always"
			}
			c.config += "appendonly yes\nappendfsync " + mode + "\n"
		}
	} else {
		interval := "1s"
		if t.Profile == "always" {
			interval = "always"
		}
		c.config = fmt.Sprintf("port: 4222\nhttp_port: 8222\njetstream {\nstore_dir: %s\nmax_memory_store: 2GB\nmax_file_store: 2GB\nsync_interval: %s\n}\n", data, interval)
	}
	path := filepath.Join(c.dir, "server.conf")
	if e = os.WriteFile(path, []byte(c.config), 0644); e != nil {
		return nil, e
	}
	name, args := "redis-server", []string{path}
	if c.engine == "nats" {
		name = "nats-server"
		args = []string{"-c", path}
		port = "4222"
	}
	if t.Trace {
		args = append([]string{"-ff", "-ttt", "-T", "-yy", "-e", "trace=fsync,fdatasync", "-o", filepath.Join(c.dir, "sync.trace"), name}, args...)
		args = append([]string{"--library-path", "/tools/lib", "/tools/strace"}, args...)
		name = "/lib/ld-musl-x86_64.so.1"
	}
	c.log, e = os.OpenFile(filepath.Join(c.dir, "server.log"), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if e != nil {
		return nil, e
	}
	c.command = exec.Command(name, args...)
	c.command.Stdout = c.log
	c.command.Stderr = c.log
	c.command.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	start := mono()
	if e = c.command.Start(); e != nil {
		c.command = nil
		c.log.Close()
		return nil, e
	}
	c.done = make(chan error, 1)
	cmd := c.command
	go func() { c.done <- cmd.Wait() }()
	c.start = map[string]any{"start_ns": start, "command": append([]string{name}, args...), "pid": cmd.Process.Pid, "configuration": c.config, "directory_flags": f, "mountinfo": contents("/proc/self/mountinfo")}
	for deadline := time.Now().Add(30 * time.Second); time.Now().Before(deadline); {
		connection, err := net.DialTimeout("tcp", "127.0.0.1:"+port, 100*time.Millisecond)
		if err == nil {
			connection.Close()
			c.start["ready_ns"] = mono()
			return c.start, nil
		}
		time.Sleep(25 * time.Millisecond)
	}
	return c.start, fmt.Errorf("broker not ready within 30 seconds: %s", contents(filepath.Join(c.dir, "server.log")))
}
func (c *control) stopTrial() map[string]any {
	r := map[string]any{"stop_start_ns": mono(), "final_sample": sample()}
	group := 0
	if c.command != nil {
		group = c.command.Process.Pid
		_ = syscall.Kill(-c.command.Process.Pid, syscall.SIGTERM)
		select {
		case e := <-c.done:
			r["exit"] = fmt.Sprint(e)
		case <-time.After(10 * time.Second):
			r["forced_kill"] = true
			_ = syscall.Kill(-c.command.Process.Pid, syscall.SIGKILL)
			r["exit"] = fmt.Sprint(<-c.done)
		}
		c.log.Close()
		c.command = nil
	}
	groupGone := group == 0
	for deadline := time.Now().Add(3 * time.Second); group != 0 && time.Now().Before(deadline); {
		var status syscall.WaitStatus
		_, _ = syscall.Wait4(-group, &status, syscall.WNOHANG, nil)
		if syscall.Kill(-group, 0) == syscall.ESRCH {
			groupGone = true
			break
		}
		_ = syscall.Kill(-group, syscall.SIGKILL)
		time.Sleep(10 * time.Millisecond)
	}
	port := "6379"
	if c.engine == "nats" {
		port = "4222"
	}
	connection, portError := net.DialTimeout("tcp", "127.0.0.1:"+port, 100*time.Millisecond)
	portClosed := portError != nil
	if connection != nil {
		connection.Close()
	}
	r["process_group_gone"] = groupGone
	r["broker_port_closed"] = portClosed
	if !groupGone || !portClosed {
		r["cleanup_error"] = "broker termination not verified; store retained"
		return r
	}
	r["stop_end_ns"] = mono()
	files := map[string][]byte{}
	inventory := []map[string]any{}
	if c.dir != "" {
		_ = filepath.Walk(c.dir, func(p string, info os.FileInfo, e error) error {
			if e != nil {
				return e
			}
			relative, _ := filepath.Rel(c.dir, p)
			f, fe := flags(p, false)
			inventory = append(inventory, map[string]any{"path": relative, "bytes": info.Size(), "mode": info.Mode().String(), "flags": f, "flags_error": fmt.Sprint(fe)})
			if !info.IsDir() && (strings.HasPrefix(info.Name(), "sync.trace") || info.Name() == "server.log" || info.Name() == "server.conf") {
				b, err := os.ReadFile(p)
				if err == nil {
					var buf bytes.Buffer
					g := gzip.NewWriter(&buf)
					g.Write(b)
					g.Close()
					files[relative+".gz"] = buf.Bytes()
				}
			}
			return nil
		})
		r["files_gzip"] = files
		r["storage_inventory"] = inventory
		r["cleanup_start_ns"] = mono()
		r["cleanup_error"] = fmt.Sprint(os.RemoveAll(c.dir))
		r["cleanup_end_ns"] = mono()
		c.dir = ""
	}
	return r
}
func runControl(engine string) {
	c := &control{engine: engine}
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		c.mu.Lock()
		defer c.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		var v any
		var e error
		switch r.URL.Path {
		case "/health":
			v = map[string]any{"engine": engine, "active": c.command != nil}
		case "/stats":
			v = sample()
		case "/start":
			var t Trial
			e = json.NewDecoder(http.MaxBytesReader(w, r.Body, 65536)).Decode(&t)
			if e == nil {
				v, e = c.startTrial(t)
			}
		case "/stop":
			v = c.stopTrial()
		default:
			e = fmt.Errorf("unknown endpoint")
		}
		if e != nil {
			w.WriteHeader(500)
			v = map[string]any{"error": e.Error(), "detail": v}
		}
		json.NewEncoder(w).Encode(v)
	})
	if e := http.ListenAndServe(":8088", nil); e != nil {
		panic(e)
	}
}
