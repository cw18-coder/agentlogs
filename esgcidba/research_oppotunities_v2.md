---
title: "Research opportunities v2: feasibility of the Gemini TCO proposal"
description: "A traceable assessment of three proposed RQs and six hypotheses, with fixed pilot pipelines and go/no-go gates."
version: "2.0"
date: "2026-10-26"
parent_document: "tco_gmnb.md"
previous_series_document: "research_oppotunities.md"
status: "Design assessment; empirical pilots not executed"
---

## Executive assessment

The [Gemini Notebook proposal](./tco_gmnb.md) identifies a relevant managerial
problem: choosing and governing coding agents under resource constraints.
AgentLogs can support observational research on operational completion and
recorded resource consumption. It cannot, by itself, establish enterprise Total
Cost of Ownership (TCO), financial Return on Investment (ROI), causal model
superiority, or an optimal automatic stopping policy.

Proceed with a narrowed study, not the proposal unchanged. Prioritize RQ1,
then RQ2, and treat RQ3's modality comparison as an identification gate that
may fail before a substantive pilot. More observations cannot repair an invalid
outcome, incompatible units, an absent comparator, or a missing causal design.

This is v2 of the research opportunities series, not a replacement of the
[v1 shortlist](./research_oppotunities.md). The parent being assessed is
[tco_gmnb.md](./tco_gmnb.md), especially Sections 3.1-3.2 for RQs and hypotheses,
4.2-4.3 for measurement and estimation, and 5.1 for proposed interventions.
The parent and v1 are preserved unchanged. All judgments below are based on
document and schema inspection, not new empirical findings.

| Priority   | Parent question                                           | Feasibility as written                                | Defensible opportunity                                                                                | Decision before thesis drafting                                  |
| ---------- | --------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1          | RQ1: model choice, success, and cost per resolution       | Conditional; causal and enterprise claims unsupported | Compare named model groups on operational completion and recorded units per completed initial session | Pilot if model overlap and comparable consumption units exist    |
| 2          | RQ2: context expansion, caching, and cost                 | Conditional; substantial metering validation needed   | Describe context scaling and cache-associated resource differences within comparable billing regimes  | Audit counters first, then pilot both hypotheses separately      |
| 3          | RQ3: tools versus direct generation and optimal intensity | Low; modality identification may be impossible        | Compare validated execution groups, or explicitly narrow to descriptive intensity economics           | No modality pilot without genuine comparable non-tool executions |

## Traceability from the parent to the v2 decision

| Parent reference     | Original proposition                                                            | v2 disposition                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Section 3.1, RQ1/H1a | Frontier models complete complex tasks more often                               | Retain as an adjusted association between named model groups in a prespecified complexity stratum               |
| Section 3.1, RQ1/H1b | Frontier models have higher cost per success on simpler tasks                   | Retain with a population-level consumption/completion ratio, never a per-failure division                       |
| Section 3.1, RQ2/H2a | Uncached expansion causes super-linear tokens and credits                       | Separate observed token scaling from billing; neither exponential growth nor causation is assumed               |
| Section 3.1, RQ2/H2b | Caching reduces cost without harming completion                                 | Retain as a joint economic association and completion safeguard; no-harm requires an explicit margin            |
| Section 3.2, RQ3/H3a | Tools causally improve success versus direct inference                          | Block until the two modalities are validated; observational adjustment does not establish causation             |
| Section 3.2, RQ3/H3b | Moderate tool use maximizes ROI                                                 | Replace with a testable descriptive U-shaped units-per-completion hypothesis; an interior minimum may not exist |
| Section 4.3          | Heckman/IV, Tobit, and Cox models deliver causal economic conclusions           | Replace invalid specifications as described below; no unsupported instrument or artificial censoring            |
| Section 5.1          | Estimated thresholds justify automated routing, termination, and cache controls | Restrict to decision-support candidates; deployment benefits require prospective validation                     |

All parent references in this table refer to
[the supplied Gemini proposal](./tco_gmnb.md). Its institutional compliance
claims in Section 6 have not been verified against original program guides.

## Corrections required before any pilot

### Scope, provenance, and schema

The [README](../README.md), [changelog](../CHANGELOG.md), and
[dataset card](https://huggingface.co/datasets/risenlab/agentlogs) identify release
`1.0-20261008`, schema `v1.0`, with a cutoff of 30 September 2026.
The parent's Section 4.1 says 30 August; that is incorrect.
The [arXiv v1 paper](https://arxiv.org/html/2608.29204v1) describes the older
five-table release and July collection, not the later eight-table snapshot.

The dataset covers public repositories in a more-than-10-star sampling frame,
not an identified enterprise population. Firm revenue, employee labor, salary,
license invoices, infrastructure bills, avoided effort, business benefits, and
counterfactual human-only delivery costs are not provided. A monetary TCO/ROI
thesis needs additional authorized organizational data and a new design.
The secondary-data-only alternative is resource efficiency, not financial ROI.

| Parent assumption                                    | Verified boundary and required correction                                                                                                                |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 624,668 complete parsed logs                         | The published count concerns sessions with logs. `log_found` is not proof of full call, usage, or subagent coverage; `parsed` is an entry-level property |
| 317,878 agent-authored PRs                           | PR links mean the agent worked on a PR, not necessarily authored it; see the [PR schema](../docs/schema/pull_request.md)                                 |
| Workflow runs represent complete CI activity         | They are the workflows hosting agent sessions, not a census of downstream tests; see the [workflow schema](../docs/schema/workflow_run.md)               |
| Usage is `agent_session_logs.usage...`               | Actual documented paths are `data.usage.prompt_tokens`, `data.usage.completion_tokens`, and `data.usage.prompt_tokens_details.cached_tokens`             |
| `repositories.stars` is a historical control         | The field is `stargazers_count`; snapshot popularity is not necessarily popularity at assignment                                                         |
| Premium requests are integer turn charges            | `premium_requests` is a float; neither a one-per-turn rule nor a universal billing interpretation follows                                                |
| Model strings identify expensive/capable tiers       | Presence, frequency, historical pricing, and capability ordering must be verified; parent examples are not a model inventory                             |
| Hundreds of billions of credits prove billing spikes | Log fields include `total_nano_aiu`; scale, semantics, duplication, and nesting must be audited before interpreting large numbers                        |

Field-level evidence is in the [session schema](../docs/schema/agent_session.md),
[log schema](../docs/schema/agent_session_log_entry.md), and
[repository schema](../docs/schema/repository.md).
The [session exporter](../packages/risenlab-agentlogs-collector/src/agentlogs/collector/export/sessions.py)
copies `usage.type`, `usage.amount`, and `usage.credits` from API payloads; it
does not establish a monetary exchange rate.
The [log exporter](../packages/risenlab-agentlogs-collector/src/agentlogs/collector/export/session_logs.py)
also retains `total_nano_aiu` in distinct usage structures. Do not equate these
quantities or infer an observed billion-credit invoice from their magnitudes.
No specific conversion or cause for the parent's extreme values has been verified.

### Outcomes and economic estimands

Define S as operational session completion, using terminal state values verified
during calibration. Do not assume that a `completed` session resolved its issue,
passed tests, produced a correct patch, or secured maintainer acceptance.
Treat failures and cancellations as separate reported categories, combined as
S = 0 only for the preregistered binary endpoint. Running/unknown states are not
failed sessions; report their coverage and do not silently exclude them.

Let C be recorded session consumption in one validated, comparable unit regime.
Keep credits, premium requests, raw nano-units, and tokens separate. The primary
economic statistic for a group g is:

```text
R_g = sum(C_i for all eligible sessions in g) / sum(S_i in g)
    = mean(C_i in g) / probability(S_i = 1 in g)
```

This includes failed-session consumption. It is recorded units per operationally
completed initial session, not total task resolution cost, marginal cost, or ROI.
If the denominator is zero, the ratio is undefined and must be reported as such.
It must not be set to zero, imputed at a percentile, or averaged from C_i / S_i.
Averages among successful sessions alone omit the resource burden of failures.

For adjusted comparisons, standardize mean consumption and completion probability
to the same covariate distribution, then divide the two standardized quantities.
Bootstrap repositories and refit both models jointly so ratio uncertainty includes
uncertainty and covariance in numerator and denominator.

### Identification and mathematical claims

* Prompt complexity is not a credible instrument for tool use: it can directly
  affect both completion and consumption. Repository tool-enablement policies
  are not established structured variables and could also affect outcomes
  directly. The proposed exclusion restriction is unsupported.
* Classical Heckman sample-selection correction is not a generic cure for
  endogenous tool choice. Adding an inverse Mills ratio to logistic regression
  does not automatically identify an average causal effect.
* C_i / S_i for a failure is division by zero, not a censored observation.
  Assigning a 99th-percentile cost and fitting Tobit creates a fabricated endpoint.
  Use separate consumption and completion models and the ratio above.
* Completed sessions have generally had more opportunity to produce tool calls.
  Regressing completion on realized whole-session intensity can mix process,
  stopping, and outcome. Interpret it descriptively, not as the effect of
  prescribing additional calls.
* Cox analysis cannot treat every `completed_at` as successful resolution.
  Cancellation and failure can terminate execution, and whole-session token/cache
  variables contain future information relative to session start. Omit this
  optional survival analysis from the fixed pilots rather than claim a causal
  resolution hazard.
* Constant added context can produce roughly quadratic cumulative input volume,
  not necessarily exponential growth. Cache reuse, truncation, compaction, and
  variable tool outputs alter the trajectory. Resource metering need not scale
  identically to raw tokens.
* The parent's positive repair probabilities assume every tool step helps and
  never introduces an error. That assumption cannot prove H3a from observed data.
* A negative second derivative at a stationary point establishes a local maximum
  under the stated assumptions, not global strict concavity or existence of an
  interior optimum. The corresponding cost curve can be monotonic or flat.
  A minimum is not an inflection point.

Transaction Cost Economics may motivate governance questions, but token counts
do not exhaust transaction costs. A model available to many firms is not, by
itself, evidence of an inimitable firm resource under RBV.
The parent's "Context Expansion Trade-Off Theory" needs an independently sourced
theoretical basis; do not present it as an established theory without review.

## Shared pilot protocol for all three RQs

### Stage 0: calibration and measurement gate

Pin dataset release `1.0-20261008`, its immutable revision, schema/package version,
local code commit, file hashes, extraction date, and seeds. Use the
[repository analysis examples](../scripts/analysis/) for projected Parquet queries;
do not download all logs before checking metadata coverage.

Use 60 calibration sessions from at least 10 repositories, deliberately covering
candidate models, metering types, failed/cancelled outcomes, and differing run
lengths. This is a diagnostic sample, not an effect-estimation sample. Audit all
60 traces manually where logs are present. Reserve them outside all evaluative
pilot and confirmation datasets.

Freeze these rules before looking at pilot exposure-outcome contrasts:

1. Enumerate model names, terminal states, dates, usage types, and missingness.
   Establish whether each planned comparison has contemporaneous support.
2. Reconstruct complete model invocations and tool calls from streamed
   delta/message records. Deduplicate by call IDs and event order; do not count
   request/result pairs, fragments, or telemetry summaries as new invocations.
3. Distinguish per-invocation usage from cumulative summaries. Require at least
   95% agreement of automated call reconstruction with the adjudicated audit,
   and aggregate counter reconciliation within 5% on at least 90% of audited
   sessions where comparable totals exist. Report exceptions, not silent repairs.
4. Establish units and accounting scope independently of the effect being tested.
   Determine whether session totals already include delegated work; do not add
   child consumption again. Quarantine incompatible or unresolved billing regimes.
5. For cache analyses, distinguish cache reads from cache creation and validate
   whether cached input is a subset of reported prompt input. A missing cache
   counter is unknown, not zero; a zero prompt denominator has no cache ratio.
6. Recover original request text separately from platform scaffolding and quoted
   history. Two coders validate task category and complexity on at least 50
   calibration/validation requests; require kappa at least 0.70 and report raw
   agreement. Complexity is a rubric-based proxy, not latent difficulty measured
   without error.

If accounting cannot be validated, the monetary/credit hypotheses are no-go.
A token-only study can remain useful, but is an explicitly different scope,
not an unannounced substitution for cost evidence.

### Sampling and fixed analysis contract

Use the first observed session of each task as the analysis unit. Require
initial-assignment eligibility using the frozen request/event rubric; separate
review-only or correction-only tasks. Exclude ambiguous task links. Session
indices alone do not prove that the full historical task was collected.
The estimand is initial-session performance, not all retries or lifetime task cost.

Allow terminal successes, failures, and cancellations with known state.
Require session creation at least seven days before the conservative cutoff
of 29 September 2026 23:59:59 UTC; report residual nonterminal sessions as
unascertained. This defines an observed-terminal cohort, not guaranteed complete
follow-up or time-to-success inference. A nonterminal fraction above 10% fails
the primary coverage gate rather than being recoded as failure.

Construct frames from metadata, then sample randomly with a fixed seed,
proportionally within month, model/regime, and the RQ-specific comparison strata.
Estimate population contrasts with the recorded inverse inclusion weights
when strata are deliberately oversampled. Keep every task and any shared linked
PR in a single pilot/confirmation partition. Resample repositories for uncertainty;
the 75 million log events are not 75 million independent observations.

All evaluative pilots require:

* At least 40 repositories, with no repository exceeding 10% of weighted rows
* At least 90% ascertainment of required outcomes/exposures among sampled
  metadata-eligible sessions, reported by model, month, and regime
* At least 100 completed and 100 noncompleted sessions overall; any subgroup
  hypothesis must also meet its more specific counts below
* Real within-repository and within-calendar-period exposure overlap, not a
  comparison where models/modalities perfectly identify different repositories
  or time periods
* Identifiable models, stable resampling, and no unresolved separation or
  extrapolation into unsupported comparison regions

Use mixed-effects logistic regression for completion with a repository intercept.
For mean consumption including zeros, use a two-part model: logistic probability
of positive C, then Gamma/log-link mean C conditional on C > 0, each with a
repository intercept. If all observations have positive consumption, the
positive probability is identically one; omit only that non-identifiable part.
Preserve genuine heavy tails in the primary estimates and report their leverage.

Common pre-execution controls are request-based task category, complexity,
log original-request length, calendar month, and declared reasoning effort.
RQ2/RQ3 also control for named model. Never use total prompt tokens as baseline
task complexity. Do not adjust RQ1 for downstream tool count, tokens, or retries:
they can be consequences of model selection. Snapshot stars are not historical
confounder measurements.

Lock category pooling, missing-category rules for optional covariates, centering,
and spline knots after calibration but before evaluative pilots. Exposures,
outcomes, and primary consumption units are never silently imputed.
Use repository bootstrap 90% intervals for pilot decisions and 95% intervals
for confirmation. Prespecified sensitivities remove the single largest repository,
restrict to common model-month support, and remove the top 1% consumption tail
as a diagnostic only. A conclusion that depends on dropping costly failures fails
the stability gate.

The models and estimands below remain fixed as sample size increases. Calibration
can reject a design, but must not turn into outcome-driven model shopping.
A new proxy, unit, threshold, or method requires a versioned amendment and fresh
evaluation data. Failure of an optional endpoint does not redefine the primary one.

### Decision logic and confirmation

The numerical practical thresholds below are provisional managerial judgments,
not values supplied by the dataset. Obtain supervisor agreement before freezing.
Go requires measurement/overlap gates, an attainable confirmation sample, and
the RQ-specific effect criteria. A p-value alone never determines go.

A pilot is inconclusive if its interval includes both meaningful benefit and
meaningful harm, if relevant group/event counts are insufficient, or if estimates
are unstable. Increase only through the next prespecified sample blocks, up to
twice the stated initial target, for count or precision deficiencies, never to
chase significance. At that cap, do not keep sampling until a desired sign appears.

No-go applies when a construct/comparator is absent, or an adequately estimated
interval rules out the hypothesized practical effect. An opposite-direction
result can motivate a separately disclosed research direction; it does not
confirm the parent's hypothesis.

Estimate the final sample by simulation under the smallest practical effect,
using conservative ranges for pilot base rates, clustering, exposure imbalance,
and heavy-tailed consumption. A five-percentage-point completion difference near
50% needs approximately 3,130 independent observations before clustering;
stratified hypotheses and economic ratios can require substantially more.
Do not use the observed pilot effect as the assumed true effect.

Reserve untouched confirmation data. If confirming several hypotheses, apply
Holm adjustment across the retained primary hypothesis family; use simultaneous
intervals for curve claims and an explicit noninferiority test for no-harm claims.
Pilot findings remain exploratory and must be disclosed as such.

## RQ1: Model selection and recorded resource efficiency

### Assessment and narrowed question

Parent: [Section 3.1, RQ1, H1a, H1b](./tco_gmnb.md).
Feasibility is highest of the three, conditional on model/regime overlap.
Named model metadata and operational states are directly available; credible
complexity coding and comparable units are the principal burdens.

Narrowed RQ1: Among initial task sessions in overlapping model-month-repository
settings, how do named model groups differ in operational completion and recorded
units per completion within prespecified initial-task complexity strata?

Choose one candidate higher-capability model A and comparator B before pilot
outcomes are examined. Verify names and any capability/pricing labels using
appropriate dated evidence. Without that evidence, call them A and B; do not
assume the parent examples exhaust the actual inventory. No pooling into a
universal "frontier" tier across incompatible models or billing periods.

Code complexity before execution as high (cross-component change or multiple
explicit integration constraints) versus low/medium (localized change without
those requirements). Require enough request detail; exclude uncodable cases.
This coarse proxy cannot eliminate confounding by true difficulty.

### Pilot design and fixed tests

Target 1,200 initial sessions, with at least 150 in each model-by-complexity cell.
Require at least 50 completions and 50 noncompletions per cell, and at least 20
repositories that use both models in overlapping months. Expand to 2,400 only
under the shared count/precision rule.

Fit the common completion and consumption models with model, complexity, their
interaction, and the remaining baseline controls. Standardize A/B comparisons
within each complexity stratum. Do not infer a routing threshold at a complexity
score that the two-category rubric does not identify.

* H1a-v2: In high-complexity work, A has at least a five-percentage-point higher
  adjusted operational completion probability than B.
* H1b-v2: In low/medium-complexity work, A has at least 20% higher adjusted
  recorded units per completion than B, meaning R_A / R_B >= 1.20.

For H1a pilot go, require the point estimate >= +5 points, the lower 90% bound
above -5 points, and interval width <= 20 points.
For H1b pilot go, require the point ratio >= 1.20, lower 90% bound > 0.80,
and upper/lower interval-bound ratio <= 2.0. Require stable directions in the
locked sensitivities for both. Ratios with nonpositive or unbounded confidence
bounds fail the precision gate.

Evaluate the two hypotheses separately. If only H1a passes, a completion-focused
model-comparison thesis remains possible, but the economic-routing claim does
not. If only H1b passes, resource efficiency may be studied without claiming
frontier superiority. An economic routing narrative combining both needs both.

### Principal threats and deliverable

Users choose models; complexity, task assignment, subscriptions, and developer
expertise can differ systematically. Weighting or regression cannot prove that
switching a task to model A would improve it. Initial-session ratios omit later
rescue costs and human review effort. A validated model-comparison matrix is a
defensible DBA output; enterprise ROI, optimal routing, and savings are not
established by this observational pilot.

## RQ2: Context scaling and cache-associated consumption

### Assessment and narrowed question

Parent: [Section 3.1, RQ2, H2a, H2b](./tco_gmnb.md).
Feasibility is medium because the relevant fields exist, but their presence does
not prove consistent metering, complete invocations, or cache comparability.

Narrowed RQ2: Within a named model and validated metering regime, how does
uncached input scale with observed invocation count, and is higher cache reuse
associated with lower recorded consumption without a practically important
completion deficit?

For N deduplicated model invocations, let P_t be prompt input, K_t cache-read
input, and O_t output for invocation t. Only when the subset convention is
validated, define:

```text
I = sum(P_t)
O = sum(O_t)
U = sum(P_t - K_t)
q = sum(K_t) / sum(P_t)
```

Use the ratio of sums, not an unweighted average of per-turn cache ratios.
Treat inconsistent counters, missing K_t, and I = 0 as unknown for this analysis.
Explicitly distinguish this q from any model-specific cache-creation metric.

### Pilot design and fixed tests

Target 800 initial sessions in validated model/regime strata with N >= 3 and
complete positive U, I, and relevant cost counters. Retain genuine C = 0 in
the two-part consumption model. Require at least 100 sessions each with
q <= 0.50 and q > 0.50, at least 100 in each invocation-count tercile, and
at least 20 repositories with both cache groups within comparable strata.
Expand to 1,600 only under the shared rule.

* H2a-v2: Uncached input volume U scales super-linearly with N; a practically
  important scaling exponent is at least 1.15.
* H2b-v2: Increasing q from 0.25 to 0.75 is associated with at least 20% lower
  adjusted mean recorded consumption, with an operational completion difference
  no worse than -5 percentage points.

For H2a, regress log(U) on log(N), initial invocation log(P_1), model/regime,
baseline controls, and a repository intercept. Inspect within-session input
trajectories, compaction events, and cumulative curves as prespecified diagnostics.
Pilot go requires exponent estimate >= 1.15, lower 90% bound > 1.0,
and interval width <= 0.50, with stable direction in sensitivities.

This is descriptive scaling conditional on observed stopping. N is endogenous,
and U is a sum over N terms. Growth partly reflects accounting construction;
an exponent near one indicates proportional accumulation, not proof of
inefficient governance. Token scaling alone does not demonstrate credit scaling.

For H2b, fit the common consumption model with q, log(N), q-by-log(N),
log(I), log(1 + O), model/regime, and baseline controls. Fit a separate completion
model with q, log(N), model/regime, and baseline controls. Report standardized
q = 0.75 versus 0.25 contrasts at the upper invocation-count quartile fixed
from calibration, averaging over the shared supported covariate distribution.
Require actual joint support near both q values at those invocation counts;
do not extrapolate to a cache level observed only for a different model.

For pilot go, require the mean-consumption ratio <= 0.80, upper 90% bound < 1.20,
and upper/lower interval-bound ratio <= 2.0. Also require completion point
difference > -5 points, lower 90% bound > -10 points, and interval width <= 20
points. These screening rules do not establish noninferiority. Confirmation
requires a multiplicity-aware lower confidence bound above the -5-point margin
as well as evidence for the economic contrast.

### Principal threats and deliverable

Cache hit rate is not randomly assigned. Prompt stability, infrastructure routing,
request length, model defaults, and session survival influence it. The cache
ratio shares a denominator with input volume; conditioning on input volume and
invocation count defines a resource-accounting comparison, not a total causal
effect. If consumption is mechanically derived from cached/uncached token prices,
the result largely restates the tariff rather than discovering a behavioral
mechanism. Report that limitation, and test whether independent operational
variation and the completion safeguard add a worthwhile DBA contribution.

H2a and H2b receive separate decisions. A token-scaling result without comparable
cost units supports a narrowed trace-accounting study, not the parent's cost
claim. No pilot result validates "forcing cache re-indexing" or another platform
control not evidenced in the data.

## RQ3: Tool modality and intensity economics

### Assessment and narrowed questions

Parent: [Section 3.2, RQ3, H3a, H3b](./tco_gmnb.md).
Feasibility is low as written. AgentLogs concerns a tool-capable cloud-agent
platform, not a designed experiment containing comparable direct-generation
executions. Zero observed calls can mean startup failure, missing logs,
unrecorded delegated work, an immediate refusal, or a task requiring no code.

Distinguish two questions:

* RQ3a-v2: If genuine, comparable non-tool executions exist, are observed
  execution groups associated with different operational completion rates?
* RQ3b-v2: Among reconstructable tool-using sessions, is there a supported
  interior minimum in recorded units per operational completion over observed
  tool intensity?

RQ3b can be evaluated independently of RQ3a, but cannot answer whether tools
outperform direct generation. Relabeling the question must be explicit.

### Modality gate and H3a pilot

First inspect up to 100 randomly selected apparent zero-call candidates and
100 tool-using candidates, separate from evaluation. Require complete execution
traces, interpretable request/output, evidence of actual non-tool generation,
and comparable task/output requirements in the same model-month settings.
Reconcile session operational completion with the output requirement in both
groups. If one group can complete by emitting prose while the other must edit
files or open a PR, platform completion is not a comparable success measure.

Require at least 90% of audited apparent zero-call candidates to be genuine
non-tool executions and identifiable comparable outcome semantics.
If not, H3a is no-go in AgentLogs alone. Do not infer a direct-inference control
group from `tool_call_count == 0`.

If the gate passes, target 800 initial sessions, at least 200 in each modality,
and at least 50 completions and 50 noncompletions per modality. Require 20
repositories with both modalities in contemporaneous common support.
If stratified oversampling is needed, retain inclusion weights. Expand to 1,600
only under the shared rule.

H3a-v2: Tool-using sessions have at least a five-percentage-point higher adjusted
operational completion probability than genuine comparable non-tool sessions.
Fit the common completion model with modality, named model, and baseline
controls, without total tokens or final duration as controls.
Pilot go requires point difference >= +5 points, lower 90% bound > -5 points,
interval width <= 20 points, and sensitivity direction stability.

The result remains a realized-execution association, not a causal tool effect.
Early termination and task selection can generate the contrast. Failure of the
modality gate calls for a separately designed experiment or external comparison
dataset, not a more elaborate instrument assembled from the same missing data.

### Intensity pilot and H3b

Target 1,000 tool-using initial sessions with validated top-level tool counts
k and comparable consumption. Count completed tool invocations once; distinguish
failures of the invoked tool from duplicate request/result records. Keep explicit
failed invocations as calls, and keep subagent scope consistent with the cost
accounting boundary.

Require at least 100 sessions and 30 operational completions in each of five
intensity bands whose boundaries are quintiles frozen from calibration.
Tied counts that cannot support five distinct bands fail this shape-study gate;
do not force a smooth curve through absent intensity levels. Expand to 2,000
only under the shared rule.

H3b-v2: Within supported intensity ranges, adjusted recorded units per completion
have an interior minimum at least 20% below the ratios in both adjacent lower-
and higher-intensity bands. The cost curve would be U-shaped; an inverted U
would describe its reciprocal efficiency, not cost itself.

Fit the common completion and consumption models with a restricted cubic spline
in log(1 + k), using three distinct knots fixed at calibration percentiles
10, 50, and 90, named model, and baseline controls. Derive R(k) from standardized
mean consumption divided by standardized completion probability.
Use repository bootstrap simultaneous bands on a prespecified supported k grid.
Do not use Tobit or impose a quadratic minimum by construction.

Pilot go requires an interior trough, point estimates at least 20% below both
adjacent bands, and bootstrap intervals for each trough/adjacent-band ratio with
upper bounds < 1.20 and upper/lower bound ratios <= 2.0. At least 80% of bootstrap
fits must place a trough in the same band, with direction stable in sensitivities.
These are screening thresholds, not confirmation of an optimal policy.

Report flat, monotonic, boundary-minimum, or unstable curves as inconclusive/no-go
for H3b as appropriate. A larger sample must not be used to guarantee that a
U-shape appears. Because whole-run k reflects difficulty and stopping, even a
stable descriptive trough is not the number of calls at which to terminate a
new run. Establishing that policy requires sequential decision data and prospective
evaluation of continuation versus interruption.

## Decisions after the pilots and use in Chapters 1-3

Maintain six hypothesis-level decisions, not one overall "proposal validated"
label. An RQ with a measurement failure cannot inherit support from another RQ.
One well-measured hypothesis with a credible managerial contribution is preferable
to an overextended thesis promising all six.

| Pilot outcome                                             | Thesis decision                                                                                          |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| RQ1 passes overlap, accounting, and both hypothesis gates | Prioritize a model-selection resource-efficiency proposal with bounded observational claims              |
| RQ1 completion passes but economics fails                 | Consider operational performance, explicitly dropping TCO/ROI and economic-routing claims                |
| RQ2 metering and joint H2b screen pass                    | Consider a cache/resource-accounting thesis, subject to novelty and independent operational contribution |
| RQ2 only token scaling passes                             | Assess a narrower process-accounting topic; do not advertise financial cost reduction                    |
| RQ3 modality gate fails                                   | Drop H3a for this dataset; H3b remains a separately scoped possibility                                   |
| H3b has no stable interior trough                         | Drop optimal-intensity claims; report the observed curve without an automatic stopping recommendation    |
| All pilots are inconclusive or infeasible                 | Do not force a TCO thesis; return to the v1 alternatives or obtain authorized additional data            |

Use a go decision to work backwards into the first three chapters:

1. Proposal: state the actual population, managerial decision, measurable endpoint,
   retained hypothesis, practical threshold, and limits. A defensible working title
   is "Recorded Resource Efficiency of Model Choice in Public Cloud-Agent Tasks:
   An Observational Study Using AgentLogs."
2. Literature review: verify theory, distinguish established evidence from the
   parent's assumptions, review prior model/resource studies, and demonstrate the
   selected RQ's novelty. A statistically detectable tariff identity is not enough.
3. Research design: document sampling, counter validation, coding reliability,
   estimands, weighting, bootstrap uncertainty, confounding, simulated final power,
   preregistration, and ethics. Analyze confirmation outcomes only after this
   design is frozen.

Keep calibration, exploratory pilots, amendments, and confirmation distinct.
If several hypotheses pass, choose by measurement quality, attainable precision,
managerial relevance, and feasibility rather than the smallest p-value.
The parent's automatic routing, forced cache controls, privilege changes, and
termination rules remain untested interventions, not thesis findings.

## Governance and evidence status

Public data still require institutional ethics review or exemption, data
minimization, restricted raw-log access, and care around credentials and personal
information. Avoid individual performance scoring and unnecessary quotation of
identifiable traces. Do not send raw repository/session content to external
annotation services without appropriate authorization.

Attribute AgentLogs under CC BY 4.0; repository code is separately MIT-licensed.
Do not assert compliance with institutional page counts, plagiarism procedures,
hosting rules, or grading scales without the authoritative guides. Nothing in
this assessment validates the parent's Section 6 compliance claims.

No full-release data profiling, model-frequency count, billing conversion,
sample-size simulation, or empirical pilot was executed for v2. All target
samples and feasibility judgments are conditional design recommendations.
Published dataset totals describe the release, not the eligible analytical
sample.

## References and lineage

* [Parent proposal: tco_gmnb.md](./tco_gmnb.md), supplied Gemini Notebook draft;
  Sections 3-5 are the principal assessment targets; read 26 October 2026.
* [Series v1: research_oppotunities.md](./research_oppotunities.md), the earlier
  pilot-first shortlist; retained as a separate set of alternatives.
* [AgentLogs README](../README.md),
  [Hugging Face card](https://huggingface.co/datasets/risenlab/agentlogs), and
  [pinned release](https://huggingface.co/datasets/risenlab/agentlogs/tree/1.0-20261008).
* Richards, J., Horikawa, K., Fan, Y., Kashiwa, Y., and Wessel, M. (2026).
  [AgentLogs, arXiv v1](https://arxiv.org/html/2608.29204v1).
  DOI: [10.48550/arXiv.2608.29204](https://doi.org/10.48550/arXiv.2608.29204).
* [Schema reference](../docs/schema/README.md),
  [changelog](../CHANGELOG.md), and the schema/exporter evidence linked above.
  These establish fields and provenance, not independently validated billing
  semantics or causal effects.
