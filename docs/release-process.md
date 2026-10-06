# 发布流程

发布的完成标准不是 Git 已推送，而是 marketplace 中安装的插件副本与已发布内容一致。

## PR 节奏

`main` 受分支保护，每个改动都要经 PR 与 CI，所以 PR 的切分决定了合并次数：

1. **一个模块一个 PR。** Spec、Plan、代码、文档与 CHANGELOG 在同一个 PR 里；需要发版时，版本号改动（下节第 1、2 条）
   放在这个 PR 的最后一个提交，不再另开发版 PR。合并后在合并提交上打 tag。
2. **一个需求跨多个模块时，一个需求发一次版**：只在最后一个模块的 PR 里改版本号。在此之前合并的模块让 `main` 的代码
   领先于已发布版本：Codex 钉在 tag 上不受影响，Claude 的 marketplace 源是 `main` 上的 `./plugins/spec-guard`，但按版本号
   判断是否更新，版本号不变时不会拉到中间状态。
3. **发版后只开一个收尾 PR**：发布证据、该模块最后一个检查点的勾与零星更正，在全部宿主核对完成后一次提交，不拆成几个。
   不要把它们留到下一个模块的 PR：那期间模块在 `main` 上仍显示进行中，`add-module` 也会因“做到一半”拒绝插入；
   也不要只留在本地，避免随 worktree 丢失。
4. **合并由用户进行。** 只改证据文件的收尾 PR 是否在 CI 通过后自动合并，只按用户的明确长期授权执行。

## 发布前

1. 确认 Claude 与 Codex manifest 的版本一致，并把 README 里 Codex 安装命令的 `--ref` 改成新版本；
   `check-readme-sync.py` 会拦下不一致。
2. 按用户影响更新 `CHANGELOG.md`。
3. 若存在破坏性行为变更，先提供迁移指南；严格串行变更见
   [migration-strict-serial.md](migration-strict-serial.md)。
4. 运行 `/bin/bash scripts/validate.sh` 与受改动面影响的聚焦测试。
5. 若修改 Codex manifest、hook 或技能，运行 `/bin/bash evals/codex-plugin-smoke.sh --selftest`。
6. 最终待发布提交还须在 macOS 用系统 `/bin/bash` 跑上述完整校验，以及
   `plugins/spec-guard/hooks/test-phase-guard.sh` 和
   `plugins/spec-guard/hooks/test-verify-artifacts.sh`。记录运行主机与结果；
   Ubuntu CI 不能替代 macOS Bash 3.2 验证，无法运行时标为未验证。

## 发布

1. 提交已验证的变更。
2. 创建匹配版本的 Git tag。
3. 推送提交和 tag。
4. 刷新 marketplace，并在新会话中安装/启用更新后的插件。
5. 在 `/hooks` 审核 `UserPromptSubmit`，然后从临时消费者项目运行真实 Codex smoke。

不同宿主的 marketplace 刷新命令与权限策略可能不同；先以 `codex plugin marketplace --help`
或宿主 UI 显示的当前命令为准，不要假定工作区 HEAD 已被运行时自动采用。

## 发布后核对

```bash
codex plugin marketplace list
codex plugin list --json
```

核对 `spec-guard@spec-guard-marketplace` 已启用、版本正确且 `source.path` 是预期来源。真实
smoke 的 `--expected-source` 必须与该字段精确一致：本地 marketplace 通常是候选工作区，Git
marketplace 则是 Codex 的缓存副本。不要猜测这两个路径相同。

如果开发分支与安装副本版本不同，先判定是“待发布候选”还是“本地分支落后于发布线”。不要仅为
消除版本差异改 manifest；应在独立的合并或发布任务中决定版本与变更来源。
