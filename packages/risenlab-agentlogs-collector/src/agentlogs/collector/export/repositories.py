from typing import Any, ClassVar

from agentlogs.schema import Repository, RepositoryLanguage, RepositoryMetric
from .exporter import Exporter
from .common import format_task_reference, format_user_reference
from ..state import ResourceRecord
from ..datetime import parse_utc_datetime

INT64_NONE_SIGNAL = 2**63 - 1

def convert_str_nullable(dict: dict[str, Any], key: str) -> str | None:
    value = dict[key]
    if value is None or value == "":
        return None

    return str(value)


def convert_bool(dict: dict[str, Any], key: str) -> bool:
    value = dict[key]
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() == "true":
        return True
    if isinstance(value, str) and value.lower() == "false":
        return False
    raise ValueError(f"Field '{key}' is not a boolean ({value})")

def convert_int(dict: dict[str, Any], key: str) -> int:
    value = int(dict[key])

    if value >= INT64_NONE_SIGNAL:
        raise ValueError(f"Field '{key}' is too large ({value})")
    
    return value

def convert_int_nullable(dict: dict[str, Any], key: str) -> int | None:
    value = dict[key]
    if value is None or value == "":
        return None

    value = int(value)

    if value == INT64_NONE_SIGNAL:
        return None
    elif value > INT64_NONE_SIGNAL:
        raise ValueError(f"Field '{key}' is too large ({value})")
    
    return value

class RepositoryExporter(Exporter[Repository]):
    resource_type: ClassVar[str] = "repository"
    expand_relations: ClassVar[list[str]] = ["repository_tasks", "repository_owner"]

    def get_record_type(self) -> type[Repository]:
        return Repository

    def format_resource(
        self, 
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]]
    ) -> Repository | None:
        assert isinstance(resource.payload, dict)
        payload = resource.payload

        tasks_collected_partial_or_full = (
            resource.metadata.get("unarchived_tasks_found") != "false" or
            resource.metadata.get("archived_tasks_found") != "false"
        )
        if not tasks_collected_partial_or_full and len(resource.relations_from.get("repository_tasks", [])) > 0:
            raise ValueError("Repository has tasks but could not collect tasks")

        if not tasks_collected_partial_or_full:
            return None

        if "full_name" not in resource.aliases:
            raise ValueError("Repository is missing full_name alias")

        owners = expanded_resources_from.get("repository_owner", [])
        if len(owners) == 0:
            raise ValueError("Repository must have owner")
        if len(owners) > 1:
            raise ValueError("Repository has more than one owner")
        owner = format_user_reference(owners[0])

        tasks = [
            format_task_reference(related_resource)
            for related_resource in expanded_resources_from.get("repository_tasks", [])
            if related_resource.metadata.get("unattached") != "true"
        ]

        return Repository(
            full_name=resource.aliases["full_name"],
            owner=owner,

            agent_tasks=tasks,

            archived=convert_bool(payload, "isArchived"),
            disabled=convert_bool(payload, "isDisabled"),
            locked=convert_bool(payload, "isLocked"),
            fork=convert_bool(payload, "isFork"),

            homepage=convert_str_nullable(payload, "homepage"),
            has_wiki=convert_bool(payload, "hasWiki"),
            license=convert_str_nullable(payload, "license"),
            main_language=payload["mainLanguage"],
            default_branch=convert_str_nullable(payload, "defaultBranch"),
            size=convert_int(payload, "size"),

            created_at=parse_utc_datetime(payload["createdAt"]),
            pushed_at=parse_utc_datetime(payload["pushedAt"]),
            updated_at=parse_utc_datetime(payload["updatedAt"]),
            last_commit_at=parse_utc_datetime(last_commit) if (last_commit := convert_str_nullable(payload, "lastCommit")) else None,
            last_commit_SHA=convert_str_nullable(payload, "lastCommitSHA"),

            forks_count=convert_int(payload, "forks"),
            stargazers_count=convert_int(payload, "stargazers"),
            watchers_count=convert_int_nullable(payload, "watchers"),
            commits_count=convert_int_nullable(payload, "commits"),
            branches_count=convert_int_nullable(payload, "branches"),
            releases_count=convert_int_nullable(payload, "releases"),
            contributors_count=convert_int_nullable(payload, "contributors"),
            total_issues_count=convert_int_nullable(payload, "totalIssues"),
            open_issues_count=convert_int_nullable(payload, "openIssues"),
            total_pull_requests_count=convert_int_nullable(payload, "totalPullRequests"),
            open_pull_requests_count=convert_int_nullable(payload, "openPullRequests"),

            labels=payload["labels"],
            topics=payload["topics"],
            languages=[
                RepositoryLanguage(language=name, bytes=size)
                for name, size in payload["languages"].items()
            ],

            blank_lines=convert_int_nullable(payload, "blankLines"),
            code_lines=convert_int_nullable(payload, "codeLines"),
            comment_lines=convert_int_nullable(payload, "commentLines"),
            metrics=[
                RepositoryMetric(
                    language=metric_payload["language"],
                    blank_lines=convert_int(metric_payload, "blankLines"),
                    code_lines=convert_int(metric_payload, "codeLines"),
                    comment_lines=convert_int(metric_payload, "commentLines"),
                )
                for metric_payload in payload["metrics"]
            ],
        )