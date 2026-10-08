# 维护者工作流

本文件承接 `CLAUDE.md` 的按需细节，避免每次开发都加载评测历史和低频操作。

## 变更前

先阅读 [设计](design.md) 与 [审查透镜](lenses.md)。前者定义产品边界，后者记录本仓库
反复出现的假断链、空断言与交接失败模式。

作者仓库同时用 spec-guard 管理自身开发（见 `CLAUDE.md`），这里的 hook 输出反映本仓库
initiative 状态，且来自已安装版插件，不是产品回归。用临时 Git 项目验证真实行为。

## 验证矩阵

每次改动先运行下面三条（与预推送 hook 一致；`validate.sh` 已包含清单一致性、检查器回归、
退役扫描与 Codex smoke 判决器自检）：

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

下列改动还必须运行相应聚焦检查：

| 改动范围 | 必跑检查 |
| --- | --- |
| `phase-guard.sh` 或激活/阶段逻辑 | `test-phase-guard.sh` 与 `test-verify-artifacts.sh` |
| `verify-artifacts.sh` 或共享判据 | `test-verify-artifacts.sh` 与 `test-phase-guard.sh` |
| Codex manifest 或 hook 注册 | `scripts/check-manifests.py`、`test-hook-entry.sh` 与 `evals/codex-plugin-smoke.sh --selftest` |
| 旧 tracker bridge 退役 | `test-retire-legacy-tracker-bridge.sh` 与 Proposal focused suites |
| Proposal preflight 或 proof | `test_proposal_promotion_proof.py`、`test_proposal_publication.py` 与完整 Proposal focused suites |
| `check-*.py` | `scripts/test-checkers.sh`，每条新判据都有一正一反用例 |
| `spec-digest.py` | 其 self-test、phase 与 verify 两侧回归 |
| Local 账本、归档恢复或 Proposal 收尾的 Local 适配器 | 下节的三个可选验收测试 |

macOS 上必须用 `/bin/bash`，以覆盖系统自带 bash 3.2；不要让 Homebrew bash 掩盖兼容问题。

已退役 initiative 的 `history-migration.py import --confirm` 只供维护者处理旧证据，
不作为 Claude 命令或 Codex skill 的日常用户入口。先运行只读 `preview` 并核对目标与冲突；
实际导入须取得针对本次写入的明确确认。现行用户入口只提供迁移预览。

## 可选验收测试（需固定外部运行时）

下面三个**刻意不在** `scripts/validate.sh` 与 CI 里：它们要调用已装好的固定 Epiq 运行时，
CI 没有、也不该有。但它们是唯一能证明适配器发出的参数名**被真实运行时接受**的东西 ——
其余测试用的是假传输，只锁住「我们发了什么」。运行时改名时假传输测试会全绿，而写入路径
静默失效（v0.41.0 的 GitHub `state` 大小写事故就是同一形状的另一个后端）。

```bash
SPEC_GUARD_EPIQ_RUNTIME=/path/to/verified/epiq python3 -B \
  plugins/spec-guard/hooks/test_local_ledger_acceptance.py
SPEC_GUARD_EPIQ_RUNTIME=/path/to/verified/epiq python3 -B \
  plugins/spec-guard/hooks/test_local_ticket_restore_acceptance.py
SPEC_GUARD_EPIQ_RUNTIME=/path/to/verified/epiq python3 -B \
  plugins/spec-guard/hooks/test_proposal_closeout_local_acceptance.py
```

改 `local_ledger_*`、`local_ticket_*`、`proposal_closeout_local.py` 或升级固定的 Epiq 版本时
跑它们，并把运行主机、运行时版本与结果记进发布证据；没跑就标未验证，不要留空。
未设 `SPEC_GUARD_EPIQ_RUNTIME` 时三者都报跳过并**退出 2**（2026-10-05 实测），
与通过的 `0`、失败的 `1` 分开 —— 把它们接进任何运行器时按 `2` 判「没跑起来」，不要当成通过。

`scripts/check-acceptance-wired.py` 只保证本节或某个运行器真的提到了每个验收测试；
它不证明这些测试跑过。

## 可选但高价值的检查

```bash
/bin/bash evals/module-namespace.sh --scaffold-only
```

`module-namespace` 的非 scaffold 模式会调用真实宿主；运行时不要同时测试、编辑或提交，
不能把“环境未就绪”误报为产品失败。
退出 0 表示有约定组进入模块目录、无约定组完整落在根目录，观察到路径差异；
**两次真实运行都是退出 2**：2026-10-02，以及 2026-10-05 在 v0.42.0 发布后的复跑 —— 后者是
`_preflight.sh` 三条前提首次全部满足的一次（装着的插件内容 = 仓库 HEAD 的 `plugins/spec-guard`，
工作区干净）。两次都是两组同样落进 `tasks/<module>/`（命名空间 2/2、根下 0），从无退出 0 的记录。
README 与 concepts 的问题①已据此改为「共用一份、没有保证」，不再断言「一定互相覆盖」。
**下一步不是再跑一次。** 对照组稳定使用模块目录意味着本脚本的退出 0 条件（对照组完整落在根目录）
在当前上游下可能不可达，也就是一个永远退 2 的判据；按 `docs/lenses.md` C3，该回头重新定义判据
（例如改验「约定是否让路径可预测」而不是「两组路径是否不同」），这是一次独立的设计工作。
模型运行后的退出 1 表示有约定组路径错误；退出 2 表示前置环境不满足、模型未运行完成
或对照不足（包括两组都进入模块目录）。脚手架自身无效时也会退出 1，须先修夹具。

## Codex 本地安装与真实 smoke

Codex 不把插件的 `commands/` 当作斜杠命令加载（2026-09-28 核实 codex-cli 0.154.0）：`.codex-plugin/plugin.json`
只声明 `skills` 与 `hooks`；Codex 描述插件组件的结构（`PluginDetail`）只有技能、hook、应用、MCP 服务器、应用模板与定时
任务，没有命令。`commands` 只出现在“从其他 agent 导入配置”的迁移结构里，CLI 没有对应入口，本次未验证。因此 Codex
用户的入口是 `spec-guard-ops` 等 skill；`commands/*.md` 里的 Codex 根目录解析只服务于这类导入后的副本。

插件管理器安装的是 marketplace 解析出的副本，不会自动读取当前 Git 工作区。先查看实际来源：

```bash
codex plugin marketplace list
codex plugin list --json
```

第一次从本地源码安装的标准流程是：

```bash
codex plugin marketplace add /absolute/path/to/spec-guard-plugin
codex plugin add spec-guard@spec-guard-marketplace
```

若 `spec-guard-marketplace` 已指向一个发布版，不要在活跃会话中替换它来测试开发源码；应在
隔离的 Codex 配置/机器中安装候选，或先明确备份并恢复原 marketplace。安装或升级后开启新会话，
在 `/hooks` 审核并信任 `UserPromptSubmit`，再运行：

```bash
/bin/bash evals/codex-plugin-smoke.sh \
  --plugin-id spec-guard@spec-guard-marketplace \
  --expected-source /absolute/path/to/spec-guard-plugin/plugins/spec-guard
```

退出码：`0` 为本次临时消费者项目的宿主机器记录含有效阶段注入，`1` 为已执行但输出无效，
`2` 为未观察到执行或安装、登录、信任、来源不匹配。`codex exec --json` 未公开 hook 事件时，
smoke 只读取匹配本次 thread id 与项目路径的 Codex 会话记录；该宿主内部格式不可用或变化时保守返回 `2`。

## 提交前

可安装预推送 hook：

```bash
/bin/bash scripts/install-git-hooks.sh
```

它在每次推送前跑 `validate.sh`、phase-guard 与 verify-artifacts 三套检查。推送里只有删除远端引用（如删已合并
分支）或推 tag 时跳过检查，并打印跳过原因：这两种推送不带新内容，tag 打在已验证的合并提交上。只要同一次推送里
有一个分支更新，就照常全跑，失败照常拦截。改了钩子文本后重新运行安装脚本，本机的 `.git/hooks/pre-push` 才会更新。

提交前检查改动只包含当前目标、没有密钥，并运行与改动面对应的验证。不要把不相关重构、版本发布
或消费者项目状态塞进同一个维护提交。

## PR 状态

改动已完成且本地验证通过时，默认创建普通 PR，等待 CI 与评审；不把草稿当成运行 CI 的前置步骤。
只有工作尚未完成或用户明确要求时才创建草稿 PR。草稿不会因 CI 通过而自动解除合并阻挡；
工作完成后须显式转为 Ready for review。
若本次开发绑定了 Local 事项，创建 PR 后记录其地址与覆盖范围；合并后按
`plugins/spec-guard/references/workflow-checkpoints.md` 核对合并提交、验证结果与事项剩余范围，
满足关闭条件才关闭并读回。PR 合并本身不代表 Local 事项已关闭。
