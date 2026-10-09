# Todo: docs-reorganization

- [x] Task 1：合并协作拆分总结到迁移说明 — 并入“版本与兼容”一节（接口 1.x、发布顺序、升级以 agent-relay CHANGELOG 为准、接口 2.0 的发布顺序）；修正过时的“保留到 0.53.x”与安装命令的 `--ref` 说明
- [x] Task 2：删除文档并清理现行引用 — 删除 47 个文件；现行引用改了 `docs/release-process.md` 与 `docs/reports/README.md` 两处；`docs/releases/*.json`（已发布证据）、`docs/retirements/`（退役记录）、`spec/`、`tasks/`、`CHANGELOG.md` 里的历史引用不改；全部发布记录仍通过 `release-evidence.py validate`
- [ ] Task 3：约定块移到 `docs/convention-block.md`，改 `check-readme-sync.py` 与其回归
- [ ] Checkpoint 1（gate）：第一批评审；链接核对、validate 通过，推送并开 PR，合并由用户进行
- [ ] Task 4：中文 README（按大纲重写，命令逐条对照）
- [ ] Task 5：英文 README（章节一一对应，语言切换行）
- [ ] Task 6：CONTRIBUTING 报 bug 与双语规则、maintainer-workflow 同步、核对 bug.yml
- [ ] Checkpoint 2（gate）：第二批评审；链接核对、validate 通过，推送并开 PR，合并由用户进行
- [ ] Task 7：`docs/commands.md`（从 workflow 拆出）
- [ ] Task 8：`docs/troubleshooting.md`
- [ ] Task 9：`docs/design.md` 中文架构说明，文档导航标明维护者文档
- [ ] Checkpoint 3（gate）：第三批评审；链接核对、validate 通过，推送并开 PR，合并由用户进行
- [ ] Task 10：下次发版时补证据
