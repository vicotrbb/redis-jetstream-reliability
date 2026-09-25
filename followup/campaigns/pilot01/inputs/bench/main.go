// All execution (including smoke tests) belongs in the authorized homelab.
package main

import (
	"bufio"
	"compress/gzip"
	"context"
	"encoding/binary"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/redis/go-redis/v9"
	"golang.org/x/sys/unix"
)

var ctx = context.Background()
var profiles = []string{"redis-memory", "redis-periodic", "redis-always", "nats-memory", "nats-periodic", "nats-always"}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
func mono() int64 {
	var ts unix.Timespec
	must(unix.ClockGettime(unix.CLOCK_MONOTONIC, &ts))
	return ts.Nano()
}
func emit(v any) { b, e := json.Marshal(scope(v)); must(e); fmt.Println(string(b)) }
func writeJSON(path string, v any) {
	b, e := json.MarshalIndent(scope(v), "", "  ")
	must(e)
	must(os.WriteFile(path, append(b, '\n'), 0644))
}
func readFile(path string) string { b, _ := os.ReadFile(path); return string(b) }
func stats(a []float64) map[string]float64 {
	b := append([]float64{}, a...)
	sort.Float64s(b)
	if len(b) == 0 {
		return nil
	}
	sum := 0.0
	for _, v := range b {
		sum += v
	}
	q := func(p float64) float64 { return b[int(math.Ceil(p*float64(len(b))))-1] }
	return map[string]float64{"mean": sum / float64(len(b)), "p50": q(.5), "p95": q(.95), "p99": q(.99), "max": b[len(b)-1]}
}

type Client struct {
	profile, name string
	r             *redis.Client
	n             *nats.Conn
	js            nats.JetStreamContext
	sub           *nats.Subscription
}

func connect(profile, name string) (*Client, error) {
	c := &Client{profile: profile, name: name}
	requestTimeout := 5 * time.Second
	if name == "admin" {
		requestTimeout = 30 * time.Second
	}
	if strings.HasPrefix(profile, "redis-") {
		c.r = redis.NewClient(&redis.Options{Addr: profile + ":6379", PoolSize: 1, MaxRetries: -1, ReadTimeout: requestTimeout, WriteTimeout: requestTimeout, Protocol: 2})
		if e := c.r.Ping(ctx).Err(); e != nil {
			return nil, e
		}
	} else {
		var e error
		c.n, e = nats.Connect("nats://"+profile+":4222", nats.Name(name), nats.NoReconnect(), nats.Timeout(5*time.Second))
		if e != nil {
			return nil, e
		}
		c.js, e = c.n.JetStream(nats.MaxWait(requestTimeout))
		if e != nil {
			return nil, e
		}
	}
	return c, nil
}
func (c *Client) close() {
	if c.r != nil {
		c.r.Close()
	} else {
		c.n.Close()
	}
}
func (c *Client) create(key string, ackWait time.Duration) error {
	if c.r != nil {
		return c.r.XGroupCreateMkStream(ctx, key, "workers", "0").Err()
	}
	storage := nats.FileStorage
	if c.profile == "nats-memory" {
		storage = nats.MemoryStorage
	}
	_, e := c.js.AddStream(&nats.StreamConfig{Name: key, Subjects: []string{key}, Storage: storage, Replicas: 1, Retention: nats.LimitsPolicy, MaxMsgs: -1, MaxBytes: -1, MaxAge: 0})
	if e != nil {
		return e
	}
	_, e = c.js.AddConsumer(key, &nats.ConsumerConfig{Durable: "workers", AckPolicy: nats.AckExplicitPolicy, AckWait: ackWait, MaxAckPending: 32768, MaxWaiting: 512, DeliverPolicy: nats.DeliverAllPolicy, ReplayPolicy: nats.ReplayInstantPolicy})
	return e
}
func (c *Client) remove(key string) {
	must(c.removeE(key))
}
func (c *Client) removeE(key string) error {
	if c.r != nil {
		return c.r.Del(ctx, key).Err()
	} else {
		return c.js.DeleteStream(key)
	}
}
func payload(i int) []byte {
	b := make([]byte, 512)
	for j := range b {
		b[j] = 'x'
	}
	binary.BigEndian.PutUint64(b, uint64(i))
	return b
}
func (c *Client) publish(key string, b []byte) error {
	if c.r != nil {
		return c.r.XAdd(ctx, &redis.XAddArgs{Stream: key, Values: map[string]interface{}{"p": b}}).Err()
	}
	_, e := c.js.Publish(key, b)
	return e
}
func (c *Client) bind(key string) error {
	if c.r != nil {
		return nil
	}
	var e error
	c.sub, e = c.js.PullSubscribe(key, "workers", nats.Bind(key, "workers"))
	return e
}

type Message struct {
	id         int
	redisID    string
	nmsg       *nats.Msg
	received   int64
	requested  int64
	deliveries uint64
}

func (c *Client) receive(key string, wait time.Duration) (*Message, error) {
	requested := mono()
	if c.r != nil {
		v, e := c.r.XReadGroup(ctx, &redis.XReadGroupArgs{Group: "workers", Consumer: c.name, Streams: []string{key, ">"}, Count: 1, Block: wait}).Result()
		if e != nil {
			return nil, e
		}
		ts := mono()
		if len(v) == 0 || len(v[0].Messages) == 0 {
			return nil, redis.Nil
		}
		m := v[0].Messages[0]
		b := []byte(m.Values["p"].(string))
		return &Message{id: int(binary.BigEndian.Uint64(b)), redisID: m.ID, received: ts, requested: requested}, nil
	}
	v, e := c.sub.Fetch(1, nats.MaxWait(wait))
	if e != nil {
		return nil, e
	}
	ts := mono()
	if len(v) != 1 {
		return nil, fmt.Errorf("unexpected fetch length %d", len(v))
	}
	meta, e := v[0].Metadata()
	if e != nil {
		return nil, e
	}
	return &Message{id: int(binary.BigEndian.Uint64(v[0].Data)), nmsg: v[0], received: ts, requested: requested, deliveries: meta.NumDelivered}, nil
}
func (c *Client) ack(key string, m *Message) error {
	if c.r != nil {
		n, e := c.r.XAck(ctx, key, "workers", m.redisID).Result()
		if e == nil && n != 1 {
			return fmt.Errorf("XACK returned %d", n)
		}
		return e
	}
	return m.nmsg.AckSync(nats.AckWait(5 * time.Second))
}
func timeout(e error) bool {
	return errors.Is(e, redis.Nil) || errors.Is(e, nats.ErrTimeout) || errors.Is(e, context.DeadlineExceeded)
}
func (c *Client) inventory(key string) (int64, int64, error) {
	if c.r != nil {
		l, e := c.r.XLen(ctx, key).Result()
		if e != nil {
			return 0, 0, e
		}
		p, e := c.r.XPending(ctx, key, "workers").Result()
		if e != nil {
			return 0, 0, e
		}
		return l, p.Count, nil
	}
	s, e := c.js.StreamInfo(key)
	if e != nil {
		return 0, 0, e
	}
	u, e := c.js.ConsumerInfo(key, "workers")
	if e != nil {
		return 0, 0, e
	}
	return int64(s.State.Msgs), int64(u.NumAckPending), nil
}

type Event struct {
	sent, puback, requested, received, acked int64
	worker                                   int
}

func trial(profile string, consumers, publishers, count int, key, out string) (result map[string]any, runErr error) {
	admin, e := connect(profile, "admin")
	if e != nil {
		return nil, e
	}
	defer admin.close()
	if e = admin.create(key, 30*time.Second); e != nil {
		return nil, fmt.Errorf("setup/create: %w", e)
	}
	defer func() {
		if e := admin.removeE(key); e != nil {
			emit(map[string]any{"kind": "cleanup_error", "key": key, "profile": profile, "error": e.Error(), "primary_error": fmt.Sprint(runErr), "utc_end": time.Now().UTC()})
			if runErr != nil {
				runErr = fmt.Errorf("%w; cleanup also failed: %v", runErr, e)
			} else if result != nil {
				result["cleanup_error"] = e.Error()
			} else {
				runErr = fmt.Errorf("cleanup: %w", e)
			}
		}
	}()
	events := make([]Event, count)
	seen := make([]int32, count)
	pubs := make([]*Client, publishers)
	for j := range pubs {
		pubs[j], e = connect(profile, fmt.Sprintf("pub%d", j))
		if e != nil {
			return nil, e
		}
		defer pubs[j].close()
	}
	cs := make([]*Client, consumers)
	for j := range cs {
		cs[j], e = connect(profile, fmt.Sprintf("worker%d", j))
		if e != nil {
			return nil, e
		}
		defer cs[j].close()
		if e = cs[j].bind(key); e != nil {
			return nil, e
		}
	}
	before := readFile("/sys/fs/cgroup/cpu.stat")
	start := mono()
	var idx int64
	idx = -1
	var wg sync.WaitGroup
	errs := make(chan error, publishers+consumers)
	for _, p := range pubs {
		wg.Add(1)
		go func(p *Client) {
			defer wg.Done()
			for {
				i := int(atomic.AddInt64(&idx, 1))
				if i >= count {
					return
				}
				b := payload(i)
				events[i].sent = mono()
				if e := p.publish(key, b); e != nil {
					errs <- fmt.Errorf("publish: %w", e)
					return
				}
				events[i].puback = mono()
			}
		}(p)
	}
	wg.Wait()
	pubEnd := mono()
	select {
	case e := <-errs:
		return nil, e
	default:
	}
	var completed int64
	var duplicates int64
	drainStart := mono()
	deadline := drainStart + int64(120*time.Second)
	for j, c := range cs {
		wg.Add(1)
		go func(j int, c *Client) {
			defer wg.Done()
			for atomic.LoadInt64(&completed) < int64(count) {
				if mono() > deadline {
					errs <- errors.New("drain deadline")
					return
				}
				m, e := c.receive(key, 100*time.Millisecond)
				if timeout(e) {
					continue
				}
				if e != nil {
					errs <- fmt.Errorf("receive: %w", e)
					return
				}
				if m.id < 0 || m.id >= count {
					errs <- errors.New("invalid application ID")
					return
				}
				fresh := atomic.CompareAndSwapInt32(&seen[m.id], 0, 1)
				if !fresh {
					atomic.AddInt64(&duplicates, 1)
				}
				if e = c.ack(key, m); e != nil {
					errs <- fmt.Errorf("ack: %w", e)
					return
				}
				if fresh {
					events[m.id].received = m.received
					events[m.id].requested = m.requested
					events[m.id].acked = mono()
					events[m.id].worker = j
					atomic.AddInt64(&completed, 1)
				}
			}
		}(j, c)
	}
	wg.Wait()
	select {
	case e := <-errs:
		return nil, e
	default:
	}
	lastAck := drainStart
	pl, dl, al, ql := make([]float64, count), make([]float64, count), make([]float64, count), make([]float64, count)
	cl := make([]float64, count)
	workers := make([]int, consumers)
	for i, v := range events {
		if seen[i] != 1 || v.acked == 0 || v.puback == 0 {
			return nil, fmt.Errorf("incomplete ID %d", i)
		}
		if v.acked > lastAck {
			lastAck = v.acked
		}
		pl[i] = float64(v.puback-v.sent) / 1e6
		dl[i] = float64(v.received-drainStart) / 1e6
		al[i] = float64(v.acked-v.received) / 1e6
		ql[i] = float64(v.received-v.sent) / 1e6
		cl[i] = float64(v.acked-v.requested) / 1e6
		workers[v.worker]++
	}
	stored, pending, e := admin.inventory(key)
	if e != nil {
		return nil, e
	}
	if stored != int64(count) || pending != 0 || duplicates != 0 {
		return nil, fmt.Errorf("integrity failed: stored=%d pending=%d duplicates=%d", stored, pending, duplicates)
	}
	if out != "" {
		f, e := os.Create(filepath.Join(out, key+".csv.gz"))
		if e != nil {
			return nil, e
		}
		gz := gzip.NewWriter(f)
		cw := csv.NewWriter(gz)
		must(cw.Write([]string{"id", "publish_start_ns", "publish_ack_ns", "request_start_ns", "delivery_ns", "consumer_ack_ns", "worker"}))
		for i, v := range events {
			must(cw.Write([]string{strconv.Itoa(i), strconv.FormatInt(v.sent, 10), strconv.FormatInt(v.puback, 10), strconv.FormatInt(v.requested, 10), strconv.FormatInt(v.received, 10), strconv.FormatInt(v.acked, 10), strconv.Itoa(v.worker)}))
		}
		cw.Flush()
		must(cw.Error())
		must(gz.Close())
		must(f.Close())
	}
	return map[string]any{"kind": "trial", "key": key, "profile": profile, "consumers": consumers, "publishers": publishers, "n": count, "payload_bytes": 512, "publish_start_ns": start, "publish_end_ns": pubEnd, "drain_start_ns": drainStart, "drain_end_ns": lastAck, "publish_mps": float64(count) * 1e9 / float64(pubEnd-start), "drain_mps": float64(count) * 1e9 / float64(lastAck-drainStart), "publish_ms": stats(pl), "drain_delivery_ms": stats(dl), "ack_ms": stats(al), "cycle_ms": stats(cl), "publish_to_delivery_ms": stats(ql), "worker_counts": workers, "stored": stored, "pending": pending, "duplicates": duplicates, "driver_cpu_before": before, "driver_cpu_after": readFile("/sys/fs/cgroup/cpu.stat")}, nil
}

func campaign(mode, out string) {
	must(os.MkdirAll(out, 0755))
	blocks, n := 10, 16384
	cs := []int{1, 2, 4, 8, 16}
	pubs := 16
	if mode == "pilot" {
		blocks = 1
		n = 512
		cs = []int{1, 16}
	}
	if mode == "serial" {
		n = 1024
		cs = []int{1}
		pubs = 1
	}
	done := map[string]bool{}
	attempts := map[string]int{}
	previous, _ := os.ReadFile(filepath.Join(out, "summary.jsonl"))
	for _, line := range strings.Split(string(previous), "\n") {
		if line == "" {
			continue
		}
		var row map[string]any
		must(json.Unmarshal([]byte(line), &row))
		base, _ := row["base_key"].(string)
		if base == "" {
			base, _ = row["key"].(string)
		}
		attempts[base]++
		if row["kind"] == "trial" {
			done[base] = true
		}
	}
	f, e := os.OpenFile(filepath.Join(out, "summary.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	must(e)
	defer f.Close()
	enc := newScopedEncoder(f)
	rng := rand.New(rand.NewSource(20260923))
	serial := 0
	runtimeFile := "runtime.json"
	if len(previous) > 0 {
		runtimeFile = "runtime-resume-" + time.Now().UTC().Format("20060102T150405") + ".json"
	}
	writeJSON(filepath.Join(out, runtimeFile), map[string]any{"utc_start": time.Now().UTC(), "go": runtime.Version(), "gomaxprocs": runtime.GOMAXPROCS(0), "cpuinfo": readFile("/proc/cpuinfo"), "kernel": readFile("/proc/version"), "mode": mode, "seed": 20260923})
	for block := 0; block < blocks; block++ {
		type Cell struct {
			p string
			c int
		}
		cells := []Cell{}
		for _, p := range profiles {
			for _, c := range cs {
				cells = append(cells, Cell{p, c})
			}
		}
		rng.Shuffle(len(cells), func(i, j int) { cells[i], cells[j] = cells[j], cells[i] })
		for _, cell := range cells {
			serial++
			base := fmt.Sprintf("T%s%03d", mode, serial)
			if done[base] {
				continue
			}
			key := base
			if attempts[base] > 0 {
				key = base + "r" + strconv.Itoa(attempts[base]+1)
			}
			_, e := trial(cell.p, cell.c, pubs, 256, key+"warm", "")
			if e != nil {
				v := map[string]any{"kind": "error", "block": block, "key": key, "base_key": base, "consumers": cell.c, "order": serial, "profile": cell.p, "stage": "warmup", "error": e.Error(), "utc_end": time.Now().UTC()}
				must(enc.Encode(v))
				emit(v)
				panic(e)
			}
			v, e := trial(cell.p, cell.c, pubs, n, key, out)
			if e != nil {
				v = map[string]any{"kind": "error", "block": block, "key": key, "base_key": base, "consumers": cell.c, "order": serial, "profile": cell.p, "error": e.Error(), "utc_end": time.Now().UTC()}
				must(enc.Encode(v))
				emit(v)
				panic(e)
			}
			v["block"] = block
			v["base_key"] = base
			v["attempt"] = attempts[base] + 1
			v["harness_revision"] = "admin-v3"
			v["order"] = serial
			v["utc_end"] = time.Now().UTC()
			must(enc.Encode(v))
			must(f.Sync())
			emit(v)
		}
	}
}

func victim(profile, key string) {
	c, e := connect(profile, "victim")
	must(e)
	defer c.close()
	must(c.bind(key))
	m, e := c.receive(key, 5*time.Second)
	must(e)
	emit(map[string]any{"received_ns": m.received, "id": m.id, "redis_id": m.redisID})
	time.Sleep(time.Hour)
}
func recoverOne(profile string, delta time.Duration, age float64, poll time.Duration, seed int64, key string, noReclaim bool) map[string]any {
	admin, e := connect(profile, "admin")
	must(e)
	defer admin.close()
	must(admin.create(key, delta))
	defer func() {
		if err := admin.removeE(key); err != nil {
			emit(map[string]any{"kind": "cleanup_error", "key": key, "profile": profile, "error": err.Error()})
		}
	}()
	must(admin.publish(key, payload(0)))
	survivor, e := connect(profile, "survivor")
	must(e)
	defer survivor.close()
	must(survivor.bind(key))
	cmd := exec.Command(os.Args[0], "victim", profile, key)
	stdout, e := cmd.StdoutPipe()
	must(e)
	cmd.Stderr = os.Stderr
	must(cmd.Start())
	scanner := bufio.NewScanner(stdout)
	if !scanner.Scan() {
		panic("victim delivered no receipt")
	}
	var receipt struct {
		Received int64 `json:"received_ns"`
		ID       int   `json:"id"`
	}
	must(json.Unmarshal(scanner.Bytes(), &receipt))
	result := make(chan recoveryResult, 1)
	finish := func(m *Message, err error, attempts int) {
		result <- recoveryResult{m: m, e: err, attempts: attempts, loopEndNS: mono()}
	}
	stop := make(chan struct{})
	rng := rand.New(rand.NewSource(seed))
	phase := time.Duration(0)
	if poll > 0 {
		phase = time.Duration(rng.Int63n(int64(poll)))
	}
	go func() {
		attempts := 0
		time.Sleep(phase)
		for {
			select {
			case <-stop:
				finish(nil, errors.New("censored"), attempts)
				return
			default:
			}
			attempts++
			if survivor.r != nil && !noReclaim {
				msgs, _, e := survivor.r.XAutoClaim(ctx, &redis.XAutoClaimArgs{Stream: key, Group: "workers", Consumer: "survivor", MinIdle: delta, Start: "0-0", Count: 1}).Result()
				ts := mono()
				if e != nil {
					finish(nil, e, attempts)
					return
				}
				if len(msgs) > 0 {
					m := msgs[0]
					finish(&Message{id: int(binary.BigEndian.Uint64([]byte(m.Values["p"].(string)))), redisID: m.ID, received: ts}, nil, attempts)
					return
				}
				time.Sleep(poll)
			} else {
				m, e := survivor.receive(key, 100*time.Millisecond)
				if timeout(e) {
					continue
				}
				finish(m, e, attempts)
				return
			}
		}
	}()
	remaining := receipt.Received + int64(float64(delta)*age) - mono()
	if remaining > 0 {
		time.Sleep(time.Duration(remaining))
	}
	killStart := mono()
	must(cmd.Process.Kill())
	exitErr := cmd.Wait()
	killEnd := mono()
	limit := 5*delta + 2*time.Second
	if noReclaim {
		limit = 2 * delta
	}
	observation := observeRecovery(result, stop, limit)
	rr, censor := observation.result, observation.censored
	v := map[string]any{"kind": "recovery", "key": key, "profile": profile, "delta_ms": float64(delta) / 1e6, "age_fraction": age, "poll_ms": float64(poll) / 1e6, "phase_ms": float64(phase) / 1e6, "delivery_ns": receipt.Received, "kill_start_ns": killStart, "kill_end_ns": killEnd, "kill_exit": fmt.Sprint(exitErr), "censored": censor, "no_reclaim": noReclaim, "attempts": rr.attempts, "censor_window_ms": float64(limit) / 1e6}
	observation.record(v)
	if !censor {
		must(rr.e)
		if rr.m.id != 0 {
			panic("wrong recovered ID")
		}
		if rr.m.received < killStart {
			panic("message recovered before kill")
		}
		must(survivor.ack(key, rr.m))
		v["redelivery_ns"] = rr.m.received
		v["delivery_to_redelivery_ms"] = float64(rr.m.received-receipt.Received) / 1e6
		v["failure_to_redelivery_ms"] = float64(rr.m.received-killStart) / 1e6
		v["nats_deliveries"] = rr.m.deliveries
		if survivor.n != nil && rr.m.deliveries != 2 {
			panic("not one redelivery")
		}
	}
	v["reconciliation_start_ns"] = mono()
	stored, pending, e := admin.inventory(key)
	v["reconciliation_end_ns"] = mono()
	must(e)
	v["stored"] = stored
	v["pending"] = pending
	if stored != 1 || (!censor && pending != 0) || (censor && pending != 1) {
		panic("recovery inventory mismatch")
	}
	return v
}
func recovery(out string) {
	must(os.MkdirAll(out, 0755))
	f, e := os.Create(filepath.Join(out, "summary.jsonl"))
	must(e)
	defer f.Close()
	enc := newScopedEncoder(f)
	type Cell struct {
		p       string
		d, poll time.Duration
		age     float64
		rep     int
		control bool
	}
	cells := []Cell{}
	for rep := 0; rep < 10; rep++ {
		for _, d := range []time.Duration{250 * time.Millisecond, time.Second} {
			for _, age := range []float64{.1, .75} {
				for _, p := range []string{"redis-periodic", "nats-periodic"} {
					polls := []time.Duration{0}
					if p == "redis-periodic" {
						polls = []time.Duration{10 * time.Millisecond, 100 * time.Millisecond}
					}
					for _, poll := range polls {
						cells = append(cells, Cell{p, d, poll, age, rep, false})
					}
				}
			}
		}
	}
	for rep := 0; rep < 5; rep++ {
		for _, d := range []time.Duration{250 * time.Millisecond, time.Second} {
			cells = append(cells, Cell{"redis-periodic", d, 0, .1, rep, true})
		}
	}
	rng := rand.New(rand.NewSource(20260923))
	rng.Shuffle(len(cells), func(i, j int) { cells[i], cells[j] = cells[j], cells[i] })
	for i, c := range cells {
		v := recoverOne(c.p, c.d, c.age, c.poll, int64(i+20260923), fmt.Sprintf("R%03d", i), c.control)
		v["rep"] = c.rep
		must(enc.Encode(v))
		must(f.Sync())
		emit(v)
	}
}

func main() {
	must(loadIdentity())
	if len(os.Args) < 2 {
		panic("mode required")
	}
	if os.Args[1] != "victim" {
		if len(os.Args) != 3 {
			panic("mode and fresh output directory required")
		}
		must(freshSeries(os.Args[2]))
	}
	switch os.Args[1] {
	case "victim":
		victim(os.Args[2], os.Args[3])
	case "pilot", "main", "serial":
		campaign(os.Args[1], os.Args[2])
	case "recovery":
		recovery(os.Args[2])
	case "durability":
		durability(os.Args[2])
	case "validation":
		validation(os.Args[2])
	default:
		panic("unknown mode")
	}
}
