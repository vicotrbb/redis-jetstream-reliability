package main

import "time"

type recoveryResult struct {
	m         *Message
	e         error
	attempts  int
	loopEndNS int64
}

type recoveryObservation struct {
	result          recoveryResult
	censored        bool
	budgetStartNS   int64
	deadlineNS      int64
	timerObservedNS int64
	waitEndNS       int64
}

// The deadline is a nominal budget, not the end of observation. An outstanding
// broker call must return before the survivor can stop. Record both events.
func observeRecovery(result <-chan recoveryResult, stop chan struct{}, limit time.Duration) recoveryObservation {
	o := recoveryObservation{budgetStartNS: mono()}
	o.deadlineNS = o.budgetStartNS + int64(limit)
	timer := time.NewTimer(limit)
	defer timer.Stop()
	select {
	case o.result = <-result:
	case <-timer.C:
		o.timerObservedNS = mono()
		o.censored = true
		close(stop)
		o.result = <-result
	}
	o.waitEndNS = mono()
	return o
}

func (o recoveryObservation) record(v map[string]any) {
	v["observation_schema"] = "recovery-endpoints-v1"
	v["censor_budget_start_ns"] = o.budgetStartNS
	v["nominal_censor_deadline_ns"] = o.deadlineNS
	v["timer_notification_observed_ns"] = nil
	if o.censored {
		v["timer_notification_observed_ns"] = o.timerObservedNS
	}
	v["survivor_loop_completed_ns"] = o.result.loopEndNS
	v["controller_wait_completed_ns"] = o.waitEndNS
	if o.result.e != nil {
		v["survivor_result_error"] = o.result.e.Error()
	}
	// Preserve a receipt returned while the controller was stopping the survivor.
	// This is distinct from a no-recovery control and is not silently discarded.
	if o.censored && o.result.m != nil {
		v["receipt_returned_during_shutdown_ns"] = o.result.m.received
		v["receipt_returned_during_shutdown_id"] = o.result.m.id
	}
}
