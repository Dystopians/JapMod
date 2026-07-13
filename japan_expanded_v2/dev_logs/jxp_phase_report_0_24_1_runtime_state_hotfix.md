# 日轮诸道 0.24.1：理念与任务运行态修复

日期：2026-07-09

## 问题证据

- 用户截图中，理念组标题为“朱子礼制日本理念”，悬停项目却是吉利支丹理念“天正遣欧”。这证明当前国家同时保留了不同终局 tag 的免费国家理念组，而非单纯的图标宽度问题。
- 现有 `error.log` 出现 `Missing Icon 'national_idea8'`，与超过七项的叠加免费理念组一致。
- 同一日志两次记录五组 `mission.cpp:353`：JXP 五列分别与 `DOM_japanse_missions_*` 原版日本任务组重叠。
- 未压缩的 `autosave.eu4` 中，玩家国家的 `country_missions` 同时序列化了原版 DOM 与 JXP 任务组；`completed_missions` 中的 JXP 完成记录仍然存在，说明进度主要是被错误任务组遮蔽，而非从存档删除。
- 存档还保留六个以原始字节 `EF BB BF` 开头的历史 JXP 任务组键。旧版本玩法脚本的 BOM 被 EU4 1.37.5 当成首个顶层任务组键的一部分保存。

## 已实施修复

1. 将两个 1.37.5 原版日本任务覆盖文件中的 23 个顶层任务组统一改名为 `jxp_disabled_vanilla_*`，同时保留 `potential` 与 `potential_on_load` 的双重禁用。
2. 将隔离原版任务内残留的五处直接 `swap_non_generic_missions` 全部改为 `jxp_refresh_route_missions_effect`，全 Mod 只剩延迟隐藏事件执行真正刷新。
3. 新增 `jxp_sync_route_national_ideas_effect`：KJP/CJP/EJP/RFJ/SJP/IJP/WAK 在非自定义理念国家中自动执行一次 `swap_free_idea_group`，并校验当前 tag 对应理念组。
4. 移除九处可拒绝的 `ideagroups.1` 询问。路线 tag 的国家理念现在属于确定性国体状态，不再允许旧理念残留。
5. 新增一次性迁移 `jxp_migration_v023.6`：清除卡住的刷新标记、强制理念同步，并安排一日后的规范任务刷新。
6. 为存档中实际发现的六个 BOM 污染任务组生成逐字节锁定、永不激活的兼容别名，使刷新能够识别并剔除坏键；普通玩法脚本仍禁止 BOM。
7. 任务状态矩阵由 47 扩展为 188：37 个大名和 10 个统一后状态，分别覆盖双 DLC、仅 Domination、仅 Mandate of Heaven、无相关 DLC。
8. 所有统一后状态强制保留 `jxp_japan_state_missions` 与 `jxp_japan_court_missions` 两条共享主干，防止宗教或终局 tag 切换隐藏已完成的共同任务。
9. 将日志确认无效的 `aggressive_expansion_impact` 修正改为 1.37.5 原版使用的 `ae_impact`。

## 静态验收

- 版本：`0.24.1`。
- 175/175 个玩法脚本通过 Clausewitz 解析。
- 238 个任务、34 个正式任务组、188 个有效状态全部通过五槽覆盖、零通用回填、单元格冲突、依赖、连线几何与共享主干连续性检查。
- 两个原版任务覆盖文件与 1.37.5 固定哈希一致，除生成式隔离、双禁用及延迟刷新替换外无漂移。
- 6/6 个旧档 BOM 兼容别名通过完整字节比对。
- 七个终局国家理念组均为七项；全 Mod 只有一个规范 `swap_free_idea_group`，没有 `ideagroups.1` 路线调用。
- 32 项单元测试通过。
- `validate_jxp_mod.ps1` 的一般校验、发布校验、拓扑、资源与单元测试全部通过。

## 运行时状态

本阶段遵照用户要求，没有启动 EU4，因此当前结论为“静态安全”，尚未标记“游戏内确认”。

旧档验证必须冷启动 EU4 后加载存档，推进至少两日，再检查：

- 理念栏只剩当前 tag 对应的七项理念，标题与悬停文本属于同一路线；
- 五列任务树只包含当前路线的 JXP 任务组；
- 已完成的 JXP 共享任务重新显示为完成；
- 新生成的 `error.log` 不再出现 `national_idea8` 或 JXP 与 `DOM_japanse_missions_*` 的 `mission.cpp:353`。

路线专属任务在切换到另一互斥路线后不会继续显示；这是分支设计。共同国家建设与朝廷主干则必须连续保留，现已由验证器强制保证。
