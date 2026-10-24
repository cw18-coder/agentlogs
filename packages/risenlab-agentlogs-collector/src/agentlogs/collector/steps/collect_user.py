from typing import Any

from ..priorities import PRIORITIES
from ..runtime.resolver import ResolveJob, Resolver, Step
from ..resources import UserDraft
from ..runtime.processor import Result
from ..state.resource import ResourceRef


def user_reference_draft(
    payload: object,
    relations_to: dict[str, list[ResourceRef]] | None = None,
) -> UserDraft:
    user_id = payload.get("id") if isinstance(payload, dict) else None
    if user_id in (0, None, ""):
        user_id = None
    graphql_id = payload.get("node_id") if isinstance(payload, dict) else None
    if graphql_id in (None, ""):
        graphql_id = None
    if user_id is None and graphql_id is None:
        raise ValueError("user reference is missing id and graphql id")
    return UserDraft(
        id=user_id,
        graphql_id=graphql_id,
        relations_to=relations_to or {},
    )


class ResolveUser(Resolver):
    resource_type = "user"
    graphql = (
        Step(
            resolve_using="graphql_node_id",
            required_aliases=("graphql_id",),
            priority=PRIORITIES["collect_user_graphql_node_id"],
            fetch=lambda api, aliases: api.request_user_from_node_id(aliases["graphql_id"]),
        ),
        Step(
            resolve_using="graphql_mint_global_id",
            required_aliases=("id",),
            priority=PRIORITIES["collect_user_graphql_mint_global_id"],
            fetch=lambda api, aliases: api.request_user_from_minted_id(int(aliases["id"])),
        ),
        Step(
            resolve_using="graphql_login",
            required_aliases=("login",),
            priority=PRIORITIES["collect_user_graphql_login"],
            fetch=lambda api, aliases: api.request_user_from_login(aliases["login"]),
        ),
    )
    rest = (
        Step(
            resolve_using="rest_id",
            required_aliases=("id",),
            priority=PRIORITIES["collect_user_rest_id"],
            fetch=lambda api, aliases: api.request_user_from_id(int(aliases["id"])),
        ),
    )

    @classmethod
    def resolved(cls, body: dict[str, Any], job: ResolveJob) -> Result:
        login = body.get("login")
        if str(body.get("type") or "").lower() == "bot" and login:
            html_url = body.get("html_url")
            if html_url:
                slug = str(html_url).rstrip("/").rsplit("/", 1)[-1]
                derived = f"{slug}[bot]"
                if login != derived and login not in {"Copilot", "Claude", "Codex"}:
                    raise ValueError(f"Bot login {login!r} does not match {derived!r}")
                login = derived
            elif not str(login).endswith("[bot]"):
                login = f"{login}[bot]"
        return Result(
            resources=[
                UserDraft(
                    id=None if body.get("id") is None else body["id"],
                    login=login,
                    graphql_id=body.get("node_id"),
                    payload=body,
                    metadata={"found_using": job.resolve_using},
                )
            ]
        )

    @classmethod
    def unfound(cls, job: ResolveJob) -> Result:
        return Result(
            resources=[
                UserDraft(
                    id=job.aliases.get("id"),
                    login=job.aliases.get("login"),
                    graphql_id=job.aliases.get("graphql_id"),
                    found=False,
                )
            ]
        )
