# 日轮诸道阶段报告：0.10.0 路线与开府家风低频共鸣事件

日期：2026-07-09

## 本阶段定位

本阶段继续推进“各大名统一日本后的多样性”目标。在 0.9.9 的一次性“议定诸道家法”之后，0.10.0 新增低频 MTTH 事件层，让统一后的日本在路线确定后继续受到开府家风影响。该层不是决议，而是偶发风味事件，避免决议列表过长，同时增加中后期代入感。

## 新增玩法

新增 5 个低频事件，对应五类开府家风：

- 武门：旗帐、军役与新国体的摩擦。
- 京洛：官途、谱系、席次与新路线名分的调和。
- 海国：浦港旧例、水军、通事与外海路线的适配。
- 境目：边地关门、马市、远境誓纸与新路线的接合。
- 社寺市座：寺社、市座、门前町与路线公法的冲突。

每个事件均有两个选项：

- 路线压力选项：按当前路线推进对应时代属性。
  - 锁国/一向宗偏向天下秩序。
  - 开国、吉利支丹、改革宗、海峡/伊斯兰、倭寇偏向海门外学。
  - 朱子礼制、王政复古偏向天皇裁可。
- 家风调和选项：按创立家族所属类型推进对应家风属性。

## 新增文件

- `events/jxp_30_route_house_resonance_events.txt`
- `common/event_modifiers/jxp_30_route_house_resonance_modifiers.txt`
- `common/scripted_effects/jxp_30_route_house_resonance_effects.txt`
- `localisation_source/jxp_30_route_house_resonance_l_english_utf8_source.yml`
- `localisation/jxp_30_route_house_resonance_l_english.yml`

## 修改文件

- `common/scripted_effects/jxp_debug_effects.txt`
  - 新增 `jxp_clear_route_house_resonance_effect` 调用。
- `descriptor.mod` 与外层 `.mod`
  - 版本号更新至 `0.10.0`。
- `eu4-modding` skill
  - `check_jxp_japan_coverage.py` 新增 `Route-house resonance coverage`。
  - `modding-reference.md` 新增低频 route/founder MTTH 事件校验经验。

## 当前全局任务对应进度

- 各大名国家特殊事件与特殊决议：已有前统一、统一后、家族议会和家风层覆盖。
- 特定家族/大名统一日本的特殊事件与加成：0.10.0 增加统一后低频路线/家风共鸣事件。
- 路线国家多样性：现在包含路线改革、路线任务、路线/家风一次性评议和路线/家风偶发事件。
- 大名理念微调：已完成并由专用 checker 审计。

## 校验结果

通过：

- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- `check_jxp_japan_coverage.py`
  - `Route-house resonance coverage`：5/5 家风事件全 OK。
- `quick_validate.py` for `eu4-modding` skill
- 新 active localisation：UTF-8 BOM 为 true，raw CJK 为 0。
- descriptor：外层与内层均为 UTF-8 BOM，版本 `0.10.0`。
- 原版 EU4 根目录无 `jxp_*` 残留。

## 后续建议

- 下一阶段可挑选少量“具体创立家族 × 具体路线”的代表组合做稀有事件，例如大友吉利支丹、毛利开国、足利王政、伊达倭寇、朝仓朱子等。
- 若继续扩大覆盖，建议仍以低频 MTTH 为主，不要继续增加常驻决议。
