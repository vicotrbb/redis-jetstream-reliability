package main

import (
	"errors"
	"testing"
	"time"
)

func TestRecoveryBudgetWaitsForOutstandingOperation(t *testing.T) {
	for _, lateReceipt := range []bool{false, true} {
		name := "empty control"
		if lateReceipt {
			name = "late receipt retained"
		}
		t.Run(name, func(t *testing.T) {
			result := make(chan recoveryResult)
			stop := make(chan struct{})
			done := make(chan recoveryObservation, 1)
			go func() { done <- observeRecovery(result, stop, time.Millisecond) }()
			select {
			case <-stop:
			case <-time.After(5 * time.Second):
				t.Fatal("budget did not trigger survivor stop")
			}
			select {
			case <-done:
				t.Fatal("controller finished before the outstanding operation returned")
			default:
			}
			rr := recoveryResult{e: errors.New("censored"), attempts: 1}
			if lateReceipt {
				rr.m, rr.e = &Message{id: 7, received: mono()}, nil
			}
			rr.loopEndNS = mono()
			result <- rr
			o := <-done
			if !o.censored || o.deadlineNS != o.budgetStartNS+int64(time.Millisecond) ||
				o.timerObservedNS < o.deadlineNS || rr.loopEndNS < o.timerObservedNS || o.waitEndNS < rr.loopEndNS {
				t.Fatalf("invalid endpoint ordering: %+v", o)
			}
			v := map[string]any{}
			o.record(v)
			_, hasLate := v["receipt_returned_during_shutdown_ns"]
			if hasLate != lateReceipt || v["timer_notification_observed_ns"] != o.timerObservedNS {
				t.Fatal(v)
			}
		})
	}
}

func TestRecoveryBeforeBudgetDoesNotInventExpiry(t *testing.T) {
	result := make(chan recoveryResult, 1)
	stop := make(chan struct{})
	result <- recoveryResult{m: &Message{id: 0, received: mono()}, attempts: 1, loopEndNS: mono()}
	o := observeRecovery(result, stop, time.Hour)
	if o.censored || o.timerObservedNS != 0 || o.waitEndNS < o.result.loopEndNS {
		t.Fatalf("successful receipt mislabeled: %+v", o)
	}
	select {
	case <-stop:
		t.Fatal("success incorrectly triggered stop")
	default:
	}
	v := map[string]any{}
	o.record(v)
	if v["timer_notification_observed_ns"] != nil {
		t.Fatal("invented timer timestamp", v)
	}
}
