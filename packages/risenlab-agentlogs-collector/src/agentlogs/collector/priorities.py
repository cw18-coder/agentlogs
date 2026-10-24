COLLECT_REPOSITORY_TASKS_PAGE_PRIORITY = 281
COLLECT_PULL_REQUEST_TIMELINE_PAGE_PRIORITY = 131

PRIORITIES: dict[str, int] = {
    "seed_repositories": 299,
    "collect_repository_tasks": 280,
    "collect_session_log": 260,
    "collect_task": 240,
    "collect_pull_request_graphql_global_id": 193,
    "collect_pull_request_graphql_number_repo": 192,
    "collect_pull_request_graphql_mint_global_id": 191,
    "collect_pull_request_rest_number_repo": 190,
    "collect_workflow_run": 140,
    "collect_pull_request_timeline": 130,
    "collect_user_graphql_node_id": 125,
    "collect_user_graphql_mint_global_id": 123,
    "collect_user_graphql_login": 122,
    "collect_user_rest_id": 121,
}
