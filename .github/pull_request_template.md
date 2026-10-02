## 变更

<!-- 一句话 -->

## 关联

- Local 事项（内容可公开时填写，多个逐条列出）：《标题》（短编号）；本 PR 覆盖范围：
- GitHub Issue（如适用）：Closes #

私有 Local 事项不在公开 PR 中填写标题或编号；把 PR 地址和覆盖范围记在本地事项即可。
合并后核对实际合并提交和验证结果，并写回关联的 Local 事项；若事项仍有其他交付或验收，保持开放。

## 自检

- [ ] `bash scripts/validate.sh` 通过
- [ ] `bash plugins/spec-guard/hooks/test-phase-guard.sh` 通过
- [ ] 改了状态机逻辑的话，已补测试用例
- [ ] 改了命令的话，README 命令表已更新
- [ ] 如果是发版，plugin.json 的 version 和 CHANGELOG 已更新

## 三条硬约束是否仍成立

- [ ] 未声明约定的仓库仍然静默退出
- [ ] 探测失败时降级而不是误报
- [ ] hook 仍然只读，不做写操作
