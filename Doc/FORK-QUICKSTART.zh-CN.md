# 小兔头分支：先看懂，再手动体验

这是已有开源管理软件的改造，不是新写的 CUDA 矿工。源码在 Windows 的 `D:\Projects\toolazytoname\RainbowMiner`，GitHub 为 https://github.com/toolazytoname/RainbowMiner ，开发分支 `xiaotutou-prl`，上游 remote 为 `upstream`。

## 这个分支改了什么

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

## 以后手动体验界面

当前另有 KRig 的一次体验任务在运行，到池内累计 1 PRL 会停止；不要同时运行两个矿工。

等旧任务结束后，再在项目目录打开 `Start.bat`。若出现初次配置向导，用自己的普通挖矿钱包配置，只选择 NVIDIA / PearlHash / Kryptex / 一个矿工，先保留暂停状态。浏览器界面默认是 `http://localhost:4000`；“Support RBM / Donate”页面顶部有本分支的收费和收款地址说明。

不要把这里的维护者捐赠地址当成普通使用者钱包。维护者自己在本机试用时可以填自己的地址，发布给别人时应让对方填写自己的普通挖矿地址。

当前项目没有 KRig 的内置适配器，上游已有 OneZeroMiner、BzMiner 等 PRL 适配器。它们的费用、支持范围和实际性能应分别核实。本次没有下载或启动它们，不把离线测试通过当成矿池接受份额或 GUI 已验收。

## 更新与发布

`origin` 是自己的 fork；`upstream` 是原项目。更新前确认工作区干净，fetch 上游并审查差异，再合并。不要运行上游 ZIP 更新覆盖本目录。

本项目仍为 GPLv3，发布修改版时提供对应源码和许可证，保留上游署名；第三方二进制分别遵守其许可证。本次新增提交均为源码、配置、测试和文档，不新增矿工二进制或制作安装包。上游仓库已有辅助 EXE/DLL，fork 仍继承它们，其独立许可与来源未在本轮逐项审计。
