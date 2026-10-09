# Spec: validate-parallel-files

## Objective

`validate.sh` 的回归段把约 50 个测试文件一个接一个串行跑，本机一次全套约 200 秒；verify-and-commit 的全档、pre-push 与
CI 每次都要等它。这些测试大多各用各的临时目录，互不相干，可以同时跑。本模块把回归段改为分组并行，让全套明显变快，
同时不少跑一步、不漏报一次失败。来源：slow-test-speedup 收尾时列出的候选，用户 2026-10-09 确认写入能力图。

读者：本仓库维护者。

## 测出来的现状（2026-10-09，本机 8 核）

- 完整 `validate.sh`：200.7 秒（user 119.3、sys 115.9），当时负载 15–18；输出 960 行、29 个段落标题。
- 逐条单独计时（负载 9–17），67 条命令合计约 209 秒；最慢的几条：

| 步骤 | 秒 |
|---|---|
| `scripts/test_validate_quick.py` | 35.4 |
| `hooks/test_proposal_submit.py` | 19.5 |
| `scripts/test_pre_push_environment.py` | 18.7 |
| `run_tests_parallel.py test_proposal_promotion_proof.py` | 15.7 |
| `hooks/test_module_insert.py` | 15.5 |
| `scripts/test_verify_and_commit.py` | 11.7 |
| `run_tests_parallel.py test_module_cost_report.py` | 11.6 |
| `hooks/test_proposal_publication.py` | 10.7 |

  结构检查（JSON、Shell 语法、可执行位、各 `check-*.py`）每条都在 1 秒以内。
- CI 跑在 `ubuntu-latest`（4 核），整体约 1 分 43 秒。

## 共享状态核对（静态扫描，实现时再实测）

- 没有测试写全局 git 配置（`config --global`、`~/.gitconfig`）。
- 固定 `/tmp` 路径只出现在字符串里，不读写真实路径（`test_self_report.py` 的 `/tmp/sg-self-report-fixture/badmap`、
  几处假数据）。
- 写 `.git/spec-guard/verified-trees` 和取 `--git-common-dir` 的，都是测试自己建的临时仓库。
- 用到 `$HOME` / `Path.home()` 的只有 `codex-plugin-smoke.sh`、`check-command-names.py`、`check-state-paths.py`、
  `test-checkers.sh`；实现时逐个确认它们只读或只写自己的临时 HOME。
- `test_validate_quick.py` 在真仓库上跑 `validate.sh --quick`，并按 `git ls-files` 把工作区打包复制一份。如果别的
  测试并行时往仓库工作区写临时文件，它会读到。所以实测时要在跑前、跑后对比仓库的 `git status --porcelain --ignored`。

## Assumptions

以下待用户确认：

1. **做法**：新建 `scripts/run_steps_parallel.py`（只依赖标准库，Python 3.9 可用）。`validate.sh` 把回归段的命令
   按原顺序交给它，它用固定大小的进程池同时跑若干条。每条命令的标准输出与错误输出各写一个临时文件，按**原顺序**
   完整打印：前面的步骤都打印完、本步也结束时，就立即打印本步，不等全部跑完。不选纯 bash 后台作业，因为 bash 3.2
   没有 `wait -n`，限制不了同时运行的个数。
2. **分组**：
   - 回归段并行：从"校验器自身的回归"到"Codex 真实宿主 smoke 判决器自检"，共 50 条左右。
   - 文件顶部的结构检查（每条不到 1 秒）、"指纹算法自检""本机状态路径"、`--quick` 也跑的"发布证据记录回归"
     "README 内嵌声明块""命令 frontmatter"，保持串行、不改。
   - `test_self_report.py` 换 TMPDIR 再跑一遍的那一步，作为并行组里的一条：它在 git 目录里用 `mktemp -d` 建目录，
     用完按固定前缀删除。两遍 `test_self_report.py` 互不共享可写路径，可以同时跑。
   - 段落标题（`═══ … ═══`）照旧写在 `validate.sh` 里，由运行器在该段第一条输出前打印。`test_validate_quick.py`
     对标题的检查不变。
3. **同时运行的个数**：默认取 CPU 核数，可用环境变量 `SG_VALIDATE_JOBS` 改；设为 1 时与改前一样逐条串行，供排查
   用。慢的三个测试仍由 `run_tests_parallel.py` 在内部再分进程，接受短时间进程数超过核数。
4. **失败判定**：每条命令看自己的退出码，任一条非零即整体失败。末尾列出失败的步骤（显示完整命令），并核对实际
   运行的步骤数等于交给它的步骤数，少一条也算失败。没有超时（与改前一致）。
5. **回归**：新建 `scripts/test_run_steps_parallel.py`，覆盖以下情况，并登记进 `validate.sh`：
   - 全部通过时退出 0；
   - 一条失败时退出非零并报出那条命令；
   - 输出按原顺序；
   - `SG_VALIDATE_JOBS=1` 串行；
   - 段落标题出现在该段的输出之前；
   - 步骤数核对。

   每条判据手工改坏一次，确认会变红。
6. **实测不共享状态**：并行版连跑 5 遍全绿。每遍跑前、跑后对比以下内容，确认没有变化：
   - 仓库的 `git status --porcelain --ignored`；
   - `.git` 下的文件列表；
   - `~/.spec-guard` 与 `~/.local/state/spec-guard` 的文件列表。

   CI 也要绿。
7. **验收与目标**：改后在相近负载下再计时一次完整 `validate.sh`，记下负载，写进 todo。目标：本机 100 秒以内（约
   减半）。CI 改前、改后的耗时也记下。做不到时在 todo 和 PR 里说明原因，由用户决定。
8. **范围**：只改 `validate.sh` 的调度，新增运行器和它的回归，不改任何测试与被测代码。插件发布包不变，因为
   `scripts/` 不进包。不发版，下次发版时写进 CHANGELOG 的"维护者工具"。

## Requirements

1. 新建 `scripts/run_steps_parallel.py`，参数是有序的步骤列表，可夹带段落标题。它按假设 1、3、4 运行并打印，输出
   每段标题、每条步骤的完整输出、步骤总数、失败步骤与结论。
2. `validate.sh` 的回归段改为调用它（假设 2），其余段落与 `--quick` 行为不变。改后的步骤总数不少于改前。
3. 新建 `scripts/test_run_steps_parallel.py`（假设 5）。
4. 共享状态实测（假设 6）、计时（假设 7）、变异证明与 Python 3.9（`/usr/bin/python3`）结果写进 todo。

## Commands

```bash
python3 -B scripts/test_run_steps_parallel.py
/usr/bin/python3 -B scripts/test_run_steps_parallel.py
/bin/bash scripts/validate.sh
SG_VALIDATE_JOBS=1 /bin/bash scripts/validate.sh
```

## Boundaries

- Always：每条命令的输出完整、按原顺序；任一条失败即整体失败。
- Ask first：推送、PR；改任何测试或被测代码，包括发现共享状态需要改测试的时候。
- Never：为提速跳过、合并或删除步骤；吞掉某一步的输出或退出码。
- 不保证：运行器被 Ctrl-C 打断时，正在跑的子进程与换 TMPDIR 那一步的临时目录（git 目录下的
  `sg-self-report-tmpdir.*`）不一定清理，可能残留，需要手动删除（2026-10-09 审查补记）。

## Success criteria

1. 本机完整 `validate.sh` 在 100 秒以内（或说明为什么做不到）。
2. 步骤数不少于改前，任一步失败仍会让整体失败，并报出是哪一步。
3. 并行连跑 5 遍全绿，仓库、`.git` 与本机状态目录不留变化；CI 绿。

## Open questions

无。
