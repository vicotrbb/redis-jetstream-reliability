# Conditional delivery-model formalization

## Current verification status

The unchanged model was freshly compiled on the homelab at 2026-09-25T00:16:26.539308+00:00 for version 1.2.0, after all follow-up benchmark namespaces were cleaned up. All ten declarations passed with warnings treated as errors, using the same source, compiler binary and transitive logical dependencies as the original check. The receipt is `../revisions/20260924-followup/lean-recheck.json`; its log and cleanup receipt are alongside it.

The first disposable runner was temporarily unschedulable because its designated node requires a control-plane scheduling toleration. The first readiness wait expired before that correction. Its launch source, failure log, additive pod patch and separately identified continuation are retained. No compiler invocation began before the corrected pod became ready. The correction changed no proof or experimental observation, and the namespace was deleted after successful compilation.

## Historical initial verification

**Verified on the homelab with Lean 4.24.0**, at 2026-09-23T23:25:50Z, after benchmark collection ended. The command ran in namespace `msgrel-20260923`, pod `runner`, and exited zero with warnings treated as errors. See `verification.log` and `verification.json` for the version, container provenance, command, source and compiler hashes, and all ten transitive axiom reports. The exact checked source SHA-256 is `169fa4a50504ba59b34a3159bcdc0c1a1d89139c28a323856e4be40805928d03`. No Lean executable or broker workload was run on the workstation.

The first homelab check failed only because an unused hypothesis name triggered a warning treated as an error. Renaming that binder to `_hAgeNonnegative` preserved the mathematical assumption and resolved the warning; the initial output remains in `verification-first.log`. The successful statements use only standard Lean logical dependencies: `propext`, `Quot.sound`, and, for one algebraic equivalence, `Classical.choice`. The four finite-trace declarations have no axioms. No `sorryAx`, custom axiom, or native-evaluation dependency is present.

The checked target is **Lean 4.24.0**, pinned in `lean-toolchain`. The sole import is `Std`, shipped with Lean; there is no mathlib, Lake dependency, package download, external solver, or native-evaluation proof path. The file contains complete checked proof terms/scripts rather than placeholders. The target release is historical, not a latest-release claim. Its [official release record](https://lean-lang.org/doc/reference/latest/releases/v4.24.0/) identifies release date 2025-10-14.

## What is formalized

In version 1.2.0, the main article presents the short analytical model without numbered theorems. The labels in the mapping below refer to the complete hand proofs in `paper/supplement-model.tex`, compiled into the supplementary PDF. The main article's residual and occupancy equations retain the corresponding assumptions and scope.

| Declaration in `DeliveryModel.lean` | Mathematical statement | Manuscript mapping |
|---|---|---|
| `residual_decomposition` | `selection + observation - f = delta - (f-d) + (selection-(d+delta)) + observation` over integers | Algebra in the proof of `thm:recovery` |
| `residual_timeout_bound` | Given broker-age and bounded selection/observation premises, residual delay is positive and bounds failure-to-observation latency | Integer-time specialization of `thm:recovery` |
| `observed_receipt_offset` | Observed receipt-to-redelivery minus timeout equals later selection/observation overhead minus initial receipt offset | `cor:observed` |
| `observed_excess_negative_iff` | Observed excess is negative exactly when initial receipt offset exceeds later overhead | Algebraic explanation following `cor:observed` |
| `busy_sum_le_capacity`, `consumer_capacity` | If each consumer's total busy time is at most `T`, their summed busy time is at most `C*T` | Division-free summation step of `thm:concurrency` |
| `uninterrupted_orders` | Effect/ACK and ACK/effect each yield one effect in a crash-free trace | Clarifies that neither order is defined to fail unconditionally |
| `effect_before_ack_crash` | A finite effect, crash, restart, redelivery, effect, ACK trace completes two effects | First counterexample in `prop:effects` |
| `ack_before_effect_crash` | A finite ACK, crash, restart trace completes zero effects and disables redelivery | Second counterexample in `prop:effects` |
| `each_order_has_counterexample` | Each of the two separate-operation orders has its displayed legal execution with effect count unequal to one | Finite witness formulation of `prop:effects` |

Times in the first four declarations are `Int`, so subtraction has its usual signed meaning; time units may be interpreted as integer nanoseconds or other fixed ticks. The theorem has no rounding, server-clock synchronization, scheduler, or network model. `P` and `B` are actual bounds supplied as hypotheses. A configured polling sleep is not automatically a value satisfying `P`. The observed-offset algebra holds without sign assumptions; interpreting `u`, `w`, and `b` as nonnegative delays is a separate model assumption in the paper.

Capacity uses `List Nat`, with one total busy time per consumer. The theorem proves the sum bound for arbitrary list length. It **assumes** each total is bounded by the window length. The finite-window argument deriving that premise from nonoverlapping intervals contained in the window remains in the paper; the Python event analysis checks those conditions on the collected traces. This Lean file does not formalize real-number division, the identity `X = C*U/mean_R`, a rate comparison, or a statistical result.

The finite crash model explicitly retains both broker pending state and a durable external-effect counter across consumer crashes. A restart loses the local payload. An effect increments the counter, and a broker acknowledgment clears pending status. Redelivery is possible only for pending work and does not deduplicate effects. All invalid events produce `none`; a trace yielding `some state` therefore contains only enabled steps. ACK does not erase an already-held payload, allowing both operation orders to succeed without a crash. Transactions, durable application deduplication, idempotent effects, broker failure, and external-store failure are outside this model.

## What is not proved

There is no formal connection here between these definitions and Redis, NATS, Go, Linux, the harness, or measured data. The artifact does not verify implementation conformance, timeout liveness without bounds, infinite executions of Redis new-message reads, storage survival, the source-code persistence audit, exactly-once impossibility for all applications, bootstrap coverage, or universal performance rankings. The paper's storage-contract proposition and IID zero-event derivation remain explicit hand proofs. This is an optional formalization of selected conditional model statements.

## Reproduce the homelab verification

Execute only after benchmark collection ends, so toolchain installation and proof compilation cannot affect measurement conditions. `verify.sh` pins the official Linux Lean 4.24.0 archive and verifies its SHA-256 before extraction. It installs `zstd` only in the disposable runner container if missing. The initial network attempt encountered a DNS failure; the configured retry succeeded, and the archive checksum matched. The first log retains this history.

Copy this directory to `/work/formal` in the homelab runner, then execute:

```sh
kubectl --context homelab -n msgrel-20260923 exec runner -- sh /work/formal/verify.sh
```

Preserve the version output, stdout/stderr, exit status, compiler/container provenance, and SHA-256 of the exact source. Inspect every `#print axioms` result. Accept no `sorryAx`, custom logical axioms, or native-evaluation axioms. The file declares no axioms and uses kernel-checked `omega`, induction, simplification, definitional equality, and ordinary `decide`; the latter is distinct from native compiled evaluation. Successful checking establishes the displayed conditional theorems under Lean's trusted foundation, not that their premises hold in a production broker.

## Primary references

- Leonardo de Moura and Sebastian Ullrich, [The Lean 4 Theorem Prover and Programming Language](https://lean-lang.org/papers/lean4.pdf), CADE 28, 2021, pp. 625–635, [DOI](https://doi.org/10.1007/978-3-030-79876-5_37). BibTeX key: `demoura2021lean4`.
- [Official Lean 4.24.0 release record](https://lean-lang.org/doc/reference/latest/releases/v4.24.0/) and [tagged release](https://github.com/leanprover/lean4/releases/tag/v4.24.0). BibTeX key: `lean424release`.
- [Official Lean reference: axioms and transitive dependency inspection](https://lean-lang.org/doc/reference/latest/Axioms/). This mutable reference explains the checking/audit concepts; the executable version remains pinned above.

## Separate revision check

The unchanged source was separately recompiled in the homelab on 2026-09-24 in namespace `msgrel-rev20260924-a002`, using the same checksum-verified Lean 4.24.0 archive. All ten declarations passed with warnings treated as errors. The transitive axiom lists match the original receipt. See `../revisions/20260924/lean-recheck.json` and its log. No Lean execution occurred on the workstation. The historical reproduction command above names the original, deleted measurement namespace; for a fresh check, use a separately created homelab validation runner and its actual namespace.
