# Internal review resolution

- R1: changed the scaling claim to a sufficient condition and stated the exact required U/mean-R ratio.
- R2: removed causal isolation wording for the serial sensitivity, which changes both publisher count and workload duration/count.
- R3: analysis now checks every reported raw-trace summary mean, maximum, quantile, drain rate and occupancy, and both recovery intervals. For timed publication, end must equal the last raw ACK; for fixed-count publication, end is explicitly the return of the publisher join and may be slightly later than the last raw ACK. That original denominator is retained and checked, rather than falsely asserting equality.
- Made positive denominator assumptions explicit; stated continuous-time/broker-clock assumptions and unobserved broker age.
- Bootstrap intervals describe uncertainty in means under exchangeable blocks, not prediction coverage or exact finite-sample guarantees.
- All observed setup/warm-up incidents are retained and disclosed. Administrative timeout changes do not change timed publication/consumer deadlines.
- Recovery nominal Delta(1-alpha) is labeled a client-receipt-based reference, not a verified empirical lower bound.
- A second static audit scoped the 256-message warm-up to concurrency, durability, and serial trials; recovery uses its separate single-message setup.
- Per-message event claims now identify the successful receive-request invocation. Empty and timed-out receive attempts have no per-message trace row.
- Recovery descriptions now state that survivor polling begins before the kill, nominal censor budgets begin after observed process exit, and the final state reconciliation waits for survivor-loop shutdown.
- The serialized synchronization-stage bound now assigns at most b confirmations to each completed synchronization operation, eliminating an ambiguous many-groups-to-one-operation premise.
- The cleanup-error preservation statement is narrowed to the fixed-count trial path; the untouched publication-only and recovery paths retain their original behavior.

- The final timed failure is retained in an independent outcome manifest and failure ledger. The analyzer fails closed if either is missing or inconsistent. Its accidental completed replay is excluded; interrupted operator-only D043 state is disclosed.
- Variable-size bootstrap samples use the completed planned trials: Redis-always publication has nine, other primary publication profiles have ten. Paired ratios use common completed blocks. All manuscript sample-count claims were checked against these outcomes.
- Final internal read-only audit found no material numerical or scope error in the abstract, results, or conclusion. All 420 aggregate CSV rows match the corresponding JSON estimates and intervals. The audit checked recovery medians, occupancy, p99 endpoints, ratios, failures, and final resource receipts.
- Ten Lean declarations passed on the homelab; the checked source digest matches both log and JSON receipt. The only initial checker repair was an unused binder rename, retaining the hypothesis. Formal scope and standard logical dependencies are stated explicitly.
- The raw-data analyzer completed successfully. The compiled paper passes section, reference, overflow, trial-count, and proof-receipt checks. Final visual layout review is recorded in `data/derived/visual-review.json`.
