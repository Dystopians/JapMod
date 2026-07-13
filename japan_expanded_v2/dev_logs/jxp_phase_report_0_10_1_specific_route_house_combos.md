# 日轮诸道阶段报告：0.10.1 具体创立家族与路线组合事件

日期：2026-07-09

## 本阶段定位

本阶段继续推进“特定家族或者大名统一日本的特殊事件和加成”。此前 0.9.9 与 0.10.0 已建立路线/家风的通用交互层；0.10.1 开始加入更具体的“创立大名 × 路线”代表组合事件，让特定家族统一日本后的路线选择拥有更鲜明的历史气息。

## 新增组合

新增 6 个低频 MTTH 事件：

- 大友 × 吉利支丹：府内圣堂与丰后旧臣。
- 毛利 × 开国通商：濑户内朱印船议。
- 足利 × 王政复古：公方旧名奉还。
- 朝仓 × 朱子礼制：一乘谷讲学。
- 伊达 × 开国通商：庆长使节再议。
- 宗氏 × 倭寇路线：对马海峡诸札。

每个事件均有两项选择：

- 路线取向：强化当前路线所代表的国体方向。
- 家族取向：保留创立大名旧法、旧臣或地方经验，以换取更稳妥的本土整合。

## 新增文件

- `events/jxp_31_specific_route_house_events.txt`
- `common/event_modifiers/jxp_31_specific_route_house_modifiers.txt`
- `common/scripted_effects/jxp_31_specific_route_house_effects.txt`
- `localisation_source/jxp_31_specific_route_house_l_english_utf8_source.yml`
- `localisation/jxp_31_specific_route_house_l_english.yml`

## 修改文件

- `common/scripted_effects/jxp_debug_effects.txt`
  - 接入 `jxp_clear_specific_route_house_combo_effect`。
- `descriptor.mod` 与外层 `.mod`
  - 版本号更新至 `0.10.1`。
- `eu4-modding` skill
  - `check_jxp_japan_coverage.py` 新增 `Specific route-house combo coverage`。
  - `modding-reference.md` 新增具体 founder-tag/route 组合事件的表格式覆盖经验。

## 当前全局任务对应进度

- 大名特殊事件与决议：已覆盖前统一、统一后家族、路线/家风通用层，并开始加入具体路线组合事件。
- 特定家族统一日本加成：本阶段新增 6 个代表性具体组合。
- 大名理念：已完成并由 checker 审计。
- 后续建议：继续按此格式补充更多代表组合，例如织田×锁国、岛津×海峡、上杉×王政、今川×朱子、北条×锁国或王政等。

## 校验结果

通过：

- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- `check_jxp_japan_coverage.py`
  - `Specific route-house combo coverage`：6/6 组合全 OK。
- `quick_validate.py` for `eu4-modding` skill
- 新 active localisation：UTF-8 BOM 为 true，raw CJK 为 0。
- descriptor：外层与内层均为 UTF-8 BOM，版本 `0.10.1`。
- 原版 EU4 根目录无 `jxp_*` 残留。

## 注意事项

- 本阶段仍未进行游戏内 UI 与日志测试；当前结论基于静态校验和专用覆盖校验。
- 具体组合事件数量不宜一次性扩展到 37×9，应优先选择历史合理、路线辨识度高、玩法收益清晰的组合逐步追加。
