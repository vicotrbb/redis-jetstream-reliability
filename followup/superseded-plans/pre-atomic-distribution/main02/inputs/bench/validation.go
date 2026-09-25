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
	for i, cell := range []struct {
		profile string
		control bool
	}{{"redis-periodic", false}, {"nats-periodic", false}, {"redis-periodic", true}} {
		poll := time.Duration(0)
		if cell.profile == "redis-periodic" && !cell.control {
			poll = 10 * time.Millisecond
		}
		row := recoverOne(cell.profile, 250*time.Millisecond, .1, poll, int64(i+20260924), fmt.Sprintf("endpoint%02d", i), cell.control)
		start := row["censor_budget_start_ns"].(int64)
		deadline := row["nominal_censor_deadline_ns"].(int64)
		loopEnd := row["survivor_loop_completed_ns"].(int64)
		waitEnd := row["controller_wait_completed_ns"].(int64)
		reconcileStart := row["reconciliation_start_ns"].(int64)
		reconcileEnd := row["reconciliation_end_ns"].(int64)
		if start < row["kill_end_ns"].(int64) || deadline <= start || waitEnd < loopEnd || reconcileStart < waitEnd || reconcileEnd < reconcileStart {
			panic("invalid recorded recovery endpoint order")
		}
		if cell.control {
			timer := row["timer_notification_observed_ns"].(int64)
			if !row["censored"].(bool) || timer < deadline || loopEnd < timer || row["pending"].(int64) != 1 {
				panic("nominal budget was confused with control completion")
			}
		} else if row["censored"].(bool) || row["timer_notification_observed_ns"] != nil || row["redelivery_ns"].(int64) < row["kill_end_ns"].(int64) {
			panic("active recovery endpoint validation failed")
		}
		row["kind"] = "validation_recovery_endpoints"
		must(appendOutcome(filepath.Join(out, "summary.jsonl"), row))
		emit(row)
	}
}
