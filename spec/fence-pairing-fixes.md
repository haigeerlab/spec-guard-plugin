# Spec: fence-pairing-fixes

<!-- spec-guard: review approved 12d42f9fd656 -->

## 目标

插件读 Markdown 时要跳过代码块（```` ``` ```` 或 `~~~` 围起来的一段）里的示例。有三处判断「代码块在哪结束」时只比行首前 3 个字符，
下面两种写法会让代码块提前结束，后面的示例被当成正文：

- 外层 4 个反引号、里面包着 3 个反引号的示例；
- 代码块里出现 ```` ```python ```` 这类带语言名的行（按 Markdown 它不是结尾）。

三处（2026-10-28 在 `main` `00cf11c9` 上核对）：

| 位置 | 管什么 | 读错的后果 |
|---|---|---|
| `hooks/documentation_baseline.py` `_visible_lines`（账本 B5WE8BZ） | 文档基线表；`documentation_impact`、`documentation_verification` 也导入它 | 示例表被当成真表，报「不止一张表」或读进错误的行 |
| `hooks/module_stage.py` `review_marker_lines` | 找 Spec / Plan 的批准标记；批准指纹（`review_digest`）据此排除标记行，`review_mark.py` 据此改写标记 | 示例里的标记被当成真标记：批准状态、阶段提示可能判断错 |
| `hooks/proposal_submit.py` `_headings` | 找 Proposal 的 `## ` 标题 | 示例里的标题被当成真章节 |

`capability_map._visible_lines` 与 `module_scope._visible` 在 0.84.2 已按 Markdown 配对：结尾要同一种字符、不短于开头、后面只有空白。
本模块让这三处用同一规则。

给谁用：开了文档基线的项目、写 Spec / Plan 时放了代码块示例的用户、提交 Proposal 的用户。

登记：需求来自用户本人（2026-10-28，「把 B5WE8BZ 写成需求总结」，确认「说完了」），不需要回告。账本 B5WE8BZ 在本模块合并后关闭。
说明：登记时写的是「未实测有真实项目因此出错，需要时再排」，到现在也没有出错报告；这次是用户主动要做。

## 边界

**总是做**

- 每处先写一个在旧代码上失败的测试（4 个反引号包 3 个；代码块里出现带语言名的 ```` ``` ```` 行），确认红了再改，改完转绿。
- 能直接调用 `capability_map._visible_lines` 的就调用，不再各写一份判定。
- `review_marker_lines` 是 phase-guard 与 verify-artifacts 共用的判据：按项目规则两边都补正反回归（`test-phase-guard.sh`、`test-verify-artifacts.sh`）。
- 发版前按 `docs/release-process.md`「发布前」做；发版后按「发布」「发布后核对」做，证据写进 `docs/releases/v0.85.2-*.json`。

**先问**

- 发现某处换成新规则会改变一个**正常写法**文件的解析结果（不只是修好错误写法）时。
- 发版任一步失败时，停下说明，不改用别的路子。

**不做**

- 不改代码块之外的解析逻辑；不碰 `capability_map`、`module_scope`（已经是对的）；不改 `spec-digest.py` 的指纹算法。
- 不顺手统一仓库里其他读 Markdown 的写法。

## 要你确认的假设

1. **补丁版本 0.85.2**：只修解析的边界情况，接口（`interface.json`）不变。CHANGELOG 0.85.2 写这三处，再在「文档」一节带上 #424（Codex 0.164 重新批准 hook）。
2. **批准指纹只在错误写法下会变**：`review_digest` 排除的是标记行，判定改了以后，只有带「4 包 3」这类代码块、且代码块里写着标记示例的 Spec / Plan，
   指纹才会变（会出现一次「批准后已修订」提示）。正常写法的文件不受影响；本仓库 162 份 Spec / Plan 改前改后的批准状态逐个比对，必须全部一致。
3. 分支 `claude/fence-pairing-fixes`，从 `main`（`00cf11c9`）开出；一个 PR，版本号放在最后一个提交。

## 验收标准

- AC1：`documentation_baseline._visible_lines` 按 Markdown 配对；基线、影响、核验三个功能各有一个「4 包 3」或「带语言名的行」的测试，改前红、改后绿。
- AC2：`module_stage.review_marker_lines` 按 Markdown 配对；`test_module_stage`（或对应 Python 测试）加先红后绿的用例；
  `test-phase-guard.sh` 与 `test-verify-artifacts.sh` 各加一正一反：代码块里的示例标记不算、代码块外的真标记照常识别。
- AC3：`proposal_submit._headings` 按 Markdown 配对，加先红后绿的测试。
- AC4：本仓库所有 Spec / Plan 的批准状态改前改后一致（脚本逐个比对，结果写进 todo）。
- AC5：两份 `plugin.json` 为 `0.85.2`，README 中英 `--ref v0.85.2`，`check-readme-sync.py`、`check-manifests.py` 通过，CHANGELOG 有 `## [0.85.2]` 一节；
  `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 在 macOS 系统 `/bin/bash` 上通过并记录主机；改了 `.sh` 就跑 ShellCheck。
- AC6（合并后）：在合并提交上打 `v0.85.2` tag、发 Release；Claude 与 Codex 安装副本刷新并核对（Codex 先在命令行版 `codex` 的 `/hooks` 重新批准，再跑 smoke）；
  四份发布证据与本模块最后一个检查点的勾在一个收尾 PR 里提交；关闭账本 B5WE8BZ。

## 未决问题

- **Q1：范围？**
  - A（推荐）：三处一起修。同一种错误，批准标记那处影响批准状态。
  - B：只修账本那一条（文档基线）。
- **Q2：批准标记那处按「共享判据」处理吗？**
  - A（推荐）：按。phase-guard 与 verify-artifacts 两边都补正反回归（AC2），多一些测试工作量。
  - B：只补 Python 单元测试。
- **Q3：合并后的发版几步，要不要你逐步点头？**
  - A（推荐）：批准本模块最终验收时，同时授权「合并后按发布流程一次做完」：我先核对合并状态，再打 tag、发 Release、刷新并核对两个宿主、开收尾 PR；
    只在某一步失败时停下。Codex 的 hook 重新批准要你在命令行版 `codex` 里点，到那一步我开好终端请你批准。收尾 PR 只改 `docs/releases/` 和 todo 末行、
    CI 通过时，按 2026-10-13 的长期授权由我合并。
  - B：每一步单独问你。

**已定（2026-10-28，用户）：Q1 A；Q2 A；Q3 A。**

## 文档建议

CHANGELOG 写 0.85.2 一节（含 #424）；README 中英只改 `--ref`。使用者文档不用改（行为只是修好边界情况）。项目没有文档基线。

## 变更记录
