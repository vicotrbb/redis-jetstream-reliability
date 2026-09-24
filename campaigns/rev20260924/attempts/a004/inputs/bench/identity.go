package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
)

var campaignID, attemptID string

func loadIdentity() error {
	campaignID, attemptID = os.Getenv("MSGREL_CAMPAIGN_ID"), os.Getenv("MSGREL_ATTEMPT_ID")
	valid := regexp.MustCompile(`^[a-z0-9]([a-z0-9-]{0,18}[a-z0-9])?$`)
	if !valid.MatchString(campaignID) || !valid.MatchString(attemptID) {
		return fmt.Errorf("explicit MSGREL_CAMPAIGN_ID and MSGREL_ATTEMPT_ID are required")
	}
	return nil
}
func scope(v any) any {
	if row, ok := v.(map[string]any); ok {
		for key, value := range map[string]string{"campaign_id": campaignID, "attempt_id": attemptID} {
			if old, exists := row[key]; exists && old != value {
				panic("record identity mismatch")
			}
			row[key] = value
		}
	}
	return v
}

type scopedEncoder struct{ encoder *json.Encoder }

func newScopedEncoder(w io.Writer) scopedEncoder { return scopedEncoder{json.NewEncoder(w)} }
func (e scopedEncoder) Encode(v any) error       { return e.encoder.Encode(scope(v)) }

func freshSeries(out string) error {
	if err := os.MkdirAll(filepath.Dir(out), 0755); err != nil {
		return err
	}
	if err := os.Mkdir(out, 0755); err != nil {
		return fmt.Errorf("refusing existing series destination: %w", err)
	}
	writeJSON(filepath.Join(out, "identity.json"), map[string]any{"campaign_id": campaignID, "attempt_id": attemptID})
	return nil
}
