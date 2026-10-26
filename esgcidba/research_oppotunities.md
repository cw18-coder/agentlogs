---
title: "DBA research opportunities using AgentLogs"
description: "Three feasibility-ranked, pilot-first thesis designs with fixed analysis pipelines and explicit decision gates."
version: "1.0"
date: "2026-10-26"
status: "Research shortlist; pilots not yet executed"
---

## Recommendation and feasibility ranking

Start with Opportunity 1: delegation clarity and acceptance of agent-assisted work.
It connects a controllable management practice to an observable outcome, with less
log reconstruction than the alternatives. Run a bounded pilot before investing
in the first three thesis chapters. A promising pilot earns a larger study; it
does not establish a finding or justify a causal claim.

Each opportunity is a standalone Doctor of Business Administration thesis. None
requires another opportunity's results, proprietary organizational data, interviews,
or a new experiment. The shared procedures below are methodological standards,
not dependencies between the three studies.

| Rank   | Standalone opportunity                                | Feasibility   | Main managerial decision                           | Initial analyzable pilot            | Main constraint                                |
| ------ | ----------------------------------------------------- | ------------- | -------------------------------------------------- | ----------------------------------- | ---------------------------------------------- |
| 1      | Delegation clarity and work acceptance                | High          | How should managers specify work for AI agents?    | 600 PRs across at least 40 repos    | Recovering the original human specification    |
| 2      | Early execution repetition as an escalation signal    | Medium        | When should an agent run receive human attention?  | 800 PRs across at least 40 repos    | Reconstructing tool calls and their timing     |
| 3      | Actionable reviewer feedback and work acceptance      | Lower         | How should reviewers formulate agent corrections?  | 400 PRs across at least 40 repos    | Recovering genuine, timestamped human feedback |

Sample sizes are planning targets, not verified available counts or power
guarantees. Feasibility ranks reflect measurement burden and selection risk, not
the expected size or statistical significance of an effect.

## Evidence base and boundaries

### What the three sources establish

The [repository README](../README.md) and
[Hugging Face dataset card](https://huggingface.co/datasets/risenlab/agentlogs)
describe release `1.0-20261008`, schema `v1.0`, with a stated cutoff of
30 September 2026. They report 363,624 tasks, 635,886 sessions, 75,631,136 log
entries, and 40,565 repositories with agent tasks. The eight tables total
approximately 64.9 GB. Session metadata, PR metadata, and timelines allow
process-to-outcome linkage without fetching new private data.

The [paper, arXiv v1](https://arxiv.org/html/2608.29204v1), describes an earlier
release, version `0.2`: 307,416 tasks, 549,239 sessions, 64,255,174 log entries,
and 35,810 repositories with tasks. Collection occurred on 10-17 July 2026.
That release had five tables and did not collect further PR or workflow metadata.
The paper's counts and collection dates must not be presented as those of v1.0.
The [changelog](../CHANGELOG.md) confirms the later addition of PRs, timelines,
and workflow runs.

The paper motivates research on task formulation, process efficiency, failure,
and human-agent collaboration. Its Appendix A illustrates feedback embedded in
a session prompt, followed by an edit and a response to a comment. This supports
the plausibility of Opportunities 1-3, but one example establishes neither
measurement coverage nor an effect. The proposed managerial constructs and
hypotheses are research proposals, not results reported by the authors.

### What is observable, and what is not

* Merge is a proxy for acceptance into a repository, not verified code quality,
  customer value, realized productivity, profitability, or employee performance.
* Session completion is an execution state, not evidence that a PR was accepted.
* Elapsed calendar time is not human labor time. Tokens, tool calls, credits, and
  premium requests are distinct resource measures, not interchangeable monetary costs.
* The data concern observed activity on GitHub's cloud agent platform in public
  repositories sampled through a more-than-10-star frame. They do not represent
  all software organizations, private enterprise deployments, or all AI agents.
* Absence of observed tasks does not prove non-adoption. Deleted resources,
  unsuccessful API retrievals, unavailable logs, and unobserved activity matter.
* Repository metadata are snapshots, not necessarily values at task assignment.
  Stars, contributor counts, and size must not be treated as historical controls
  without historical evidence.
* The PR fields `created_by_tasks` and `created_by_sessions` mean the agent
  worked on the PR, not necessarily that it authored it. Scope all three studies
  to agent-assisted work; do not relabel it as exclusively agent-generated.
* Logged reasoning is model-produced text, not a validated account of cognition,
  intent, employee motivation, or managerial trust.

### Verified schema anchors

| Construct or linkage          | Available fields and documentation                                                                                                       | Caution                                                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Task, repository, sessions    | `id`, `repository.full_name`, `sessions`, `created_at`, `creator` in [tasks](../docs/schema/agent_task.md)                               | Task metadata do not provide a standalone original-request text field     |
| Prompt and execution          | `task.id`, `session_index`, `prompt`, `event`, `model`, timestamps in [sessions](../docs/schema/agent_session.md)                        | Prompt and event content can include wrappers and quoted history          |
| Trace and tool execution      | `entry_index`, `data.created`, `data.choices`, `data.content`, call IDs in [logs](../docs/schema/agent_session_log_entry.md)             | Parsed JSON does not imply complete, deduplicated, timestamped tool calls |
| PR acceptance                 | `graphql_id`, repository/number, `created_at`, `merged_at`, `closed_at` in [PRs](../docs/schema/pull_request.md)                         | Missing linked PR rows are unknown outcomes, not rejected work            |
| Feedback chronology           | `event_index`, `created_at`, `actor`, `event`, `message` in [timelines](../docs/schema/pull_request_timeline_event.md)                   | Review-comment bodies and inline threads are not guaranteed complete      |
| User/bot classification       | User types on sessions and timeline actors; [user schema](../docs/schema/user.md)                                                        | A session's user role does not by itself establish human authorship       |
| Agent execution status        | `status`, `conclusion`, `session` in [workflow runs](../docs/schema/workflow_run.md)                                                     | These are agent-hosting workflows, not a census of downstream CI tests    |

## Fixed pilot-to-thesis protocol

### Freeze the design before evaluating outcomes

1. Pin release `1.0-20261008`, schema `v1.0`, package `~=1.0.0`, dataset revision
   commit, repository commit, and extraction date. Retain file hashes, seeds,
   eligibility queries, exclusions, and a data dictionary.
2. Use 30 separate calibration units per opportunity to establish extraction,
   human/bot rules, event vocabulary, and coding examples. Exclude these units
   from both the evaluative pilot and confirmation sample. Coders must not see
   downstream merge outcomes while constructing exposure labels.
3. Freeze hypotheses, codebooks, time origins, covariates, models, sensitivity
   analyses, practical-effect thresholds, and decision rules. Record this protocol
   in a timestamped preregistration before the evaluative pilot.
4. Run exactly that pipeline on the pilot. For a selected thesis, increase the
   sample through the same eligibility and sampling rules, without changing
   constructs, windows, endpoints, or model specifications.
5. If calibration cannot support a construct, stop that opportunity. A different
   proxy or analysis is a separately versioned protocol requiring fresh calibration
   and pilot data, not an undocumented alteration during scale-up.

No pilot has been run for this v1 shortlist. This deliverable specifies the
research, not executable analysis software or empirical estimates.

### Cohort, time origin, and outcome discipline

Use one row per unique PR, not one row per log entry or session. Link task IDs
to sessions, and task/session artifact references to PRs using stable IDs, with
repository-plus-PR-number as the documented fallback. Aggregate one-to-many
relations before joining. Audit ambiguous and missing links rather than allowing
join multiplication to manufacture a large sample.

For Opportunities 1 and 2, use the earliest completed session of the earliest
linked task that meets that opportunity's criteria. Require one unambiguous PR
artifact, a PR already created by session completion, and a PR still open and
unmerged then. That completion timestamp is the landmark and time origin.
Include only initial sessions, not later feedback sessions, as the index session.
Resolve ties by stable task/session IDs, not outcome quality.

For Opportunity 3, use the first eligible human correction episode on an open,
unmerged PR with prior observed agent activity. Its feedback timestamp is the
time origin. Do not condition eligibility on whether the agent subsequently
responds. This includes failed or absent responses.

The common primary outcome is merge within 30 calendar days after the study's
time origin. Require the entire 30-day window to precede the published cutoff;
use the conservative end of 29 September 2026 UTC if cutoff-time precision is
unavailable. Open or closed-unmerged PRs at day 30 are zero for this endpoint.
Missing PR records, ambiguous chronology, and insufficient follow-up are unknown
or ineligible, never zero. A later merge does not change the day-30 outcome.

Using the completion landmark deliberately excludes initial-session failures,
PRs merged before completion, and work without a linked PR. It avoids comparing
different amounts of initial-session exposure time, but limits inference to
completed, still-open, PR-linked work. Publish that selection explicitly; neither
Opportunity 1 nor 2 estimates overall delegation success.

### Sampling, sufficiency, and scaling

Build the eligibility frame from metadata first. Draw PRs randomly with a fixed
seed, stratifying proportionally by index calendar month and broad language
group. Download or scan logs only for selected sessions and linked follow-ups.
Do not treat the bundled demonstration sample or the first Parquet shard as a
representative research sample. The paper's tiny sample describes its older
release and is not a power basis for these pilots.

Reserve disjoint pilot and confirmation PR IDs before exposure-outcome analysis;
keep every task/session associated with a PR in that PR's partition. The three
exploratory pilots may share PRs, but no pilot PR may enter the eventual
confirmatory dataset. Keep shared-PR dependence in mind when comparing pilots.

Each pilot must meet all of these sufficiency checks:

* At least 40 repositories; no repository contributes more than 10% of rows.
* At least 100 merged and 100 non-merged PRs, and at least 100 observations in
  each exposure comparison group defined below.
* At least 20 repositories contain both exposure groups, so the result is not
  solely a comparison between different repositories.
* At least 90% of metadata-eligible sampled units have resolvable primary
  outcomes and required exposure measurements. Report each missingness reason
  separately, alongside group-specific coverage.
* For manual exposure coding, two independent coders label at least 100 units,
  or 25% of the pilot if greater. Require Cohen's kappa at least 0.70 and report
  raw agreement. Adjudicate disagreements without downstream outcome access.
* The fitted primary contrast has a 90% interval no wider than 20 percentage
  points, with no separation, unidentified contrast, or unresolved fit failure.

These gates prevent a nominally large but uninformative pilot from passing.
If a target sample fails a count or precision gate, draw the next PRs from the
prespecified random sequence, up to twice its initial size. Do not expand because
a p-value is disappointing. If still insufficient, classify the opportunity as
inconclusive or infeasible for the available frame.

For scale intuition only, detecting a difference from 50% to 55% merge probability
requires approximately 3,130 independent observations in total at two-sided
alpha 0.05 and 80% power, with equal groups. Clustering, unequal groups, missingness,
and covariate structure can increase this substantially. A 600-row pilot cannot
reliably confirm a five-percentage-point effect.

Estimate final sample requirements by simulation of the locked model, using pilot
base rates, exposure prevalence, repository clustering, and conservative nuisance
parameter ranges. Target 80% power for the prespecified practically important
effect, not the inflated observed pilot effect. If the eligible, held-out frame
cannot supply that sample, do not promise a powered thesis.

### Common estimation and safeguards

Fit a logistic mixed-effects model with a repository random intercept and the
opportunity-specific exposure and pre-origin covariates. Report standardized
probability differences in percentage points as well as odds ratios. Obtain
uncertainty by resampling repositories and refitting the locked model. Report
90% intervals for pilot decisions and 95% intervals for confirmatory inference.
Do not substitute another estimator silently if the model or bootstrap fails.

Prespecify coarse task categories (bug fix, feature, maintenance/documentation,
other), model families, calendar-month terms, and log prompt length. Classify
task type from the original request, not later outcomes. Pool rare categorical
levels by fixed frequency rules set during calibration, not by effect size.
Check overlap and report group sizes and covariate balance before interpretation.
Model metadata marked unknown remain explicit; missing human request text,
exposure, time origin, or outcome is not imputed.

Do not adjust primary models for variables caused after the exposure, such as
later session count, later review activity, final diff size, eventual CI result,
or realized total effort. They may mediate the association or introduce bias.
Where request-based scope is specified below, code a narrow/broad indicator
from the initial request using a frozen rubric.

Locked sensitivities are a within-repository fixed-effects logistic model on
repositories with outcome variation, leave-one-repository-out estimates, and a
restriction to unambiguous single-task/single-PR links. Report changed populations
and non-estimable sensitivities. These address some observed heterogeneity and
linkage concerns, not unmeasured confounding. Also tabulate missingness by month,
model, and repository; restrict conclusions if exclusions are patterned.

Treat all pilot tests as exploratory. A favorable pilot is not thesis confirmation.
Use untouched confirmation data for the selected primary hypothesis at two-sided
alpha 0.05; if more than one opportunity is confirmed, apply Holm adjustment
across the confirmed primary hypotheses. Secondary endpoints remain exploratory.

### Go, no-go, and inconclusive rules

The provisional smallest practically important effect is five percentage points
in 30-day merge probability for every primary contrast, in its hypothesized
direction. This is a planning judgment, not a threshold supplied by AgentLogs.
Confirm its business relevance with the supervisor before preregistration.

* Go to proposal development when all measurement and sufficiency gates pass,
  the primary point estimate reaches the practical threshold, the 90% interval
  excludes an equally important effect in the opposite direction, and sensitivity
  point estimates do not reverse direction. A powered confirmation sample must
  also be attainable.
* No-go for the hypothesized managerial opportunity when measurement is
  infeasible, or the entire 90% interval rules out the hypothesized practical
  effect after the prespecified sampling limit. A credible opposite-direction
  finding is scientifically interesting, but is not support for the original
  hypothesis.
* Inconclusive when the interval still includes both practically important
  directions, precision/count gates fail, or sensitivities undermine stability.
  Do not call a non-significant result proof of no effect.

If several opportunities pass, prefer the higher-feasibility rank, better
measurement coverage, and lower projected confirmation cost, in that order.
Do not select the smallest p-value or largest observed effect. Record the
selection process and the other pilots in the eventual thesis.

## Opportunity 1: Delegation clarity and work acceptance

### Business problem, question, and theoretical lens

Managers can standardize how work is assigned to agents, but verbose assignments
are not necessarily clear assignments. The business problem is whether explicit
delegation contracts are associated with more accepted work, rather than merely
more agent activity.

RQ1: Among completed initial agent sessions linked to still-open PRs, is greater
clarity in the original human work specification associated with a higher
probability of merge over the following 30 days?

Use goal-setting theory and organizational information-processing theory as
candidate lenses: explicit goals and completion criteria may reduce ambiguity
in delegated work. The literature review must establish the actual theoretical
gap and test whether extending these constructs to human-agent delegation is
novel. The dataset paper alone does not establish DBA-level novelty.

H1: A high-clarity specification is associated with a higher adjusted 30-day
merge probability than a low-clarity specification. The practical target is
an increase of at least five percentage points.

### Operationalization and research design

Conduct a retrospective observational cohort study using the shared completion
landmark. Recover the original human request from the index session's `prompt`,
`event.content`, or the opening user-content block in its log. Establish source
precedence during calibration; exclude irreconcilable versions, platform-only
instructions, and prompts consisting only of inaccessible issue links.

Strip platform wrappers, quoted prior agent output, and reviewer history.
An initial-session identifier does not guarantee a fresh human assignment;
exclude review-only tasks and follow-up corrections using the frozen rubric.
Do not score the agent's plan or its summary as the manager's specification.

Code four binary dimensions from the human request:

1. A concrete intended deliverable or change
2. A bounded scope, including relevant component or explicit exclusions
3. Observable acceptance criteria
4. An explicit verification method, such as a named test or check

Sum to a 0-4 clarity score. Compare high clarity (3-4) with low clarity (0-2).
Keep the split fixed in pilot and confirmation. Double-code using the shared
reliability procedure; report agreement on each dimension as well as the group.
This is a proposed task-specific index requiring content validation, not an
established psychometric scale.

### Analysis, pilot, and standalone contribution

Target 600 eligible PRs, expandable to 1,200 only under the shared rule.
Fit the common primary model with clarity group, task category, model family,
calendar month, log human-request length, and initial scope. Standardize the
high-minus-low merge probability contrast. Request length distinguishes clarity
from verbosity; scope is an imperfect proxy for difficulty, not complete control.

As a secondary descriptive endpoint, compare the number of additional sessions
initiated within seven days of the landmark. Use a negative-binomial mixed model
with the same covariates and repository structure, reporting count ratios.
Include zero follow-ups. Fewer sessions need not mean better work, so interpret
this only alongside the primary acceptance outcome.

The pilot-specific make-or-break question is whether original human requests
can be separated from generated scaffolding reliably. Apply the common go/no-go
rules to H1. Stop if most apparent clarity comes from platform templates.

The standalone DBA contribution is an evidence-based delegation checklist and
an estimate of its association with work acceptance in the bounded population.
Residual confounding by developer skill, issue complexity, team norms, and
unobserved linked context prevents a claim that adopting the checklist causes
better outcomes. Conditioning on completed, PR-linked work also creates selection
risk. A future experiment would be needed to establish intervention effects;
it is not a dependency of this thesis design.

## Opportunity 2: Early execution repetition as an escalation signal

### Business problem, question, and theoretical lens

Autonomous activity can consume resources without advancing a deliverable.
Managers need observable warning indicators for attention allocation, not a
ranking based only on which model is most popular.

RQ2: Among completed initial agent sessions with sufficient early trace data,
does repeated execution of unchanged operations early in the run identify work
with a lower subsequent 30-day merge probability?

Use management control and exception-based monitoring as candidate lenses.
The proposed contribution is a measurable process signal linked to acceptance,
not proof that human intervention would rescue a run.

H2: An early repetition flag is associated with a lower adjusted 30-day merge
probability than no flag. The practical target is a decrease of at least five
percentage points.

### Operationalization and research design

Conduct a retrospective landmark cohort study. In addition to the shared
eligibility rules, require the first ten reconstructable top-level tool calls
of the index session, their order, and interpretable arguments. Shorter runs
are outside this population, not missing observations to be padded with zeros.
Define exposure from those ten calls only; start outcome follow-up at session
completion for both groups, avoiding unequal post-exposure observation windows.

Reconstruct calls across `choices[].delta.tool_calls` and
`choices[].message.tool_calls`. Combine streamed fragments and deduplicate
request/result and delta/message representations using IDs and ordering.
`entry_index` orders events; it does not establish that every event is a call.
Do not mix nested subagent calls into the top-level ten.

Flag repetition when the same operation occurs at least three times in those
ten calls, using an identical tool name and semantically unchanged arguments,
with no intervening file modification. Normalize JSON key order and insignificant
whitespace, but do not erase meaningful paths, command flags, or search patterns.
Exclude status polling and explicitly requested repeated verification using
rules established in calibration. Human auditors validate at least 100 traces
and require precision and recall of at least 0.85 against their adjudicated labels.
If calls, arguments, or intervening edits cannot be resolved, label exposure
unknown rather than no repetition.

### Analysis, pilot, and standalone contribution

Target 800 eligible PRs, expandable to 1,600. The larger target reflects the
unknown prevalence of repetition and losses from trace reconstruction.
Fit the common primary model with the flag, task category, model family,
calendar month, log initial-request length, and initial scope. Report the
flagged-minus-unflagged standardized merge probability difference.

For an exploratory resource endpoint, count additional top-level tool calls
in subsequent linked sessions during seven days after the landmark, using
event timestamps and excluding the index session entirely. Fit a negative-binomial
mixed model with the same controls and report count ratios. Require timestamped,
complete logs for this secondary analysis and report its separate denominator;
unknown log coverage is not zero activity. Tokens may be summarized by model
as supplementary diagnostics only, after validating per-call versus cumulative
usage and duplicate records.

The pilot-specific make-or-break questions are whether the flag is sufficiently
prevalent and whether repetition is distinguishable from legitimate iteration.
Require the common group-count and measurement gates plus the trace precision/
recall gate. Apply the shared decision rules to H2, not to a conveniently
significant resource endpoint.

The standalone DBA contribution is an auditable exception-monitoring indicator
and a decision aid for prioritizing human attention. Task difficulty, unfamiliar
repositories, and tool limitations may cause both repetition and non-acceptance.
The flag is not a causal diagnosis of waste. No labor savings, optimal stopping
rule, or benefit from terminating agent runs can be inferred from this design.
Do not deploy an automatic stop policy on the basis of this pilot.

## Opportunity 3: Actionable reviewer feedback and work acceptance

### Business problem, question, and theoretical lens

Human review is a governance mechanism for delegated work, but review requests
vary in actionability. The management question is how to formulate corrective
feedback, not merely whether more comments appear on difficult work.

RQ3: Among open PRs with prior observed agent activity that receive a human
correction, is actionable feedback associated with a higher probability of merge
within the following 30 days?

Use feedback intervention theory and coordination theory as candidate lenses.
Translate them into observable message attributes, without inferring reviewer
attitudes or organizational culture from comment wording.

H3: High-actionability human correction episodes are associated with a higher
adjusted 30-day merge probability than low-actionability episodes. The practical
target is an increase of at least five percentage points.

### Operationalization and research design

Conduct a retrospective feedback-episode cohort study with one episode per PR.
Use the first timestamped, substantive human correction directed to the agent
after prior observed agent work. A correction must request a change; approval,
bot messages, agent self-comments, and logistical chatter are not exposures.
Use the timestamp of that message as time origin, not the next agent response.
If several corrections share that timestamp, treat them as one episode.

Recover feedback from timeline records, corroborated by subsequent session
`event.content` or opening prompt context where available. Match by comment ID
when possible. Quoted old comments are not new episodes. The timeline schema
does not guarantee complete inline review text, so exclude episodes with
unresolvable authorship, timing, or substantive message content. Do not invent
a complete review history from the paper's illustrative transcript.

Code three binary dimensions:

1. Identifies the specific defect or unwanted behavior
2. States the desired correction or expected behavior
3. Provides a verification criterion or concrete passing example

High actionability means all three dimensions; low actionability means zero
to two. Code requested correction severity separately as cosmetic/documentation,
localized functional, or architectural/cross-cutting, using the episode text.
Double-code the exposure and severity with the shared reliability rules.

### Analysis, pilot, and standalone contribution

Target 400 eligible PRs, expandable to 800. Fit the common primary model with
actionability group, correction severity, initial task category, model family
of the latest pre-feedback session, calendar month, log feedback length, log
PR age at feedback, and count of completed pre-feedback agent sessions.
These covariates precede the exposure; later response effort does not.
Report the high-minus-low standardized merge probability difference.

As a secondary endpoint, code whether a human repeats the same unresolved
correction within seven days. Include PRs without a subsequent agent response;
report response presence separately. Fit a logistic mixed model with the same
covariates only where review coverage supports ascertainment. Absence of a
retrieved comment is not proof that no further correction occurred. If coverage
cannot support this endpoint, report it as unmeasurable rather than redefining it.

The pilot-specific make-or-break question is whether genuine corrective feedback
can be reconstructed without selecting only successful agent responses.
Apply the common gates and H3 decision rules. Stop if actionable-message groups
are too rare or review-thread coverage cannot support the primary exposure.

The standalone DBA contribution is a reviewer-feedback rubric and evidence
about its relationship with acceptance of agent-assisted work. Reviewer expertise,
defect severity, maintainer authority, and willingness to merge remain potential
confounders. Neither reviewer authority nor a full human review labor budget
is guaranteed in the schema. This study cannot establish that better wording
causes acceptance, reduces labor costs, or increases trust.

## Efficient execution and research governance

### Bounded sequence for choosing a thesis

1. Start with a metadata-only coverage audit and Opportunity 1 calibration.
   Download small tables first; avoid a full log download unless required.
2. Run Opportunity 1's frozen pilot if calibration passes. If it meets the go
   criteria, prioritize it rather than running two more pilots to hunt for a
   stronger result.
3. If Opportunity 1 fails or remains inconclusive, proceed to Opportunity 2,
   then Opportunity 3. Each has its own calibration, sample, and decision.
4. Produce a decision record with eligibility counts, a linkage flow diagram,
   coding reliability, exposure balance, estimates and intervals, sensitivity
   results, projected confirmation sample, and the go/no-go/inconclusive rationale.
5. After choosing an RQ, write Chapters 1-3 before analyzing confirmation outcomes.
   Keep the same pipeline and increase only the eligible sample. If no opportunity
   passes, retain that conclusion rather than manufacturing a positive RQ.

DuckDB over projected Parquet columns is a suitable starting point, with Polars
or streaming for nested log reconstruction, following the
[analysis examples](../scripts/analysis/). Filtering after downloading a shard
does not imply that only the selected rows were transferred; verify sharding
and storage requirements before estimating pilot cost.

### Turning a go decision into the first three chapters

| Chapter                       | Pilot evidence carried forward                                       | Work still required before confirmation                                                         |
| ----------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 1: Proposal                   | A measurable problem, bounded population, practical effect target    | State the managerial problem, scope, contribution, RQ, hypotheses, and limitations              |
| 2: Literature review          | Evidence that the proposed constructs can be observed                | Review theory and prior empirical studies systematically; establish novelty and rival accounts  |
| 3: Research design            | Coverage, reliability, clustering, base rates, and runtime estimates | Document epistemology, sampling, ethics, operationalization, locked models, and simulated power |

Writing backwards from a pilot is appropriate for feasibility and measurement
planning, not for presenting exploratory findings as predictions made in advance.
Disclose which hypotheses preceded the pilot, all failed pilots, any protocol
amendments, and the independent confirmation partition. Supervisor and institutional
requirements govern whether a secondary-data-only design meets the DBA standard.

### Ethics, reproducibility, and limits of the shortlist

Seek institutional ethics review or exemption before coding identifiable public
traces. Public availability is not blanket permission to profile individuals.
Pseudonymize users and repositories in analysis exports, minimize retained text,
restrict raw-log access, and redact secrets or personal information encountered.
Do not upload raw traces to external annotation or language-model services without
appropriate authorization. Manual local coding is sufficient for these designs.

Honor the dataset's CC BY 4.0 attribution and the repository code's separate MIT
license. Suggested dataset attribution is: AgentLogs dataset by RISEN Lab,
licensed under CC BY 4.0. Publish derived codebooks, aggregate outputs, sampling
manifests subject to ethics approval, and reproducible analysis specifications
rather than redistributing unnecessary identifiable transcripts.

The theory lenses above are starting points for a literature search, not a
completed literature review or a verified novelty claim. The three supplied
sources and linked local schema documentation were read for this shortlist;
no broad literature review, data download of the full release, or statistical
pilot was performed.

## Source references

* [AgentLogs repository README](../README.md), current local checkout, read
  26 October 2026
* [AgentLogs dataset card](https://huggingface.co/datasets/risenlab/agentlogs),
  read 26 October 2026; use the
  [pinned release](https://huggingface.co/datasets/risenlab/agentlogs/tree/1.0-20261008)
  for analysis
* Richards, J., Horikawa, K., Fan, Y., Kashiwa, Y., and Wessel, M. (2026).
  [AgentLogs: A Dataset for Opening the Black Box of GitHub's Cloud Agent,
  arXiv v1](https://arxiv.org/html/2608.29204v1).
  DOI: [10.48550/arXiv.2608.29204](https://doi.org/10.48550/arXiv.2608.29204).
  The current repository citation uses the revised title ending
  "Cloud Agents on GitHub"; this shortlist distinguishes the supplied v1 text.
* [Schema reference](../docs/schema/README.md) and
  [release changelog](../CHANGELOG.md), read 26 October 2026
