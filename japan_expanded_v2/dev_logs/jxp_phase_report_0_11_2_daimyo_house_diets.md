# 日轮诸道阶段报告：0.11.2 大名家法评定
日期：2026-07-09

## 本阶段定位

0.11.2 继续推进“大名特殊性”主线。本阶段没有继续堆叠统一后的路线事件，而是把可操作空间前移到大名阶段：新增一个统一前可主动点击的“家法评定”决议，由当前大名记录 origin 后按创立家门类型进入不同分支事件。

玩家在同一事件里只会看到本家所属家门类型的两项选择，使早期大名阶段不仅有一次性地方决议，也能在制度气质上做出分歧。

## 新增机制

新增决议：

- `jxp_decision_convene_house_diet`
  - 仅大名阶段、未选择建国路线、37 个预期大名 tag 可见。
  - 召开家法评定前会调用 `jxp_ensure_daimyo_polity_effect`，确保三项时代属性初始化并记录当前大名 origin。
  - 触发 `jxp_house_diet.1`。

新增事件：

- `jxp_house_diet.1`
  - `is_triggered_only = yes`。
  - 依据 5 类创立家门触发器显示对应选项：
    - 武家型：军役帐 / 旗头机断。
    - 公家型：官途家名 / 本国代官法。
    - 海商型：浦方法度 / 船籍海番。
    - 边境型：境目番所 / 境目市口。
    - 寺社町座型：社寺旧例 / 町座公账。
  - 每类 2 个选项，均影响三项时代属性之一，并给予 20 年国家修正。
  - 额外保留一个仅用于缺失 origin 的 fallback 选项，避免 debug 或旧存档手动触发时出现无选项事件。

新增国家修正：

- `jxp_34_warrior_muster_law`
- `jxp_34_warrior_captain_privileges`
- `jxp_34_court_rank_law`
- `jxp_34_court_domain_law`
- `jxp_34_maritime_port_law`
- `jxp_34_maritime_admiral_rolls`
- `jxp_34_frontier_barrier_law`
- `jxp_34_frontier_market_charter`
- `jxp_34_temple_privilege_law`
- `jxp_34_temple_accounting_law`

## 文件变更

- 新增 `decisions/jxp_34_daimyo_house_diets.txt`
- 新增 `events/jxp_34_daimyo_house_diet_events.txt`
- 新增 `common/event_modifiers/jxp_34_daimyo_house_diet_modifiers.txt`
- 新增 `localisation_source/jxp_34_daimyo_house_diet_l_english_utf8_source.yml`
- 新增 `localisation/jxp_34_daimyo_house_diet_l_english.yml`
- 修改 `common/scripted_effects/jxp_debug_effects.txt`
  - 清除 `jxp_34_house_diet_convened`。
  - 移除 10 个新增家法修正。
- 修改 descriptor
  - 版本号更新为 `0.11.2`。

## Skill 与校验增强

- `check_jxp_japan_coverage.py`
  - 新增 `daimyo_house_diet_report`。
  - 检查决议链、事件、fallback、本地化、debug cleanup。
  - 检查 5 类家门分支各自的 2 个选项、2 个修正、修正文案和清理链路。
- `modding-reference.md`
  - 新增经验：单个决议按家门类型分支时，覆盖检查必须验证完整分支矩阵，而不是只验证按钮存在。

## 当前全局任务对应进度

- “各个大名国家特殊事件、特殊决议”
  - 已有每个大名的 tag/组别特殊决议与事件覆盖。
  - 本阶段新增大名阶段可主动选择的家法评定，覆盖全部 37 个预期大名。
- “特定家族或者大名统一日本的特殊事件和加成”
  - 既有 founder legacy、founder house reforms、route-house combo 仍保持 37/37 覆盖。
  - 本阶段新增的家法选择会在统一前塑造 origin 记忆，后续可进一步让统一后任务或改革读取这些家法结果。
- “增加多样性特殊性”
  - 同一类大名不再只有随机议题事件，也可通过决议选择制度方向。

## 校验结果

已通过：

- `validate_eu4_mod.ps1`
  - No issues found。
- `check_mission_series_overlap.py`
  - no route-profile mission slot overlaps found。
- `check_jxp_japan_coverage.py`
  - `Daimyo house diet coverage` 全项 OK。
  - `all_origin_combo_coverage 37/37` 仍保持通过。
- `quick_validate.py` for `eu4-modding` skill
  - Skill is valid。
- 编码检查
  - `jxp_34_daimyo_house_diet_l_english.yml`: UTF-8 BOM true, raw CJK 0, escape triplets 616。
  - `descriptor.mod` 与外层 `.mod`: UTF-8 BOM true, version `0.11.2`。
- 原版 EU4 根目录残留检查
  - 无 `jxp_*` 残留文件。

## 剩余风险与下一步

- 尚未进行游戏内 UI 实测。建议用任意大名开局，确认“召开家法评定”只出现一次，点击后只显示本家所属家门类型的两个选项。
- 下一步可以把家法结果接入任务树或统一后改革，例如让“家法军役帐”降低某些武家路线任务门槛，让“浦方法度”强化开国、倭寇或海峡路线任务分支。
