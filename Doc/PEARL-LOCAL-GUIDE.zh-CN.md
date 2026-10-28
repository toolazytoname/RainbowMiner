# 小兔头：本地 Pearl 管理工具

## 为什么有两个工程

RainbowMiner 是管理工程：决定什么时候启动或停止、使用哪个计算后端、观察温度和功率、记录结果。soat-miner 是独立 MIT 工程，里面才是实际 GPU 计算和可修改的 CUDA 内核。KRig 是另一个可选计算后端，当前只有发布二进制，不能声称拥有它的内核源码。分开保存可以保留各自上游历史与许可证，也能分别对比和回退。

代码分两个仓库，使用时只需一个开始/停止入口。开源内核是否更快，必须同功率实测；更换管理器本身不会增加显卡的算力。

## 日常操作

沿用桌面原来的挖矿面板与开始/停止按钮。部署完成后，按钮通过同名任务调用本仓库 `Scripts/PearlExperience/payout_experience.py`，不需要你手工先打开两个程序。当前部署与真实矿池验收状态以 Windows 实验记录为准，本文不把尚未部署的代码写成已接管。

也可在 PowerShell 中进入 `D:\Projects\toolazytoname\RainbowMiner`：

```powershell
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Status
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Start -Minutes 60
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Stop
```

`Start -Minutes 60` 是本轮最多一小时，仍受原体验截止时间和首次打款门槛约束。停止后看 `Status` 中 `Status=stopped`、`MinerPid=null`、`PowerRestored=true`。如果你或其他程序在运行期间另行修改过功率上限，工具保留该外部设置并单独记录，不覆盖它。

## 这次体验的边界

使用原来的公开 PRL 地址与 Kryptex 矿池；不会因为更换管理代码而丢掉池内余额。已确认和待确认之和达到矿池门槛，或者矿池出现打款记录，就停止 GPU 计算；等待成熟和打款不需要继续挖矿。达到门槛与实际到账是两个阶段，矿池结算规则仍由矿池决定。

原来的挖矿截止时间从 `D:\Apps\KRig\Runtime\payout-experience.json` 延续，重新启动不续期。手动停止、温度保护、出现其他 GPU 程序或运行异常都会结束本轮，不会自动重开。CPU 任务可以同时运行，本工具让自己的进程以较低 CPU 优先级运行。

本轮最高 220W，仅调整显卡功率上限。温度保护阈值为核心 80℃、热点 100℃、显存结温 96℃；没有手工调频、电压或风扇，也没有修改 Defender。正常停止后恢复本轮开始前的功率上限。

## 文件在哪里

- 管理源码：`D:\Projects\toolazytoname\RainbowMiner`。
- 计算内核源码：`D:\Projects\toolazytoname\soat-miner`。
- KRig 程序及本地配置：`D:\Apps\KRig`。
- 体验状态：`D:\Apps\KRig\Runtime\体验进度.html` 与两个 JSON 状态文件。
- 挖矿运行记录：`D:\AI\Playgrounds\KRig`。
- 开源内核实验：`D:\AI\Playgrounds\soat-miner\20261028-prl3090`。

源码已按仓库分目录，实验输出不提交普通 Git。程序只需要公开收款地址，不读取助记词、私钥或钱包密码。Github 代码是管理逻辑与开源计算实验的备份，运行日志和本机配置留在 Windows。


## 本轮实际验收

自己的管理代码已有一轮矿池实挖：5 个接受份额、0 拒绝。PS7 和 Windows PowerShell 5.1 都通过了真实本机接口和原生 API 类校验；完整上游网页界面没有据此宣称已验收。

实际开始/停止入口约 5 秒内停止并恢复到本轮开始前的 370W；新增一个很小的 GPU 上下文时，正在计算的矿工约 2 秒内让路，保留新任务正常运行。开始次数增加没有延长原体验截止时间。

功率标定入口也纳入同一截止时间和首次门槛保护；遇到温度或资源保护就结束，不会自行挑旧档位继续启动。平时继续用原面板的开始和停止。GPU 实验和实挖互斥，实验记录分别放在对应的 Playgrounds 目录。

停止按钮在等待打款阶段也有效：此时显卡已经停止，按钮只会结束后台查询；不会撤回或改变矿池余额。余额和打款两个公开 API 请求各设置 8 秒网络超时，两次查询之间每秒检查停止请求，不再固定等待五分钟才处理。之后仍可直接打开矿池页面查看到账。
