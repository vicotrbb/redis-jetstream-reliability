package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sync/atomic"
	"time"
)

// Functional checks run only in the homelab. These are excluded from the paper's
// performance data and do not replicate the original campaign.
func validation(out string) {
	for _, profile := range []string{"redis-memory", "nats-memory"} {
		prefix := "check" + profile
		row, err := trial(profile, 2, 2, 32, prefix+"drain", out)
		must(err)
		row["kind"] = "validation_drain"
		must(appendOutcome(filepath.Join(out, "summary.jsonl"), row))
		emit(row)
		row, err = timedPublishWith(profile, prefix+"success", out, 100*time.Millisecond, nil)
		must(err)
		row["kind"] = "validation_publication"
		must(appendOutcome(filepath.Join(out, "summary.jsonl"), row))
		emit(row)
		var calls atomic.Int64
		decorator := func(pubs []publishCall) []publishCall {
			for i, original := range pubs {
				original := original
				pubs[i] = func(b []byte) error {
					if err := original(b); err != nil {
						return err
					}
					if calls.Add(1) == 4 {
						return fmt.Errorf("injected lost confirmation after successful broker append")
					}
					return nil
				}
			}
			return pubs
		}
		row, err = timedPublishWith(profile, prefix+"failure", out, time.Second, decorator)
		if err == nil || row["unknown"].(int64) < 1 {
			panic("failure injection was not recorded")
		}
		if row["stored"].(int64) <= row["confirmed"].(int64) {
			panic("ambiguous confirmation was mislabeled")
		}
		if _, e := os.Stat(filepath.Join(out, row["partial_events"].(string))); e != nil {
			panic(e)
		}
		row["kind"] = "validation_failure"
		row["error"] = err.Error()
		must(appendOutcome(filepath.Join(out, "failed-trials.jsonl"), row))
		emit(row)
	}
}
