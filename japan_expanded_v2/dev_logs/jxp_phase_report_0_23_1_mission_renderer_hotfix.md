# 日轮诸道 0.23.1 任务树渲染修复报告

日期：2026-07-09

## 问题根因

本轮没有把“脚本可解析、拓扑无环”误当成“游戏界面一定能正常绘制”。对本机 EU4 1.37.5 的 `Japanese_Missions.txt` 与 `DOM_Japanese_Missions.txt` 逐条统计后，确认原版日本任务树的可见连线满足以下规律：

- 纵向最多跨 2 行；
- 横向只连接相邻列；
- 不让纵线穿过另一任务节点；
- 相邻列的对角线不交叉；
- 单个任务最多绘制 3 条前置连线。

0.23.0 的任务虽然通过了旧拓扑校验，却存在最多跨 17 行、横跨 4 列以及单节点 4 条前置线的情况。旧校验还以“跨列连线数量多”为美观指标，反而鼓励了过度连线。

此外，`jxp_54_route_foundation_missions.txt` 调用了未定义的 `jxp_tenka_order_at_least_35`。EU4 在 `error.log` 中将该任务文件标记为解析失败，其他任务仍引用其中节点时便会出现缺失或断线。

第一次重启后的真实引擎日志还发现 18 条 `mission.cpp:353`：若干独立编写的 JXP 非通用任务组虽然行区间分离，却仍在同一 slot 中同时争用任务列。与本机正常工作的 Europa Expanded 对照后，确认成熟任务大修采用“覆盖原版任务文件、用共同开关让原版树与自定义树互斥、每个国家版本使用一套完整列”的架构，而不是继续叠加候选组。此前所有 JXP 任务组还统一写了 `potential_on_load = { always = yes }`，使互斥候选被宽泛预加载，也不符合该成熟模式。

## 已完成修复

- 新增并注册 `jxp_tenka_order_at_least_35`。
- 保留全部 187 个任务 ID，将 35 个分散任务组整合为 28 个自定义 series。
- 将 13 个建国基础任务并入共通国政/朝廷列，将 3 个家法任务并入朝廷列，将 6 个朱子国内建设任务并入礼制/王政列；移除已经清空的独立基础和家法任务文件。
- 基于本机 SHA256 锁定的 EU4 1.37.5 原文件生成 `Japanese_Missions.txt` 与 `DOM_Japanese_Missions.txt` 最小覆盖。23 个原版任务组仅增加 `jxp_use_custom_missions_trigger` 排除条件，除此之外与原版逐行一致。
- 移除 28 个宽泛 `potential_on_load = { always = yes }`，路线变化继续通过唯一的延迟 `swap_non_generic_missions = yes` 刷新。
- 原版树被互斥关闭后，将全部自定义坐标统一上移 8 行；所有代表状态从第 1 行开始，不再留下空白首屏。
- 所有可见 `required_missions` 连线限制为最多 2 行、相邻 1 列。
- 过远但仍有玩法意义的前置条件改写为任务 `trigger` 内的 `mission_completed = ...`，因此不再绘制坏线，同时不降低解锁门槛。
- 对角交叉、穿过节点、非相邻列和拥挤父节点均纳入硬错误。
- 将“宣称天命”和“打破天命”移动到第五列相邻分支位；二者互斥，不再被共同要求为后续任务的强制前置。共同后续由天命处置结果 flag 与“平衡天命”任务控制。
- 新增一次性隐藏迁移事件 `jxp_migration_v023.2`。旧存档在一个游戏日后重建任务树，并设置 `jxp_mission_renderer_migration_v0231`。
- 调试清理效果会清除新迁移 flag。
- 新增可重复执行的 `tools/jxp_validation/reflow_missions_v0231.py`；连续执行两次结果稳定。
- 新增 `consolidate_mission_series_v0231.py` 与 `create_japanese_mission_overrides_v0231.py`，分别复现任务组整合和锁定原版覆盖。

## 验证加强

- 代表状态由 11 个扩展到 15 个。
- 大名阶段现在分别验证武家、朝廷、海洋、边境、寺社市场五种家系；大友使用 `OTM` 海洋家系配置单独验证。
- 任务触发器检查会确认任务文件调用的每个 `jxp_*` scripted trigger 均真实存在，防止 Clausewitz 语法通过但 EU4 运行时拒载文件。
- 有效拓扑使用 Mod 虚拟文件覆盖规则，不会把游戏根目录原文件和 Mod 覆盖文件重复计算。
- 校验器确认两份覆盖文件除共同排除条件外与锁定原版逐行相同，并禁止自定义树残留空白首屏、同列 JXP series 竞争、长距离连线、非相邻列和对角交叉。

## 当前验证结果

- 通用 Mod 校验：通过。
- JXP 发布校验：11/11 通过。
- Clausewitz 脚本：166/166 通过。
- 任务：187 个 ID、28 个自定义任务组、2 个锁定原版覆盖、15 个代表状态；无原版/JXP 同时激活、同列 JXP series 竞争、格位碰撞、失效前置、逆向边、超距边、穿节点边或交叉边。
- 回归测试：24/24 通过，包括覆盖互斥、原版预加载禁用、合法原版分段、JXP series 竞争和未定义任务触发器检测。
- 坐标可视化审计：大友、开国日本、朱子礼制日本、吉利支丹日本四种有效树均无断边、穿节点或对角交叉；开国树的天命处置分支与太平洋/东亚双翼能够在五列内完整排布。
- 政府改革、七路线理念、儒教与神道桥接、改革中心、本地化、sprite 与 DDS 校验均通过。

## 运行时说明

EU4 于 `2026-07-09 16:26:29` 启动。对同一进程后续写至 `16:29:40` 的完整 `error.log` 复查时，发现三条残余 `mission.cpp:353`：`jxp_shinto_branch_missions`、`jxp_japan_state_missions`、`jxp_japan_court_missions` 仍分别与三个 Domination 日本任务组重叠。

代码级根因是：`potential_on_load` 属于无国家作用域的全局预加载门，不能依靠 tag、country flag 或国家 scripted trigger 排除原版任务组。此前的原版覆盖虽然在国家 `potential` 中互斥，但原版 series 已经先进入候选池。

最终修复已将两份锁定原版覆盖中的全部 23 个 series 设置为 `potential_on_load = { always = no }`，并继续保留 `potential` 中的国家互斥作为第二层防线。生成器、精确覆盖比对和两项专门回归测试均已同步更新；当前静态发布门禁 11/11、Clausewitz 166/166、回归测试 24/24 全部通过。

任务定义不能热加载，因此在写入最终预加载修复后又进行了完整冷启动。EU4 新进程于 `2026-07-09 16:37:28` 启动，`setup.log` 已完整加载到灾难定义末尾，最终 `error.log` 写于 `16:38:47`。精确扫描结果为：`mission.cpp:353 = 0`、`Non-generic mission series = 0`、`Unknown trigger type = 0`、`Parsing Errors = 0`、包含 `jxp_` 的错误行 = 0；未生成崩溃报告。

因此本阶段已经同时通过静态拓扑、可视化坐标、覆盖生成一致性和 EU4 实际引擎冷启动四层验证。游戏内旧存档仍应经过一个游戏日，让 `jxp_migration_v023.2` 完成一次任务刷新。

部署前备份：

`C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\_jxp_backups\japan_expanded_v2_before_mission_layout_hotfix_20260709_154614.zip`

`C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\_jxp_backups\japan_expanded_v2_before_series_consolidation_20260709_161217.zip`

## 当前 Playset 与兼容边界

- 启动器当前顺序为：Chinese Language Supplementary Mod for 1.37（8）→ Chinese Language Mod for 1.37（16）→ 日轮诸道（21）。日轮诸道最后加载，因此本 Mod 的日本任务覆盖文件会生效；本轮实际引擎日志已经验证该顺序可用。
- Chinese Language Supplementary Mod 同样带有 `missions/DOM_Japanese_Missions.txt`。不要把它排到日轮诸道之后，否则它会覆盖本轮的互斥开关并重新引入原版/自定义任务混装。
- Europa Expanded 当前未启用。它也覆盖日本任务文件，现阶段视为任务树层面的不兼容 Mod；若未来同时启用，需要单独制作以最终加载者为目标的兼容补丁，不能只靠调整任务坐标解决。
