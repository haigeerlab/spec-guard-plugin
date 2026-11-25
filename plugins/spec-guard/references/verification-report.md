# 合并前验证报告 `spec-guard.verification/v1`

新流程模块合并前，由**非作者**照回归文档逐条执行（⑦），写一份 JSON 报告。报告由执行方（autopilot）写在它自己的证据目录，
例如 `~/.autopilot/evidence/<owner>__<repo>/<patchId>.verification.json`；spec-guard 只读它、判断它是否成立，成立再记下结论。
判据只有一处：`hooks/verification.py check`。本文写报告长什么样，问题代码的完整说明见插件根目录 `interface.json` 的 `verification`。

## 三步

1. **记作者**：开工后，写代码的会话运行 `python3 -B hooks/verification.py author --project <项目> --module <id>`。
   会话 id 只从环境变量读（Claude Code 的 `CLAUDE_CODE_SESSION_ID`、Codex 的 `CODEX_THREAD_ID`），记在公共 git 目录 `spec-guard/authors/<id>.json`，不进提交。
2. **校验**：`verification.py check --project <项目> --module <id> --report <报告> --json`，只读；退出 0 成立，1 不成立，3 判不了（例如没有作者记录）。
3. **记结论**：`verification.py record … --report <报告>` 先预览，加 `--confirm` 才写到公共 git 目录 `spec-guard/verification/<id>.json`。

多模块需求的整体联调回归（`spec/usage/<需求>.regression.md`）把 `--module <id>` 换成 `--usage <需求>`，报告里 `module` 写 `null`、`usage` 写需求名；作者取「涉及的模块」各自作者的合集。

## 字段

报告级：

| 字段 | 内容 |
|---|---|
| `schema` | 固定 `spec-guard.verification/v1` |
| `module`／`usage` | 模块 id 或需求名，另一个写 `null` |
| `regression` | `{document, sha256}`：回归文档的路径与整份文档原始字节的 sha256（用 `regression_view --json` 给出的 `sha256`） |
| `base`、`head` | merge-base 与被验证的提交 |
| `patchId` | `git diff <base> <head> \| git patch-id --stable` 的第一列 |
| `executor` | `{sessionId, host, vendor, sameVendorAsAuthor}`：执行者会话；不能是作者 |
| `verdict` | `pass`／`pass-with-notes`／`fail` |
| `cases` | 每条用例一项，见下 |
| `notes` | 意见：`[{title, detail, location, evidence}]`，`location` 是 `文件:行` 或用例编号；会被自动开成后续 issue |

用例级（`cases` 的每一项）：

| 字段 | 内容 |
|---|---|
| `id`、`method` | 用例编号与执行方式，要与回归文档一致 |
| `result` | `pass`／`fail`／`baseline-fail`（改动前就失败，不算阻断） |
| `failCategory` | 只在 `fail` 时写：`run-failure`（失败的运行）、`user-bug`（用户会遇到的 bug，附复现）、`check-failure`（跑不过的检查）、`wrong-doc`（改错的文档） |
| `baselineCommit` | 只在 `baseline-fail` 时写：改动前的提交（`base` 或其祖先） |
| `evidence` | `[{type, path, sha256, source}]`；`type` 为 `log`／`screenshot`／`file`／`user-quote`；`path` 可以是绝对路径或相对报告所在目录；`source` 只在 `user-quote` 时写（用户原话的出处） |

## 怎样算成立

- 回归文档没变（`regression.sha256` 对得上），文档里每条用例都有结果，报告里没有多出来的用例，执行方式一致；
- `manual` 用例有用户原话（`user-quote` 且写了 `source`）；
- `fail` 属于四类之一并附证据；风格、命名、要未来改动才成立的风险只能写进 `notes`；
- `baseline-fail` 附改动前的提交与证据；
- 结论跟着用例走：有 `fail` 就只能是 `fail`；没有 `fail`、有意见是 `pass-with-notes`；都没有是 `pass`；
- 执行者不是作者记录里的会话；
- `patchId` 等于当前补丁（默认分支与 HEAD 的 merge-base 到 HEAD），rebase 后补丁不变就照样成立。

证据文件、`base..head` 的提交在本机读不到时不判不成立，只列进 `unverified`。

## 例子

```json
{
  "schema": "spec-guard.verification/v1",
  "module": "export-csv",
  "usage": null,
  "regression": {"document": "tasks/export-csv/regression.md", "sha256": "3f1c…（64 位）"},
  "base": "9a0e…（40 位）",
  "head": "c71b…（40 位）",
  "patchId": "5d2a…（40 位）",
  "executor": {"sessionId": "verifier-7", "host": "codex", "vendor": "openai", "sameVendorAsAuthor": false},
  "verdict": "pass-with-notes",
  "cases": [
    {"id": "R1", "method": "command", "result": "pass", "failCategory": null, "baselineCommit": null,
     "evidence": [{"type": "log", "path": "R1.log", "sha256": "…", "source": null}]},
    {"id": "R2", "method": "manual", "result": "pass", "failCategory": null, "baselineCommit": null,
     "evidence": [{"type": "user-quote", "path": "R2-quote.txt", "sha256": "…", "source": "会话 3c9e，2026-11-26 10:02"}]},
    {"id": "R3", "method": "script", "result": "baseline-fail", "failCategory": null, "baselineCommit": "9a0e…",
     "evidence": [{"type": "log", "path": "R3-base.log", "sha256": "…", "source": null}]}
  ],
  "notes": [{"title": "列名可以更清楚", "detail": "导出表头用了内部字段名", "location": "src/export.py:42", "evidence": null}]
}
```

## 记下之后

- `/map --json` 每个模块的 `verification` 给出 `{verdict, patchId, notes, reportSha256, current}`；`current` 为真且结论不是 `fail` 才算过。
- 合并是 auto 的模块，算过就当最终 gate 已过（合并后补勾）；合并由用户决定的模块，验收消息写明结论。
- 远端合并硬卡读不到本机的 git 目录，执行方另把「结论＋patchId＋报告 sha256」写进机器人证据评论，两边都要对上。
