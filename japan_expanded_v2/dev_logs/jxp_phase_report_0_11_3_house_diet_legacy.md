# 日轮诸道阶段报告：0.11.3 家法入国制
日期：2026-07-09

## 本阶段定位

0.11.3 承接 0.11.2 的“大名家法评定”。上一阶段让大名在统一前能选择本家的制度气质；本阶段解决其长期承接问题：每个家法选项现在会留下具体选择 flag，并在统一日本后通过“编入天下法度”决议转化为永久但温和的国家遗产修正。

这使大名阶段的选择能够真正延伸到建国后，而不是只停留在一个 20 年临时修正上。

## 结构修复

修改 `events/jxp_34_daimyo_house_diet_events.txt`：

- 每个家法选项现在都会设置一个持久选择 flag：
  - `jxp_34_selected_warrior_muster_law`
  - `jxp_34_selected_warrior_captain_privileges`
  - `jxp_34_selected_court_rank_law`
  - `jxp_34_selected_court_domain_law`
  - `jxp_34_selected_maritime_port_law`
  - `jxp_34_selected_maritime_admiral_rolls`
  - `jxp_34_selected_frontier_barrier_law`
  - `jxp_34_selected_frontier_market_charter`
  - `jxp_34_selected_temple_privilege_law`
  - `jxp_34_selected_temple_accounting_law`

这些 flag 是后续统一后事件、任务树分支或特殊改革读取家法传统的稳定入口。

## 新增统一后内容

新增决议：

- `jxp_decision_integrate_house_diet_law`
  - 仅统一日本状态可见。
  - 要求已经召开过大名家法评定。
  - 触发 `jxp_house_diet_legacy.1`。

新增事件：

- `jxp_house_diet_legacy.1`
  - 根据 10 个具体选择 flag 显示对应选项。
  - 移除仍在持续的 0.11.2 临时家法修正。
  - 授予对应永久国家修正。
  - 旧存档若只有通用 `jxp_34_house_diet_convened` 而没有具体选择 flag，会显示 fallback 选项。

新增永久修正：

- `jxp_35_legacy_warrior_muster_law`
- `jxp_35_legacy_warrior_captain_privileges`
- `jxp_35_legacy_court_rank_law`
- `jxp_35_legacy_court_domain_law`
- `jxp_35_legacy_maritime_port_law`
- `jxp_35_legacy_maritime_admiral_rolls`
- `jxp_35_legacy_frontier_barrier_law`
- `jxp_35_legacy_frontier_market_charter`
- `jxp_35_legacy_temple_privilege_law`
- `jxp_35_legacy_temple_accounting_law`

## 文件变更

- 新增 `decisions/jxp_35_house_diet_legacy_decisions.txt`
- 新增 `events/jxp_35_house_diet_legacy_events.txt`
- 新增 `common/event_modifiers/jxp_35_house_diet_legacy_modifiers.txt`
- 新增 `localisation_source/jxp_35_house_diet_legacy_l_english_utf8_source.yml`
- 新增 `localisation/jxp_35_house_diet_legacy_l_english.yml`
- 修改 `events/jxp_34_daimyo_house_diet_events.txt`
- 修改 `common/scripted_effects/jxp_debug_effects.txt`
- 修改 descriptor
  - 版本号更新为 `0.11.3`。

## Skill 与校验增强

- `check_jxp_japan_coverage.py`
  - `daimyo_house_diet_report` 现在检查 10 个具体选择 flag 是否由早期选项写入，并由 debug cleanup 清理。
  - 新增 `house_diet_legacy_report`，检查统一后决议、事件、fallback、10 个永久修正、本地化和 cleanup。
- `modding-reference.md`
  - 新增经验：早期选择若要影响后期，不应只依赖 timed modifier，必须设置具体持久 `selected_*` flag，并让后期事件读取该 flag。

## 当前全局任务对应进度

- “各个大名国家特殊事件、特殊决议”
  - 大名阶段已有 tag/组别特殊决议、家门议题事件和家法评定决议。
- “特定家族或者大名统一日本的特殊事件和加成”
  - 本阶段新增从大名阶段选择到统一后永久遗产的承接链。
  - 统一后遗产不再只由 origin/archetype 决定，也可由玩家在统一前的具体家法选择决定。
- “增加多样性特殊性”
  - 同一创立家门类型内部现在有两条可延续至统一后的不同制度记忆。

## 校验结果

已通过：

- `validate_eu4_mod.ps1`
  - No issues found。
- `check_mission_series_overlap.py`
  - no route-profile mission slot overlaps found。
- `check_jxp_japan_coverage.py`
  - `Daimyo house diet coverage` 全项 OK。
  - `House diet legacy coverage` 全项 OK。
  - `all_origin_combo_coverage 37/37` 仍保持通过。
- `quick_validate.py` for `eu4-modding` skill
  - Skill is valid。
- 编码检查
  - `jxp_35_house_diet_legacy_l_english.yml`: UTF-8 BOM true, raw CJK 0, escape triplets 623。
  - `descriptor.mod` 与外层 `.mod`: UTF-8 BOM true, version `0.11.3`。
- 原版 EU4 根目录残留检查
  - 无 `jxp_*` 残留文件。

## 剩余风险与下一步

- 尚未进行游戏内 UI 实测。建议测试路径：大名开局 -> 召开家法评定 -> 统一日本或 debug 统一 -> 点击“编入天下法度”，确认只显示对应家法遗产选项。
- 下一步可把 10 个 `jxp_34_selected_*` 或 10 个 `jxp_35_legacy_*` 修正接入任务树条件，让大名家法真正塑造建国后任务分支。
