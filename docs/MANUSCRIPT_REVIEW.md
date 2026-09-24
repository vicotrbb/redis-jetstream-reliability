# Independent academic and source review

Historical review on 2026-09-23. Scope: the then-current `paper/main.tex`, `paper/references.bib`, prospective protocol, execution/deviation log, relevant Go measurement paths, and the analysis script. This is a source and mathematical review; it ran no benchmark, fault injection, or broker operation. At that checkpoint the draft's empirical results, abstract, and conclusion were awaiting complete collection and were outside this review's completeness assessment. Later validation is recorded in [FINAL_REVISION_VALIDATION.md](FINAL_REVISION_VALIDATION.md).

Review baseline SHA-256:

| File | Digest |
|---|---|
| `paper/main.tex` | `eb1422f86873ffe7654da6ff257fe57ae259075d9f5484f0ea953cb64f2a8e76` |
| `docs/PROTOCOL.md` | `eab81dece0c2fec9bd4ec6f1e77ff5da12ddcf200ee20d59249837f627d378f5` |
| `docs/DEVIATIONS.md` | `ac90fa134d477562b30ecd1838d3e7f0901dfcca1e2926f70847ced69c6cdf3b` |
| `bench/analyze.py` | `a0c96a5f2a9810195434b54acfcba592d65ee19c7ca490e85f632803356bc62c` |

Line references below refer to this baseline and may move after revision.

## Findings requiring correction before delivery

### R1 ;  Incorrect necessary condition for linear throughput scaling

**Priority: P1. Location: `paper/main.tex:154`.** The sentence “Linear scaling therefore requires both approximately stable cycle cost and approximately stable occupancy” does not follow from the correct preceding identity. Linear scaling requires the ratio `U(C) / mean_R(C)` to remain approximately constant. Both numerator and denominator can vary proportionally while throughput scales linearly. Stable occupancy and stable cycle cost are sufficient, not individually necessary.

Replace that sentence with:

> Approximately stable cycle cost and occupancy are sufficient for approximately linear scaling. More generally, linear scaling requires the ratio \(U(C)/\overline R(C)\) to remain approximately constant; increasing \(C\) alone does not prove it.

The occupancy theorem, its proof, its ratio identity, and the following nonmonotonicity counterexample are otherwise valid under their stated assumptions. This is a prose correction; it does not require new measurements.

### R2 ;  Serial-publication sensitivity does not isolate publisher count

**Priority: P2. Location: `paper/main.tex:250`.** The claim that the serial series “exposes the effect of outstanding-publication count” suggests attribution to one changed factor. The comparison also changes fixed duration to fixed message count, total work, and exposure to periodic synchronization. The later discussion and appendix correctly acknowledge this limitation, but they do not repair the earlier causal wording.

Replace the relevant sentence with:

> It provides a separate one-publisher workload sensitivity; differences cannot be attributed solely to publisher count because duration and total workload also differ.

No rerun is required if this remains a separate descriptive sensitivity experiment. Do not interpret the W1/W16 contrast as a controlled estimate of batching or publisher-count effects.

### R3 ;  Raw-event validation does not yet cover all reported metrics

**Priority: P2. Locations: `paper/main.tex:304`; `bench/analyze.py:1`, `51–55`, and `63–109`.** The manuscript says analysis recomputes percentile values, throughputs, and occupancy from collected files; the script's docstring makes the stronger claim that every reported statistic is recomputed from raw events. Several reported measures are still taken from unverified summary fields. `verify_events` checks publication and cycle quantiles, but does not independently verify `drain_mps`, `cycle_ms.mean`, `ack_ms.p99`, or `drain_delivery_ms.p99`. Its occupancy calculation uses summary `drain_mps`. Publication throughput is reconstructed from summary interval endpoints without checking that the end is the maximum raw publication-confirmation timestamp.

Recommended analysis-only repair, using integer nanosecond timestamps before conversion:

- Verify `publish_end_ns` (or timed-series `end_ns`) equals `max(publish_ack_ns)`, and every publication starts within the appropriate measurement interval.
- Compute drain duration as `max(consumer_ack_ns) - drain_start_ns`, and verify `drain_mps = N * 1e9 / duration_ns`.
- Compute cycle values from `consumer_ack_ns - request_start_ns` and verify their arithmetic mean as well as their reported quantiles.
- Compute acknowledgment values from `consumer_ack_ns - delivery_ns` and drain-delay values from `delivery_ns - drain_start_ns`; verify every reported percentile.
- Compute occupancy directly as `sum(consumer_ack_ns - request_start_ns) / (C * duration_ns)`, retaining the per-worker nonoverlap checks.
- Verify recovery `delivery_to_redelivery_ms` from `redelivery_ns - delivery_ns`, as already done for failure-to-redelivery latency. Verify the recorded JetStream delivery count against two in analysis as well as in the harness.

Then regenerate tables, figures, and confidence intervals from the checked values. These changes require reanalysis of retained files, not recollection. The existing paired bootstrap resamples the same block indices in both conditions and correctly computes a ratio of resampled means.

## Required final-integration disclosures

### The observed setup failure and checkpoint resume

The known interruption is already recorded appropriately in `docs/DEVIATIONS.md`; it should also appear in the main methods or limitations text. The first 51 completed timed trials remain valid observations. Tmain052 failed during stream creation before either timed phase, so it must not be converted into a publication-latency sample or a message-loss observation. Its original error record and logs must remain in the artifact.

Suggested paragraph, preserving the actual evidence boundary:

> Main collection paused after 51 completed trials when Tmain052 reached a five-second client deadline during stream creation, before publication or drain timing began. The NATS log recorded the stream-create request taking 8.0186 seconds; the underlying cause was not established. We retained the original logs and completed trials, added append-only checkpoint/resume handling without changing the timed paths or workload, retried that condition under a fresh stream name, and continued the original deterministic schedule. Performance tables therefore condition on successful trial initialization and do not estimate stream-creation availability.

The reviewed resume loop rebuilds the original seeded block ordering before skipping completed trials and records retry keys separately. No schedule-changing defect was found in that path. If later incidents occur, disclose those actual incidents separately rather than extending this explanation speculatively.

### RQ1 references and censoring

The generated recovery table currently includes `Delta * (1 - alpha)`, and the plot marks that value. In the final caption or discussion, call it a **nominal client-receipt-based reference**, not an established lower bound for the measured sample. The actual theorem uses broker age `h = f - d`; the controller instead schedules the kill from client receipt, and the kill-call timestamp is an estimate bracketed by observed process exit. The existing corollary correctly represents the initial delivery-to-receipt offset.

The analysis presently asserts that every active-reclamation trial completed. If the actual collected data satisfy that assertion, report all 120 successes and the ten deliberately censored no-reclaim controls. If an active-reclamation trial is censored, preserve it and adapt the analysis to report that actual outcome; do not delete it or treat its observation-window endpoint as an exact recovery time. This is an integration condition, not a claim that such censoring occurred.

## Recommended precision improvements

1. **Confidence-interval estimand (`main.tex:254`).** “Intervals describe repeated-run variation” can be mistaken for a prediction interval covering 95% of individual future runs. Prefer: “These nominal 95% bootstrap confidence intervals summarize uncertainty in the condition mean across the ten measured blocks, under the resampling assumption that blocks are exchangeable. They are not prediction intervals for individual runs or population-wide hardware guarantees.” The existing threats discussion already identifies small-sample, skew, and serial-dependence limitations. Exact 95% finite-sample coverage is not proved by percentile bootstrapping.

2. **Formal versus verified recovery assumptions (`main.tex:92`).** The observed kill age is controlled relative to client receipt; the broker event and hence exact `h < Delta` are unobserved. Say these are assumptions of the isolated formal model, rather than implying every timing assumption was directly verified by the experiment. A sentence can explain that nominal ages were selected below the timeout, with the unobserved receipt offset accounted for in the observation model. Also make clear that idealized continuous-time eligibility abstracts from broker timer quantization and requires no relevant clock discontinuity; the manuscript's measurement-validity paragraph already recognizes quantization.

3. **Nonzero denominators (`main.tex:134–142`).** State `N > 0`, `T > 0`, and integer `C >= 1` when defining the finite-window model. These conditions are satisfied by the intended workloads but make the division assumptions explicit.

4. **Synchronization-stage service bound (`main.tex:167`).** Specify that each confirmation group is associated with one completed synchronization operation and consider `F > 0`; otherwise the relationship between the two counts is implicit. The bound is an explanatory abstract service bound, not a measured device-flush result.

5. **Prospective protocol wording.** `PROTOCOL.md:13` still says “synchronization requested on each operation” and “bounded steady-state path,” while the source audit and manuscript correctly recognize group commit, asynchronous JetStream consumer-state persistence, and unproved stationarity. Preserve the historical prospective document. Append a clarification to the deviation log or final protocol notes that the paper uses “synchronous append policy” and “bounded append workload,” with the source-derived caveats, instead of silently rewriting the historical registration claim.

## Proof and source conclusions

- The residual-time theorem is algebraically valid under its explicitly bounded selection and observation assumptions. It proves a conditional model statement, not a universal implementation latency guarantee.
- The client-observation corollary correctly explains why receipt-to-redelivery minus timeout can be negative without refuting broker eligibility.
- The Redis new-message-read-only infinite execution is a valid liveness counterexample for the pinned release and stated policy. Finite negative controls illustrate it but do not themselves prove an infinite behavior.
- The occupancy inequality and identity are valid for finite, nonoverlapping, contained consumer intervals. R1 above repairs the only identified invalid inference from that identity.
- The stable-storage proposition correctly conditions on successful, honored synchronization, preservation, required metadata, and correct recovery. It does not certify that either implementation satisfies those assumptions under all faults.
- The effect/acknowledgment ordering counterexamples are valid in the separate non-idempotent-effect model. The text appropriately avoids claiming exactly-once effects are impossible with transactions or durable deduplication.
- The zero-failure confidence-limit formula is correct for IID Bernoulli trials; the text correctly declines to treat correlated message completions as independent fault trials.
- Source support is appropriate for the stated Redis and NATS versions. In particular, the paper retains the NATS R1 asynchronous consumer-state caveat, pinned `Fetch(1)` demand-gap behavior, and the distinction between confirmation and power-loss survival.
- The 27 citation keys used by this draft resolve to the 28-entry verified bibliography. No invented reference or missing citation key was found. The related-work section correctly qualifies the KCI abstract-only access, the preprint, and the Jepsen technical report. It makes no unsupported first-comparison novelty claim.

No critical timed-path defect requiring a benchmark rerun was identified in this review. Delivery should wait for R1–R3 corrections, complete empirical data and generated results, the observed-incident disclosure, and final manuscript/render verification. This review does not guarantee acceptance by a venue or substitute for independent replication or external peer review.
