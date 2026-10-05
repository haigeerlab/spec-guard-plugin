# 决策：A10 native 转正采用单 Mac 实机门槛

状态：已接受（2026-10-04，用户明确决定），同日已被取代。本文件调整的是 native 转正门槛，
而该门槛已不再是旧传输退役的前置条件，见
[`2026-10-04-native-only-collaboration-sunset.md`](2026-10-04-native-only-collaboration-sunset.md)。
本文件保留原方案作为记录，不代表其中任何门槛当时已经满足。

当时的修订对象：[`2026-09-28-xats-sunset.md`](2026-09-28-xats-sunset.md) 第 1 条的主机数量；
其余条款在当时继续有效。

## 背景

A10 的产品范围是同一台 Mac 上的 Claude Code／Codex 会话通信，不承诺跨机器发现、网络通信或远程唤醒。
原决定要求连续两个发布版本分别在至少两台主机验收。第二台物理 Mac 并不验证跨机器能力，也不是当前产品
范围的必要条件，却会阻塞同机能力的转正取证。

GitHub Actions 可以提供 `macos-latest` runner，但 GitHub-hosted runner 的每个 job 都使用新建、结束后销毁的
虚拟机。普通 CI 没有本机现成的 Claude Code／Codex 登录态、已存在目标会话和人工授权上下文，因此只把工作流
改成 macOS 不能证明真实会话的发现、收发、空闲唤醒和回退。参考：
[GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)。

## 决策

1. **单 Mac、多版本验收。** 连续两个实际发布版本，各自在一台本机 Mac 上完成 native mailbox 的收发、
   空闲会话唤醒和回退演练。验收记录写入该版本的 `docs/releases/v<version>-*.json`。同一台 Mac 可以承担
   两个版本的验收；不要求第二台 Mac，也不要求跨机器通信。
2. **其余转正门槛不变。** 仍须至少升级一次固定上游 revision，且升级后唤醒验收通过；提出 Proposal 时仍须
   没有未关闭的 native P1/P2。
3. **CI 只按实际证据计级。** GitHub-hosted macOS CI 可以作为 macOS 源码兼容性和自动化回归的补充证据，
   但不能替代真实宿主验收。只有某个 runner 确实具备受控的 Claude Code／Codex 宿主、登录态、目标会话与
   授权，并完成同一验收矩阵时，才可把其记录计作那一版的单 Mac 宿主证据。
4. **默认行为不随本修订改变。** 满足上述证据门槛后才可以提出 native 默认化 Proposal；在 Proposal 被人工
   接受前，XATS 仍是默认，native 仍是实验性选项。

## 影响

- 当前本机是每个候选发布版本唯一需要的实机宿主，不再等待第二台 Mac。
- 既有 2026-10-04 同机验收仍是候选源码的支持性证据；它没有写入已发布版本的 release JSON，不能倒算为
  一个合格发布版本。
- 当前仓库不新增 macOS CI job。现有 Ubuntu CI 已覆盖仓库校验；增加无法运行真实宿主会话的 macOS job 只会
  重复源码验证，不提高 A10 宿主证据等级。
- 不修改全局 Claude/Codex 配置，不增加模型绕过，不开放 LAN／公网服务，也不删除任一传输层。
