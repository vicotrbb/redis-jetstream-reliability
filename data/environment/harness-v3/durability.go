package main

import (
	"compress/gzip"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

type PubEvent struct {
	ID          int64
	Sent, Acked int64
	Worker      int
}

func timedPublish(profile, key, out string) map[string]any {
	admin, e := connect(profile, "admin")
	must(e)
	defer admin.close()
	must(admin.create(key, 30*time.Second))
	defer admin.remove(key)
	clients := make([]*Client, 16)
	for i := range clients {
		clients[i], e = connect(profile, fmt.Sprintf("pub%d", i))
		must(e)
		defer clients[i].close()
	}
	events := make([][]PubEvent, 16)
	var wg sync.WaitGroup
	var seq int64
	seq = -1
	before := readFile("/sys/fs/cgroup/cpu.stat")
	start := mono()
	end := start + int64(5*time.Second)
	for i, c := range clients {
		wg.Add(1)
		go func(i int, c *Client) {
			defer wg.Done()
			for mono() < end {
				id := atomic.AddInt64(&seq, 1)
				b := payload(int(id))
				sent := mono()
				must(c.publish(key, b))
				acked := mono()
				events[i] = append(events[i], PubEvent{id, sent, acked, i})
			}
		}(i, c)
	}
	wg.Wait()
	after := readFile("/sys/fs/cgroup/cpu.stat")
	count := int64(0)
	last := start
	latencies := []float64{}
	perSecond := make([]int, 7)
	for _, es := range events {
		for _, ev := range es {
			count++
			if ev.Acked > last {
				last = ev.Acked
			}
			latencies = append(latencies, float64(ev.Acked-ev.Sent)/1e6)
			s := int((ev.Acked - start) / 1e9)
			if s < len(perSecond) {
				perSecond[s]++
			}
		}
	}
	stored, pending, e := admin.inventory(key)
	must(e)
	if stored != count || pending != 0 || seq+1 != count {
		panic("timed publication integrity")
	}
	f, e := os.Create(filepath.Join(out, key+".csv.gz"))
	must(e)
	gz := gzip.NewWriter(f)
	cw := csv.NewWriter(gz)
	must(cw.Write([]string{"id", "publish_start_ns", "publish_ack_ns", "worker"}))
	for _, es := range events {
		for _, ev := range es {
			must(cw.Write([]string{strconv.FormatInt(ev.ID, 10), strconv.FormatInt(ev.Sent, 10), strconv.FormatInt(ev.Acked, 10), strconv.Itoa(ev.Worker)}))
		}
	}
	cw.Flush()
	must(cw.Error())
	must(gz.Close())
	must(f.Close())
	return map[string]any{"kind": "durability", "key": key, "profile": profile, "n": count, "publishers": 16, "target_seconds": 5, "start_ns": start, "end_ns": last, "publish_mps": float64(count) * 1e9 / float64(last-start), "publish_ms": stats(latencies), "stored": stored, "pending": pending, "per_second_counts": perSecond, "driver_cpu_before": before, "driver_cpu_after": after}
}
func durability(out string) {
	must(os.MkdirAll(out, 0755))
	f, e := os.Create(filepath.Join(out, "summary.jsonl"))
	must(e)
	defer f.Close()
	enc := json.NewEncoder(f)
	rng := rand.New(rand.NewSource(20260923))
	serial := 0
	for block := 0; block < 10; block++ {
		order := append([]string{}, profiles...)
		rng.Shuffle(len(order), func(i, j int) { order[i], order[j] = order[j], order[i] })
		for _, p := range order {
			serial++
			key := fmt.Sprintf("D%03d", serial)
			_, e := trial(p, 16, 16, 256, key+"warm", "")
			must(e)
			v := timedPublish(p, key, out)
			v["block"] = block
			v["utc_end"] = time.Now().UTC()
			must(enc.Encode(v))
			must(f.Sync())
			emit(v)
		}
	}
}
