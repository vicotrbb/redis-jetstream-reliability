# Follow-up protocol and validation record

This record concerns the experimental extension prepared on 24 September 2026. It does not certify the original collection retrospectively. All broker execution, Go runtime tests and tracing used only `kubectl --context homelab`. The workstation performed authoring and analysis.

## Prospective boundary

The final collection harness is `bench/followup/`, separate from the unchanged historical `bench/*.go` implementation. Three primary plans, `main01`, `main02` and `main03`, each contain 204 cells. Each plan and its source/configuration inputs were sealed before its first measurement. Seeds are 2026092401, 2026092402 and 2026092403. The protocol is `docs/FOLLOWUP_PROTOCOL.md` and its campaign-local copies. This is a prospective follow-up after examining the original study, not an externally registered original experiment.

An earlier set of unexecuted primary plans is retained under `followup/superseded-plans/pre-atomic-distribution/`. A binary-deployment correction superseded those input snapshots before any primary workload ran. Their planned treatment matrix was unchanged. No pilot observation enters the primary summaries.

The frozen protocol's phrase "distinct ... input hashes" is imprecise: each campaign has a separately sealed input snapshot, but identical source snapshots legitimately have identical content hashes. Namespace, seed, plan and destination identities distinguish the deployments. The manuscript uses "separately hashed input snapshots"; the frozen protocol bytes remain preserved. This wording correction changes no treatment or analysis rule.

## Excluded development and validation

| Pilot | Planned | Collected | Complete | Failed | Remaining not executed | Purpose and disposition |
|---|---:|---:|---:|---:|---:|---|
| pilot01 | 35 | 35 | 31 | 4 | 0 | Initial functional paths; two startup-readiness failures and two missing tracer-library failures retained. Setup changes and continuations are documented in its directory. |
| pilot02 | 35 | 35 | 35 | 0 | 0 | Both tracers, verified process-group shutdown, normal publication/drain/readback and recovery. Predates final observation/provenance safeguards. |
| pilot03 | 17 | 7 | 5 | 2 | 10 | Full-duration publication. One deliberate returned-error case and one NATS 2.10.24 OOM during untimed readback; campaign stopped. Kubernetes last state identifies `OOMKilled`. |
| pilot04 | 17 | 17 | 15 | 2 | 0 | Uniform 4 GiB broker limit; all four 15-second memory publication/readback paths; current recovery instrumentation, compression and both tracers. Two deliberate returned-error/panic cases. |
| pilot05 | 10 | 0 | 0 | 0 | 10 | Setup failed when a controller attempted to execute the binary while it was still being copied. The previous container log reports `Text file busy`. No trial invocation occurred. |
| pilot06 | 10 | 10 | 8 | 2 | 0 | Final atomic deployment and diagnostic collection; 65536-message drains at 2/4 CPUs, both tracers, and two deliberate returned-error/panic cases. |

The pilot03 broker limit was 1 GiB. The primary limit is uniformly 4 GiB, with Redis's 2 GiB memory limit and JetStream's 2 GiB memory-store/file-store limits. The literals `2gb` and `2GB` each parse as 2147483648 bytes in both pinned versions, as checked in `revisions/20260924-followup/configuration-unit-check.json`. These are distinct product accounting limits, not equivalent resource contracts. No primary resource setting was changed in response to a primary outcome.

Pilot05 also records an attempted readiness check while bootstrap was still running. It timed out without invoking any workload. The primary series controller waits for bootstrap to finish successfully before starting collection.

Pilot06 compiled the final Go source with Go 1.24.4 and passed three meaningful Go tests with the race detector. The deployed Linux/amd64 binary SHA-256 is `004a548f41a472c635d5784ce213cc359c722e7c288ae65bebe4ca8e7455e0ca`. The code tests cover deterministic payload identity, nearest-rank selection at 149 observations, and preservation of partial/unknown event records without overwriting destinations. Real broker pilot cases complement these checks; they are not a proof covering every error or crash.

Independent analysis of pilot04 checked 3,955,202 timed event records and all 17 planned outcomes. Pilot06 checked 398,119 timed records and all ten outcomes, plus its six preload traces. Injected returned errors and caught panics retain eight confirmed requests and a ninth unknown request after a successful append. The corresponding broker inventory contains nine messages; client confirmation and stored presence remain distinct.

`bench/followup/test_analyze.py` contains five local, offline verifier tests. They reject missing mandatory event/preload evidence, forged invocation output, and missing thread traces; verify that failed pairs remain unavailable; and retain wholly failed conditions. These are analysis checks on copied or synthetic records, not locally executed broker experiments.

## Resolution of source-review findings

The dated review in `FOLLOWUP_HARNESS_REVIEW.md` is historical. Its concrete implementation findings were addressed before primary collection:

- Require pinned images, preserve runtime version and image receipts, and bind executed primary collector bytes to the input snapshot.
- Use an exclusive prelaunch marker, a separate invocation completion record, exact stdout/result agreement, and exit-status consistency. An interrupted invocation cannot be silently replayed.
- Copy the binary to a staging filename, atomically rename it, and verify each deployed digest before readiness.
- Verify process-group disappearance and broker-port closure before cleanup. Propagate traversal, read, compression and diagnostic-write errors; retain the store when diagnostic collection cannot be completed.
- Require every inventoried thread trace and mandatory event/preload traces. Validate worker bounds, confirmed-record errors, admission timing, identity sets and interval occupancy independently.
- Preserve first-request evidence when both recovery channels are ready. Distinguish intentional observation shutdown from network, decoding and panic errors. Classify receipt timing from timestamps separately from timer-branch selection.
- Keep failed publication prefixes separate from successful workload throughput. Failed conditions and missing pairs remain represented in the analysis.
- Define paired contrasts prospectively and correct the diagnostic repetition wording to one observation per condition per deployment.

The final Go files and collector match pilot06 and all three primary input snapshots. Pilot04 validates the unchanged full-duration publication and recovery logic; pilot06 validates the final deployment and diagnostic changes. The resource and timing matrix remains a scoped, single-replica, shared-hardware study.

## Primary bootstrap observations

The initial main01 pod snapshot reports one premeasurement restart of the Redis-current `trace-tools` initializer. Its final initializer exit code is zero, the deployed tracer has a recorded version and binary hash, and the restart counter remains unchanged in the final pod snapshot. Broker/driver work-container restart counters are zero. The original initializer log and reason are not retained; no cause is inferred. This is a bootstrap observation outside the 204 planned trial outcomes, not a replayed trial. The protocol requires successful readiness before measurements and does not require that infrastructure initialization never retry.

`revisions/20260924-followup/main01-initializer-review.json` records the observation and source files. The strengthened offline environment check verifies successful initializer completion, pinned initializer images, unchanged pod UIDs and unchanged initializer counters through measurement. It records initialization retries instead of silently excluding the campaign or describing all containers as never restarted.

The tracer is resolved from Alpine's package repository during bootstrap; its observed version and executable digest are retained in each current broker's environment receipt. This is recorded tool identity, not a pinned APK dependency closure. A later bootstrap must compare those identities rather than assume the package repository remains unchanged. The analysis and report generators can evolve after collection; their current source hashes are bound to their outputs. Frozen measurement inputs remain unchanged.

## Limits of validation

Returned errors and caught panics are preserved after workers join. Abrupt driver/host loss before serialization can still erase buffered observations. The fault injection is a client-side error after a successful append, not a demonstration of actual network-loss behavior. No storage-fault, power-loss, host-failover or external replication result is implied. Full stored-payload readback does not establish stable-media survival and does not compare every delivered payload during the timed drain.

The readback implementation compares every stored byte with the deterministic expected payload and checks the complete ID set at runtime. Its retained receipt reports counts and the comparison outcome; it does not archive a second copy of every read-back payload. Offline verification checks those receipts and the validated comparison code. Independent reexecution of broker readback would require a new campaign because the measured stores are intentionally deleted after collection.

Collection, analysis, fresh proof verification, cleanup, and document QA are complete and reported in [FINAL_REVISION_VALIDATION.md](FINAL_REVISION_VALIDATION.md). The primary series contains 601 completed procedures and eleven retained publication failures across all 612 planned cells. This development record is not a substitute for the source-bound execution and validation receipts.
