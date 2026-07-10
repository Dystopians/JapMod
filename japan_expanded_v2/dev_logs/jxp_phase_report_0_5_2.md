# 日轮诸道：日本扩展风味包 热修复报告

更新时间：2026-07-09
当前版本：0.5.2

## 问题

成为朱子礼制日本后：

- 神道教没有可靠显示为已融合。
- 朱子礼制日本不再显示保留神道礼制的日本神道分支任务。
- 任务树仍有显示问题，部分追加任务与原版日本任务或其他路线分支挤在同一列同一位置。

## 根因

1. CJP 转换效果中虽然直接调用过 `add_harmonized_religion = shinto`，但缺少统一的同步入口和已有存档兜底事件。如果一次性效果在事件顺序、旧存档或调试转换中没有落稳，之后没有自动修补。
2. 0.5.1 只修复了 `slot > 5` 不可见问题，但把大量追加任务移到第 9 行起。Domination 日本任务本身在前五列中会占用第 9-13 行附近的位置，因此追加任务仍可能与原版任务重叠。
3. 原 0.5 的神道分支要求 `religion = shinto` 且排除 `CJP/jxp_path_confucian`，所以朱子礼制日本即使理念上融合神道，也不会显示神道分支。

## 修复

宗教同步：

- 新增 `jxp_confucian_sync_shinto_effect`。
- `jxp_change_to_cjp_effect` 改为调用该同步效果。
- `jxp_confucian.2` 改为调用该同步效果。
- 新增隐藏兜底事件 `jxp_confucian.9`：已成为 CJP 或拥有朱子路线 flag、国教为儒教但缺少神道合礼状态时，会自动补上神道融合、神道合礼 flag、神道合礼修正与伊势保护。

任务显示：

- 自定义任务仍限制在 `slot = 1-5`。
- 所有与原版共存的主干任务统一从 `position = 14` 或之后开始，避免撞上 Domination 日本任务第 9-13 行。
- 朱子礼制日本的 CJP 可见布局现在为：
  - 共享国政主干：第 1/2 列 14-19 行。
  - 朱子礼制主干：第 5 列 14-20 行。
  - 神道合礼分支：第 4 列 14-18 行。
  - 朱子儒教分支：第 3 列 14-18 行。
  - 国内制度分支：第 3 列 21-26 行。
  - 边疆外交分支：第 5 列 27-32 行。

神道分支：

- `jxp_shinto_branch_missions` 现在允许 CJP/朱子路线在国教为儒教且拥有 `has_harmonized_with = shinto` 或 `jxp_confucian_shinto_syncretism` flag 时显示。
- 该分支不再排除 `CJP` 或 `jxp_path_confucian`。

## 受影响文件

- `common/scripted_effects/jxp_07_confucian_religion_effects.txt`
- `common/scripted_effects/jxp_scripted_effects.txt`
- `events/jxp_route_events.txt`
- `missions/jxp_japan_missions.txt`
- `missions/jxp_03_overseas_missions.txt`
- `missions/jxp_04_daimyo_missions.txt`
- `missions/jxp_09_religious_route_missions.txt`
- `missions/jxp_10_popular_maritime_missions.txt`
- `missions/jxp_11_branching_missions.txt`
- `descriptor.mod`
- `../japan_expanded_v2.mod`

## 校验

- EU4 Mod 校验脚本：通过。
- `missions` 中无 `slot > 5`。
- `missions` 中无 `position >= 40`。
- 本次未改动可见中文文案，因此未重新生成 localisation。

## 游戏内测试建议

新档测试：

- 进入日本统一路线，选择朱子礼制日本。
- 变为 `CJP` 后，确认国教为儒教。
- 约 1 天至 1 个月内应拥有神道合礼状态；若任务界面刷新不及时，可关闭再打开任务界面或读档。
- 任务树中应同时看到朱子儒教分支与保留神道礼制的神道分支。

旧档测试：

- 读取已经成为 CJP 的旧档后等待约 1 个月。
- 隐藏兜底事件应自动补上神道融合与神道合礼 flag。
