package main

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

type Trial struct {
	ID          string  `json:"id"`
	Campaign    string  `json:"campaign"`
	Block       int     `json:"block"`
	Kind        string  `json:"kind"`
	Engine      string  `json:"engine"`
	Version     string  `json:"version"`
	Profile     string  `json:"profile"`
	Host        string  `json:"host"`
	Publishers  int     `json:"publishers"`
	Consumers   int     `json:"consumers"`
	CPUs        int     `json:"cpus"`
	Seconds     float64 `json:"seconds"`
	Count       int     `json:"count"`
	Payload     string  `json:"payload"`
	Compression string  `json:"compression"`
	Trace       bool    `json:"trace"`
	Recovery    string  `json:"recovery"`
	DeltaMS     int     `json:"delta_ms"`
	Age         float64 `json:"age"`
	Kill        bool    `json:"kill"`
	Seed        int64   `json:"seed"`
	Pilot       bool    `json:"pilot"`
}
type Event struct {
	ID        int64
	Start     int64
	End       int64
	Received  int64
	Worker    int
	Confirmed bool
	Error     string
}

var templates [][]byte

func preparePayload(kind string) {
	templates = make([][]byte, 4096)
	rng := rand.New(rand.NewSource(24092026))
	for i := range templates {
		b := make([]byte, 512)
		for j := 8; j < len(b); j++ {
			if kind == "random" {
				b[j] = byte(rng.Intn(256))
			} else {
				b[j] = 'x'
			}
		}
		templates[i] = b
	}
}
func payload(id int64) []byte {
	b := make([]byte, 512)
	copy(b, templates[id%int64(len(templates))])
	binary.BigEndian.PutUint64(b, uint64(id))
	return b
}
func quantiles(values []float64) map[string]float64 {
	if len(values) == 0 {
		return nil
	}
	v := append([]float64{}, values...)
	sort.Float64s(v)
	sum := 0.
	for _, x := range v {
		sum += x
	}
	return map[string]float64{"mean": sum / float64(len(v)), "p50": v[int(math.Ceil(.5*float64(len(v))))-1], "p99": v[int(math.Ceil(.99*float64(len(v))))-1], "max": v[len(v)-1]}
}
func saveJSON(path string, v any) error {
	b, e := json.MarshalIndent(v, "", "  ")
	if e != nil {
		return e
	}
	f, e := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if e != nil {
		return e
	}
	defer f.Close()
	if _, e = f.Write(append(b, '\n')); e != nil {
		return e
	}
	return f.Sync()
}
func request(t Trial, endpoint string, input any) (map[string]any, error) {
	var body io.Reader
	if input != nil {
		b, e := json.Marshal(input)
		if e != nil {
			return nil, e
		}
		body = bytes.NewReader(b)
	}
	c := http.Client{Timeout: 60 * time.Second}
	r, e := c.Post("http://"+t.Host+":8088/"+endpoint, "application/json", body)
	if e != nil {
		return nil, e
	}
	defer r.Body.Close()
	var v map[string]any
	decoder := json.NewDecoder(r.Body)
	decoder.UseNumber()
	e = decoder.Decode(&v)
	if e != nil {
		return nil, e
	}
	if r.StatusCode != 200 {
		return v, fmt.Errorf("control %s: %v", endpoint, v)
	}
	return v, nil
}
func phaseStart(t Trial, r map[string]any, label string) error {
	b, e := request(t, "stats", nil)
	if e != nil {
		return e
	}
	r[label+"_broker_before"] = b
	r[label+"_driver_before"] = sample()
	return nil
}
func phaseEnd(t Trial, r map[string]any, label string) error {
	r[label+"_driver_after"] = sample()
	b, e := request(t, "stats", nil)
	r[label+"_broker_after"] = b
	return e
}
func persistEvents(path string, events [][]Event) (map[string]any, error) {
	f, e := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if e != nil {
		return nil, e
	}
	g := gzip.NewWriter(f)
	w := csv.NewWriter(g)
	w.Write([]string{"id", "start_ns", "end_ns", "received_ns", "worker", "confirmed", "error"})
	count := 0
	for _, group := range events {
		for _, v := range group {
			w.Write([]string{strconv.FormatInt(v.ID, 10), strconv.FormatInt(v.Start, 10), strconv.FormatInt(v.End, 10), strconv.FormatInt(v.Received, 10), strconv.Itoa(v.Worker), strconv.FormatBool(v.Confirmed), v.Error})
			count++
		}
	}
	w.Flush()
	if e = w.Error(); e != nil {
		return nil, e
	}
	if e = g.Close(); e != nil {
		return nil, e
	}
	if e = f.Sync(); e != nil {
		return nil, e
	}
	if e = f.Close(); e != nil {
		return nil, e
	}
	b, e := os.ReadFile(path)
	if e != nil {
		return nil, e
	}
	h := sha256.Sum256(b)
	return map[string]any{"path": filepath.Base(path), "sha256": hex.EncodeToString(h[:]), "records": count}, nil
}
func warmup(t Trial, admin *client) error {
	key := "W" + t.ID
	if e := admin.create(key, 30*time.Second); e != nil {
		return e
	}
	consumer, e := connect(t, "warmup")
	if e != nil {
		return e
	}
	defer consumer.close()
	if e = consumer.bind(key); e != nil {
		return e
	}
	for i := int64(0); i < 256; i++ {
		if e = admin.publish(key, payload(i)); e != nil {
			return e
		}
		m, err := consumer.receive(key, time.Second)
		if err != nil {
			return err
		}
		if e = consumer.ack(key, m); e != nil {
			return e
		}
	}
	if e = admin.remove(key); e != nil {
		return e
	}
	time.Sleep(time.Second)
	return nil
}
func publication(t Trial, admin *client, out string, r map[string]any) error {
	clients := make([]*client, t.Publishers)
	for i := range clients {
		c, e := connect(t, fmt.Sprintf("pub%d", i))
		if e != nil {
			return e
		}
		defer c.close()
		clients[i] = c
	}
	events := make([][]Event, len(clients))
	var seq atomic.Int64
	var stopped atomic.Bool
	var wg sync.WaitGroup
	problems := make(chan error, len(clients))
	if e := phaseStart(t, r, "publication"); e != nil {
		return e
	}
	start := mono()
	deadline := start + int64(t.Seconds*1e9)
	r["start_ns"] = start
	r["admission_deadline_ns"] = deadline
	for worker, c := range clients {
		wg.Add(1)
		go func(worker int, c *client) {
			defer wg.Done()
			defer func() {
				if p := recover(); p != nil {
					stopped.Store(true)
					problems <- fmt.Errorf("publisher panic: %v", p)
				}
			}()
			for mono() < deadline && !stopped.Load() {
				id := seq.Add(1) - 1
				b := payload(id)
				v := Event{ID: id, Start: mono(), Worker: worker}
				events[worker] = append(events[worker], v)
				slot := len(events[worker]) - 1
				e := c.publish(t.ID, b)
				events[worker][slot].End = mono()
				if e != nil {
					events[worker][slot].Error = e.Error()
					stopped.Store(true)
					problems <- e
					return
				}
				events[worker][slot].Confirmed = true
			}
		}(worker, c)
	}
	wg.Wait()
	r["joined_ns"] = mono()
	phaseErr := phaseEnd(t, r, "publication")
	close(problems)
	var primary error
	for e := range problems {
		if primary == nil {
			primary = e
		}
	}
	if primary == nil {
		primary = phaseErr
	}
	trace, e := persistEvents(filepath.Join(out, "events.csv.gz"), events)
	r["trace"] = trace
	if e != nil {
		return e
	}
	last := start
	confirmed := int64(0)
	lat := []float64{}
	for _, group := range events {
		for _, v := range group {
			if v.Confirmed {
				confirmed++
				if v.End > last {
					last = v.End
				}
				lat = append(lat, float64(v.End-v.Start)/1e6)
			}
		}
	}
	r["attempted"] = seq.Load()
	r["confirmed"] = confirmed
	r["unknown"] = seq.Load() - confirmed
	r["end_ns"] = last
	r["latency_ms"] = quantiles(lat)
	if confirmed > 0 {
		r["throughput_mps"] = float64(confirmed) * 1e9 / float64(last-start)
	}
	if primary != nil {
		r["confirmed_prefix_throughput_mps"] = r["throughput_mps"]
		delete(r, "throughput_mps")
		return primary
	}
	r["stage"] = "readback"
	verification, e := admin.readback(t.ID, confirmed, payload)
	r["payload_verification"] = verification
	return e
}
func drain(t Trial, admin *client, out string, r map[string]any) error {
	pubs := make([]*client, 16)
	for i := range pubs {
		c, e := connect(t, fmt.Sprintf("preload%d", i))
		if e != nil {
			return e
		}
		defer c.close()
		pubs[i] = c
	}
	var next atomic.Int64
	var stopped atomic.Bool
	var wg sync.WaitGroup
	problems := make(chan error, 32)
	preload := make([][]Event, len(pubs))
	if e := phaseStart(t, r, "preload"); e != nil {
		return e
	}
	r["preload_start_ns"] = mono()
	for worker, c := range pubs {
		wg.Add(1)
		go func(worker int, c *client) {
			defer wg.Done()
			defer func() {
				if p := recover(); p != nil {
					stopped.Store(true)
					problems <- fmt.Errorf("preload worker panic: %v", p)
				}
			}()
			for !stopped.Load() {
				id := next.Add(1) - 1
				if id >= int64(t.Count) {
					return
				}
				b := payload(id)
				preload[worker] = append(preload[worker], Event{ID: id, Start: mono(), Worker: worker})
				slot := len(preload[worker]) - 1
				e := c.publish(t.ID, b)
				preload[worker][slot].End = mono()
				preload[worker][slot].Confirmed = e == nil
				if e != nil {
					preload[worker][slot].Error = e.Error()
					stopped.Store(true)
					problems <- e
					return
				}
			}
		}(worker, c)
	}
	wg.Wait()
	r["preload_end_ns"] = mono()
	phaseErr := phaseEnd(t, r, "preload")
	saved, e := persistEvents(filepath.Join(out, "preload.csv.gz"), preload)
	r["preload_trace"] = saved
	if e != nil {
		return e
	}
	if len(problems) > 0 {
		return <-problems
	}
	if phaseErr != nil {
		return phaseErr
	}
	consumers := make([]*client, t.Consumers)
	for i := range consumers {
		c, e := connect(t, fmt.Sprintf("worker%d", i))
		if e != nil {
			return e
		}
		defer c.close()
		if e = c.bind(t.ID); e != nil {
			return e
		}
		consumers[i] = c
	}
	events := make([][]Event, t.Consumers)
	var tickets atomic.Int64
	if e := phaseStart(t, r, "drain"); e != nil {
		return e
	}
	r["start_ns"] = mono()
	for worker, c := range consumers {
		wg.Add(1)
		go func(worker int, c *client) {
			defer wg.Done()
			defer func() {
				if p := recover(); p != nil {
					stopped.Store(true)
					problems <- fmt.Errorf("consumer panic: %v", p)
				}
			}()
			for !stopped.Load() {
				ticket := tickets.Add(1) - 1
				if ticket >= int64(t.Count) {
					return
				}
				events[worker] = append(events[worker], Event{ID: -1, Start: mono(), Worker: worker})
				slot := len(events[worker]) - 1
				m, e := c.receive(t.ID, 5*time.Second)
				if e == nil {
					events[worker][slot].ID = m.id
					events[worker][slot].Start = m.requested
					events[worker][slot].Received = m.received
					e = c.ack(t.ID, m)
				}
				events[worker][slot].End = mono()
				events[worker][slot].Confirmed = e == nil
				if e != nil {
					events[worker][slot].Error = e.Error()
					stopped.Store(true)
					problems <- e
					return
				}
			}
		}(worker, c)
	}
	wg.Wait()
	r["joined_ns"] = mono()
	phaseErr = phaseEnd(t, r, "drain")
	trace, e := persistEvents(filepath.Join(out, "events.csv.gz"), events)
	r["trace"] = trace
	if e != nil {
		return e
	}
	if len(problems) > 0 {
		return <-problems
	}
	if phaseErr != nil {
		return phaseErr
	}
	start := number(r["start_ns"])
	last := start
	seen := make([]bool, t.Count)
	lat := []float64{}
	for _, group := range events {
		for _, v := range group {
			if v.ID < 0 || v.ID >= int64(t.Count) || seen[v.ID] || !v.Confirmed {
				return fmt.Errorf("drain identity/confirmation mismatch")
			}
			seen[v.ID] = true
			if v.End > last {
				last = v.End
			}
			lat = append(lat, float64(v.End-v.Start)/1e6)
		}
	}
	if len(lat) != t.Count {
		return fmt.Errorf("drain count mismatch")
	}
	r["end_ns"] = last
	r["confirmed"] = t.Count
	r["throughput_mps"] = float64(t.Count) * 1e9 / float64(last-start)
	r["latency_ms"] = quantiles(lat)
	r["stage"] = "readback"
	verification, e := admin.readback(t.ID, int64(t.Count), payload)
	r["payload_verification"] = verification
	return e
}
func victim(t Trial) {
	c, e := connect(t, "victim")
	if e != nil {
		panic(e)
	}
	defer c.close()
	if e = c.bind(t.ID); e != nil {
		panic(e)
	}
	m, e := c.receive(t.ID, 5*time.Second)
	if e != nil {
		panic(e)
	}
	json.NewEncoder(os.Stdout).Encode(map[string]any{"receipt_ns": m.received, "id": m.id})
	time.Sleep(time.Hour)
}
func recovery(t Trial, admin *client, r map[string]any) error {
	if e := admin.publish(t.ID, payload(0)); e != nil {
		return e
	}
	survivor, e := connect(t, "survivor")
	if e != nil {
		return e
	}
	defer survivor.close()
	if e = survivor.bind(t.ID); e != nil {
		return e
	}
	b, _ := json.Marshal(t)
	cmd := exec.Command(os.Args[0], "victim", string(b))
	stdout, e := cmd.StdoutPipe()
	if e != nil {
		return e
	}
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if e = cmd.Start(); e != nil {
		return e
	}
	waited := false
	defer func() {
		if !waited {
			cmd.Process.Kill()
			cmd.Wait()
		}
		r["victim_stderr"] = stderr.String()
	}()
	scanner := bufio.NewScanner(stdout)
	if !scanner.Scan() {
		return fmt.Errorf("no victim receipt: %s", stderr.String())
	}
	var receipt map[string]any
	receiptDecoder := json.NewDecoder(bytes.NewReader(scanner.Bytes()))
	receiptDecoder.UseNumber()
	if e = receiptDecoder.Decode(&receipt); e != nil {
		return e
	}
	received := number(receipt["receipt_ns"])
	r["receipt_ns"] = received
	type result struct {
		m        *message
		e        error
		end      int64
		attempts int
	}
	done := make(chan result, 1)
	stop := make(chan struct{})
	firstRequest := make(chan int64, 1)
	var firstOnce sync.Once
	survivor.onRequest = func(stamp int64) { firstOnce.Do(func() { firstRequest <- stamp }) }
	delta := time.Duration(t.DeltaMS) * time.Millisecond
	phase := time.Duration(0)
	if t.Recovery == "autoclaim" {
		phase = time.Duration(rand.New(rand.NewSource(t.Seed)).Int63n(int64(10 * time.Millisecond)))
	}
	r["poll_phase_ns"] = int64(phase)
	go func() {
		defer func() {
			if p := recover(); p != nil {
				done <- result{e: fmt.Errorf("survivor panic: %v", p), end: mono()}
			}
		}()
		time.Sleep(phase)
		attempts := 0
		for {
			select {
			case <-stop:
				done <- result{e: fmt.Errorf("censored"), end: mono(), attempts: attempts}
				return
			default:
			}
			attempts++
			var m *message
			var err error
			if t.Engine == "redis" && t.Recovery != "none" {
				m, err = survivor.claim(t.ID, delta, t.Recovery)
				if timeout(err) {
					if t.Recovery == "autoclaim" {
						time.Sleep(10 * time.Millisecond)
					}
					continue
				}
			} else {
				m, err = survivor.receive(t.ID, 100*time.Millisecond)
				if timeout(err) {
					continue
				}
			}
			done <- result{m: m, e: err, end: mono(), attempts: attempts}
			return
		}
	}()
	select {
	case stamp := <-firstRequest:
		r["survivor_first_request_ns"] = stamp
	case rr := <-done:
		return fmt.Errorf("survivor failed before first request: %v", rr.e)
	case <-time.After(10 * time.Second):
		close(stop)
		return fmt.Errorf("survivor did not begin a request")
	}
	if wait := received + int64(float64(delta)*t.Age) - mono(); wait > 0 {
		time.Sleep(time.Duration(wait))
	}
	reference := mono()
	r["reference_start_ns"] = reference
	r["actual_receipt_age_ms"] = float64(reference-received) / 1e6
	if t.Kill {
		if e = cmd.Process.Kill(); e != nil {
			return e
		}
		r["victim_exit"] = fmt.Sprint(cmd.Wait())
		waited = true
	}
	r["reference_end_ns"] = mono()
	budget := 5*delta + 2*time.Second
	if t.Recovery == "none" {
		budget = 2 * delta
	}
	budgetStart := mono()
	r["budget_start_ns"] = budgetStart
	r["nominal_deadline_ns"] = budgetStart + int64(budget)
	timer := time.NewTimer(budget)
	defer timer.Stop()
	var rr result
	censored := false
	select {
	case rr = <-done:
	case <-timer.C:
		r["timer_observed_ns"] = mono()
		censored = true
		close(stop)
		rr = <-done
	}
	r["controller_end_ns"] = mono()
	r["survivor_end_ns"] = rr.end
	r["attempts"] = rr.attempts
	r["timer_branch_selected"] = censored
	r["censored"] = rr.m == nil
	if rr.m != nil {
		r["redelivery_ns"] = rr.m.received
		r["redelivery_before_reference"] = rr.m.received < reference
		r["received_during_shutdown"] = censored && rr.m.received >= number(r["timer_observed_ns"])
		r["redelivery_after_nominal_deadline"] = rr.m.received > budgetStart+int64(budget)
		r["deliveries"] = rr.m.deliveries
		if rr.m.id != 0 || !bytes.Equal(rr.m.data, payload(0)) {
			return fmt.Errorf("recovery payload mismatch")
		}
		if e = survivor.ack(t.ID, rr.m); e != nil {
			return e
		}
		r["receipt_excess_ms"] = float64(rr.m.received-received)/1e6 - float64(t.DeltaMS)
		r["reference_to_redelivery_ms"] = float64(rr.m.received-reference) / 1e6
	} else if !censored {
		return rr.e
	}
	if t.Recovery != "none" && rr.m == nil {
		return fmt.Errorf("active recovery censored")
	}
	if t.Recovery == "none" && rr.m != nil {
		return fmt.Errorf("negative control unexpectedly recovered")
	}
	return nil
}
func runTrial(t Trial, out string) (r map[string]any) {
	r = map[string]any{"trial": t, "status": "failed", "stage": "prepare", "utc_start": time.Now().UTC(), "gomaxprocs": runtime.GOMAXPROCS(0), "driver_kernel": contents("/proc/version")}
	if e := os.MkdirAll(filepath.Dir(out), 0755); e != nil {
		r["error"] = e.Error()
		return
	}
	if e := os.Mkdir(out, 0755); e != nil {
		r["error"] = e.Error()
		return
	}
	defer func() {
		if p := recover(); p != nil {
			r["error"] = fmt.Sprintf("panic: %v", p)
		}
		r["utc_end"] = time.Now().UTC()
		if e := saveJSON(filepath.Join(out, "result.json"), r); e != nil {
			r["result_write_error"] = e.Error()
		}
	}()
	preparePayload(t.Payload)
	start, e := request(t, "start", t)
	r["broker_start"] = start
	defer func() {
		stop, e := request(t, "stop", nil)
		if e != nil {
			r["stop_error"] = e.Error()
		} else {
			if f, ok := stop["files_gzip"].(map[string]any); ok {
				for name, data := range f {
					var encoded []byte
					j, _ := json.Marshal(data)
					if json.Unmarshal(j, &encoded) == nil {
						os.WriteFile(filepath.Join(out, name), encoded, 0644)
					}
				}
				delete(stop, "files_gzip")
			}
			r["broker_stop"] = stop
		}
	}()
	if e != nil {
		r["error"] = e.Error()
		return
	}
	admin, e := connect(t, "admin")
	if e != nil {
		r["error"] = e.Error()
		return
	}
	defer admin.close()
	r["stage"] = "warmup"
	r["warmup_start_ns"] = mono()
	if e = warmup(t, admin); e != nil {
		r["error"] = e.Error()
		return
	}
	r["warmup_end_ns"] = mono()
	delta := 30 * time.Second
	if t.Kind == "recovery" {
		delta = time.Duration(t.DeltaMS) * time.Millisecond
	}
	if e = admin.create(t.ID, delta); e != nil {
		r["error"] = e.Error()
		return
	}
	r["stage"] = "measurement"
	switch t.Kind {
	case "publication", "trace", "compression":
		e = publication(t, admin, out, r)
	case "drain":
		e = drain(t, admin, out, r)
	case "recovery":
		e = recovery(t, admin, r)
	default:
		e = fmt.Errorf("unknown trial kind")
	}
	r["reconciliation_start_ns"] = mono()
	inventory, ie := admin.inventory(t.ID)
	r["inventory"] = inventory
	r["reconciliation_end_ns"] = mono()
	if e != nil {
		r["error"] = e.Error()
	}
	if ie != nil {
		r["inventory_error"] = ie.Error()
	}
	if e == nil && ie == nil {
		n := number(r["confirmed"])
		pending := int64(0)
		if t.Kind == "recovery" {
			n = 1
			if t.Recovery == "none" {
				pending = 1
			}
		}
		if number(inventory["stored"]) != n || number(inventory["pending"]) != pending {
			r["error"] = "final inventory mismatch"
		} else {
			r["status"] = "complete"
			r["stage"] = "complete"
		}
	}
	return
}
func main() {
	if len(os.Args) < 3 {
		panic("control ENGINE | trial CONFIG OUT | victim JSON")
	}
	switch os.Args[1] {
	case "control":
		runControl(os.Args[2])
	case "victim":
		var t Trial
		if e := json.Unmarshal([]byte(os.Args[2]), &t); e != nil {
			panic(e)
		}
		victim(t)
	case "trial":
		var t Trial
		var b []byte
		var e error
		if os.Args[2] == "-" {
			b, e = io.ReadAll(os.Stdin)
		} else {
			b, e = os.ReadFile(os.Args[2])
		}
		if e != nil {
			panic(e)
		}
		if e = json.Unmarshal(b, &t); e != nil {
			panic(e)
		}
		r := runTrial(t, os.Args[3])
		json.NewEncoder(os.Stdout).Encode(r)
		if r["status"] != "complete" {
			os.Exit(2)
		}
	default:
		panic("unknown command")
	}
}
