# 日轮诸道阶段报告：0.9.9 路线与开府家风交叉评议

日期：2026-07-09

## 本阶段定位

本阶段继续推进“各大名统一日本后的特殊性”目标。此前版本已经具备大名理念、前统一事件/决议、创立家族遗产会议、路线政府改革与开府家法改革；0.9.9 新增一层“路线 × 开府家风”的一次性评议，使统一后的路线国家不只由宗教或国体决定，也会受到创立家族传统的调和。

## 新增玩法

- 新增一次性决议 `jxp_decision_convene_route_house_compromise`：统一日本、已选择路线、拥有创立家族 origin 后可见。
- 决议按当前路线派发 9 个事件：
  - 锁国、开国、吉利支丹、朱子礼制、王政复古、改革宗、海峡/伊斯兰、一向宗、倭寇路线。
- 每个事件提供两类选择：
  - 路线压倒家法：获得路线专属中期修正，并调整对应时代属性。
  - 家法驯化路线：按创立家族所属类型获得家风修正。
- 创立家族类型沿用既有五类：
  - 武门、京洛、海国、境目、社寺市座。

## 新增文件

- `decisions/jxp_29_route_house_compromise_decisions.txt`
- `events/jxp_29_route_house_compromise_events.txt`
- `common/event_modifiers/jxp_29_route_house_compromise_modifiers.txt`
- `common/scripted_effects/jxp_29_route_house_compromise_effects.txt`
- `localisation_source/jxp_29_route_house_compromise_l_english_utf8_source.yml`
- `localisation/jxp_29_route_house_compromise_l_english.yml`

## 修改文件

- `common/scripted_effects/jxp_debug_effects.txt`
  - 接入 `jxp_clear_route_house_compromise_effect`，使 debug reset 清除新决议 flag 与所有新修正。
- `descriptor.mod` 与外层 `.mod`
  - 版本号更新至 `0.9.9`，保留 UTF-8 BOM。
- `eu4-modding` skill
  - `check_jxp_japan_coverage.py` 新增 `Route-house compromise coverage`。
  - `modding-reference.md` 新增跨系统路线/创立家族链路校验经验。

## 当前全局任务对应进度

- 各大名国家特殊事件与特殊决议：已覆盖，并继续由覆盖检查器审计。
- 特定家族/大名统一日本的特殊事件和加成：0.9.9 新增路线与开府家风交叉评议，使统一后路线也受创立家族影响。
- 大名理念微调：已在 0.9.2 完成，0.9.8 已固化完整性校验。
- 各日本建国分支政府改革：已在 0.9.0、0.9.5、0.9.6 完成路线与创立家族改革层。

## 校验结果

通过：

- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- `check_jxp_japan_coverage.py`
  - 新增 `Route-house compromise coverage`：9/9 路线全 OK，5/5 家风调和修正全 OK。
- `quick_validate.py` for `eu4-modding` skill
- 新 active localisation：UTF-8 BOM 为 true，raw CJK 为 0。
- 原版 EU4 根目录无 `jxp_*` 残留。

## 后续建议

- 下一阶段可继续补充“路线 × 具体创立家族”的稀有事件，例如织田锁国、毛利开国、大友吉利支丹、朝仓朱子、伊达倭寇等少量代表性组合。
- 若要进一步提高完成度，建议把这些组合事件做成低频 MTTH，而不是继续增加一次性决议，以免决议列表过长。
