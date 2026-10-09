# Spec: self-report-tmpdir-independence

## Objective

`scripts/test_self_report.py` 的 `TempProjectTests.test_temp_directory_projects_are_excluded_and_counted` 用
`tempfile` 生成的目录拼出“临时目录项目”的路径。`self_report.is_temp` 只认 `/private/tmp/`、`/tmp/`、
`/private/var/folders/`、`/var/folders/` 四个前缀，所以外部把 `TMPDIR` 设到别处时，这个用例会变红；CI 用默认
`TMPDIR`，一直没暴露。来源：第二轮联调审查 #268 时指出，用户 2026-10-09 决定单独做成模块、先写会红的测试、不用条件跳过。

读者：本仓库维护者。

## Assumptions

用户于 2026-10-09 确认：

1. 用例改用固定的临时前缀路径（如 `/tmp/sg-self-report-fixture/badmap`，取 realpath，无需存在）构造临时项目，与同一
   夹具里 `self.real` 的固定写法一致；不用 `skipUnless` 等条件跳过。
2. `validate.sh` 在 `TMPDIR` 指向仓库 git 目录下一个临时建的目录（不在四个前缀下）时再跑一遍 `test_self_report.py`，
   跑完删除该目录；本机与 CI 都会检查。先在现有测试上确认这一遍会红，修后转绿，再手动改回确认会重新变红。
3. 插件发布包不变，不改版本号；最后一项是下次发版时补证据。

## Requirements

1. `test_self_report.py` 的该用例不再从 `self.root` 推导临时项目路径。
2. `validate.sh` 增加外部 `TMPDIR` 那一遍，失败计入总结果；临时目录无论成败都会删除。
3. 其余 `test_self_report.py` 用例在两种 `TMPDIR` 下都通过。

## Commands

```bash
/bin/bash scripts/validate.sh
python3 -B scripts/test_self_report.py
```

## Boundaries

- Always：只用 `bash`、`git`、`python3`；临时目录只建在仓库的 git 目录里，用完即删。
- Ask first：推送、PR。
- Never：用条件跳过绕开；改 `self_report.py` 的判定或插件发布包。

## Success criteria

1. 外部 `TMPDIR` 设在哪里，`test_self_report.py` 的结果都一样。
2. 这一点每次 validate 都会被检查。

## Open questions

无。
