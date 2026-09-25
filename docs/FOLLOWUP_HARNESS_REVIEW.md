# Follow-up harness source review

**Historical source-review snapshot.** Concrete findings were subsequently addressed; see [FOLLOWUP_VALIDATION.md](FOLLOWUP_VALIDATION.md) for their resolutions and the separate homelab validation evidence. This review itself remains unchanged below.

Reviewed on 24 September 2026. This was a bounded, read-only inspection of the proposed protocol, client, controller, runner, tests, and selected formal statements. No broker, benchmark, test, proof compiler, or cluster command was executed by this review. Findings were sent to the implementing agent during the pilot preparation. This document is a review record, not a certification of future collected data.

The design addresses the main historical concerns in useful ways: each trial receives a fresh broker process and data directory, publication conditions share publisher counts and admission durations, recovery includes live unacknowledging consumers, and successful publication/drain observations receive a separate complete stored-payload readback. The following implementation and interpretation checks are needed before describing those properties as demonstrated.

## Review identity

Line references below refer to the source read at approximately **2026-09-24 21:13 UTC**, after several promptly reported findings had already been corrected. Concurrent implementation continued after this snapshot. Reconcile remaining findings against the final sealed inputs rather than treating this document as a review of every later revision.

| File | SHA-256 at review snapshot |
|---|---|
| `docs/FOLLOWUP_PROTOCOL.md` | `091c24626a6881faf3da653153ed05ef22ab0b3aaf9901dad590400f987125e0` |
| `bench/followup/main.go` | `b2c48bd57f6ce93860e9d5c6a9b1a642e9b3ae415765a323af144ebec42c0b05` |
| `bench/followup/client.go` | `f7c45864efff9a4e022b581be9b926a1b9842d300a3d95076990f350a7e47ee9` |
| `bench/followup/control.go` | `5239c0ed33dbbf7a06fb9c7a326d44c474c1de26c94f17d10ea9d16d43235a97` |
| `bench/followup/run.py` | `4830c2db307db49de70f6771497fb7796a413ac4d35789882fc6edc343bf8845` |
| `bench/followup/main_test.go` | `0460d4060a8a7e2bcc39fb71c3f153f1f7c725d54199146e179dcba8d3d2abe9` |
| `formal/DeliveryModel.lean` | `169fa4a50504ba59b34a3159bcdc0c1a1d89139c28a323856e4be40805928d03` |

## Findings corrected during review

Source inspection confirmed the following changes after the initial findings were reported. Their runtime behavior still requires the homelab validation receipts.

| Initial issue | Correction visible in the reviewed source |
|---|---|
| The survivor goroutine had no recorded request-start barrier. | `client.go:104-107,133-136` invokes a request hook; `main.go:543-602` waits for its first timestamp and records actual receipt age. A timestamp proves client invocation, not server arrival or an outstanding server pull. |
| Preload failures and failed receive requests could be absent from the per-request evidence; worker panics could bypass trial serialization. | `main.go:332-379` persists preload events and captures worker panics; `414-438` creates receive-attempt records before calls and retains errors. |
| A controller timeout lost its partial output and did not attempt artifact salvage. | `run.py:230-240` records `TimeoutExpired`, retains partial output, attempts salvage, and pauses without an automatic retry. |
| Redis readback could return success after reading fewer than the expected number of messages. | `client.go:284-288` returns an error when the count differs. |
| Setting Btrfs NOCOMPRESS could retain the mutually exclusive COMPRESS flag. | `control.go:67-69` clears COMPRESS before setting NOCOMPRESS while leaving unrelated flags untouched. This follows the [Btrfs attribute rules](https://btrfs.readthedocs.io/en/latest/ch-file-attributes.html). |
| JSON decoding could unnecessarily round integer monotonic timestamps through `float64`. | `main.go:127-130,527-530` uses `UseNumber`. |

## Resolution reread at 21:17 UTC

A further read of the working files confirmed additional corrections. The main source hash was `75e693fdc6001e0d55e154185e6f3c4c4c3190ff53bf043d3a87aea8cb4b90a7`, controller hash `e3441707865823c9f6d23935502f7e8e56457e08d48a92b317deef94855c84ba`, and runner hash `a25197cab6ac9ad9595fb3a238c2b7fe62ab4a803e15ab3aa758413db6d597f8`.

| Earlier finding | Status in this reread |
|---|---|
| Missing immutable current and tracer image pins | Corrected in source. `bench/followup/image-pins.json` includes them; the resource builder requires digest references and bootstrap reads the copied input mapping. The randomized plan and executed Python runner still need the prospective identity checks described below. |
| Unverified traced-process shutdown and reused listener | Corrected in source. The controller rejects a preexisting broker listener, waits for process-group disappearance, checks port closure, and retains the store if termination cannot be verified. Homelab validation remains necessary. |
| Failed-publication throughput represented as completed-workload throughput | Corrected in source. It is now retained only as `confirmed_prefix_throughput_mps` on returned publication failure. Final summaries must still require successful readback and reconciliation. |
| Timer-branch selection conflated with receipt timing | Substantially corrected. Separate timer-branch, receipt-after-deadline, shutdown-receipt, and message-absence fields now exist. Two remaining recovery control-flow issues are recorded immediately below. |
| Host-load record absent from the initial phase sample | Host `/proc/stat` and `/proc/loadavg` reads were added. Their interpretation and availability still need validation; container CPU accounting retains the scope described below. |

Two additional concrete recovery issues were sent promptly to the implementing agent:

1. At revised `main.go:590-594`, the first-request and result channels can both be ready after the parent goroutine is descheduled. Selecting the result branch then discards an actual early redelivery and calls it a failure before the first request, despite the request hook having run. Obtain the buffered first-request timestamp independently, then retain the result through the normal path. This is a preservation issue for unusual scheduling observations, not evidence that it occurred in a pilot.
2. At revised `main.go:651-658`, taking the timer branch can suppress a real survivor network/decoding error or panic. A negative control with no received message could then return success after a failed survivor operation. Retain the survivor error and distinguish the intentional stop sentinel from actual operation failures. A successful negative control requires a functioning observation procedure through its recorded endpoint.

The implementing agent reported that pilot01 used an earlier sealed snapshot and remains excluded. That report included normal-client successes, tracer packaging failures, and two startup failures. This source review did not independently validate those pilot records and does not promote those reported results to an experiment receipt.

## Implementation and evidence checks recorded at the initial snapshot

The resolution table above supersedes the corresponding initial-source findings below. Unresolved interpretation, provenance, recording-error, and validation checks remain applicable until separately addressed.

### 1. Bind every campaign to its actual images, plan, and controller

`run.py:145-147` falls back to tags when a digest is absent. At this snapshot, `k8s/image-pins.json` contained the two historical broker images and the Go image, but neither current broker image. The tracer init container also used an unpinned Alpine tag at line 139. This does not satisfy the protocol's promise that images are resolved before measurement.

Require digest entries for all executed images, retain pulled platform identities and actual server/tracer versions, and fail preparation when a required pin is missing. The input hash map at `154-167` covers the copied source and protocol; separately seal the randomized `plan.json`, image mapping, resource manifest, and the runner actually executing the campaign. `bootstrap` currently reads the working checkout's image mapping, and `run` executes the working checkout's Python runner. A frozen copy of that runner is not by itself evidence that it was the executed copy. A final manifest can establish byte consistency, but a prospective input seal is needed for the stronger premeasurement identity claim.

### 2. Verify broker quiescence before declaring storage reset complete

The exclusive directory creation and direct process launch at `control.go:102-164` implement a useful fresh-store procedure. However, stop handling at `178-191` waits for the direct child, which is the tracer in traced trials. Readiness at `165-170` accepts a TCP listener without checking the new process's version or ownership. The review found no evidence that an orphan actually occurred.

Before deleting the trial directory or starting the next broker, retain evidence that no live broker from that process group remains and that its broker port is closed. Check that the new process is alive and returns the expected broker identity at readiness. Strace documents possible surviving descendants when the tracer exits and offers `--kill-on-exit`; group-directed signals already reduce this risk, but do not replace an observed reset gate. [Strace manual](https://man7.org/linux/man-pages/man1/strace.1.html).

The storage inventory traversal and selected-file reads at `control.go:195-213` ignore some errors, and the driver ignores extracted-log write errors at `main.go:685-694`. Record and propagate these failures. A trial with missing required configuration, server log, trace, or compression-flag evidence must not be advertised as having complete diagnostic evidence merely because timing events were saved.

### 3. Describe CPU counters and trace windows at their actual scope

`control.go:40-52` reads the container cgroup, not only the broker process. Broker-side deltas include the controller and, for traced conditions, strace. The kernel defines `cpu.stat` usage as accounting for all processes in the cgroup and its descendants. Label these quantities **container CPU**, retain usage and throttling fields, and reject or explicitly mark missing counters. The current parser can return an empty map on an unavailable file. [Kernel cgroup v2 interface](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu-interface-files).

The before/after samples at `main.go:139-152` bracket the timed phase. They do not share exactly the request window endpoints. Report their own sample durations and the extra bracket time. This supports detecting client-capacity pressure, not isolating an implementation-independent server CPU requirement.

The driver and broker run on different nodes, so their `CLOCK_MONOTONIC` values cannot be directly compared. Strace `-ttt` produces broker wall-clock timestamps. Segment syscall observations using broker-side phase timestamps or explicit broker-side markers and disclose boundary uncertainty. Do not directly align driver monotonic request timestamps with broker wall time. CPU deltas taken between samples from the same container remain interpretable.

### 4. Keep failed-workload metrics separate and preserve collection failures

`main.go:288-311` computes publication throughput from confirmed requests through the last successful reply even when another request failed. In that case the denominator can omit the failed request's completion tail. Retaining the individual records is correct, but this number is not the cost of completing the failed workload. Omit it from successful-workload summaries or clearly define a separate failure-aware metric whose endpoint includes all admitted calls.

The revised timeout branch attempts salvage. The other unexpected-exit branch at `run.py:242-244` preserves controller output but does not salvage partial remote artifacts. Apply the same bounded salvage policy to unexpected exit and collection failures, and preserve a collection-stage receipt. Serialization after the workers join still does not protect buffered data against abrupt driver/host loss; the protocol already discloses that limit correctly.

### 5. Classify recovery from timestamps, not timer-selection order

`main.go:622-637` labels an observation censored, and any returned message a shutdown receipt, according to which `select` branch runs. Go can choose either branch when the timer and result channel are both ready. A message received before the nominal deadline can therefore be retrieved after the timer branch is selected. [Go select semantics](https://go.dev/ref/spec#Select_statements).

Retain timer-branch selection as an operational event, but derive before/after-deadline receipt status from the recorded receipt and deadline timestamps. Similarly, retain a pre-reference redelivery as an observed timing deviation, not a latency forced to zero or a silently discarded trial. The new first-request barrier and actual-age field are valuable; the barrier does not prove continuous server demand. The live condition means a live consumer that deliberately stops acknowledging, not a healthy application performing a representative processing workload.

### 6. Close the prospective protocol and validation gaps precisely

The diagnostic generator at `run.py:89-102` specifies one trial per diagnostic condition in each deployment. The protocol's phrase "repeated within each deployment" suggests more than one. State the actual number prospectively or generate the intended repetitions before collection.

At this snapshot, `main_test.go` verifies payload determinism, nearest-rank percentiles, and serialization of fabricated partial event records. Those tests do not exercise raw CLAIM parsing, returned-error and panic paths through the workers, short readback, recovery deadline races, or tracer reset. Add focused fixtures and homelab pilot assertions for these boundaries. The review did not execute them and does not count source presence as a passing test.

## Construct checks that passed source inspection

- **Matched publication path.** Both products use one synchronous client call per publisher, the same 512-byte payload, publisher counts, and admission budget. The ordinary successful-run denominator extends to the final confirmation. The deadline check precedes payload preparation at `main.go:252-255`, so describe it as an admission-loop budget; do not assert that every later network-call timestamp is strictly before the deadline without checking the retained trace. Closed-loop scheduling and client costs remain part of the measured system.
- **Payload identity.** The compressible payload is byte-compatible with the original binary-ID plus `x` filler representation in `bench/main.go:129-139`. The new readback at `client.go:211-288` checks unique IDs, exact counts, and every retained 512-byte payload outside timing. This establishes successful stored-data readback. Drain receipts check length and ID but do not compare every received byte during the timed path, so avoid claiming complete verification of every delivered payload.
- **Redis CLAIM reply.** `client.go:133-164` uses RESP2 raw-command decoding and expects the documented four-element claimed entry. This avoids the historical client's two-element typed decoder. The fixed one-key, one-field, count-one workload is consistent with the parser's assumptions. Add malformed/empty/four-field fixtures and retain the homelab successful response. The ignored idle and prior-delivery fields could provide useful corroboration but are not required to time the client receipt. [Current server reply specification](https://github.com/redis/redis/blob/498ecd0d6d007db11ddb3aea9428552598a78622/src/commands/xreadgroup.json#L134-L170), [historical client typed decoder](https://github.com/redis/go-redis/blob/ed37c33a9037483ad2a6b1042e5eb6df89009a1c/command.go#L1545-L1555).
- **Acknowledgment boundary.** Redis requires an XACK count of one; JetStream waits for AckSync. This is a matched confirmed-progress interface, not proof of equal durable consumer-state contracts. The current server's asynchronous consumer-state persistence remains relevant. The exact implementation distinction and version pins are documented in [the source review](FOLLOWUP_SOURCE_REVIEW.md).
- **Compression intervention.** The flag is applied to a new trial directory before broker-created files. Record actual descendant flags and distinguish inherited compression policy from demonstrated compressed extents. A policy sensitivity on the same Btrfs device is not a second-filesystem experiment.
- **Experimental scope.** Fresh broker-owned storage removes cross-trial AOF/store accumulation. Warm-up effects, shared-device history, host load, and cache state remain. Three recreated deployments on the same hardware support a stronger conditional comparison than one accumulated campaign, but do not establish independent-host uncertainty or storage-fault survival.

## Formal interpretation

The selected Lean residual-time identities, receipt-offset identity, occupancy lemma, and effect/acknowledgment counterexamples remain consistent with their stated abstract assumptions on source inspection. No new kernel compilation was performed here.

For the live control, use a **reference event** distinct from failure. The residual-time algebra itself does not require a process death, whereas the manuscript's original fault-model paragraph at `paper/main.tex:96-100` explicitly assumes one. Similar redelivery timing in live and killed cases would support timeout eligibility as the operative mechanism under the controlled workload, not prove universal absence of death-sensitive behavior.

The new Redis CLAIM arm does not contradict the plain-new-message-read counterexample at `paper/main.tex:128-135`: CLAIM is an additional reclamation policy. Likewise, current NATS synchronization-error handling differs from the historical pinned implementation, so the statement at `paper/main.tex:171` must remain explicitly historical when current-version observations are introduced. No publication timing, readback, CPU counter, or syscall trace establishes the stable-storage premises of the conditional durability proposition without a specified storage-fault experiment.

The appropriate release gate is a sealed final input snapshot, homelab validation of the corrected boundaries, and an independent analyzer that checks every planned outcome against retained records. This review supports those concrete checks and does not replace them.
