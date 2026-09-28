# Proposal tracker read

`proposal-tracker-read` 只读取并核验一个已发布 Proposal 的普通 GitHub Issue 或 GitLab
Issue。调用方必须先通过 `proposal-publication` 得到远端默认分支的 `published` Proposal，
然后显式传入平台和目标容器；此模块不会自行从 worktree、Git remote 或 Issue 标题推断它们。

```python
from proposal_tracker_read import as_json, read_tracker

# published.proposal 仅应来自已固定的 remote-default publication result.
result = read_tracker(published.proposal, "github", "owner/repository")
safe_result = as_json(result, "github", "owner/repository")
```

GitLab 的目标容器是正整数 project id：

```python
result = read_tracker(published.proposal, "gitlab", 17)
```

读取器用只读请求列出 Issue：GitHub 为 `gh issue list --state all --limit 1000`，GitLab 为
`glab api projects/<id>/issues?state=all&per_page=100&page=<n>` 的默认 GET，逐页读取至短页，最多 10 页。
两个平台都不依赖服务端搜索：最终身份只来自正文中单独一行的完整 Proposal marker，在本地逐行匹配。
GitLab 的 `search=` 匹配不到 HTML 注释里的文字（GitLab 15.3.2 实测，2026-09-28），而 marker 正是一行
HTML 注释。关闭的 Proposal Issue 同样会被读到。读满上限仍未结束、CLI、认证、网络、JSON 或容器字段
无法核验时报 `unknown`，不会猜测。

安全 JSON 结果只有：

- `verified`：包含 `platform`、`target`、`issueId` 与唯一 `stage`。
- `absent`：完整候选集没有完整 marker。
- `invalid`：包含稳定诊断码 `tracker-contract-invalid`，表示唯一性、容器、legacy marker
  或 Proposal 标签契约不符合。
- `unknown`：包含稳定诊断码 `tracker-read-unavailable`，表示读取完整性无法证明。

JSON 不包含 Issue 正文、评论、Proposal marker、raw API response、token、远端 URL 或原始
CLI 错误。`verified` 只是 tracker 事实核验；它不批准 Proposal、不创建任务、不改变标签，
也不代表能力图已晋级。
