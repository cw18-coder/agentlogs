Optimizing Enterprise Total Cost of Ownership (TCO) and AI ROI: A Quantitative Analysis of LLM Model Selection and Tool Execution in Autonomous Cloud Software Engineering Agents

1. Introduction and Managerial Background

1.1 Managerial Problem Statement & Enterprise Context

Enterprise engineering leadership—including Chief Technology Officers (CTOs), Chief Information Officers (CIOs), and Vice Presidents of Engineering—faces severe economic and operational friction when deploying autonomous cloud software engineering agents (such as the GitHub Copilot cloud agent) across large-scale software development lifecycles. While generative artificial intelligence promises accelerated feature velocity, automated bug remediation, and reduced issue lead times, scaling autonomous agents introduces profound budget unpredictability and governance challenges.

At the core of this managerial challenge lies a structural economic transformation: shifting from traditional, predictable fixed seat-based developer licensing (e.g., standard flat monthly user fees) to dynamic, metered usage-based platform consumption model metrics (ai_credits and tier allocations such as premium_requests). Under fixed seat licensing, enterprise software budgets remain deterministic regardless of developer usage intensity. In contrast, autonomous agent deployments consume variable cloud computing resources based on model parameters, context payload sizes, and execution duration.

The primary decision-making dilemma requires enterprise leaders to balance high-capability, high-cost frontier Large Language Models (LLMs)—such as Anthropic Claude Opus 4.5/4.6/4.8 or OpenAI GPT-5.4—against lower-cost, lighter model tiers (e.g., Claude Sonnet 4.5/4.6, GPT-5.3-Codex). High-capacity frontier models possess advanced reasoning capabilities necessary for navigating complex cross-file repository architectures. However, they incur steep token burn rates and heavy platform consumption charges. Conversely, relying exclusively on lower-tier models risks frequent reasoning breakdowns, unhandled syntax errors, and repetitive session retry loops, which silently inflate overall operational expenditures.

This unpredictability is driven by the structural mechanics of multi-turn autonomous session execution. Unlike static single-turn code completion, autonomous agents interact iteratively with the execution container. As agents inspect repository file trees, execute terminal commands, parse git logs, evaluate continuous integration (CI) workflow failures (workflow_runs), resolve pull request merge conflicts, and delegate complex sub-tasks to specialized sub-agents (repo_agents), context windows expand exponentially. Because transformer architectures re-index historical context on every interaction turn, re-transmitting accumulated conversation histories, system prompts, repository schemas, and intermediate tool responses creates compounding token accumulation costs.

In enterprise environments, unmonitored agent loops can cause extreme billing anomalies. Empirical trace data from production agent platforms reveals single-session consumption spikes reaching up to 404,727,350,000 ai_credits (or multi-turn sub-agent tasks exceeding 65,977,305,000 ai_credits), driven by recursive sub-agent delegation (repo_agents) and persistent CI failure retry loops.

Formulated within the framework of ESGCI Doctor of Business Administration (DBA) criteria (Assignment A01 and S01), this research addresses a vital managerial issue: enterprise technology executives lack empirical, data-driven frameworks to optimize the Total Cost of Ownership (TCO) and Return on Investment (ROI) of autonomous coding agents. Without quantitative evidence on how model selection, prompt context expansion, and tool execution modalities interact with task completion success rates and platform billing units, executive decisions rely on unverified heuristics, exposing organizations to unbudgeted cost expansion.

1.2 TCO, Cloud Credits (ai_credits), and ROI Challenges in Autonomous Coding Agents

Evaluating the TCO of enterprise autonomous cloud agents requires accounting for direct inference fees, platform metering units, and session execution overhead. In modern agent platforms (such as the GitHub Copilot cloud agent), billing and platform allocation are tracked through specific quantitative metrics:

* Platform Consumption Units (ai_credits): Abstracted financial units billed to enterprise accounts based on total model compute time, GPU runtime, and environment infrastructure utilization during agent session runs.
* Premium Request Allocations (premium_requests): Fixed enterprise quota allocations consumed per high-tier model request session (typically metered as discrete integer units, e.g., 1 allocation per high-tier session turn).
* Token Metrics (prompt_tokens, completion_tokens, cached_tokens): Quantitative token counters recording input processing volume, generated output payload, and context cache hits per API turn within an agent session.

A crucial operational distinction exists between two primary deployment modalities: Single-Turn Direct Inference (where an LLM generates code directly from a static prompt without environment interaction) and Multi-Turn Interactive Tool Execution (where an agent interactively calls environment tools such as file edits, git operations, terminal commands, sub-agent delegation, and GitHub issue/PR commenting).

Economic Dimension	Single-Turn Direct Inference Economics	Multi-Turn Tool-Assisted Execution Economics
Primary Cost Drivers	Base prompt_tokens and generated completion_tokens from a single static API payload. Fixed baseline consumption per request.	Accumulating prompt_tokens across N interactive turns, compounding history, tool output payload tokens, and ai_credits runtime duration.
Latency and Duration	Low, deterministic session duration (created_at to completed_at spans seconds).	High, variable duration; long-running asynchronous execution environments running repository builds, CI tests, and sub-agents (repo_agents).
Financial Risk Profile	Low direct token cost per turn; high hidden risk of developer rework due to unverified code outputs, missing context, and syntax errors.	Severe token compounding cost inflation; infinite loops or excessive tool execution iterations incur diminishing marginal success returns and rapid credit depletion.
Metered Unit Allocation	Typically billed via flat premium_requests or baseline token rates.	Dynamic billing shifting rapidly between premium_requests and massive metered ai_credits allocations.
ROI Characterization	High volume, low unit cost, but lower automated task resolution probability for complex architectural issues.	High unit cost per session; high ROI potential on complex tasks if tool iterations are bounded, but negative ROI if context compounding dominates.

2. Theoretical Foundations and Literature Review

2.1 Theoretical Framework: TCE, RBV, Bounded Rationality, and Context Expansion Trade-Offs

This research proposal is grounded in four theoretical lenses that explain the economic and computational dynamics of enterprise AI agents:

1. Transaction Cost Economics (TCE):
  * Theoretical Foundation: TCE posits that economic exchanges incur governance, coordination, and transaction friction overhead. In autonomous software engineering, transaction costs manifest as session governance friction—specifically the computational, token, and monetary overhead required to coordinate multi-turn agent execution, manage container permissions, process intermediate tool outputs, and evaluate intermediate steps.
  * Actionable Research Implication: Quantifies the exact economic boundary where session interaction overhead (governance transaction cost) exceeds the marginal economic value of automated task resolution.
2. Resource-Based View (RBV):
  * Theoretical Foundation: RBV identifies valuable, rare, inimitable, and non-substitutable resources as the primary drivers of firm competitive advantage. High-capability frontier LLM models (e.g., Claude Opus 4.5/4.8, GPT-5.4) represent strategic digital assets that offer superior contextual reasoning capabilities.
  * Actionable Research Implication: Evaluates whether deploying expensive, top-tier model reasoning assets provides a net economic ROI advantage over lower-cost model tiers when controlling for empirical task complexity.
3. Bounded Rationality:
  * Theoretical Foundation: Explains human and systemic decision-making limits under cognitive, information, and computational constraints. An LLM operating purely through direct weight inference is bounded by its static pre-trained weights and initial prompt context, unable to verify whether generated code compiles or passes repository tests without external execution feedback.
  * Actionable Research Implication: Predicts that equipping agents with interactive environmental tools (e.g., file edit, test runners, git diffs) breaks parameter-bound constraints through dynamic environmental feedback loops, increasing task resolution success.
4. Context Expansion Trade-Off Theory:
  * Theoretical Foundation: Addresses the cost-capacity trade-offs inherent in transformer context windows. As multi-turn agent sessions progress, historical system prompts, repository schemas, and tool execution logs accumulate, causing O(N) or O(N^2) growth in token consumption per turn.
  * Actionable Research Implication: Models the non-linear relationship between context window accumulation, token caching efficiency (cached_tokens / prompt_tokens), and net economic cost per resolved engineering task.

2.2 Direct Weight Inference vs Interactive Tool Execution Modalities

The cognitive and computational mechanisms of software generation differ fundamentally between direct LLM weight inference and interactive tool execution:

* Direct Weight Inference Modality: The model acts as a static text-to-code translator. It receives an initial natural-language issue description or prompt and emits a single completion response containing code changes. While computationally frugal in terms of immediate per-turn token consumption, it lacks an environmental feedback mechanism. If the initial code contains syntax errors, broken imports, or flawed logic, the task fails without self-correction, transferring the cognitive and financial burden of remediation back to human engineers.
* Interactive Tool Execution Modality: The agent operates within an active container environment (e.g., GitHub Copilot cloud agent container). It actively invokes environment execution tools, including:
  * File Operations: edit, file searches, reading repository trees.
  * Git and Platform Operations: Branching, committing, opening PRs, reviewing diffs, and executing reply_to_comment.
  * System and Integration Operations: Running terminal commands, inspecting GitHub Actions CI failures (workflow_runs), and delegating sub-tasks to custom sub-agents (repo_agents).

While interactive tool execution enables autonomous self-correction by allowing the agent to observe build errors and adjust its implementation, each tool call appends fresh observations to the prompt stream. Across multi-turn sessions, this multi-turn feedback loop creates exponential token context growth, driving up ai_credits usage and introducing potential financial inefficiency if tool iterations run unchecked.

3. Formal Research Questions & Quantitative Hypotheses

3.1 Baseline Research Questions and Hypotheses (RQ1 & RQ2)

Research Question 1 (RQ1)

* RQ1: How does LLM model selection (high-capability/high-cost frontier models versus lower-cost targeted models) impact task resolution success rates and net cost-per-successful-resolution in enterprise autonomous software engineering tasks?
* Hypothesis 1a (H1a): High-capability frontier models (e.g., Claude Opus 4.5, GPT-5.4) achieve a statistically significant higher task completion rate (state == 'completed') across complex engineering tasks compared to lighter, lower-cost models (e.g., Claude Sonnet 4.5/4.6, GPT-5.3-Codex).
* Hypothesis 1b (H1b): Despite higher absolute task completion rates, high-capability frontier models exhibit a higher net cost-per-successful-resolution (ai_credits / success) on low-to-medium complexity tasks compared to lighter models, establishing a clear economic threshold for dynamic model routing.
* Theoretical Justification (RQ1): Rooted in the Resource-Based View and Transaction Cost Economics, H1a and H1b evaluate whether the superior reasoning assets of frontier models generate sufficient marginal output value to justify their higher baseline consumption rates, or whether simpler tasks suffer from economic over-engineering when routed to top-tier LLMs.

Research Question 2 (RQ2)

* RQ2: What is the quantitative impact of prompt context expansion and prompt caching efficiency (cached_tokens / prompt_tokens) on total cloud consumption costs (ai_credits) across multi-turn agent sessions?
* Hypothesis 2a (H2a): Uncached prompt context expansion across multi-turn agent sessions drives a super-linear increase in total session token consumption and associated cloud credits (ai_credits).
* Hypothesis 2b (H2b): Higher prompt caching efficiency (cached_tokens / prompt_tokens > 0.50) significantly moderates total session cost growth, reducing net cost-per-successful-resolution without negatively impacting task completion probability.
* Theoretical Justification (RQ2): Grounded in Context Expansion Trade-off theory, these hypotheses quantify how context accumulation affects transaction costs in multi-turn AI interactions, testing whether token caching mechanisms successfully restore linear cost scaling in long-running agent sessions.

3.2 Research Question 3 (RQ3) and Tool Execution ROI Hypotheses (H3a & H3b)

Research Question 3 (RQ3)

To what extent does the execution modality—specifically, interactive tool-assisted session execution versus direct non-tool generation—influence task completion success and the net economic cost-per-successful-resolution (ai_credits / task success)?

Hypothesis 3a (H3a)

Agent tasks executed with interactive tool calls will exhibit a statistically significant higher probability of successful task completion (state == 'completed') compared to tasks executed without tool calls.

* Mathematical & Economic Justification for H3a: Let P(S) represent the probability of successful task resolution (\mathbb{I}(\text{state} = \text{'completed'}) = 1). Under direct non-tool execution (T=0), P(S|T=0) = P(\text{correct initial code synthesis}), which is strictly bounded by static model weights and initial prompt context parameters. Under interactive tool execution (T>0), the agent engages in k discrete error-correction feedback steps. The overall failure probability decreases conditionally with each feedback iteration:

P(\text{Failure} \mid T=k) = P(\text{Failure} \mid T=0) \times \prod_{i=1}^{k} \left( 1 - \gamma_i \right)

where \gamma_i > 0 represents the probability of identifying and rectifying a bug, syntax error, or failing test given the i-th tool execution response (e.g., compiler feedback, test output parsing, file verification). Because \prod_{i=1}^{k} (1 - \gamma_i) < 1, the overall success probability:

P(S \mid T=k) = 1 - P(\text{Failure} \mid T=k) > P(S \mid T=0)

is strictly greater than direct inference, formally validating H3a.

Hypothesis 3b (H3b)

The net cost-per-successful-resolution (ai_credits / success) exhibits a non-linear (inverted U-shaped) relationship with tool call intensity, such that moderate tool usage maximizes economic ROI, whereas excessive tool iterations incur diminishing marginal returns due to token compounding in multi-turn feedback loops.

* Mathematical & Economic Justification for H3b: Let C(k) represent total session consumption cost in ai_credits as a function of total tool call count k. Total session cost is composed of baseline fixed container overhead C_0 and accumulating turn costs:

C(k) = C_0 + \sum_{i=1}^{k} \left( \alpha \cdot \text{prompt\_tokens}_i + \beta \cdot \text{completion\_tokens}_i \right)

Because historical conversation logs are re-transmitted on each interaction turn i, input tokens accumulate additively: \text{prompt\_tokens}_i = \text{prompt\_tokens}_0 + \sum_{j=1}^{i-1} \text{tool\_output\_tokens}_j. Consequently, total session cost C(k) expands convexly with respect to k:

\frac{\partial C(k)}{\partial k} > 0 \quad \text{and} \quad \frac{\partial^2 C(k)}{\partial k^2} > 0

Concurrently, task resolution probability P(S \mid k) exhibits strictly diminishing marginal returns with respect to tool iterations (\frac{\partial P}{\partial k} > 0, but \frac{\partial^2 P}{\partial k^2} < 0), as persistent agent retries beyond an optimal threshold reflect unrecoverable reasoning loops, ambiguous task specifications, or broken container dependencies.

Define Net Economic ROI as E(k) = \frac{P(S \mid k)}{C(k)}. The first-order condition for optimal tool usage yields:

\frac{\partial E(k)}{\partial k} = \frac{\frac{\partial P(S \mid k)}{\partial k} C(k) - P(S \mid k) \frac{\partial C(k)}{\partial k}}{[C(k)]^2} = 0 \implies \frac{\frac{\partial P(S \mid k)}{\partial k}}{P(S \mid k)} = \frac{\frac{\partial C(k)}{\partial k}}{C(k)}

To evaluate the shape of the net economic ROI profile, we evaluate the second derivative \frac{\partial^2 E(k)}{\partial k^2} at the stationary point k^*:

\frac{\partial^2 E(k)}{\partial k^2} = \frac{\frac{\partial^2 P}{\partial k^2} C(k) - P(S \mid k) \frac{\partial^2 C}{\partial k^2}}{[C(k)]^2}

Since C(k) > 0, P(S \mid k) > 0, \frac{\partial^2 P}{\partial k^2} < 0 (concave success function), and \frac{\partial^2 C}{\partial k^2} > 0 (convex cost function), the numerator is strictly negative:

\frac{\partial^2 E(k)}{\partial k^2} < 0

This establishes second-order sufficiency, formally demonstrating that Net Economic ROI E(k) is strictly concave with a unique local maximum k^* (yielding an inverted U-shaped ROI curve). Correspondingly, the reciprocal net cost-per-successful-resolution function:

E(k)^{-1} = \frac{\text{ai\_credits}}{\text{success}} = \frac{C(k)}{P(S \mid k)}

is strictly convex (\frac{\partial^2 E(k)^{-1}}{\partial k^2} > 0), establishing a U-shaped cost curve with a distinct minimum cost inflection point at k^*.

4. Quantitative Research Design & Analytical Methodology

4.1 Dataset Description and Sampling Strategy (AgentLogs Dataset)

The empirical evaluation uses the AgentLogs dataset repository (Richards et al., 2026; arXiv:2608.29204v1; hosted on Hugging Face at risenlab/agentlogs). While the initial method paper (arXiv:2608.29204v1, release v0.2, cutoff July 2026) established the data collection methodology across 549,239 sessions and 35,810 repositories (56.7\text{ GB}), this quantitative proposal utilizes the expanded AgentLogs v1.0 release snapshot (1.0-20261008, release date 8 October 2026, cutoff 30 August 2026).

The v1.0-20261008 snapshot captures multi-turn session event traces from the GitHub Copilot cloud agent platform across public GitHub repositories with over 10 stars (seeded via SEART GitHub Search).

+-----------------------------------------------------------------------------------+
|                        AgentLogs v1.0 Relational Structure                        |
+-----------------------------------------------------------------------------------+
|  repositories (N = 1,861,300 total; 40,565 public repos with agent tasks)        |
|   └── agent_tasks (N = 363,624 tasks; 353,432 with active sessions)               |
|        └── agent_sessions (N = 635,886 sessions; 624,668 complete parsed logs)    |
|             ├── agent_session_logs (N = 75,631,136 events & tool calls)           |
|             ├── pull_requests (N = 317,878) └── pull_request_timelines (9.07M)    |
|             └── workflow_runs (N = 554,496 GitHub Actions CI executions)          |
+-----------------------------------------------------------------------------------+


The refined analytical sample filters incomplete session runs lacking log files (log_found == false) or missing outcome records. The final empirical dataset comprises:

* Agent Sessions: N = 635,886 total recorded sessions (624,668 complete parsed session logs).
* Agent Tasks: N = 363,624 distinct engineering tasks across 40,565 public GitHub repositories.
* Granular Session Log Events: 75,631,136 log entry records capturing prompt payloads, reasoning traces, model strings (claude-sonnet-4.6, claude-opus-4.5, gpt-5.4, gpt-5.3-codex), token usage breakdowns, and individual tool call payloads.
* Integrated Platform Entities: 317,878 agent-authored pull requests, 9,070,939 PR timeline events, 554,496 GitHub Actions CI workflow runs, and 857,428 user/bot entities. Total dataset footprint spans 64.9\text{ GB} in sharded Parquet format.

4.2 Measurement Operationalization Matrix

Theoretical Construct	Variable Name	Data Type / Unit	Dataset Source Table	Econometric Role (DV / IV / Control)
Task Completion Success	state	Binary Categorical ('completed' = 1 vs 'cancelled'/'failed' = 0)	agent_sessions.state	Dependent Variable (DV) (H1a, H2b, H3a)
Net Cost-per-Success	cost_per_resolution	Continuous Ratio (\frac{\text{ai\_credits}}{\mathbb{I}(\text{state} = \text{'completed'})})	agent_sessions / Derived	Dependent Variable (DV) (H1b, H3b)
Total Cloud Resource Cost	ai_credits	Continuous / Consumption Units	agent_sessions.usage.credits	Dependent Variable (DV) / Cost Metric
Premium Quota Consumption	premium_requests	Continuous / Integer Count	agent_sessions.premium_requests	Control / Metering Variable
Input Context Volume	prompt_tokens	Continuous / Integer Token Count	agent_session_logs.usage.prompt_tokens	Independent Variable (IV) / Control
Output Generation Volume	completion_tokens	Continuous / Integer Token Count	agent_session_logs.usage.completion_tokens	Control Variable
Context Cache Hits	cached_tokens	Continuous / Integer Token Count	agent_session_logs.usage.prompt_tokens_details.cached_tokens	Independent Variable (IV)
Prompt Caching Efficiency	cache_ratio	Continuous Ratio (\frac{\text{cached\_tokens}}{\text{prompt\_tokens}})	Derived from agent_session_logs	Independent Variable (IV) (H2b)
Tool Execution Modality	tool_usage_flag	Binary Dummy (1 = \text{tool calls present}, 0 = \text{direct non-tool})	agent_session_logs	Independent Variable (IV) (H3a)
Tool Execution Intensity	tool_call_count	Continuous / Integer Count (k)	agent_session_logs	Independent Variable (IV) (H3b)
Model Selection Tier	model	Nominal Categorical (claude-sonnet-4.6, claude-opus-4.5, gpt-5.4, gpt-5.3-codex, etc.)	agent_sessions.model	Independent Variable (IV) (H1a, H1b) / Control
Session Lead Time Duration	session_duration	Continuous / Seconds (completed_at minus created_at)	agent_sessions	Dependent Variable (DV) / Control
Repository Popularity / Size	stars	Continuous / Integer Count	repositories.stars	Control Variable

4.3 Econometric Specifications and Data Pipeline Architecture

Endogeneity and Selection Bias Correction (Heckman Two-Stage / IV Estimation)

A critical methodological challenge in evaluating tool execution ROI is endogenous selection bias: complex, bug-heavy software tasks naturally trigger higher tool execution counts (k), whereas trivial tasks are often solved in fewer turns. Modeling task completion P(\text{state}_i = \text{'completed'}) purely as a function of tool_usage_flag or tool_call_count without controlling for task selection creates severe omitted variable bias.

To isolate the true causal effect of tool calls on resolution success, we implement a Heckman Two-Stage Selection Model paired with an Instrumental Variable (IV) framework.

1. First Stage (Selection Equation): We model the propensity of a session i to utilize tool calls (\text{tool\_usage\_flag}_i = 1) using repository-level tool enablement policies and initial task prompt complexity (\text{prompt\_complexity}_i, measured as linguistic entropy and initial token length) as instrumental variables (Z_i). Z_i directly predicts tool activation but affects task completion only through tool interaction:

\operatorname{P}(\text{tool\_usage\_flag}_i = 1 \mid Z_i, X_i) = \Phi\left( \delta_0 + \delta_1 \cdot Z_i + \delta_2 \cdot \ln(\text{stars}_i) + \delta_3 \cdot \text{model\_tier}_i + \mathbf{\gamma} \mathbf{X}_i \right)

From Stage 1, we compute the Inverse Mills Ratio (\hat{\lambda}_i). 2.  Second Stage (Outcome Equation): The estimated Inverse Mills Ratio (\hat{\lambda}_i) is included as a selection-correction control term in the structural outcome models.

Specification 1: Binary Logistic Regression with Selection Correction (H3a)

To test Hypothesis 3a, a selection-corrected binary logistic regression model estimates the odds ratio of successful task completion (\text{state}_i = \text{'completed'}), incorporating repository-level clustered standard errors (\text{Cluster}_{repo}):

\operatorname{logit}\left(P(\text{state}_{ij} = \text{'completed'})\right) = \beta_0 + \beta_1 \cdot \text{tool\_usage\_flag}_{ij} + \beta_2 \cdot \text{model\_tier}_{ij} + \beta_3 \ln(\text{prompt\_tokens}_{ij}) + \beta_4 \ln(\text{stars}_j) + \rho \hat{\lambda}_{ij} + \varepsilon_{ij}

where i indexes individual agent sessions and j indexes public GitHub repositories. Standard errors are robustly clustered at the repository level (j). A statistically significant positive coefficient (\beta_1 > 0, p < 0.001) confirms H3a, validating that interactive tool execution causally increases task completion probability when controlling for selection bias.

Specification 2: Quadratic Tobit Model with Selection Correction (H3b - Inverted U-Shaped ROI)

To evaluate Hypothesis 3b, the dependent variable is operationalized as the net cost-per-successful-resolution:

Y_{ij}^* = \frac{\text{ai\_credits}_{ij}}{\mathbb{I}(\text{state}_{ij} = \text{'completed'})}

Because failed sessions (\text{state}_{ij} \neq \text{'completed'}) do not yield a successful resolution, Y_{ij}^* is strictly left-censored or undefined for zero-success outcomes. We fit a Quadratic Tobit regression model censoring unresolvable sessions at the 99th percentile cost threshold (C_{max}):

Y_{ij}^* = \gamma_0 + \gamma_1 \cdot \text{tool\_call\_count}_{ij} + \gamma_2 \cdot (\text{tool\_call\_count}_{ij})^2 + \gamma_3 \cdot \text{model\_tier}_{ij} + \gamma_4 \cdot \text{cache\_ratio}_{ij} + \rho \hat{\lambda}_{ij} + \eta_{ij}

\text{cost\_per\_resolution}_{ij} = \begin{cases} Y_{ij}^* & \text{if } \text{state}_{ij} = \text{'completed'} \\ C_{max} & \text{if } \text{state}_{ij} \neq \text{'completed'} \end{cases}

All standard errors are clustered at the repository level (\text{Cluster}_{repo}). An inverted U-shaped net ROI profile (corresponding to a U-shaped cost-per-success curve) requires a statistically significant negative linear coefficient (\gamma_1 < 0) and a positive quadratic coefficient (\gamma_2 > 0, p < 0.01). The empirical optimal tool execution boundary (k^*) is calculated via the first-order derivative:

k^* = -\frac{\gamma_1}{2 \gamma_2}

Specification 3: TCO Log-Linear Model & Cox Lead Time Survival Analysis

* Total Cloud Resource Consumption (TCO): Log-linear regression estimating total log-transformed platform credits (\ln(\text{ai\_credits}_{ij})) against token volumes, execution duration, and tool call frequency, clustered by repository (\text{Cluster}_{repo}).
* Session Lead Time Duration: A Cox Proportional Hazards survival model treating task completion (\text{completed\_at}) as the terminal event:

h(t \mid \mathbf{X}_{ij}) = h_0(t) \exp\left( \lambda_1 \cdot \text{tool\_call\_count}_{ij} + \lambda_2 \cdot \text{model\_tier}_{ij} + \lambda_3 \cdot \text{cache\_ratio}_{ij} \right)

evaluating hazard ratios for session resolution lead time across model tiers and tool execution intensity levels.

High-Performance Data Pipeline Architecture

Given the 64.9\text{ GB} footprint of the AgentLogs v1.0 release, data processing uses an optimized columnar execution stack:

1. DuckDB Query Engine: Performs fast SQL aggregations, table joins, and filtering across sharded Parquet files (repositories, agent_tasks, agent_sessions, agent_session_logs, pull_requests, workflow_runs) directly on disk without memory overflow.
2. Polars Lazy DataFrames: Executes multi-turn session windowing, regex parsing of tool call strings (e.g., classifying edit, reply_to_comment, terminal execution, sub-agent delegation), and continuous calculation of session-level cache_ratio metrics.
3. Econometric Estimation Suite: Processed analytical DataFrames are ingested into Python statsmodels and PySurvival libraries for clustered Logistic, Tobit, and Survival model estimation.

5. Practical Managerial & Theoretical Contributions

5.1 Governance Frameworks for CTO/CIO Decision-Making: The Enterprise Agent Governance Protocol (EAGP)

To convert empirical cost-inflection models into automated enterprise administrative controls, we formulate the Enterprise Agent Governance Protocol (EAGP). The EAGP matrix translates quantitative token thresholds, model parameters, and execution metrics into real-time platform enforcement policies:

Governance Dimension	Empirical Metric & Trigger Condition	Automated Platform Enforcement Action	Enterprise TCO / ROI Objective
Dynamic Model Routing	Initial prompt complexity score \le \tau_{low} OR routine task tag (refactor, docs).	Route session to lower-cost model tier (claude-sonnet-4.6, gpt-5.3-codex).	Prevents economic over-engineering; conserves premium_requests allocations.
Model Fallback Escalation	Task failure (\text{state} \neq \text{'completed'}) on low-cost model OR complexity score > \tau_{high}.	Escalate session to top-tier frontier model (claude-opus-4.5, gpt-5.4).	Maximizes task success probability for complex architectural issues.
Tool Iteration Bounding	Tool call count k exceeds empirical inflection point (k > k^*).	Terminate automated tool iterations; trigger mandatory human-in-the-loop review.	Eliminates infinite agent retry loops; caps convex ai_credits accumulation.
Cache Optimization Enforcer	Prompt caching efficiency ratio \text{cache\_ratio} < 0.30 across T > 3 turns.	Re-structure system prompt headers; force token context cache re-indexing.	Moderates super-linear prompt context expansion costs.
Sub-Agent Privilege Control	Sub-agent delegation invocation (repo_agents) detected in untrusted repo context.	Demote sub-agent privileges; require explicit developer confirmation before fork.	Prevents exponential multi-agent billing spikes (>400\text{B} ai_credits).
CI Retry Loop Interceptor	CI workflow failure retries (workflow_runs) exceed N \ge 3 consecutive runs.	Pause agent container execution; log diagnostic summary to PR timeline.	Halts persistent build failure retry loops in continuous integration runs.

5.2 Contributions to Information Systems and Software Engineering Economics Literature

This research proposal advances the body of knowledge across Information Systems (IS), AI governance, and software engineering economics:

1. Extension of Transaction Cost Economics to AI Agent Governance: Extends TCE theory by operationalizing session governance friction and context re-indexing overhead as measurable transaction costs in autonomous human-agent systems.
2. Empirical Grounding of Resource-Based View in Generative AI: Quantifies the precise economic conditions under which frontier LLM reasoning assets deliver net positive ROI, establishing empirical task complexity thresholds where top-tier models outperform lower-cost alternatives.
3. Formalization of Agent Modality Economics: Fills a major gap in software engineering literature by shifting focus from outcome-only metrics (e.g., merged PR counts) to process economics, proving the U-shaped cost curve driven by interactive tool execution feedback loops.

6. Institutional Alignment, Ethical Governance, and Guideline Compliance

6.1 Institutional Guidelines & Evaluation Criteria Compliance (A01–A06, S01)

This proposal strictly complies with all institutional DBA requirements set forth in the ESGCI program guides (A01–A06) and the S01 Submission & Evaluation Guide:

ESGCI Assignment Code	Program Requirement & Scope	Proposal Execution & Structural Mapping
A01: Research Topic	4 Credits, 2–4 pages, M+7 months. Identifies significant managerial problem grounded in recent research.	Formulated in Section 1.1 as a formal managerial problem statement addressing enterprise TCO and AI ROI challenges.
A02: Literature Review	8 Credits, 35–45 pages, M+11 months. Comprehensive coverage, theoretical framework, formal hypotheses.	Theoretical foundations established in Section 2.1 (TCE, RBV, Bounded Rationality, Context Expansion) and Section 3.
A03: Research Design	10 Credits, 60–80 pages, M+14 months. Detailed methodology, sampling, statistical tests.	Quantitative methodology detailed in Section 4.1 (AgentLogs dataset), Section 4.2 (Matrix), and Section 4.3 (Econometrics).
A04: Data Collection & Analysis	14 Credits, 110–155 pages, M+26 months. Empirical findings, hypothesis testing, limitations.	Executed using 635,886 agent sessions; econometrics specified in Section 4.3 for Logistic/Tobit hypothesis testing.
A05: Draft Dissertation	40 Credits, 150–200 pages, M+31 months. Comprehensive draft incorporating managerial & theoretical contributions.	Synthesised in Section 5.1 (EAGP Governance Framework) and Section 5.2 (Theoretical Additions to IS Literature).
A06: Final Dissertation	80 Credits, 150–200 pages, M+35 months. Revised submission meeting full checklist and formal standards.	Institutional compliance mapped in Section 6.1 and data ethics confirmed in Section 6.2.
S01: Evaluation & Submission Guide	Guideline compliance: APA 7th style, PDF conversion, Drive hosting for files >50\text{ MB}, plagiarism rules, grading scale.	Mapped in Section 6.1 detailing mentor plagiarism rules, Drive links for >50\text{ MB} files, and A–E grade scale mapping.

Specific Institutional Guideline Compliance (S01 Directives)

In accordance with S01_Submission_&_Evaluation_Guide.pdf, the execution of this research strictly adheres to three mandatory operational directives:

1. Guideline 2 (Plagiarism Check Regulations): In strict accordance with S01 Guideline 2, official plagiarism checks are conducted exclusively by the assigned thesis mentor at the conclusion of the research process. In compliance with institutional policy, student self-checks are explicitly prohibited prior to final mentor submission.
2. Guideline 3 (Large File Deliverable Hosting): Because the refined analytical dataset and empirical estimation artifacts (64.9\text{ GB}) exceed the platform upload threshold (50\text{ MB}), all compressed Parquet files and analytical notebooks are hosted on institutional Google Drive storage, with shareable access links embedded within the submitted PDF documentation.
3. Institutional Evaluation & Grading Scale: Evaluation follows ESGCI's 5-point grading scale: A (89–98%, Outstanding Pass), B (79–88%, Excellent Pass), C (69–78%, Good Pass), D (50–68%, Average Pass), and E (<50%, Fail/Resubmit required). Supervisors assign numeric indicators 1 ("Proceed to next assignment") or 0 ("Need improvement / rework required") alongside letter grades to signal resubmission status.

6.2 Data Governance, Licensing, and APA Style Alignment

* APA 7th Edition Formatting: All in-text citations, theoretical descriptions, variable notations, and tabular layouts strictly follow APA 7th edition guidelines.
* Data Governance, Open-Science Compliance, and Licensing: The empirical AgentLogs dataset is utilized in accordance with its Creative Commons Attribution 4.0 International (CC BY 4.0) license. The accompanying analytical software package (risenlab-agentlogs) and execution scripts are governed under the open-source MIT License. Repository metadata sampling strictly complies with GitHub Acceptable Use Policies and REST API rate limits. All user data is restricted to publicly available GitHub metadata, ensuring institutional research ethics standards.