# GitHub MCP Tool Inventory v0.1

Status: GITHUB_MCP_TOOL_INVENTORY_PASS

## Boundary

This inventory records the GitHub MCP tool surface visible in TrueFoundry.

No GitHub write, destructive, merge, branch, repository creation, or file mutation tool was executed during inventory.

This is not yet DRF-governed GitHub enforcement. It is a tool-surface inventory and policy-mapping checkpoint.

## Classification Rules

```text
READ_ONLY        -> ALLOW
LOW_RISK_WRITE   -> REQUEST_REVIEW
DESTRUCTIVE      -> DENY
ADMIN            -> DENY
UNKNOWN          -> DENY
```

## Tool Classification

| Tool | Classification | Conservative decision | Reason |
| --- | --- | --- | --- |
| add_comment_to_pending_review | LOW_RISK_WRITE | REQUEST_REVIEW | Adds review comment to pending PR review. |
| add_issue_comment | LOW_RISK_WRITE | REQUEST_REVIEW | Writes comment to issue or PR thread. |
| add_reply_to_pull_request_comment | LOW_RISK_WRITE | REQUEST_REVIEW | Adds reply to PR review comment. |
| create_branch | LOW_RISK_WRITE | REQUEST_REVIEW | Creates new branch; not destructive but mutates repo state. |
| create_or_update_file | DESTRUCTIVE | DENY | Creates or modifies repository file; can affect code, CI, config, secrets. |
| create_pull_request | LOW_RISK_WRITE | REQUEST_REVIEW | Opens PR and may trigger CI/review workflows. |
| create_repository | ADMIN | DENY | Creates repo/account/org resource. |
| delete_file | DESTRUCTIVE | DENY | Deletes repository file. |
| fork_repository | LOW_RISK_WRITE | REQUEST_REVIEW | Creates fork under account/org; mutates account state. |
| get_commit | READ_ONLY | ALLOW | Reads commit details. |
| get_file_contents | READ_ONLY | ALLOW | Reads file or directory contents. |
| get_label | READ_ONLY | ALLOW | Reads repository label. |
| get_latest_release | READ_ONLY | ALLOW | Reads release metadata. |
| get_me | READ_ONLY | ALLOW | Reads authenticated user profile. |
| get_release_by_tag | READ_ONLY | ALLOW | Reads release by tag. |
| get_tag | READ_ONLY | ALLOW | Reads git tag details. |
| get_team_members | READ_ONLY | ALLOW | Reads team member usernames visible to credentials. |
| get_teams | READ_ONLY | ALLOW | Reads accessible team metadata. |
| issue_read | READ_ONLY | ALLOW | Reads issue details. |
| issue_write | LOW_RISK_WRITE | REQUEST_REVIEW | Creates or updates issue. |
| list_branches | READ_ONLY | ALLOW | Lists repository branches. |
| list_commits | READ_ONLY | ALLOW | Lists commits. |
| list_issue_fields | READ_ONLY | ALLOW | Reads issue field definitions. |
| list_issue_types | READ_ONLY | ALLOW | Reads supported issue types. |
| list_issues | READ_ONLY | ALLOW | Lists issues. |
| list_pull_requests | READ_ONLY | ALLOW | Lists pull requests. |
| list_releases | READ_ONLY | ALLOW | Lists releases. |
| list_repository_collaborators | READ_ONLY | ALLOW | Lists repository collaborators visible to credentials. |
| list_tags | READ_ONLY | ALLOW | Lists git tags. |
| merge_pull_request | DESTRUCTIVE | DENY | Merges code into target branch; potentially irreversible operational effect. |
| pull_request_read | READ_ONLY | ALLOW | Reads pull request details. |
| pull_request_review_write | LOW_RISK_WRITE | REQUEST_REVIEW | Creates/submits/deletes PR review or resolves threads. |
| push_files | DESTRUCTIVE | DENY | Pushes multiple files in a commit; can alter code/config/CI. |
| request_copilot_review | LOW_RISK_WRITE | REQUEST_REVIEW | Requests automated PR review; mutates PR/review workflow state. |
| run_secret_scanning | UNKNOWN | DENY | Reads/analyzes potentially sensitive content; deny until sensitive-read policy exists. |
| search_code | READ_ONLY | ALLOW | Searches code. |
| search_commits | READ_ONLY | ALLOW | Searches commits. |
| search_issues | READ_ONLY | ALLOW | Searches issues. |
| search_pull_requests | READ_ONLY | ALLOW | Searches pull requests. |
| search_repositories | READ_ONLY | ALLOW | Searches repositories. |
| search_users | READ_ONLY | ALLOW | Searches users. |
| sub_issue_write | LOW_RISK_WRITE | REQUEST_REVIEW | Adds sub-issue relationship; mutates issue structure. |
| update_pull_request | LOW_RISK_WRITE | REQUEST_REVIEW | Updates PR metadata/state. |
| update_pull_request_branch | DESTRUCTIVE | DENY | Mutates PR branch with latest base changes; can trigger CI and alter code state. |

## Checkpoint Result

```text
GITHUB_MCP_TOOL_INVENTORY_PASS
```

Acceptance status:

```text
GitHub official MCP connected in TrueFoundry.
tools/list succeeded.
Exact GitHub MCP tool names captured.
Tools classified into READ_ONLY / LOW_RISK_WRITE / DESTRUCTIVE / ADMIN / UNKNOWN.
Conservative flat policy drafted.
No GitHub write/destructive tool called.
Boundary documented: inventory only, not DRF-governed GitHub enforcement yet.
```

