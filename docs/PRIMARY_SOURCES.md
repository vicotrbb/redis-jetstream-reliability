# Primary-source audit for the Redis Streams / NATS JetStream study

Verified on 2026-09-23. This document records documentation and source-code evidence, not experimental results. BibTeX keys refer to `paper/references.bib`. Performance measurements must come exclusively from the authorized homelab runs.

## 1. Version boundary and reproducible configurations

Two suitable, deliberately historical release pins are Redis **7.4.2** (released 2025-01-06) and NATS Server **2.10.24** (released 2024-12-17). They support the required consumer and persistence mechanisms. They are not described here as the newest, safest, or recommended production releases. Their release records are [Redis 7.4.2](https://github.com/redis/redis/releases/tag/7.4.2) and [NATS 2.10.24](https://github.com/nats-io/nats-server/releases/tag/v2.10.24) (`redis742release`, `nats21024release`). Record actual container digests and runtime version output separately.

The GitHub tag references resolved to these commits during this audit:

| Project/tag | Commit |
|---|---|
| `redis/redis`, `7.4.2` | `a0a6f23d997b024689ba157916837f493a593a34` |
| `nats-io/nats-server`, `v2.10.24` | `1d6f7eaf0bd966dd02c95b8d5f624868f1a62544` |
| `redis/go-redis`, `v9.7.0` | `ed37c33a9037483ad2a6b1042e5eb6df89009a1c` |
| `nats-io/nats.go`, `v1.39.1` | `4ba1afe8709b048ae89888f0f94da7eb8497e7ec` |

The proposed R1 storage matrix is:

| Experimental class | Redis 7.4.2 | NATS 2.10.24, one stream replica |
|---|---|---|
| Volatile | `save ""`, `appendonly no` | stream `storage=memory` |
| Periodic | `save ""`, `appendonly yes`, `appendfsync everysec` | stream `storage=file`; server `jetstream { sync_interval: 1s }` |
| Synchronous append | `save ""`, `appendonly yes`, `appendfsync always` | stream `storage=file`; server `jetstream { sync_interval: always }` |

These are matched policy classes, not a claim that both systems have identical failure semantics or I/O paths. `sync_interval: always` is **definitely supported by v2.10.24**: its parser explicitly recognizes `always` and sets `SyncAlways`. This audit does not establish which earlier release first introduced that value. See [pinned parser, lines 2188-2195](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/opts.go#L2188-L2195) (`nats21024opts`).

Redis's pinned configuration documents AOF modes and the `no-appendfsync-on-rewrite` exception. Keep that option `no`. If automatic AOF rewrite is disabled for a bounded experiment (`auto-aof-rewrite-percentage 0`), disclose this exclusion rather than implying production rewrite costs were measured. See [configuration, lines 1429-1499](https://github.com/redis/redis/blob/a0a6f23d997b024689ba157916837f493a593a34/redis.conf#L1429-L1499) (`redis742config`).

## 2. Redis delivery and reclamation

### Documented contract

With acknowledgment tracking enabled, `XREADGROUP` records delivered messages in a group's pending-entry list (PEL). `XREADGROUP ... STREAMS key >` fetches previously undelivered entries; reading a concrete ID accesses that consumer's own pending history. A consumer crash does not turn its pending entries into new entries. This motivates an explicit recovery algorithm. See [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/) (`redisxreadgroup`). `XACK` removes an ID from the PEL and does not itself delete its stream payload: [XACK](https://redis.io/docs/latest/commands/xack/) (`redisxack`).

Current Redis documentation includes mechanisms unavailable in the selected release: `XREADGROUP CLAIM` was added in 8.4 and `XNACK` in 8.8. They must not appear as available 7.4.2 behavior. The pinned stream implementation is the authority for the study.

`XAUTOCLAIM` provides cursor-based pending-entry reclamation. Its scan examines at most `10 * COUNT` PEL entries, may return fewer claims, returns a continuation cursor, and requires continued polling even after a scan returns `0-0`: entries can become eligible later. Claiming resets idle age. Entries whose stream payload was deleted are removed from the PEL; deletion is not successful delivery. See [XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/) (`redisxautoclaim`).

### Pinned implementation

In 7.4.2, `xautoclaimCommand` computes age from the command-time snapshot and the entry's last delivery time; it skips entries with age **less than** `minidle`. Therefore equality is eligible in this implementation, despite some documentation prose saying “more than.” It updates ownership, delivery time, and the delivery counter after a successful claim. The caller controls when commands run and whether the cursor eventually visits every pending entry. There is no standalone timeout-driven transfer implied by consumer disconnection. See [stream source, lines 3355–3500](https://github.com/redis/redis/blob/a0a6f23d997b024689ba157916837f493a593a34/src/t_stream.c#L3355-L3500) (`redis742stream`).

**Experimental implication:** state the reclamation interval, `COUNT`, initial cursor, cursor advancement, and interaction with blocking new-message reads. Without a live reclaimer and fair scan progress, finite message-redelivery latency is not guaranteed. “No reclamation” is a useful control, if included in the actual protocol.

## 3. JetStream delivery and acknowledgment

### Documented contract

Use a shared durable **pull consumer** with `AckExplicit`; several worker subscriptions should bind to that same consumer. `AckWait` runs from delivery and is overridden by `BackOff` if supplied. `MaxAckPending` applies to all bound subscriptions together, so its value is a shared concurrency control, not a per-worker limit. A pull consumer also needs outstanding pull demand to deliver an eligible message. Source: [official consumer documentation, pinned documentation revision](https://github.com/nats-io/nats.docs/blob/f115becf6563e3bbe16bb94cbf87bfceb84199c1/nats-concepts/jetstream/consumers.md) (`natsconsumers`). Avoid importing post-2.10 options from that newer document into the experiment.

### Pinned implementation

NATS 2.10.24 `checkPending` compares elapsed time with `AckWait` (or the applicable backoff), queues expired sequences for redelivery, and signals available messages. Expiry is not synchronous with worker death. Its initial timer helper adds a 1 ms `ackWaitDelay`; scheduling, queued work, and client demand can add delay. No unconditional wall-clock upper bound follows. `updateAcks` on a non-replicated consumer invokes its store and sends the acknowledgment response. See [consumer source, acknowledgment path](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/consumer.go#L2232-L2253), [timer helper](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/consumer.go#L2477-L2487), and [expiry processing](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/consumer.go#L4607-L4724) (`nats21024consumer`).

The measured Go client distinguishes `Ack()` from `AckSync()`: the latter calls `ackReply` with synchronous mode, which issues `nc.Request` and awaits the server response. This confirms server processing of the acknowledgment, not an atomic transaction with application effects. See [nats.go v1.39.1, lines 3449–3535](https://github.com/nats-io/nats.go/blob/4ba1afe8709b048ae89888f0f94da7eb8497e7ec/js.go#L3449-L3535) (`natsgo1391`).

For **`Fetch(1)`**, v1.39.1 sets `noWait=false`, so the normal path does **not** first send a nonblocking probe. However, it sets server request expiration to the remaining client timeout minus 10% (capped at five seconds). With `MaxWait(100 ms)`, demand therefore expires after approximately 90 ms. If a timeout status arrives with no message, the client keeps waiting until its own deadline. Repeated calls can consequently leave approximately 10 ms gaps in pull demand, plus scheduling/transport effects. This is a client policy, not the broker's `AckWait`. See [fetch code, lines 2986–3065](https://github.com/nats-io/nats.go/blob/4ba1afe8709b048ae89888f0f94da7eb8497e7ec/js.go#L2986-L3065) (`natsgo1391`).

The measured Redis client passes `XREADGROUP` count and block duration, `XACK` IDs, and `XAUTOCLAIM` idle threshold/cursor/count as explicit command arguments. Its wrapper does not add an automatic recovery policy to new-message reads. See [go-redis v9.7.0 stream commands, lines 236–339](https://github.com/redis/go-redis/blob/ed37c33a9037483ad2a6b1042e5eb6df89009a1c/stream_commands.go#L236-L339) (`goredis970`).

## 4. Persistence: precise claims and limits

Redis documents `appendfsync always` as flushing appended commands before their replies. It permits group commit: a batch of commands can share one write and fsync. Thus “one hardware fsync per message” is not an accurate universal description. Its documentation describes `everysec` as a performance/durability compromise with potential recent-data loss. Source: [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/) (`redispersistence`).

The 7.4.2 AOF implementation can postpone a write while an earlier background fsync is in progress, waiting up to two seconds before proceeding. `always` executes `redis_fsync` and exits on fsync failure; on Linux this operation is `fdatasync`. `everysec` schedules background fsync according to time and in-progress status. Consequently, a one-second configuration is not a proved universal one-second bound on acknowledgment-to-stable-storage latency or power-loss exposure. Source: [AOF code, lines 1082–1104](https://github.com/redis/redis/blob/a0a6f23d997b024689ba157916837f493a593a34/src/aof.c#L1082-L1104) and [lines 1222–1253](https://github.com/redis/redis/blob/a0a6f23d997b024689ba157916837f493a593a34/src/aof.c#L1222-L1253) (`redis742aof`).

For NATS 2.10.24, the filestore's default sync interval is **two minutes**, so `1s` is a deliberate nondefault setting. Stream blocks call `Sync()` in the always mode; this path does not check its return value. Other writes mark a later sync as needed. Consumer acknowledgment state is updated in memory and handed to an asynchronous flusher, whose code targets approximately ten writes per second under load. When that flusher writes, always mode uses `O_SYNC`; this is not a synchronous state-file write before every R1 acknowledgment reply. Distinguish **stream-append durability** from **consumer-state persistence**, and condition stable-storage implications on successful, honored synchronization. See [filestore default](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/filestore.go#L299-L307), [stream flush](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/filestore.go#L5951-L6024), [consumer flusher](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/filestore.go#L9078-L9132), [ack updates](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/filestore.go#L9223-L9303), and [optional synchronous write](https://github.com/nats-io/nats-server/blob/1d6f7eaf0bd966dd02c95b8d5f624868f1a62544/server/filestore.go#L10036-L10060) (`nats21024filestore`).

Official NATS documentation distinguishes process failure from OS/power failure and describes the trade-off of sync cadence. Replication alone does not establish synchronous stable-storage persistence. Source: [JetStream documentation, syncing to disk](https://github.com/nats-io/nats.docs/blob/f115becf6563e3bbe16bb94cbf87bfceb84199c1/nats-concepts/jetstream/README.md) (`natsjetstream`).

**Experimental implication:** killing a consumer leaves the broker and its page cache alive. Even a broker-process kill does not simulate power loss. Throughput/latency differences between configured modes establish measured costs in this environment; they do not establish the amount of data that would survive every storage fault. Observe and report actual configuration values, file storage, volume/mount properties, and host placement.

## 5. Formal grounding that is appropriate for this paper

The following are proposed arguments for an explicitly stated abstract model, not claims that the source code has been formally verified.

1. **Timeout origin.** Let the broker's last-delivery event be at `t_d`, consumer failure at `t_f >= t_d`, and configured inactivity threshold be `tau`. With no acknowledgment, renewal, negative acknowledgment, backoff change, competing claim, or clock discontinuity, eligibility begins at `t_d + tau`. The residual waiting time at failure is `max(0, tau - (t_f - t_d))`. Actual redelivery adds reclaimer/timer scheduling, queueing, pull availability, transport, and observation overhead. A bounded upper limit requires explicit bounds on these terms. The measured client receipt is later than the broker event by an unmeasured offset; substituting it for `t_d` without this term invalidates a strict observed lower bound. This is the study's own derivation from Sections 2–3.

2. **Processing–acknowledgment gap.** A non-idempotent application effect followed by broker acknowledgment admits a crash after the effect and before the acknowledgment; a later redelivery can repeat the effect. Acknowledging first instead admits a crash before the effect. An acknowledgment API alone closes neither gap. Application atomicity, durable deduplication, or an idempotent effect is an additional assumption. The foundational end-to-end paper explicitly discusses duplicate suppression and delivery acknowledgment: [Saltzer, Reed and Clark (1984)](https://web.mit.edu/saltzer/www/publications/endtoend/endtoend.pdf) (`saltzer1984`).

3. **Failure ambiguity.** RPC failures can leave the caller uncertain whether an operation executed; an at-least-once retry policy and an exactly-once application effect are different contracts. The classic implementation paper provides the relevant historical grounding: [Birrell and Nelson (1984)](https://www.cs.cornell.edu/courses/cs614/2004sp/papers/BN84.pdf) (`birrell1984`). Do not cite FLP as a proof that exactly-once application effects are universally impossible; that would be the wrong theorem.

4. **Zero observed failures.** If `n` genuinely independent, identically distributed Bernoulli trials yield no failures, the one-sided exact `1-alpha` upper confidence limit is `1-alpha^(1/n)`, obtained by solving `(1-p)^n=alpha`. This is not zero risk. The confidence-limit foundation is [Clopper and Pearson (1934)](https://doi.org/10.1093/biomet/26.4.404) (`clopper1934`); the displayed derivation is self-contained. Correlated messages within a fault episode must not be counted as independent trials merely to shrink the interval.

None of these arguments proves a universal Redis-versus-NATS performance ordering. Such an ordering is an empirical result conditional on the measured workloads, versions, client implementation, storage, and testbed.

## 6. Evaluation methodology references

| Primary source | What it supports | Application to this study |
|---|---|---|
| [Kalibera and Jones, ISMM 2013](https://kar.kent.ac.uk/33611/) (`kalibera2013`) | Repeated measurements, uncertainty, and variation at different experimental levels | Treat independently repeated runs/blocks as the replication units; distinguish within-run message percentiles from uncertainty across runs. Report effect estimates and intervals. |
| [Mytkowicz et al., ASPLOS 2009](https://research.ibm.com/publications/producing-wrong-data-without-doing-anything-obviously-wrong) (`mytkowicz2009`) | Innocuous setup choices can bias performance conclusions; randomization and causal analysis address bias | Randomize configuration order within blocks, record placement and shared-system activity, and avoid attributing every observed difference to broker architecture. |
| [Schroeder, Wierman and Harchol-Balter, NSDI 2006](https://www.usenix.org/conference/nsdi-06/open-versus-closed-cautionary-tale) (`schroeder2006`) | Open and closed workload generators can produce materially different behavior | Declare whether each workload is preloaded, closed loop, or open loop. A drain experiment is not a production arrival-latency distribution. |
| [Tene, wrk2 repository](https://github.com/giltene/wrk2) (`wrk2`) | Constant-throughput generation and measuring from intended start time to avoid coordinated omission | For an open-loop workload, record scheduled arrival, actual publish start, acknowledgment, and completion; generator delay belongs in scheduled-arrival latency. |
| [HdrHistogram project](https://github.com/HdrHistogram/HdrHistogram) (`hdrhistogram`) | Coordinated-omission correction depends on a known expected sampling interval | Do not relabel ordinary closed-loop latency as corrected. Any synthetic correction must be stated and justified; direct scheduled-time measurements are preferable when available. |

These sources motivate design choices; citing them does not certify that a particular harness implements those choices. Confidence intervals also do not remove systematic confounding, and a small run count limits precision regardless of the number of messages inside each run.

## 7. Related work and novelty boundaries

| Work and verified status | Relevant scope | Safe distinction |
|---|---|---|
| [Lim, Gu and Yoon (2026), JKIIT 24(8), 159–169](https://kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003370234) (`lim2026`) | The official English abstract explicitly evaluates RabbitMQ, Kafka, Redis Streams, and NATS JetStream under KEDA burst, sustained, and decreasing workloads. Metadata and abstract verified; full text was not obtained in this audit. | Direct overlap in systems, but the stated research focus is autoscaling reaction/resource behavior. Do not claim the first comparison of Redis Streams and JetStream. Do not invent their detailed settings or numerical results. |
| [Paul et al. (2026), arXiv:2603.21600v1](https://arxiv.org/html/2603.21600v1) (`paul2026`) | An original eight-broker performance study with an available harness; Redis uses Pub/Sub and NATS uses Core NATS. The inspected record is a preprint; peer-reviewed publication was not verified. | Relevant to broker benchmarking and concurrency; its Redis/NATS measurements are not measurements of Streams/JetStream consumer-recovery semantics. |
| [Coenen et al. (2019), DEBS poster](https://arxiv.org/abs/2010.15534) (`coenen2019`) | A two-page accepted poster describing financial-feed requirements and the `wrench` workload/replay benchmark tool. | Supports realistic workload/reproducibility motivation, not a validated direct comparison of the two pinned products in this paper. The paper year is 2019 although the author manuscript was deposited in 2020. |
| [Kingsbury (2025), Jepsen NATS 2.12.1](https://jepsen.io/analyses/nats-2.12.1) (`kingsbury2025`) | Original fault-injection study with reproducible tests, including simulated power failures, corruption, partitions, and replicated streams. This is a technical report, not a peer-reviewed paper. | Motivates separating acknowledgment from stable storage and distinguishes stronger faults from consumer death. Its findings do not constitute tests of this study's R1 2.10.24 deployment. |

An appropriate contribution statement is a **reproducible, scoped comparison of consumer-failure recovery, consumer concurrency, and the measured cost of explicitly configured persistence policies on one documented homelab**. Establish any stronger novelty through a systematic literature review rather than an assertion.

## 8. Bibliographic verification and evidence limits

DOI metadata for Kalibera–Jones, Mytkowicz et al., Saltzer et al., Birrell–Nelson, Coenen et al., and Clopper–Pearson was checked against Crossref. USENIX supplied the NSDI citation. KCI supplied the English author/title/venue metadata for Lim et al.; no DOI was supplied, so none was invented. The Clopper–Pearson publisher page exposed metadata but full text was paywalled. The Kalibera–Jones institutional record and indexed manuscript were inspected; the repository labels its manuscript as correcting the ISMM version. These access distinctions do not affect the original algebraic derivation above, but should not be represented as a full-text systematic review.

Documentation is mutable; the source-code citations pin exact server commits and the NATS documentation citations pin revision `f115becf6563e3bbe16bb94cbf87bfceb84199c1`. Redis live command documentation was cross-checked against 7.4.2 source. No benchmark, broker deployment, or failure injection was run as part of this source-audit subtask.

## 9. Read-only protocol/harness review

The review inspected `docs/PROTOCOL.md`, `bench/main.go`, and `bench/durability.go`; it did not modify or execute the harness. The protocol's one group/shared durable, one outstanding fetch and confirmed acknowledgment per worker, retained payloads, monotonic client timing, and separate closed-loop publication phase agree with the code.

The following points must stay explicit in the paper:

- Client-observed receipt time is not the broker's pending-entry timestamp. The formal timing model and observations need the offset described in Section 5.
- Redis's 10/100 ms setting is a sleep **after** a claim reply, so elapsed command time and scheduling add to the polling cycle. With one pending message, restarting the scan at `0-0` visits the entire relevant PEL; this does not establish fairness for arbitrary large PELs.
- NATS's nominal 100 ms `Fetch` refresh can leave the demand gaps described in Section 3. It is not an uninterrupted pending pull.
- Drain throughput uses the last acknowledgment timestamp, correctly excluding trailing empty worker-fetch timeouts. Its latency from the common drain start is backlog position/completion latency, not steady-arrival request latency.
- The timed publication series stops admitting requests after five seconds and waits for admitted requests to finish. Its throughput denominator extends to the last acknowledgment, including that completion tail. Stored count and generated-ID count are checked; publication-only trials do not read back every payload identity. Per-ID delivery-integrity claims should rely on the drained and recovery trials.
- Warm-up runs use a separate stream that is deleted. They warm shared execution paths and caches, not all of the measured stream's per-stream allocation/sync state. Describe bounded append measurements without asserting established steady state.
- Unexpected failures abort the campaign; successful per-message CSVs are written only after integrity checks. A failed trial's partial event array is not saved. Preserve process/job logs and do not claim complete per-message traces of every failed or censored attempt if those traces do not exist.

No critical correctness defect requiring a benchmark rerun was identified by this read-only review. This conclusion is a source review, not an execution receipt or a claim that unobserved workload conditions were validated.

## 10. Optional abstract-model formalization

The optional `formal/DeliveryModel.lean` targets Lean 4.24.0 with only `import Std`. It contains intended proofs of the integer residual-time bound and receipt-offset identity, the sum of bounded consumer busy times, and explicit finite effect/ACK crash counterexamples. Source preparation is not a compiler-verification receipt: checking is deferred to the homelab after measurement collection. The `formal/README.md` maps each statement to the manuscript and lists the model boundaries, including the absence of any formal refinement from broker code or measured timestamps.

The [official Lean 4.24.0 release record](https://lean-lang.org/doc/reference/latest/releases/v4.24.0/) verifies the selected release and its 2025-10-14 date (`lean424release`). The [Lean project's citation page](https://lean-lang.org/lean4/doc) supplies the primary bibliographic metadata for de Moura and Ullrich's [CADE 28 system paper](https://lean-lang.org/papers/lean4.pdf), 2021, pp. 625–635, DOI [10.1007/978-3-030-79876-5_37](https://doi.org/10.1007/978-3-030-79876-5_37) (`demoura2021lean4`). The paper describes the theorem prover and proof-term approach; it is not evidence that this study's newly prepared module has compiled. The [official axiom reference](https://lean-lang.org/doc/reference/latest/Axioms/) explains transitive `#print axioms` inspection and the distinction between ordinary checking and native-evaluation proof dependencies.

## 11. Post-collection verification update

After this source audit, the study owner ran Lean 4.24.0 inside the homelab runner, after all broker measurements ended. The final invocation passed with warnings treated as errors. `formal/verification.log` and `formal/verification.json` supersede the earlier preparation-only status in Section 10; the stated proof boundaries remain unchanged. The final abstract, result interpretations, and conclusion received a separate read-only numerical/scope audit, with no material error found. These are internal AI-assisted checks, not external peer review.

## Revision source check (2026-09-24)

The blocking-read timeout correction, corrected pinned line anchors, complete Lim HTML comparison, and reference revalidation are documented in [SOURCE_REVALIDATION.md](SOURCE_REVALIDATION.md). The earlier abstract-only limitation for Lim is superseded by that full-text inspection.
