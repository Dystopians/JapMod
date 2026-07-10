# 日轮诸道阶段报告：0.11.1 全大名路线家门组合事件
日期：2026-07-09

## 本阶段定位

0.11.1 将 0.10/0.11 阶段已经建立的“建国路线 + 创立家门”互动层从代表性大名扩展到全部预期大名 origin。此前具体路线组合事件已经覆盖主要 14 家；本阶段补齐剩余 22 家，使每一个可记录 origin 的大名在统一日本并选择路线后，都至少拥有一条低频、双选项、带十年修正的专属路线家门事件。

## 新增覆盖

新增 22 个具体组合事件：

- AMA × 锁国：月山矿山与山阴山路。
- HSK × 王政复古：管领旧仪与堺商人。
- HTK × 改革宗：河内盟约与新教誓约。
- IKE × 开国：播磨城账与濑户海门。
- MAE × 朱子礼制：加贺学馆与百万石仓廪。
- SBA × 王政复古：武卫名分与尾张亲兵。
- YMN × 王政复古：六分一旧秩与山阴守备。
- RFR × 锁国：陆奥边门与九户骑马。
- KTB × 王政复古：伊势神宫礼仪与北畠朝法。
- AKM × 锁国：播磨关防与赤松家法。
- AKT × 开国：虾夷地商路与北方番所。
- CBA × 锁国：香取军仪与下总关所。
- ISK × 开国：丹后水军与天桥立水先。
- ITO × 吉利支丹：日向修院与氏族礼拜堂。
- KKC × 朱子礼制：阿苏礼学与菊池山城。
- KNO × 倭寇：濑户内掠船与伊予海誓。
- OGS × 王政复古：诹访弓马与信浓马政。
- SHN × 海峡/伊斯兰：大宰府商使与九州门户。
- STK × 王政复古：常陆军役与东国武士名簿。
- TKI × 朱子礼制：美浓川政与土岐法书。
- UTN × 锁国：日光屏障与下野社家。
- TTI × 一向：大和门徒与奈良寺社调停。

每个事件均具备：

- `jxp_is_unified_japan_state_trigger = yes`
- 对应 `jxp_origin_<tag>` 起源旗标
- 对应路线 flag 或路线 tag 条件
- 一次性 `*_combo_seen` 旗标
- `mean_time_to_happen` 低频触发，统一落在 300/310/320 月设计带
- 2 个玩家选项
- 1 个路线压力效果与 1 个家门调和效果
- 2 个十年国家修正

## 文件变更

- 修改 `events/jxp_31_specific_route_house_events.txt`
  - 新增 `jxp_specific_route_house.16` 至 `.37`。
  - 将所有新增具体组合事件的 MTTH 档位收束到覆盖检查器认可的 300/310/320 月。
- 修改 `common/event_modifiers/jxp_31_specific_route_house_modifiers.txt`
  - 新增 44 个十年国家修正。
- 修改 `common/scripted_effects/jxp_31_specific_route_house_effects.txt`
  - debug 清理现在会清除新增 22 个 seen flag，并移除新增 44 个国家修正。
- 新增 `localisation_source/jxp_33_specific_route_house_completion_l_english_utf8_source.yml`
  - 保存新增事件、选项和修正的可读中文文案源。
- 新增 `localisation/jxp_33_specific_route_house_completion_l_english.yml`
  - 已生成 EU4SpecialEscape active localisation，供中文双字节补丁环境读取。
- 修改 `descriptor.mod` 与外层 `japan_expanded_v2.mod`
  - 版本号更新为 `0.11.1`。

## Skill 与校验增强

- `check_jxp_japan_coverage.py`
  - `specific_route_house_combo_report` 现在覆盖 37 个 origin。
  - 新增 `all_origin_combo_coverage 37/37` 汇总行。
  - 对缺失的预期 origin 直接报错，而不再只依赖 major daimyo 子集。
- `modding-reference.md`
  - 新增经验：当代表性组合系统扩展为全 origin 覆盖时，检查器必须从 canonical tag source 断言完整覆盖；事件 MTTH 设计带也必须与工具保持一致。

## 当前全局任务对应进度

- “各个大名国家特殊事件、特殊决议、特定家族或者大名统一日本的特殊事件和加成”
  - 已覆盖全部 37 个预期大名 origin。
  - 每个 origin 已有：理念覆盖、开局/大名期内容、创立家门改革、统一后家门遗产议事决议、具体路线家门事件、debug cleanup。
- “增加多样性特殊性”
  - 路线 + 家门组合不再只靠泛用 archetype，而是给每个大名至少一条具名家门路线互动。
- “完善其他内容并修 bug”
  - 覆盖检查器从主要大名覆盖升级为全大名覆盖。
  - 修复新增事件 MTTH 档位与覆盖工具不一致的问题。

## 校验结果

已通过：

- `validate_eu4_mod.ps1`
  - No issues found。
- `check_mission_series_overlap.py`
  - no route-profile mission slot overlaps found。
- `check_jxp_japan_coverage.py`
  - `major_origin_combo_coverage 14/14`
  - `all_origin_combo_coverage 37/37`
  - specific route-house combo 全项 OK。
- `quick_validate.py` for `eu4-modding` skill
  - Skill is valid。
- 编码检查
  - `jxp_33_specific_route_house_completion_l_english.yml`: UTF-8 BOM true, raw CJK 0, escape triplets 2672。
  - `descriptor.mod` 与外层 `.mod`: UTF-8 BOM true, version `0.11.1`。
- 原版 EU4 根目录残留检查
  - 无 `jxp_*` 残留文件。

## 剩余风险

- 尚未进行游戏内多年观察局。静态检查已确认事件、修正、本地化、debug cleanup 与覆盖链路完整，但仍建议用已统一日本的不同 origin 存档快速观察 20-50 年，确认低频事件节奏不过密。
- 本阶段只保证每个 origin 至少一个具体路线组合事件。下一阶段若继续推进 0.12/0.7，可扩展为“每个主要 origin 多路线事件”或把特定大名路线解锁挂到任务树、特殊政府改革与灾难分支上。
