# 0.9.5 阶段报告：路线状态修复与终纲政府改革

## 本阶段目标

- 修复朱子礼制日本等路线国家在旧存档或异常路线 flag 状态下触发原版共和独裁事件的问题。
- 修复路线 flag 污染导致 CJP 显示其他路线任务列的风险。
- 让 CJP 在儒教调和/融合神道后重新显示神道风味任务列。
- 为每条日本建国路线新增一层更具特色的可选政府改革。

## 关键实现

- 新增隐藏修复事件 `jxp_realm.6`：
  - 检测路线 tag/flag 与宗教、政府类型、互斥路线 flag 的冲突。
  - 调用 `jxp_sanitize_route_state_effect` 进行路线净化。
- 新增 `jxp_sanitize_route_state_effect`：
  - 优先按当前 route tag 判定路线，避免 KJP 等路线 tag 因残留 `jxp_path_confucian` 被错误转为 CJP。
  - 清理所有互斥路线 flag、旧 route 修正和路线改革。
  - 强制路线国家回到君主制，移除 `presidential_despot_reform`、`military_dictatorship_reform`。
  - 按路线重设唯一 route flag、永久 route 修正、宗教、理念刷新、政府机制和任务刷新。
- `jxp_grant_route_reforms_effect` 现在会在授予路线改革前调用 `jxp_force_monarchical_route_effect`，更早阻断原版 `republics.3`。
- `jxp_clear_all_route_flags_effect` 现在同步清理 route country modifiers。
- `jxp_shinto_branch_missions` 新增 CJP/朱子路线兼容条件：
  - `has_harmonized_with = shinto`
  - `jxp_confucian_shinto_syncretism`
  - `jxp_confucian_shinto_synthesis`
  - `harmonized_shinto`

## 新增政府改革

新增可见改革层级 `jxp_route_institution_state_doctrine`，每条路线各 2 个终纲改革：

- 锁国：`jxp_reform_sakoku_kanei_border_cordon`、`jxp_reform_sakoku_inner_almanacs`
- 开国：`jxp_reform_open_pacific_custom_houses`、`jxp_reform_open_foreign_drill_mission`
- 吉利支丹：`jxp_reform_kirishitan_order_of_the_sun`、`jxp_reform_kirishitan_nagasaki_crown_admiralty`
- 朱子礼制：`jxp_reform_confucian_taigaku_censors`、`jxp_reform_confucian_rites_and_tenka_code`
- 王政复古：`jxp_reform_imperial_jingi_chancery`、`jxp_reform_imperial_restoration_banners`
- 改革宗：`jxp_reform_reformed_printed_oaths`、`jxp_reform_reformed_port_consistories`
- 海峡/伊斯兰：`jxp_reform_kaikyo_monsoon_sultanate`、`jxp_reform_kaikyo_qadi_shipyards`
- 一向一揆：`jxp_reform_ikko_sovereign_somon`、`jxp_reform_ikko_monto_war_leagues`
- 倭寇海邦：`jxp_reform_wokou_black_current_domain`、`jxp_reform_wokou_free_captains`

## 文件变更

- `events/jxp_realm_events.txt`
- `common/scripted_effects/jxp_scripted_effects.txt`
- `missions/jxp_11_branching_missions.txt`
- `common/governments/00_governments.txt`
- `common/government_reforms/jxp_27_route_reforms_doctrines.txt`
- `localisation_source/jxp_27_route_reforms_doctrines_l_english_utf8_source.yml`
- `localisation/jxp_27_route_reforms_doctrines_l_english.yml`
- `descriptor.mod`
- `../japan_expanded_v2.mod`

## Skill 更新

- `check_mission_series_overlap.py` 现在识别 `always = no`，不会把禁用任务组计入重叠。
- `modding-reference.md` 新增路线净化经验：
  - route tag 优先于旧 route flag。
  - route flag 清理要同步清 route modifier。
  - 路线改革授予时就应强制正确政府类型。
  - 儒教调和神道的任务分支不能只用 `religion = shinto` gate。

## 校验结果

- `validate_eu4_mod.ps1`：OK
- `check_mission_series_overlap.py`：OK
- `check_jxp_japan_coverage.py`：OK
  - Daimyo coverage 全部 OK。
  - Route reform coverage：每条路线 `hidden_auto=3`、`visible_registered=11`、`unregistered=0`。
- `quick_validate.py eu4-modding`：OK
- 新 active localisation：UTF-8 BOM 存在，raw CJK count = 0。
- 任务 slot 检查：无 `slot > 5`。
- 原版 EU4 目录 `jxp_*` 残留检查：无输出。

## 后续建议

- 进游戏用旧 CJP 存档测试一个月 tick：确认不再弹出“独裁者的崛起”，且政府回到君主制。
- 在 CJP 已调和神道后打开任务界面：应同时看到朱子礼制任务和神道风味任务列，但不应再显示开国/太平洋路线任务。
- 在九条路线分别查看政府改革末层：应只显示本路线对应的两项终纲改革。
