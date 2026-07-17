# 日轮诸道阶段报告：0.11.0 建国分支高阶政府改革
日期：2026-07-09

## 本阶段定位

0.11.0 将开发重点从“具体家族 × 路线事件”转向“日本建国分支的特色政府改革”。本阶段没有替换原有路线改革系统，而是在既有 `state_doctrine` 与 `founder_house_constitution` 之间新增一层可见、互斥、玩家可选择的高阶路线改革：`日轮国制枢机`。

## 新增改革层级

新增政府改革层：

- `jxp_route_institution_capstone`
  - 显示名：日轮国制枢机。
  - 注册在 monarchy 的 `reform_levels` 中，位于路线国制末段与创立家族宪制之间。
  - 每条建国分支 2 个改革，共 18 个。
  - 不自动授予，作为同一层级内的路线特色选择，避免一条路线同时获得两个互斥选项。

## 新增路线改革

- 锁国日本：
  - `jxp_reform_sakoku_gosanke_council`：御三家评定。
  - `jxp_reform_sakoku_kaikin_watchtowers`：海禁远见番。
- 开国通商日本：
  - `jxp_reform_open_oceanic_cabinet`：远洋参议局。
  - `jxp_reform_open_treaty_port_commission`：条约港会审司。
- 吉利支丹日本：
  - `jxp_reform_kirishitan_crown_patronage`：日轮圣座护持。
  - `jxp_reform_kirishitan_deus_vult_council`：圣战评议会。
- 朱子礼制日本：
  - `jxp_reform_confucian_rites_ministry`：礼部省。
  - `jxp_reform_confucian_harmonious_codes`：三教和同律。
- 王政复古日本：
  - `jxp_reform_imperial_daijokan_cabinets`：太政官内阁。
  - `jxp_reform_imperial_restoration_guard`：王政亲兵府。
- 新教/改革日本：
  - `jxp_reform_reformed_synodic_estates`：长老诸身分会。
  - `jxp_reform_reformed_print_capital`：印书都监。
- 海峡/伊斯兰日本：
  - `jxp_reform_kaikyo_maritime_diwan`：海洋迪万。
  - `jxp_reform_kaikyo_qadi_kanrei_court`：卡迪管领裁判所。
- 一向/民众日本：
  - `jxp_reform_ikko_somon_diet`：惣中大评定。
  - `jxp_reform_ikko_monto_levy_charter`：门徒军役约书。
- 倭寇日本：
  - `jxp_reform_wokou_corsair_council`：朱札海寇会。
  - `jxp_reform_wokou_tidewater_customs`：潮汐关市司。

## 文件变更

- 新增 `common/government_reforms/jxp_32_route_capstone_reforms.txt`
  - 定义 18 个高阶路线改革。
- 修改 `common/governments/00_governments.txt`
  - 注册 `jxp_route_institution_capstone` 层级。
- 修改 `common/scripted_effects/jxp_scripted_effects.txt`
  - `jxp_clear_route_reforms_effect` 现在清理 18 个新增改革，防止路线切换后旧改革残留。
- 新增 `localisation_source/jxp_32_route_capstone_reforms_l_english_utf8_source.yml`
  - 新增改革层级与改革文案源。
- 新增 `localisation/jxp_32_route_capstone_reforms_l_english.yml`
  - 已生成 EU4SpecialEscape active localisation。
- 修改 descriptor：
  - 版本号更新为 `0.11.0`。

## Skill 与校验增强

- `check_jxp_japan_coverage.py`
  - 路线改革检查现在会读取 scripted effects。
  - 每个路线改革都必须有 `remove_government_reform = <key>` 清理路径。
  - 层级本地化检查扩展到 `society`、`arms`、`horizon`、`state_doctrine`、`capstone`。
- `modding-reference.md`
  - 新增经验：可选路线改革层应注册但不自动授予；同时必须验证定义、potential、政府注册、层级本地化、改革本地化与路线切换清理。

## 当前全局任务对应进度

- 每个日本建国分支已经拥有更具路线识别度的政府改革层。
- 每条路线当前统计为：
  - hidden carrier/auto reforms: 3
  - visible registered route reforms: 13
  - unregistered route reforms: 0
- 本阶段强化了后续继续扩展政府改革的基础设施；之后可进一步做“路线 × 创立家族”的专属可选改革，或把部分改革解锁挂到任务树条件上。

## 校验结果

已通过：

- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- `check_jxp_japan_coverage.py`
  - 9 条路线均为 `3 13 0`
  - `major_origin_combo_coverage 14/14`
- `quick_validate.py` for `eu4-modding` skill
- `jxp_32_route_capstone_reforms_l_english.yml`
  - UTF-8 BOM: true
  - raw CJK: 0
  - escape triplets: 812
- `descriptor.mod` 与外层 `.mod`
  - UTF-8 BOM: true
  - version: `0.11.0`
- 原版 EU4 根目录：
  - 无 `jxp_*` 残留文件。

## 剩余风险

- 尚未进行游戏内政府改革 UI 实测。静态检查可确认定义、注册、本地化和清理链路，但仍建议进入统一后的日本路线，打开政府改革界面确认新层级位置和选项显示。
- 这些改革为手选层级，不会由路线切换自动授予；若后续想让任务树逐步解锁其中一部分，需要为改革增加任务 flag 或 hidden trigger，并扩展 coverage checker。
