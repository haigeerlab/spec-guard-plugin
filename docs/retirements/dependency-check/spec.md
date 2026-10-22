# Spec: dependency-check

<!-- spec-guard: review approved 95275847f856 -->

## Objective

`scope-authorization` 让批 Plan 按「需要的外部条件」授权装依赖，但宿主是按命令前缀放行的：先把包名写进依赖清单，再跑一条不带
参数的安装命令，就能绕过宿主对「加新包」的询问。module-crew 0.5.0 也据此只放行按锁文件安装，把新增依赖留给事后核对。
本模块就是这层事后核对：verify-artifacts 对比进行中模块的依赖清单新增内容和 Plan 列出的条件，有没列出的就报出来。只报告、不拦。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `scope-authorization`、`map-progress-facts`。需求来自接入协调人
转达的 R21 条目 SG-5b（用户决定 61）；用户在本会话同意按负责人的收窄方案做（锁文件不逐项比、只认常见清单），协调人已收到退回理由。

## Assumptions

1. **查哪些模块**：与 `scope-authorization` 的提示同一范围——能力图里阶段不是 `DONE`、且已有 `tasks/<id>/plan.md` 的模块。
   已完成模块不追溯。
2. **从哪里比起**：本模块 Spec 第一次提交的那个提交（与 `/map` 的 `startedAt` 同一判据，取它的提交号）。比的是那个提交到
   **工作区**的差异，未提交的改动也算。Spec 还没提交过时，从 HEAD 比起。读不出 git 历史时给「未验证」，不猜。
3. **逐项核对的清单**（只看这次差异里改过的文件，任意目录，跳过 `node_modules/`）：
   - `package.json`：`dependencies`、`devDependencies`、`peerDependencies`、`optionalDependencies` 里新增的键；改版本号不算新增。
   - `requirements*.txt`：新增的需求行，取包名（去掉版本、extras、环境标记）；`-r`、`-e`、注释与空行不算。
   - `pyproject.toml`：`[project]` 的 `dependencies = [...]`、`[project.optional-dependencies]` 下各组，以及
     `[tool.poetry.dependencies]`、`[tool.poetry.group.*.dependencies]` 两种表里新增的包名。系统 Python 3.9 没有 `tomllib`，
     所以只用一个只认这几种写法的行级读法；读不懂的写法不猜，归到第 5 条「改了、未逐项核对」。
   - Python 包名按 PEP 503 规范化（小写，`-`、`_`、`.` 视为同一个）后比较；npm 包名原样比较（含 `@scope/`）。
4. **和 Plan 怎么比**：取 Plan「需要的外部条件」那一节的文字（标题写法取到下一个同级或更高级标题为止；行首写法取那一行加紧跟
   着的列表项）。包名作为一个完整词出现在这段文字里就算列出了。这一节里写了「允许范围」（英文 `allowed scope`）时，没列出的包
   不逐个算缺，报「按允许范围授权，未逐项核对」并列出包名。Plan 没有这一节时，`scope-authorization` 的提示已经报了，这里照样
   列出新增的包，提示词说明「Plan 没有这一节」。
5. **只报改了、不逐项核对的文件**：
   - 锁文件（`package-lock.json`、`pnpm-lock.yaml`、`yarn.lock`、`bun.lockb`、`poetry.lock`、`uv.lock`、`Pipfile.lock`）：只报
     「锁文件有改动」，因为里面多是间接依赖，逐项比会刷屏。
   - 其他依赖清单（`Cargo.toml`、`go.mod`、`Gemfile`、`composer.json`、`Pipfile`、`setup.py`、`setup.cfg`）和第 3 条里读不懂的
     写法：只报「改了，未逐项核对」。
6. **输出**：每个模块最多一条 `⚠️`，按下面的顺序拼：没列出的包（按清单文件分组）、按允许范围未逐项核对的包、改了未逐项核对的
   清单、锁文件有改动。什么都没有就不输出。不加 `ok` 行，不让 verify-artifacts 失败，不联网、不装包、不写文件。
7. **版本与发布**：本模块的 PR 写 0.78.0 的版本号（两份清单、中英 README 的 `--ref`）与 CHANGELOG `[0.78.0]` 一节，覆盖
   `scope-authorization` 与本模块；CHANGELOG 里说明升级后进行中的模块可能多出两类提示（缺「需要的外部条件」、依赖没列出）。
8. `phase-guard.sh` 与每轮注入不变；`/map --json` 不加字段（核对结果只在 verify-artifacts 里）。

## Contract

### `hooks/verify-artifacts.sh`

新增一段（python 内嵌，风格同 AC 编号与「需要的外部条件」两段），每个模块的输出形如：

```text
⚠️ alpha 的依赖改动：新增依赖没写进 Plan「需要的外部条件」：apps/web/package.json：zod、dayjs；
   按允许范围授权，未逐项核对：requirements.txt：httpx；改了，未逐项核对：go.mod；锁文件有改动：pnpm-lock.yaml
```

- Plan 没有这一节时，第一段写作「新增依赖（Plan 没有「需要的外部条件」一节）：…」。
- 读不出 git 历史、读不出 Plan 或清单时 `warn "未验证：<id> 的依赖改动没有核对（原因）"`。
- python3 不可用时与其他段一样给「未验证」。

### 共享检查点规则

「最终验收列出实际改动的文件」那一行后补半句：verify-artifacts 会对照 Plan 报出没列出的新增依赖，最终验收时一并说明。

### 文档与版本

`commands/verify-artifacts.md` 与 `docs/commands.md` 的 verify-artifacts 一节写明这一项与它的范围（哪些清单逐项、哪些只报改了）；
CHANGELOG `[0.78.0]`；两份 `plugin.json` 改为 0.78.0；中英 README 的 `--ref` 改为 v0.78.0。

### 不变

- `phase-guard.sh`、每轮注入、`/map --json`、verify-artifacts 的退出码与其他检查都不变。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

在 `test-verify-artifacts.sh` 用临时 git 仓库：先提交 Spec 作为起点，再在工作区改清单。

- package.json 新增 `zod`（Plan 没列）与 `dayjs`（Plan 列了）→ 只报 zod；只改版本号 → 不报；子目录 `apps/web/package.json` 同样识别；
  `node_modules/` 下的不看。
- requirements.txt 新增 `Requests[socks]>=2`，Plan 写 `requests` → 视为列出（规范化）；新增 `httpx` → 报。
- pyproject.toml 的 `[project] dependencies` 与 `[tool.poetry.dependencies]` 各新增一个 → 识别；读不懂的写法 → 归「改了，未逐项核对」。
- Plan 写了允许范围 → 报「按允许范围授权，未逐项核对」。
- 只改锁文件 → 只报「锁文件有改动」；改 `go.mod` → 报「改了，未逐项核对」。
- Spec 还没提交 → 从 HEAD 比；模块已完成 → 不报；没有 Plan → 不报；什么都没改 → 不输出；退出码始终不变。
- 反向：包名只作为另一个包名的一部分出现在 Plan 里（Plan 写 `zod-form`，新增 `zod`）→ 仍报。

## Boundaries

- **会做**：依赖改动核对与提示、规则半句、文档、0.78.0 版本号与 CHANGELOG。
- **先问**：让这项检查失败退出；逐项比锁文件；支持更多生态的清单；把结果放进 `/map` 或每轮注入。
- **不做**：联网查包、装包、改清单或 Plan；判断依赖是否安全。

## Success criteria

- AC1：进行中模块在 package.json、requirements*.txt、pyproject.toml 里新增、而 Plan「需要的外部条件」没列的包被逐个报出，列了的不报，只改版本不报。
- AC2：Python 包名按 PEP 503 规范化比较；包名只作为别的词的一部分出现在 Plan 里时不算列出。
- AC3：Plan 写了允许范围时报「按允许范围授权，未逐项核对」；锁文件只报有改动；其他清单与读不懂的写法只报改了、未逐项核对。
- AC4：比较起点是 Spec 第一次提交到工作区；Spec 没提交时从 HEAD 比；已完成或没有 Plan 的模块不报；什么都没改不输出。
- AC5：提示不改变 verify-artifacts 的退出码；读不出时报「未验证」；不联网、不写文件。
- AC6：0.78.0 的版本号、README `--ref` 与 CHANGELOG 一节（含 scope-authorization）齐全，`validate.sh` 与两边回归通过；`phase-guard.sh` 输出不变。

## Open questions

- 无。
