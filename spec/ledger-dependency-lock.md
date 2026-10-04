# Spec: ledger-dependency-lock

## Objective

本地事项账本（`local-ticket-ledger`）的运行时是外部 npm 包 `epiq@1.11.0`。现在的安装命令是
`npm install --ignore-scripts --prefix <staging> epiq@1.11.0`：只固定了顶层包；epiq 有 15 个直接依赖，其版本范围是浮动的，解析后整棵树共 269 个包，
插件既不附带 lockfile，也不校验任何安装包的完整性。两次安装可能装上不同的代码；某个依赖一旦被投毒，
导入时就会以用户权限执行（`--ignore-scripts` 只能挡住安装脚本）。

本模块让账本运行时按插件附带的 lockfile 安装，由 `npm ci` 逐个校验每个依赖的 sha512 完整性。

登记：2026-09-29 按用户决定经 `/spec-guard:add-module` 快速插入能力图。范围只包含 epiq。旧协作传输的
依赖风险已随 2026-10-04 native-only 退役完成而从当前产品面消失；原时点事实保留在历史决策中。

## Assumptions

用户已于 2026-09-29 确认：

1. lockfile 随插件分发，位于 `plugins/spec-guard/locks/local-ticket-ledger/`，包含 `package.json` 与
   `package-lock.json`（每个依赖的精确版本与 `integrity`）。维护者在临时目录用
   `npm install --package-lock-only --ignore-scripts epiq@1.11.0` 生成：只读取注册表元数据，不下载安装包、不执行代码。
2. 安装改为：把这两个文件复制进临时安装目录，运行 `npm ci --ignore-scripts --no-audit --no-fund`。任何依赖
   完整性不符都失败，沿用现有的"校验通过才原子换上、失败只删临时目录"保护。
3. 已经用旧方式安装的运行时照常可用，不自动重装；`status` 报告它未锁定，并给出重新安装的方法。
4. epiq 版本保持 1.11.0；升级时由维护者重新生成 lockfile。
5. 仍需联网从注册表下载，沿用用户的 npm 配置与镜像，但内容必须与 lockfile 中的哈希一致；离线安装不在范围内。
6. 本模块不管理协作运行时依赖。

## Contract

### L1 lockfile 与防漂移

- `plugins/spec-guard/locks/local-ticket-ledger/package.json` 只声明一个依赖 `epiq`，版本与
  `local_ledger_runtime.PACKAGE_VERSION` 精确相等；`package-lock.json` 的 `lockfileVersion` 为 3，根依赖与之一致，
  且锁定的每个包都带有 `resolved` 与 `integrity`。
- 回归测试断言上述关系，任何一处漂移（版本常量、package.json、lockfile 根依赖不一致，或某个包缺 `integrity`）都失败。
- 发布包会自动包含 `locks/`，因为它在 `plugins/spec-guard/` 之下；`release-package.py` 的校验不需要修改。

### L2 按 lockfile 安装

- `install_runtime` 把两个文件复制进临时目录，改运行 `npm ci --ignore-scripts --no-audit --no-fund`（在临时目录中
  执行，不再用 `--prefix` 加包名）。安装后把一份与插件一致的 `package-lock.json` 留在运行时目录，作为"按哪份
  lockfile 安装"的记录。
- 缺少插件 lockfile、`npm ci` 失败、或安装结果不满足现有校验时，不换上任何目录，报告具体原因。

### L3 状态与升级路径

- `runtime_status` 在现有校验之外增加字段 `lock`：
  - `locked`：运行时目录里的 `package-lock.json` 与插件附带的逐字节一致；
  - `unlocked`：运行时有效但没有 lockfile，或与插件附带的不一致（旧方式安装、或插件升级了 lockfile）。
  `state` 仍为 `ready`，账本照常可用；`unlocked` 时给出重新安装的提示。
- `install_runtime` 遇到 `ready` 且 `locked` 的运行时，照旧拒绝（已安装）。遇到 `ready` 但 `unlocked` 的运行时，只有
  调用方显式传入替换参数（例如 `--replace-unlocked`）时才替换：先在临时目录完成锁定安装与校验，再原子地换下旧
  目录；任何一步失败都保留旧运行时不动。
- 运行时目录只包含 npm 依赖；账本数据位于项目的 `.epiq/` 与 `__epiq_state__` 分支，不受替换影响。测试证明替换
  只动运行时目录。
- `local-ticket-ledger-ops` skill 与 `/spec-guard:local-ticket-ledger` 命令：展示 `lock` 状态；替换必须先经用户明确确认。

### L4 文档

- `references/local-ticket-ledger-runtime.md`：安装方式、`lock` 状态含义、维护者重新生成 lockfile 的步骤。
- `spec/collaboration-messaging.md` 与 `references/collaboration-runtime.md`：说明协作运行时由其自身的固定
  revision 管理，不属于本模块的 npm lockfile 范围。
- `CHANGELOG.md` Unreleased：用户可见的变更与升级方法。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py
python3 -B plugins/spec-guard/hooks/test_local_ledger_adapters.py
python3 -B plugins/spec-guard/hooks/test_ticket_entry.py
/usr/bin/python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

```text
plugins/spec-guard/locks/local-ticket-ledger/package.json, package-lock.json -> L1：随插件分发的锁定清单
plugins/spec-guard/hooks/local_ledger_runtime.py                            -> L2、L3：锁定安装、lock 状态、替换
plugins/spec-guard/hooks/test_local_ledger_runtime.py                       -> L1–L3 回归
plugins/spec-guard/skills/local-ticket-ledger-ops/SKILL.md,
  commands/local-ticket-ledger.md                                           -> L3：展示与确认
plugins/spec-guard/references/local-ticket-ledger-runtime.md                -> L4
spec/collaboration-messaging.md, references/collaboration-runtime.md         -> L4：协作依赖边界
CHANGELOG.md                                                                 -> L4
```

## Testing strategy

- 每项先写测试并确认它在当前代码上失败，再修改。
- 单元测试（假 npm，沿用现有测试的做法）：
  - 安装命令是 `npm ci --ignore-scripts --no-audit --no-fund`，在含两个锁定文件的临时目录中执行；
  - 缺插件 lockfile 或 `npm ci` 失败时，正式目录不出现、临时目录被清理；
  - `lock` 状态：一致为 `locked`；缺失或不一致为 `unlocked`，且 `state` 仍为 `ready`；
  - `ready` 加 `locked` 时拒绝安装；`ready` 加 `unlocked` 时，不带替换参数拒绝，带替换参数时原子替换；替换失败时旧运行时逐字节不变；
  - 防漂移：版本常量、`package.json` 与 lockfile 根依赖一致，每个包都有 `integrity`。
- 真实安装验证（不进 `validate.sh`，结果记录在交付说明）：在临时目录用真实 npm 按 lockfile 安装一次，
  `runtime_status` 为 `ready` 加 `locked`；再篡改 lockfile 中一个包的 `integrity`，确认 `npm ci` 失败、没有目录被换上。
  不触碰本机 `~/.spec-guard` 下正在使用的运行时。

## Boundaries

- Always：先红后绿；只按插件附带的 lockfile 安装；失败不换上目录；替换只动运行时目录。
- Ask first：升级 epiq 版本；在用户机器上替换已有运行时（必须经用户明确确认）。
- Never：执行依赖的安装脚本；绕过完整性校验；自动重装或替换用户已有的运行时；触碰账本数据（`.epiq/`、`__epiq_state__`）。

## Success criteria

- 新安装的账本运行时由 `npm ci` 按插件 lockfile 安装，`status` 报告 `locked`；篡改任一 `integrity` 会让安装失败，
  且不留下半装的目录。
- 旧方式安装的运行时 `status` 为 `ready` 加 `unlocked`，仍可使用；经用户确认可以原子替换为锁定安装，失败时旧运行时不变。
- 防漂移测试守住版本常量、`package.json` 与 lockfile 的一致性。
- 文档写明锁定安装、升级方法，以及与协作运行时的依赖边界。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过。
