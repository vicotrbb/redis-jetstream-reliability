package main

import (
	"compress/gzip"
	"encoding/csv"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestRequestFailurePreservesConfirmedAndUnknownAttempts(t *testing.T) {
	calls := 0
	sentinel := errors.New("injected request timeout")
	events, _, err := publicationEvents([]publishCall{func([]byte) error {
		calls++
		if calls == 4 {
			return sentinel
		}
		return nil
	}}, time.Second)
	if !errors.Is(err, sentinel) {
		t.Fatalf("primary error was lost: %v", err)
	}
	if len(events[0]) != 4 {
		t.Fatalf("expected all four attempted requests, got %d", len(events[0]))
	}
	path := filepath.Join(t.TempDir(), "partial.csv.gz")
	hash, err := persistPublication(path, events, false)
	if err != nil || len(hash) != 64 {
		t.Fatalf("trace not persisted: %s %v", hash, err)
	}
	f, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	z, err := gzip.NewReader(f)
	if err != nil {
		t.Fatal(err)
	}
	defer z.Close()
	records, err := csv.NewReader(z).ReadAll()
	if err != nil {
		t.Fatal(err)
	}
	if len(records) != 5 {
		t.Fatal(records)
	}
	for _, r := range records[1:4] {
		if r[5] != "confirmed" || r[2] == "0" {
			t.Fatal(r)
		}
	}
	last := records[4]
	if last[5] != "unknown" || last[2] != "0" || !strings.Contains(last[6], "timeout") {
		t.Fatal(last)
	}
	if _, err = persistPublication(path, events, false); err == nil {
		t.Fatal("overwrote existing trace")
	}
}

func TestWorkerPanicIsContainedWithUnknownAttempt(t *testing.T) {
	events, _, err := publicationEvents([]publishCall{func([]byte) error { panic("injected panic") }}, time.Second)
	if err == nil || !strings.Contains(err.Error(), "injected panic") {
		t.Fatal(err)
	}
	if len(events[0]) != 1 || events[0][0].Acked != 0 {
		t.Fatal(events)
	}
	if _, err = persistPublication(filepath.Join(t.TempDir(), "partial.csv.gz"), events, false); err != nil {
		t.Fatal(err)
	}
}

func TestIdentityAndDestinationProtection(t *testing.T) {
	t.Setenv("MSGREL_CAMPAIGN_ID", "study")
	t.Setenv("MSGREL_ATTEMPT_ID", "a1")
	if err := loadIdentity(); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "series")
	if err := freshSeries(path); err != nil {
		t.Fatal(err)
	}
	if err := freshSeries(path); err == nil {
		t.Fatal("existing series accepted")
	}
	row := scope(map[string]any{"key": "D038"}).(map[string]any)
	if row["campaign_id"] != "study" || row["attempt_id"] != "a1" {
		t.Fatal(row)
	}
	t.Setenv("MSGREL_CAMPAIGN_ID", "../other")
	if err := loadIdentity(); err == nil {
		t.Fatal("unsafe identity accepted")
	}
}
