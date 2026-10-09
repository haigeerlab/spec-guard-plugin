# Todo: docs-reorganization

- [x] Task 1：合并协作拆分总结到迁移说明 — 并入“版本与兼容”一节（接口 1.x、发布顺序、升级以 agent-relay CHANGELOG 为准、接口 2.0 的发布顺序）；修正过时的“保留到 0.53.x”与安装命令的 `--ref` 说明
- [x] Task 2：删除文档并清理现行引用 — 删除 47 个文件；现行引用改了 `docs/release-process.md` 与 `docs/reports/README.md` 两处；`docs/releases/*.json`（已发布证据）、`docs/retirements/`（退役记录）、`spec/`、`tasks/`、`CHANGELOG.md` 里的历史引用不改；全部发布记录仍通过 `release-evidence.py validate`
- [x] Task 3：约定块移到 `docs/convention-block.md`，改 `check-readme-sync.py` 与其回归 — readme-sync 用例 9 条（含“SYNC 区只在 README 里 → 报错”“英文 README 的 --ref 落后 → 报错”），现有检查器上 4 条红；变异（检查器读回 README）4 条变红；`docs/release-process.md` 改为中英两份 README 同步改 `--ref`
- [x] Checkpoint 1（gate）：第一批评审；链接核对、validate 通过，推送并开 PR，合并由用户进行 — 一次性脚本核对全部站内链接：现行文档里的 15 个失效链接都在 `docs/retirements/`，指向早已退役的模块 Spec，本模块之前就存在，退役记录原样保留；`spec/`、`tasks/`、`CHANGELOG.md` 的 16 个按决定不改
- [x] Task 4：中文 README（按大纲重写，命令逐条对照）— 按 12 节大纲重写；撤掉旧迁移说明的链接（文件保留在 `docs/migrations/`）。命令对照：
  - `setup-convention` 的 `--replace`、`--dry-run`，`teardown-convention` 的 `--dry-run`：对照 `plugins/spec-guard/commands/*.md` 的 argument-hint
  - `phase`、`verify-artifacts`、`add-module`、`config`：对照命令文件的 description
  - Claude 更新与卸载（`claude plugin marketplace update`、`claude plugin update`、`claude plugin uninstall`）、Codex 的 `codex plugin remove`、`codex plugin marketplace upgrade`/`remove`、`codex plugin list`：对照本机 CLI 的 `--help`
  - Codex 的 `ref` 改 `~/.codex/config.toml` 后 `marketplace upgrade`：历次发版的实际做法
  - python3 故障提示原文（“python3 不可用”“python3 无法运行”）：对照 `phase-guard.sh` 第 55、71 行
- [x] Task 5：英文 README（章节一一对应，语言切换行）— `README.en.md` 13 节与中文版一一对应，另加一句“除 README 外链接的文档为中文”；两份顶部有语言切换行
- [x] Task 6：CONTRIBUTING 报 bug 与双语规则、maintainer-workflow 同步、核对 bug.yml — `bug.yml` 去掉已退役的 tracker 字段与错误的 hook 路径，改为用 `/spec-guard:phase`、`verify-artifacts` 的输出；`check-readme-sync.py` 的 `--ref` 正则改为在反引号处结束（README 表格里命令写在行内代码中），先加用例在旧检查器上为红；Spec 补写 `docs/releases/0.9.0-local-candidate.json` 的 2 处历史链接
- [x] Checkpoint 2（gate）：第二批评审；链接核对、validate 通过，推送并开 PR，合并由用户进行 — 链接核对：除 `docs/retirements/` 原有的 15 个外没有新的失效链接；README 用到的 `docs/workflow.md#命令对照` 锚点存在
- [x] Task 7：`docs/commands.md`（从 workflow 拆出）— 21 条命令按用途分组写参数、作用、输出与退出码，逐份对照 `plugins/spec-guard/commands/*.md`；命令对照表从 `docs/workflow.md` 搬来，workflow 那一节只留链接。`scripts/check-command-table.py` 改核对 `docs/commands.md`，新用例“表只在 docs/workflow.md 里 → 报错”与“每个命令都在表里”在旧检查器上为红
- [x] Task 8：`docs/troubleshooting.md` — 阶段提示不出现、MAP_INVALID（报错原文取自 `capability_map.py`，含模块表数量）、UNKNOWN、python3 故障（原文取自 `phase-guard.sh`）、Codex 不加载、其他提示（activeModule 无效、Project config invalid、Paused、Suspended 等）
- [x] Task 9：`docs/design.md` 中文架构说明，文档导航标明维护者文档 — 部件、数据流、两个宿主的差异、不变量，保留 Proposal／本地边界、项目配置、文件布局（File layout，插件与检查器注释仍按此名引用）与退役边界；`CLAUDE.md` 的描述同步；两份 README 的常用命令、故障排查改链到新文档，示例补上计数行（第二轮联调审查 #276 指出），导航加“维护者”一组
- [x] Checkpoint 3（gate）：第三批评审；链接核对、validate 通过，推送并开 PR，合并由用户进行 — 链接核对除 `docs/retirements/` 原有 15 个外无新增；新文档的锚点都存在；退役名称扫描通过
- [ ] Task 10：下次发版时补证据
