# Publication venue assessment

Assessed on 2026-09-23 for **An Empirical Evaluation of Message Delivery Reliability and Recovery Characteristics in Redis Streams and NATS JetStream**. The requested priorities are a practical publication path and a citable DOI. This is an assessment, not a submission or publication. Prices and journal metrics are current observations and may change before acceptance.

## Recommendation

**Journal target: PeerJ Computer Science, Research Article.** Its published review criteria explicitly permit meaningful software performance comparisons and emphasize methodological validity rather than perceived novelty or impact. That is a particularly direct fit for this bounded empirical study. A real research question, a documented contribution beyond existing work, robust evidence, and available data are still required; derivative work is excluded. This recommendation is a fit assessment, not an estimate of acceptance probability. [PeerJ editorial criteria](https://peerj.com/about/editorial-criteria/cs)

**Easiest DOI-only route: Zenodo, deposited as a preprint.** It is free and registers a DOI when the record is published. Zenodo does not evaluate scientific correctness through journal peer review; the resulting work is citable but remains an unreviewed preprint. This directly meets a DOI/citation objective without waiting for a journal decision. Deposit the reproducibility artifact as a linked dataset/software record if separate citation and versioning are useful. [Zenodo terms](https://about.zenodo.org/terms/), [DOI registration](https://help.zenodo.org/docs/deposit/about-records/), [review boundary](https://support.zenodo.org/help/en-gb/2-safelisting-spam/141-what-content-do-you-consider-spam)

My preferred sequence is to prepare the public artifact and preprint for Zenodo, then submit the research article to PeerJ Computer Science. PeerJ permits manuscripts previously available on preprint servers. If the publication budget is zero and formal journal peer review is required, use **SN Computer Science's subscription route** instead. [PeerJ policies](https://peerj.com/about/policies-and-procedures/cs), [SN publication routes](https://link.springer.com/journal/42979/how-to-publish-with-us)

## Shortlist

| Destination | DOI / review | Current author cost | Assessment for this paper |
|---|---|---|---|
| **Zenodo** | DOI on publication; repository screening is not journal peer review | **Free** | Lowest-burden route to a publicly citable preprint and reproducibility artifact. It does not confer journal acceptance. |
| **PeerJ Computer Science** | DOI-bearing, peer-reviewed journal | **US$755 Basic individual lifetime membership** for the current sole-author manuscript, if within its one-publication-per-12-month allowance; alternatively **US$2,155 APC**; applicable taxes extra | Preferred journal fit: empirical performance comparisons are explicitly contemplated by the review criteria. |
| **SN Computer Science** | DOI-bearing, peer-reviewed journal | **No APC under the subscription route**; optional OA currently US$3,290 / GBP2,390 / EUR2,690, plus applicable taxes | Strong zero-APC journal alternative. Scope includes network performance and distributed/cloud computing. The publisher's final version is not freely readable under the subscription route. |
| **Computers (MDPI)** | DOI-bearing, peer-reviewed open-access journal | **CHF1,800 APC**, plus applicable taxes | Plausible alternative for applied computer-systems experiments, with fast publisher-reported editorial timings. More expensive than the current single-author PeerJ membership route; speed is not evidence of higher acceptance probability. |

Sources for fees and policies: [PeerJ pricing](https://peerj.com/pricing), [SN fees and routes](https://link.springer.com/journal/42979/how-to-publish-with-us), [SN scope](https://link.springer.com/journal/42979/aims-and-scope), [Computers fees](https://www.mdpi.com/journal/computers/apc), [Computers scope](https://www.mdpi.com/journal/computers/about), [Zenodo terms](https://about.zenodo.org/terms/).

DOI evidence includes PeerJ's published articles using `10.7717/peerj-cs.*`, such as [this publisher-hosted article](https://peerj.com/articles/cs-142/), and the Computers article [Performance Comparison of Python-Based Complex Event Processing Engines for IoT Intrusion Detection: Faust Versus Streamz](https://www.mdpi.com/2073-431X/15/3/200), DOI `10.3390/computers15030200`. These illustrate DOI publication and, in the latter case, a related article type; they do not predict acceptance of this manuscript. SN DOI evidence and the other evaluated outlets are documented in [VENUE_ALTERNATIVES.md](VENUE_ALTERNATIVES.md).

## What “easy” can reasonably mean

The strongest predictor available here is fit to stated criteria, not a promised acceptance rate. PeerJ's live journal page displays an overall acceptance rate of **33%**. That aggregate is not this manuscript's probability, and it is a reason not to call the journal automatic or guaranteed. Its pricing page advertises **30–35 days to first decision**; its journal page separately displays **32 days from acceptance to publication**. Neither figure is total submission-to-publication time, and the two should not be added as a guaranteed schedule. [PeerJ journal page](https://peerj.com/journals/computer-science/), [pricing information](https://peerj.com/pricing)

SN Computer Science's live page reports a **96-day median submission-to-first-decision** interval. Computers' official flyer reports **15.4 days to first decision** and **3.9 days from acceptance to publication**, medians for papers published in the first half of 2026. These figures concern different populations and stages; they are not a controlled comparison of review speed or acceptance odds. [SN journal page](https://link.springer.com/journal/42979), [Computers publisher flyer](https://www.mdpi.com/journal/computers/special_issue_flyer_pdf_v2/C6SEF177U7)

For Zenodo, the DOI becomes registered only when the draft is actually published, not merely when reserved. A deposit submitted to a community can await curator action. The ordinary publication path without a community avoids that community-review wait, subject to account and repository controls. [Create an upload](https://help.zenodo.org/docs/deposit/create-new-upload/), [records awaiting review](https://support.zenodo.org/help/en-gb/6-collaborate-and-share/3-why-is-my-record-in-review)

## PeerJ cost details that matter here

Victor Bona is the sole author in the current manuscript. The membership calculation changes if authors are added: all must have eligible memberships. Basic permits one publication per 12 months. The FAQ removes the former regular-review requirement and permits payment at acceptance, before production. There is no need to pay merely to test editorial fit. More than 40 typeset pages can incur a surcharge; local PDF length does not determine final typeset length. [Official pricing and expanded FAQs](https://peerj.com/pricing)

## Manuscript-specific preparation before journal submission

The local manuscript is an empirical research article with randomized blocks, explicit failed outcomes, conditional proofs, and a reproducibility artifact. Those are relevant strengths. Its main limitations remain a shared single-homelab storage environment, historical releases, short publication trials, compressible payloads, no power-loss experiment, and unequal consumer-state durability semantics. The source already acknowledges these. Reviewers may nevertheless require additional experiments; neither DOI assignment nor Lean checking removes that possibility.

1. **Present the contribution as a controlled empirical evaluation.** Clearly explain what the combination of failure-age measurements, consumer concurrency, and persistence profiles adds beyond existing comparison studies. Do not market the simple conditional model proofs as formal verification of the brokers.
2. **Make the artifact accessible to reviewers.** The current artifact is local. PeerJ requires reproducibility materials at submission; its policies specify archival identification for code hosted in Git repositories. A linked Zenodo artifact DOI is a practical fit. [Code and data policy](https://peerj.com/about/policies-and-procedures/cs#code-data-availability)
3. **Complete author review and accurate declarations.** The present generic Codex acknowledgment should become a specific account of AI assistance, available tool/version information, and human verification. The author must personally review the scientific claims, analysis, references, and final manuscript and take responsibility for them. Funding, competing interests, and contributions must reflect the author's actual circumstances. PeerJ's policy allows responsible AI assistance but retains editorial discretion when it replaces core author responsibilities. [Authorship and AI policies](https://peerj.com/about/policies-and-procedures/cs#generative-AI)
4. **Prepare a concise journal-facing manuscript and cover letter.** Keep the measured results central; supporting proof details and operational ledgers can remain in appendices or supplementary material as appropriate. The ordinary Research Article category is the suitable one, rather than a software-tool or data-descriptor article. [Scope and article types](https://peerj.com/about/aims-and-scope/cs)

These are preparation recommendations. No manuscript, authorship statement, license, funding statement, public record, or external account was changed during this assessment.

## Alternatives not preferred for the unchanged manuscript

SoftwareX centers the contribution on research software, Data in Brief on reusable datasets, and JOSS on substantive research software with demonstrated maturity and use. The current paper's contribution is the experimental comparison. Reframing it for those outlets would be additional work and would not provide an easier submission of the same article. Current policies, charges, and eligibility details are in [the companion source note](VENUE_ALTERNATIVES.md).

## Evidence provenance

Official publisher and repository pages were checked on 2026-09-23. PeerJ's web-search fetches returned HTTP 403, so its live journal, editorial-criteria, policy, pricing, and expanded FAQ pages were read through the in-app browser instead. Some MDPI pages returned HTTP 429 on direct opening; their publisher-owned indexed pages and official flyer supplied the cited fee/scope/timing evidence. No third-party fee aggregator was used as the authority for the prices above. Suitability rankings and expected editing effort are judgments based on the local manuscript and the cited policies, not publisher commitments.
