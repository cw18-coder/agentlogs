from typing import TypedDict


class User(TypedDict, total=False):
    id: int
    login: str
    type: str
    created_at: str
    node_id: str
    html_url: str


class UserRef(TypedDict, total=False):
    id: int
    login: str
    node_id: str
    type: str


class RepositoryRef(TypedDict, total=False):
    id: int
    full_name: str


class Label(TypedDict, total=False):
    name: str


class AutoMerge(TypedDict, total=False):
    enabled_by: UserRef | None
    merge_method: str
    commit_title: str
    commit_message: str


class PullRequestBranch(TypedDict, total=False):
    ref: str
    sha: str
    repo: RepositoryRef | None


class PullRequest(TypedDict, total=False):
    id: int
    node_id: str
    number: int
    title: str
    body: str | None
    state: str
    locked: bool
    draft: bool
    user: UserRef | None
    labels: list[Label]
    active_lock_reason: str | None
    created_at: str
    updated_at: str
    closed_at: str | None
    merged_at: str | None
    assignees: list[UserRef]
    requested_reviewers: list[UserRef]
    head: PullRequestBranch
    base: PullRequestBranch
    author_association: str
    auto_merge: AutoMerge | None
    merged: bool
    mergeable: bool | None
    mergeable_state: str
    merged_by: UserRef | None
    maintainer_can_modify: bool
    additions: int
    deletions: int
    changed_files: int


class ReferencedWorkflow(TypedDict, total=False):
    path: str
    sha: str
    ref: str


class WorkflowRun(TypedDict, total=False):
    id: int
    name: str | None
    node_id: str
    check_suite_id: int
    check_suite_node_id: str
    head_branch: str | None
    head_sha: str
    path: str
    run_number: int
    run_attempt: int
    referenced_workflows: list[ReferencedWorkflow] | None
    event: str
    status: str | None
    conclusion: str | None
    workflow_id: int
    created_at: str
    updated_at: str
    actor: UserRef
    triggering_actor: UserRef
    run_started_at: str
    repository: RepositoryRef
    head_repository: RepositoryRef
    head_repository_id: int
    display_title: str


class TimelineEvent(TypedDict, total=False):
    event: str
    created_at: str
    actor: UserRef | None
    assignee: UserRef | None
    label: Label | str | None
    commit_id: str
    message: str
