# 小兔头分支：先看懂，再手动体验

这是已有开源管理软件的改造，不是新写的 CUDA 矿工。源码在 Windows 的 `D:\Projects\toolazytoname\RainbowMiner`，GitHub 为 https://github.com/toolazytoname/RainbowMiner ，开发分支 `xiaotutou-prl`，上游 remote 为 `upstream`。

## 本机日常入口与项目分工（2026-10-29）

本机日常使用桌面 Pearl 面板，或本仓库的 `Scripts/PearlExperience/Manage-Pearl.ps1`。它是独立的一次体验控制器，负责手动启停、220W 上限、温度保护、其它 GPU 任务让路和原体验截止；不执行完整 RainbowMiner 的收益切换及维护者捐赠轮次。

```powershell
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Status
```

启停参数与保护规则见 [日常控制器说明](../Scripts/PearlExperience/README.md)。源码分别在 `D:\Projects\toolazytoname\RainbowMiner`（管理）与 `D:\Projects\toolazytoname\soat-miner`（MIT CUDA 计算），每个 GitHub 仓库各一个目录。

截至本次核对，矿工已因其它 GPU 客户端触发保护而停止，原功率上限已恢复；这不是已达到打款门槛的声明。配置仍选 SOAT，KRig 的额外费用开关仍关闭；用户随后选择继续优化开源内核，先做受保护实验，没有自动恢复日常挖矿。此段是有日期的快照，操作前先查实际状态，不把文档当作实时进程信息。

同为 220W 的完整对照中，KRig 比开源版本快约 10.17%。目前验证连接下 KRig 收 3% 开发费，按测得算力折算仍约高 6.86%，不是实测收入；不要因挖矿在 Windows 本机就推断免开发费。开源内核保留作实验，日常可复用同一管理工具。详见 [实测对照与后端选择](COMPUTE-BACKEND-COMPARISON.md) 和 [KRig 适配器](KRIG-INTEGRATION.md)。

## 完整 RainbowMiner 主程序的改动与捐赠说明

以下捐赠配置属于完整主程序，与上述独立日常控制器区分使用。

1. 开发者捐赠轮次使用 `Data/ForkDonation.json` 中的本地配置，不再从上游服务器覆盖收款地址。
2. 本分支的维护者为“小兔头”，PRL 主网公开地址：

   `prl1pnuee3duuwy0jduln4snrfjal38kwrhp3v92lt8yua4d3pcn39rsqsutgft`

3. 默认每天 24 分钟，约 1.67% 的时间用于维护者捐赠轮次；它是时间份额，不保证恰好占收益的 1.67%。设 `Donate=0` 可关闭，小于 10 分钟的设置也会被尊重。
4. 只在 Kryptex 以 PearlHash 挖 PRL；不把 PRL 地址填进 BTC、邮箱或矿池账号字段。地址需要通过 Bech32m 校验，强制 SSL；配置无效或矿池不可用时跳过，不换到另一个人的地址。
5. 普通用户的挖矿收款地址由用户配置；捐赠结束后恢复原配置。这个地址不是软件使用者默认的全额收款地址。
6. 矿工开发者费、矿池费另算。捐赠页面会展示本分支维护者和公开地址，下方仍保留上游的自愿支持链接。
7. 首次启动默认暂停，默认关闭自动更新、暂停时更新及外部矿机监控。ZIP 更新器会退出，防止覆盖 fork；通过 Git 审查更新。已有用户配置不会被默认值覆盖。
8. 安装与启动不自动添加 Defender 排除项。不要为运行测试关闭杀毒或恢复被隔离的软件。

## 现在怎样验证源码（不挖矿、不下载矿工）

在项目目录用已经安装的 PowerShell 7 执行：

```powershell
& 'D:\Apps\PowerShell\7\pwsh.exe' -NoProfile -File .\Tests\Test-Fork.ps1 -WorkDirectory 'D:\AI\Playgrounds\RainbowMiner\manual-review'
```

测试不会调用矿池、启动矿工、执行硬件超频或修改系统设置。结果应全部为 PASS。

本机这一轮测试产物在 `D:\AI\Playgrounds\RainbowMiner\20261028-review`，不提交本地日志、配置或凭据。

## 可选：手动体验完整 RainbowMiner 界面

先使用上面的 Status 命令核对当前状态。若日常控制器正在运行，先通过同一入口停止并确认矿工退出、功率恢复；不要同时启动两套矿工。

确认没有其它矿工运行后，再在项目目录打开 `Start.bat`。若出现初次配置向导，用自己的普通挖矿钱包配置，只选择 NVIDIA / PearlHash / Kryptex / 一个矿工，先保留暂停状态。浏览器界面默认是 `http://localhost:4000`；“Support RBM / Donate”页面顶部有本分支的收费和收款地址说明。

不要把这里的维护者捐赠地址当成普通使用者钱包。维护者自己在本机试用时可以填自己的地址，发布给别人时应让对方填写自己的普通挖矿地址。

本分支已经加入 `Miners/KRig.ps1`、`Modules/KRig.psm1` 和对应测试，完成 PowerShell 7/5.1 各 19 项离线检查及真实 KRig API 读取验证。离线测试使用的基类替身及真实 API 验证范围见 KRig 说明；这不代表完整 RainbowMiner Web 界面或所有矿工均验收。上游另有 OneZeroMiner、BzMiner 等 PRL 适配器，其费用、支持和性能应分别核实，未在本次下载或启动它们。

## 更新与发布

`origin` 是自己的 fork；`upstream` 是原项目。更新前确认工作区干净，fetch 上游并审查差异，再合并。不要运行上游 ZIP 更新覆盖本目录。

本项目仍为 GPLv3，发布修改版时提供对应源码和许可证，保留上游署名；第三方二进制分别遵守其许可证。本次新增提交均为源码、配置、测试和文档，不新增矿工二进制或制作安装包。上游仓库已有辅助 EXE/DLL，fork 仍继承它们，其独立许可与来源未在本轮逐项审计。
