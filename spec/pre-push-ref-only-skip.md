# Spec: pre-push-ref-only-skip

## Objective

`scripts/install-git-hooks.sh` 生成的 pre-push 钩子不读 git 传入的推送清单，每次推送都跑 validate.sh、phase-guard、
verify-artifacts 三套检查，约 3 分钟。删除已合并分支、推送打在已验证合并提交上的 tag 时，这些检查验证不了任何新东西，
却让收尾步骤各等一次。来源：「spec-guard 插件根目录解析检查」会话观测到的候选，用户 2026-10-09 选定，并决定只推 tag
也跳过。

读者：本仓库维护者（人或 agent）。

## Assumptions

用户于 2026-10-09 确认：

1. 钩子从 stdin 读取 `<local ref> <local sha> <remote ref> <remote sha>` 行。local sha 全为 0 的行是删除；remote ref
   以 `refs/tags/` 开头的行是推 tag。所有行都是删除或推 tag 时跳过三套检查，打印一行跳过原因；只要有一行更新分支就照常
   全跑，失败照常拦截。清单为空时照常全跑。
2. 只改 `scripts/install-git-hooks.sh` 生成的钩子文本与 `scripts/test_pre_push_environment.py`；用真实的本地推送测试。
3. `docs/maintainer-workflow.md` 的“提交前”一节写明跳过规则。
4. 合并后重新运行 `scripts/install-git-hooks.sh`，替换本机由它装的 `.git/hooks/pre-push`。
5. 插件发布包不变：不改版本号、不写 CHANGELOG 版本标题，随统一发版 0.55.0；最后一项是 0.55.0 发版时补证据。

## Requirements

1. 生成的钩子先读完 stdin 再决定；跳过时输出包含“跳过”与原因（删除 / tag），退出 0，不调用任何检查。
2. 回归：只删远端分支时三套检查都不调用且删除成功；只推 tag 时不调用且 tag 到达远端；分支与 tag 一起推时三套都调用；
   现有用例（普通 checkout、linked worktree、任一检查失败拦截）保持通过。新断言先在现有钩子上变红，并手动改坏确认会变红。
3. 文档写明跳过规则与“分支推送照常全跑”。

## Commands

```bash
/bin/bash scripts/validate.sh
python3 -B scripts/test_pre_push_environment.py
```

## Boundaries

- Always：钩子只依赖 `bash` 与 `git`；测试只用临时目录里的本地仓库。
- Ask first：推送、PR；重新安装本机钩子之外的任何本机文件改动。
- Never：分支推送跳过检查；改插件发布包内容或版本号。

## Success criteria

1. 删除分支、只推 tag 的推送不再等待检查。
2. 任何分支更新仍跑三套检查，失败仍拦截推送。

## Open questions

无。
