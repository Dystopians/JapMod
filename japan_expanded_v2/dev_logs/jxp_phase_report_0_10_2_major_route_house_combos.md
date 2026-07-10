# 日轮诸道阶段报告：0.10.2 主要大名路线组合补全
日期：2026-07-09

## 本阶段定位

0.10.2 继续推进“特定家族或大名统一日本的特殊事件和加成”。0.10.1 已建立 6 个代表性的创立大名 × 路线组合事件；本阶段将该系统扩展到 14 个主要大名，确保每个主要大名至少拥有一个具体路线组合事件，而不是只依赖通用家风事件。

## 新增具体组合

本阶段新增 9 个低频 MTTH 组合事件，每个事件都有两个可选方向：路线制度化，或保留创立家族旧法。

- 织田 × 开国通商：安土朱印与天下市场。
- 德川 × 锁国：谱代闭国与三河人质秩序。
- 武田 × 朱子礼制：甲州法度与山国军法。
- 上杉 × 王政复古：管领奏书与越后义理。
- 北条 × 锁国：小田原检地与总构守备。
- 岛津 × 海峡/伊斯兰：萨南商港与萨摩铸炮。
- 长宗我部 × 一向/民众路线：一领具足与土佐乡约。
- 大内 × 开国通商：山口勘合与周防商议。
- 今川 × 朱子礼制：东海道礼法与骏府家法。

加上 0.10.1 已有的大友、毛利、足利、朝仓、伊达、宗氏组合后，主要大名覆盖为 14/14。

## 关键实现

- `events/jxp_31_specific_route_house_events.txt`
  - 新增 `jxp_specific_route_house.7` 至 `.15`。
  - 每个事件都使用统一日本、创立 origin flag、路线 flag/tag、一次性 seen flag 作为触发条件。
- `common/event_modifiers/jxp_31_specific_route_house_modifiers.txt`
  - 新增 18 个十年国家修正，每个组合两种奖励方向。
- `common/scripted_effects/jxp_31_specific_route_house_effects.txt`
  - Debug/重测清理新增 9 个 seen flag 与 18 个修正。
- `localisation_source/jxp_31_specific_route_house_l_english_utf8_source.yml`
  - 新增全部事件、选项、修正文案。
- `localisation/jxp_31_specific_route_house_l_english.yml`
  - 已从 source 重新生成 EU4SpecialEscape active localisation。
- `descriptor.mod` 与外层 `japan_expanded_v2.mod`
  - 版本号更新为 `0.10.2`。

## Skill 与校验增强

- `eu4-modding` skill 的 `modding-reference.md` 增补经验：
  - 当一个开发阶段承诺覆盖“主要大名”等具名子集时，不能只验证已写事件是否完整，还应把 expected-combo 表与目标 tag 子集比对，防止遗漏某个主要家族。
- `check_jxp_japan_coverage.py` 增强：
  - `Specific route-house combo coverage` 现在输出 `major_origin_combo_coverage 14/14`。
  - 如果 14 个主要大名中任何一个没有具体路线组合，脚本会失败。

## 当前全局任务对应进度

- 各大名特殊事件、特殊决议：37 个大名已有前统一/统一后基础家风层；14 个主要大名已有具体路线组合事件。
- 特定家族统一日本的特殊事件和加成：已完成 founder legacy council、route-house compromise、route-house resonance，以及主要大名具体组合层。
- 大名理念微调：37 个大名理念组已完整覆盖，并由 checker 校验 start、bonus、trigger、free、7 个理念和本地化。
- 政府改革特色化：路线改革与 founder-house 改革已注册并校验；后续可继续增加“路线 × 家族”的可选改革层。
- 后续重点：把具体组合系统从 14 个主要大名逐步扩展到 37 个大名，或优先围绕玩家常用家族增加 mission/event/decision 联动。

## 校验结果

已通过：

- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- `check_jxp_japan_coverage.py`
  - `major_origin_combo_coverage 14/14`
  - 15 个具体组合全部 OK。
- `quick_validate.py` for `eu4-modding` skill
- `jxp_31_specific_route_house_l_english.yml`
  - UTF-8 BOM: true
  - raw CJK: 0
  - escape triplets: 1966
- `descriptor.mod` 与外层 `.mod`
  - UTF-8 BOM: true
  - version: `0.10.2`
- 原版 EU4 根目录：
  - 无 `jxp_*` 残留文件。

## 剩余风险

- 本阶段尚未进行游戏内 UI、事件弹窗、存档读档和 `error.log` 实测。
- 静态脚本能确认结构、触发门槛、本地化、清理和任务重叠，但无法替代一次真实进局观察；建议用任一主要大名统一后切换路线，观察 20-50 年，确认低频组合事件弹出节奏合理。
