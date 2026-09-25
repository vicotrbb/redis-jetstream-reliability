# Controlled follow-up protocol

Prepared before collection on 24 September 2026. This is a new, prospectively specified follow-up to the published version 1.1.0 case study, not a retrospective registration of the original campaign. The original raw evidence and release remain unchanged. Pilot observations test this protocol and are excluded from its reported measurements. Any subsequent change must be recorded before the affected measurements.

## Questions and estimands

1. Does residual timeout predict redelivery under both killed and still-live unacknowledging consumers, including Redis's current `XREADGROUP CLAIM` path? Compare receipt-based timer excess and reference-event-to-redelivery latency, with the delivery-to-receipt offset explicitly unobserved.
2. Does increasing driver CPU availability alter measured C=1 versus C=16 drain throughput in the high-throughput memory and periodic profiles? Compare 2 and 4 CPU limits with matching `GOMAXPROCS`, using phase-specific driver and broker CPU counters. This evaluates this client path; it does not isolate an implementation-independent broker capacity.
3. What confirmed-publication costs occur from a defined fresh storage starting state, at matched publisher counts and admission durations? Compare memory, periodic and always policies within each engine and version. Source-derived differences in consumer-state persistence remain separate from performance attribution.

## Environment and versions

Every broker execution, runtime test, tracer, and proof compiler runs only through `kubectl --context homelab`. Broker placement is homelab-01; the driver is on homelab-02. Other namespaces and services are untouched. Only one follow-up broker is actively driven at a time. Shared-host load is recorded and remains an external-validity boundary.

The historical versions are Redis 7.4.2 and NATS Server 2.10.24. Current stable versions verified against official releases are Redis 8.10.2 and NATS Server 2.15.0. Images are resolved to digests before measurement. The same Go client versions as the original artifact are retained to avoid changing broker and client versions together. Redis CLAIM uses an explicitly parsed raw command because its extended reply differs from the older client's typed decoder. The NATS asynchronous stream persistence mode is not enabled.

Each broker has two CPUs and 1 GiB RAM. Driver limits are two or four CPUs with 2 GiB RAM, and the corresponding Go runtime setting. Network transport, single-replica scope, and 512-byte payload size follow the original study. Core comparisons use the original highly compressible payload. A payload/compression sensitivity is specified separately.

## Storage reset and warm-up

Every trial starts a new broker process in a newly created, exclusively named data directory. There is no retained AOF or JetStream store from another trial. The controller records start, readiness, stop, cleanup, effective configuration, image identity, filesystem observations and server logs. A warm-up uses 256 messages on a separate stream, acknowledges them, removes that stream, then waits one second. Thus the defined starting state includes the same stated warm-up operation, whose physical effects can differ by engine. Redis automatic AOF rewriting remains disabled within the bounded trial.

Fresh directories do not reset the underlying device, operating-system caches, temperature, free-space layout, or unrelated load. The estimand is the configured system's performance from this starting procedure, not an isolated hardware fsync cost or steady-state production behavior. Recreating deployments provides campaign replication on the same hardware, not independent-host replication.

## Primary matrix and ordering

Three separately provisioned deployment campaigns use distinct namespaces, input hashes, raw directories and random seeds. Within each campaign:

- Publication: two engines, historical/current versions, three policies, and 1/16 publishers, in three randomized complete blocks. Each trial admits requests for 15 seconds and includes the completion tail in the throughput denominator. There is one outstanding request per publisher.
- Driver-capacity sensitivity: current versions, two engines, memory/periodic policies, C=1/16 consumers, and 2/4 driver CPUs, in two randomized complete blocks. Every trial preloads and drains 65,536 messages. Preload and consumption have separate counters and timestamps.
- Recovery: historical/current JetStream, historical/current Redis XAUTOCLAIM with 10 ms sleep, and current Redis CLAIM; thresholds 250/1000 ms, receipt-based ages 10%/75%, killed/live-unacknowledging victims, and two randomized repetitions. Survivors begin requesting before the reference event. Redis new-message-only negative controls use both versions and a nominal two-threshold observation budget. Exact observation endpoints and any shutdown receipt are retained.

Publication and drain trials retain all per-request timestamps, application identifiers, completion states, worker identities, and count reconciliation. Complete payload readback or digest verification occurs outside the timed path. A failed request is retained as an unknown outcome unless a later readback resolves its stored identity. Client confirmation and stored presence remain distinct facts. Failed attempts are never silently replaced or assigned fabricated throughput.

## Mechanism diagnostics

Current-version always profiles receive matched 1/16-publisher, 15-second trials with and without tracing of both `fsync` and `fdatasync`, repeated within each deployment. Tracing is diagnostic and its overhead is measured by the corresponding untraced conditions. Syscall durations do not establish stable-media behavior or uniquely identify a filesystem cause.

A separate current-version, 16-publisher always sensitivity crosses compressible/pseudorandom payloads with inherited/disabled per-directory compression, where the filesystem supports verified per-directory control. This retains the same filesystem and device and is not described as a second-filesystem replication. Unsupported controls must be reported rather than silently substituted. No host mount options or unrelated directories are changed.

## Analysis and stopping

All planned cells and stage outcomes are retained. A returned request failure stops that trial's admission; already admitted calls are joined and recorded before cleanup. Collection proceeds to other planned cells only after a verified fresh broker reset. Infrastructure failure pauses the campaign, preserves its records and requires a separately documented continuation. Abrupt driver or host loss can still destroy buffered per-message observations and must be reported.

The analyzer independently recomputes metrics from raw traces and rejects mismatched counts, duplicate identities, invalid time ordering, stale inputs or missing planned outcomes. Report each deployment's condition means and paired contrasts, the range across deployments, sample counts, failures and raw tail ranks. With only three deployment campaigns on shared hardware, do not claim verified population confidence coverage or independent-host uncertainty. New results supplement the original campaign and are never pooled with it as interchangeable replications.

The campaign ends after its specified matrix and diagnostics, regardless of effect direction. Additional exploratory runs require separately identified cells and cannot be promoted to planned observations. Manuscript claims are written after verified analysis, including null, contradictory and inconclusive findings.
