package main

import (
	"bytes"
	"compress/gzip"
	"encoding/binary"
	"encoding/csv"
	"os"
	"path/filepath"
	"testing"
)

func TestPayloadIdentityAndReproduction(t *testing.T) {
	for _, kind := range []string{"compressible", "random"} {
		preparePayload(kind)
		for _, id := range []int64{0, 4095, 4096, 1000001} {
			p := payload(id)
			if len(p) != 512 || binary.BigEndian.Uint64(p) != uint64(id) {
				t.Fatal("invalid payload", kind, id)
			}
			preparePayload(kind)
			if !bytes.Equal(p, payload(id)) {
				t.Fatal("nonreproducible payload", kind, id)
			}
			if bytes.Equal(p, payload(id+4096)) {
				t.Fatal("identity reused across template cycle")
			}
		}
	}
}

func TestTailRankAndEmptySamples(t *testing.T) {
	if quantiles(nil) != nil {
		t.Fatal("empty sample must not invent a percentile")
	}
	v := make([]float64, 149)
	for i := range v {
		v[i] = float64(i + 1)
	}
	if quantiles(v)["p99"] != 148 {
		t.Fatal("nearest-rank p99 incorrect")
	}
}

func TestPartialEventsRetainUnknown(t *testing.T) {
	path := filepath.Join(t.TempDir(), "events.csv.gz")
	events := [][]Event{{{ID: 0, Start: 10, End: 20, Confirmed: true}, {ID: 1, Start: 30, End: 40, Error: "injected timeout"}}}
	receipt, e := persistEvents(path, events)
	if e != nil || receipt["records"] != 2 {
		t.Fatal(receipt, e)
	}
	f, e := os.Open(path)
	if e != nil {
		t.Fatal(e)
	}
	defer f.Close()
	g, e := gzip.NewReader(f)
	if e != nil {
		t.Fatal(e)
	}
	defer g.Close()
	rows, e := csv.NewReader(g).ReadAll()
	if e != nil {
		t.Fatal(e)
	}
	if len(rows) != 3 || rows[1][5] != "true" || rows[2][5] != "false" || rows[2][6] != "injected timeout" {
		t.Fatal(rows)
	}
	if _, e = persistEvents(path, events); e == nil {
		t.Fatal("overwrote prior observations")
	}
}
