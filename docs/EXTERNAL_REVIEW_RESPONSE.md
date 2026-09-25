# Response to the supplied AI-assisted audit

The supplied review recommended fresh storage, synchronization tracing, CPU sensitivity, current server releases, a broader literature foundation, and a shorter analytical presentation. It is an AI-assisted audit, not a journal referee report or independent experimental replication. The original audit text remains in the conversation attachment; this file records the study's response without attributing peer-review status to it.

## Experimental changes

| Review concern | Revision | Evidence and scope |
|---|---|---|
| Accumulated Redis AOF versus deleted JetStream stores | Every follow-up trial starts a new broker process and exclusive store, with the same warm-up procedure. Three separately provisioned campaigns use matched 15-second publication budgets at 1/16 publishers. | `docs/FOLLOWUP_PROTOCOL.md`, campaign input snapshots, per-trial reset records and raw outcomes. This removes cross-trial broker-file accumulation, not shared-host/device history. The original dataset is unchanged. |
| Unexplained always-mode behavior | Current always profiles have matched traced/untraced trials, capturing both fsync and fdatasync across threads with phase boundaries. | All trace files, call durations, failures, boundary overlaps and perturbation ratios are retained. Traces do not establish which filesystem or device mechanism dominates. |
| Possible driver CPU constraint | Current memory/periodic drain tests cross C=1/16 with 2/4 driver CPUs and matching GOMAXPROCS. Phase-specific cgroup and host counters bracket the work. | 65536-message workloads, driver/broker CPU, throttling and sample durations. This tests the measured client path; it does not establish a broker-capacity ceiling. |
| Historical release choice and Redis CLAIM | Historical releases remain identified as such; Redis 8.10.2 and NATS 2.15.0 are added. Current Redis CLAIM is a separate recovery arm beside common-policy XAUTOCLAIM. | Pinned images, runtime versions, source commits and raw four-field CLAIM decoding. Plain reads without CLAIM still do not reclaim other consumers' pending entries. |
| RQ1 mostly follows the residual-time identity | The recovery comparison adds live, deliberately unacknowledging victims matched to killed victims, actual receipt ages, first-request evidence and exact observation endpoints. | All 240 active episodes and 12 plain-read controls completed across the three deployments. The tested mechanism remains one pending message with available survivor demand, not loaded or large-PEL recovery. |
| Compression may matter | Current always profiles cross filler/pseudorandom-template payloads with inherited/disabled Btrfs compression policy. | Directory and actual file flags are verified. This is a policy comparison on one filesystem/device, not a second-filesystem test or a measured extent-compression ratio. |

## Interpretation and presentation

The acknowledgment-contract distinction is now prominent in the introduction, abstract, model, discussion and conclusion. Pinned sources support a difference between synchronized stream append and per-acknowledgment consumer-state persistence. They do **not** establish that this distinction quantitatively explains the entire historical throughput gap. The review's causal wording was therefore not adopted.

The proposed statement that Btrfs with zstd is the dominant cause was also not adopted. The diagnostics can reveal call behavior and compression-policy sensitivity, but dominance relative to device, shared load, runtime and protocol costs requires controls absent from this study. We report observed patterns and the limits of attribution.

The main model is shortened to its useful identities, assumptions and counterexamples. In version 1.2.0, complete numbered hand proofs remained in the supplement; the unchanged selected Lean model receives a fresh homelab compilation after the new measurements. These proofs constrain interpretation rather than certify either implementation.

Related work now includes the Kafka/RabbitMQ comparison by Dobbelaere and Esmaili, SPECjms2007 methodology, the pinned OpenMessaging Benchmark drivers, MillWheel and Kafka transaction semantics, alongside the earlier related studies. The review and bibliography explicitly distinguish workloads and guarantees and avoid an exhaustive-novelty claim.

Version 1.2.0 moved detailed historical failure accounting, interruption diagnostics, sparse-tail information and full proofs to supplementary material. The original section order, typography and author identity are preserved. The new article integrates the follow-up outcomes rather than merely adding disclaimers to the old estimates.

## Evidence and release boundary

Every planned primary outcome remains represented. Returned-error and caught-panic observations distinguish confirmations from unknown outcomes. Development pilots, failed setup attempts, superseded unexecuted plans and failed primary trials stay visible. Historical D038 client traces and exact original censor endpoints cannot be recovered and are not imputed.

The follow-up analysis independently reconstructs event metrics, paired completed-block contrasts, CPU deltas, syscall summaries and outcome counts. A separate standard-library checker recalculates the summary and pairing arithmetic. Campaign ranges are descriptive; neither three shared-hardware deployments nor numerous messages establish independent-host confidence coverage.

The current validation narrative is [FINAL_REVISION_VALIDATION.md](FINAL_REVISION_VALIDATION.md). It records actual collection, proof, analysis, document-review and cleanup results. That experimental revision was released as version 1.2.0; version 1.1.0 remains unchanged. Public GitHub hosting, content verification, DOI-bearing archival deposit and scientific peer review remain separate states.

## Subsequent reporting audit and integrated article, version 1.3.0

The later supplied audit recommended a short reporting revision. Its principal recommendations were adopted after checking the retained trial table and selected raw event traces. Ten of 72 planned always-profile publication attempts failed (13.9%): four during warm-up and six during timing. Periodic profiles had one timed failure in 72 attempts; memory profiles had none in 72. The seven timed failures contain 22 unknown requests, with recorded waits of 5.000 to 5.002 seconds. A timeout does not identify broker completion, and warm-up failures are not fifteen-second measurement windows.

The audit described five completed trials with maxima above two seconds. Recalculation finds four, with maxima from 2.297 to 4.183 seconds; the next largest is 1.969 seconds. The article reports all seven completed primary trials with a maximum of at least one second, labels this a post-observation descriptive selection, and retains every observation in the primary summaries. It does not adopt the suggested one-in-five-window frequency. The trace diagnostics' largest synchronization call was 544.563 ms; those separate samples do not establish the cause of the untraced multi-second events.

The article now explicitly connects JetStream's one synchronization call per confirmation at both publisher counts to the pinned serialized single-stream append path. Redis's concurrent aggregate corresponds to approximately 8.3 confirmations per synchronization call. This is source-consistent mechanism evidence, not a complete causal decomposition or a mapping of individual confirmations to calls. Memory/periodic current/historical ratio means range from 0.9603 to 1.0232, with deployment ratios from 0.9401 to 1.1237. These are descriptive comparisons, not version equivalence tests.

At the author's request, version 1.3.0 places every supplementary section, table, figure and full mathematical argument inside the article appendices. There is one current reader-facing PDF. The original title, authorship, typography and main section order are preserved. The integration check compares retained contents with the archived version 1.2.0 documents; neither experimental observations nor the Lean source changed. The public raw-data/code artifact remains available separately for computational reproduction. No new benchmark or proof execution was needed for this document revision.
