package main

import (
	"compress/gzip"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"fmt"
	"io"
	"math/rand"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

type PubEvent struct {
	ID                 int64
	Sent, Acked, Ended int64
	Worker             int
	Error              string
}
type publishCall func([]byte) error

// Returned request errors stop admission. All already-started calls are joined.
// Observations remain buffered during timing and are synced before cleanup.
// Abrupt driver/host loss can still destroy buffered observations; no stronger
// crash-persistence guarantee is asserted for this diagnostic harness.
func publicationEvents(calls []publishCall, duration time.Duration) ([][]PubEvent, int64, error) {
	events := make([][]PubEvent, len(calls))
	var stopped atomic.Bool
	var seq atomic.Int64
	seq.Store(-1)
	var wg sync.WaitGroup
	errors := make(chan error, len(calls))
	start := mono()
	end := start + int64(duration)
	for i, publish := range calls {
		wg.Add(1)
		go func(i int, publish publishCall) {
			defer wg.Done()
			defer func() {
				if value := recover(); value != nil {
					stopped.Store(true)
					errors <- fmt.Errorf("publisher %d panic: %v", i, value)
				}
			}()
			for mono() < end && !stopped.Load() {
				id := seq.Add(1)
				b := payload(int(id))
				ev := PubEvent{ID: id, Sent: mono(), Worker: i}
				events[i] = append(events[i], ev)
				slot := len(events[i]) - 1
				err := publish(b)
				events[i][slot].Ended = mono()
				if err != nil {
					events[i][slot].Error = err.Error()
					stopped.Store(true)
					errors <- fmt.Errorf("publisher %d id %d: %w", i, id, err)
					return
				}
				events[i][slot].Acked = events[i][slot].Ended
			}
		}(i, publish)
	}
	wg.Wait()
	close(errors)
	var first error
	for err := range errors {
		if first == nil {
			first = err
		}
	}
	return events, start, first
}

func persistPublication(path string, events [][]PubEvent, complete bool) (string, error) {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if err != nil {
		return "", err
	}
	defer f.Close()
	gz := gzip.NewWriter(f)
	cw := csv.NewWriter(gz)
	header := []string{"id", "publish_start_ns", "publish_ack_ns", "worker"}
	if !complete {
		header = append(header, "operation_end_ns", "status", "error")
	}
	if err = cw.Write(header); err != nil {
		return "", err
	}
	for _, es := range events {
		for _, ev := range es {
			row := []string{strconv.FormatInt(ev.ID, 10), strconv.FormatInt(ev.Sent, 10), strconv.FormatInt(ev.Acked, 10), strconv.Itoa(ev.Worker)}
			if !complete {
				status := "confirmed"
				if ev.Acked == 0 {
					status = "unknown"
				}
				row = append(row, strconv.FormatInt(ev.Ended, 10), status, ev.Error)
			}
			if err = cw.Write(row); err != nil {
				return "", err
			}
		}
	}
	cw.Flush()
	if err = cw.Error(); err != nil {
		return "", err
	}
	if err = gz.Close(); err != nil {
		return "", err
	}
	if err = f.Sync(); err != nil {
		return "", err
	}
	if err = f.Close(); err != nil {
		return "", err
	}
	// The directory entry is also synced before any broker cleanup.
	dir, err := os.Open(filepath.Dir(path))
	if err != nil {
		return "", err
	}
	err = dir.Sync()
	dir.Close()
	if err != nil {
		return "", err
	}
	in, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer in.Close()
	hash := sha256.New()
	if _, err = io.Copy(hash, in); err != nil {
		return "", err
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

func timedPublish(profile, key, out string) (result map[string]any, runErr error) {
	return timedPublishWith(profile, key, out, 5*time.Second, nil)
}

func timedPublishWith(profile, key, out string, duration time.Duration, decorate func([]publishCall) []publishCall) (result map[string]any, runErr error) {
	result = map[string]any{"kind": "durability_failure", "key": key, "profile": profile, "stage": "setup"}
	admin, err := connect(profile, "admin")
	if err != nil {
		return result, err
	}
	defer admin.close()
	// Cleanup reports cannot replace a request error or erase its partial trace.
	defer func() {
		if err := admin.removeE(key); err != nil {
			result["cleanup_error"] = err.Error()
			emit(map[string]any{"kind": "cleanup_error", "key": key, "profile": profile, "error": err.Error(), "primary_error": fmt.Sprint(runErr)})
		}
	}()
	if err = admin.create(key, 30*time.Second); err != nil {
		return result, err
	}
	calls := make([]publishCall, 16)
	for i := range calls {
		client, err := connect(profile, fmt.Sprintf("pub%d", i))
		if err != nil {
			return result, err
		}
		defer client.close()
		calls[i] = client.publishCall(key)
	}
	if decorate != nil {
		calls = decorate(calls)
	}
	before := readFile("/sys/fs/cgroup/cpu.stat")
	events, start, primary := publicationEvents(calls, duration)
	finish := mono()
	after := readFile("/sys/fs/cgroup/cpu.stat")
	var attempted, confirmed int64
	last := start
	latencies := []float64{}
	perSecond := make([]int, 1)
	for _, es := range events {
		for _, ev := range es {
			attempted++
			if ev.Acked == 0 {
				continue
			}
			confirmed++
			if ev.Acked > last {
				last = ev.Acked
			}
			latencies = append(latencies, float64(ev.Acked-ev.Sent)/1e6)
			second := int((ev.Acked - start) / 1e9)
			for len(perSecond) <= second {
				perSecond = append(perSecond, 0)
			}
			perSecond[second]++
		}
	}
	result = map[string]any{"kind": "durability_failure", "key": key, "profile": profile, "stage": "timed_publication",
		"attempted": attempted, "confirmed": confirmed, "unknown": attempted - confirmed,
		"publishers": 16, "target_seconds": duration.Seconds(), "start_ns": start, "observation_end_ns": finish,
		"driver_cpu_before": before, "driver_cpu_after": after}
	// Persist before inventory or cleanup, both of which can themselves fail.
	partialName := key + ".attempts.csv.gz"
	hash, saveErr := persistPublication(filepath.Join(out, partialName), events, false)
	if saveErr != nil {
		result["trace_error"] = saveErr.Error()
		return result, fmt.Errorf("publication error: %v; preserving events: %w", primary, saveErr)
	}
	result["partial_events"] = partialName
	result["partial_events_sha256"] = hash
	stored, pending, inventoryErr := admin.inventory(key)
	if inventoryErr != nil {
		result["inventory_error"] = inventoryErr.Error()
	} else {
		result["stored"] = stored
		result["pending"] = pending
	}
	if primary != nil {
		return result, primary
	}
	if inventoryErr != nil {
		result["stage"] = "inventory"
		return result, inventoryErr
	}
	if stored != confirmed || pending != 0 || attempted != confirmed || confirmed == 0 {
		result["stage"] = "integrity"
		return result, fmt.Errorf("publication count reconciliation failed")
	}
	if _, err = persistPublication(filepath.Join(out, key+".csv.gz"), events, true); err != nil {
		return result, err
	}
	result["kind"] = "durability"
	result["n"] = confirmed
	result["end_ns"] = last
	result["publish_mps"] = float64(confirmed) * 1e9 / float64(last-start)
	result["publish_ms"] = stats(latencies)
	result["per_second_counts"] = perSecond
	return result, nil
}
func (c *Client) publishCall(key string) publishCall {
	return func(b []byte) error { return c.publish(key, b) }
}

func appendOutcome(path string, row map[string]any) error {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	if err = newScopedEncoder(f).Encode(row); err != nil {
		return err
	}
	return f.Sync()
}
func durability(out string) {
	rng := rand.New(rand.NewSource(20260923))
	serial := 0
	for block := 0; block < 10; block++ {
		order := append([]string{}, profiles...)
		rng.Shuffle(len(order), func(i, j int) { order[i], order[j] = order[j], order[i] })
		for _, profile := range order {
			serial++
			key := fmt.Sprintf("D%03d", serial)
			emit(map[string]any{"kind": "warmup_start", "key": key, "profile": profile, "utc": time.Now().UTC()})
			_, err := trial(profile, 16, 16, 256, key+"warm", "")
			var row map[string]any
			if err != nil {
				row = map[string]any{"kind": "durability_failure", "key": key, "profile": profile, "stage": "warmup"}
			} else {
				row, err = timedPublish(profile, key, out)
			}
			row["block"] = block
			row["harness_revision"] = "campaign-isolation-v6"
			row["utc_end"] = time.Now().UTC()
			if err != nil {
				row["error"] = err.Error()
				must(appendOutcome(filepath.Join(out, "failed-trials.jsonl"), row))
				emit(row)
				panic(err)
			}
			must(appendOutcome(filepath.Join(out, "summary.jsonl"), row))
			emit(row)
		}
	}
}
