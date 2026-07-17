# 日轮诸道 0.23.2 政府改革可见性修复报告

日期：2026-07-09

## 现象与证据

玩家截图中的君主制改革界面只显示原版改革。对当前 `autosave.eu4` 的只读检查确认：玩家为 `JAP`，拥有 `jxp_path_open_trade`，但改革栈中没有任何 0.23 系列的可选路线改革。因此问题不是路线条件未满足，而是候选改革没有进入政府改革树。

当前启用的两个中文 Mod 均不包含 `common/governments/00_governments.txt`，日轮诸道是当前 Playset 中唯一覆盖该文件的启用 Mod，故本轮问题不是政府文件加载顺序冲突。

## 代码级根因

1. 27 项玩家可选路线改革把 `jxp_path_*` 动态路线 flag 写在 `potential` 中。EU4 在政府改革树建立时会据此裁掉候选，而路线 flag 通常在开局后才获得；改革即使有定义、有本地化、已注册到层级，也可能永远不进入界面。
2. 旧架构仍通过 `jxp_grant_route_reforms_effect` 自动授予 27 项 `basic_reform = yes` 的未注册路线改革。这些是不可见的后台改革，不符合“并入原版前 11 级供玩家选择”的设计要求。
3. `jxp_realm.5` 同时等待一个后台改革和一个玩家可选改革，却只授予后台改革。玩家可选改革从未显示、也从未被授予，使隐藏检查事件持续重复。
4. 38 项建国来源改革只有动态 `potential`，却没有统一的旧存档精确授予入口；其后续事件虽然检查 `has_reform`，但改革本身可能从未进入改革栈。

## 0.23.2 修复

- 27 项路线改革的 `potential` 统一改为稳定的日本政体身份，并加入 `has_reform = <self>` 作为已选保留条件。
- 九条路线的 tag/flag 条件全部移动到动态 `trigger`；每条路线恰有 3 项改革。
- 所有可选路线改革加入 `allow_normal_conversion = yes`，继续注册在原版君主制前 11 级，不增加第 12 级以后层级。
- `jxp_grant_route_reforms_effect` 不再自动授予 parked 改革，只保留政体纠正、遗留清理和建国来源迁移职责。
- 新增 `jxp_remove_legacy_autogranted_route_reforms_effect`，旧存档会移除此前自动塞入的 27 项不可见基础改革。
- 新增 `jxp_grant_founder_house_reform_effect`：按唯一 `jxp_origin_*` 精确授予一项建国来源改革；无来源的迁移/调试存档使用通用改革。
- `jxp_realm.5` 改为一次性 0.23.2 迁移，设置 `jxp_reform_visibility_migration_v0232` 后停止，不再每日等待未选择的可选改革。
- 调试清理同步清除 `jxp_reform_visibility_migration_v0232` 与 `jxp_founder_reform_assigned_v0232`。
- 新增可重复执行的 `rewrite_government_reforms_v0232.py`；连续执行结果一致。

## 当前改革分布

- 第 2 级：按建国来源精确授予一项家法/建国宪制改革。
- 第 3 至 11 级：27 项路线改革按官僚、宗教、军制、议政、行政、经济、正统性和权力分立主题嵌入原版层级。
- 开国通商路线：第 5 级“异国炮术契约”；第 8 级“银座会计所”“敕许商馆网”。
- 其余八条路线各有 3 项对应改革；未选择的路线改革保持锁定，不会错误获得其效果。

## 验证结果

- 通用 Mod 校验：通过。
- JXP 发布门禁：11/11 通过。
- Clausewitz：167/167 通过。
- 政府改革：27 项可见路线改革、38 项建国来源改革全部定义并注册；306 项历史草案保持 parked。
- 路线矩阵：9/9 路线各 3 项；动态路线条件只允许出现在 `trigger`。
- 自动授予审计：0 项可选路线改革被自动授予；0 项 parked 改革被自动授予；38 项建国来源改革各有且只有一个授予分支。
- 回归测试：26/26 通过，其中包含路线与建国来源重写器幂等测试。
- 图标与本地化：现有 35 张 57x57 RGBA DDS 与对应 sprite 校验继续通过；本轮没有新增图片需求。

政府改革定义不能热加载。下一次由玩家正常启动 EU4、载入旧存档并推进一个游戏日后，迁移事件才会完成遗留清理与建国来源改革授予。根据玩家要求，本轮不会再次自行启动游戏；最终界面确认留待玩家正常测试。

部署前备份：

`C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\_jxp_backups\japan_expanded_v2_before_reform_visibility_hotfix_20260709_164900.zip`
