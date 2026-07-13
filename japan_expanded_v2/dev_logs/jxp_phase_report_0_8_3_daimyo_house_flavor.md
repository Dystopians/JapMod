# 日轮诸道 0.8.3 阶段报告：剩余大名家名风味与遗产补强

## 背景

0.8.2 已为剩余日本大名补齐完整理念组。随后只读审计确认：这些大名已有通用大名任务、分组事件、分组决议和分组统一遗产，但缺少更鲜明的一家一策事件与统一后补充遗产；同时主要大名组中的 `SOO` 仍缺大名阶段事件和决议。

## 本阶段完成

- 新增 `events/jxp_19_remaining_daimyo_flavor_events.txt`。
- 新增 `decisions/jxp_19_remaining_daimyo_flavor_decisions.txt`。
- 新增 `common/event_modifiers/jxp_19_remaining_daimyo_modifiers.txt`。
- 新增并生成本地化：
  - `localisation_source/jxp_19_remaining_daimyo_flavor_l_english_utf8_source.yml`
  - `localisation/jxp_19_remaining_daimyo_flavor_l_english.yml`
- 为 `SOO` 补充：
  - 大名阶段风味事件 `jxp_major_daimyo.14`
  - 决议 `jxp_decision_soo_tsushima_brokers`
  - 修正 `jxp_15_soo_tsushima_brokers`
- 扩展 `jxp_debug_clear_event_state_effect`，清理新加的 `jxp_19` 决议 flag、事件 seen flag、legacy flag 和 modifier。
- 将版本提升为 `0.8.3`。

## 十一家大名新增内容

- `ASA`：一乘谷评议、谷中书札、朝仓一乘谷之治。
- `HTK`：若江被官誓约、两畠山之议、畠山管领武名。
- `IKE`：姬路城账目、白壁之城、池田姬路制置。
- `MAE`：金泽文艺、金泽茶声、前田百万石风仪。
- `SBA`：武卫旧职、武卫之名、斯波武卫遗制。
- `YMN`：六分一旧簿、六分一旧梦、山名西军旧望。
- `AKM`：播州城链、播州关砦、赤松播磨城网。
- `KKC`：阿苏火祭、阿苏火色、菊池火国调停。
- `STK`：鹿岛点兵、鹿岛誓刀、佐竹常陆军役。
- `TKI`：美浓三川普请、三川水声、土岐美浓水政。
- `UTN`：日光关使、日光与白河、宇都宫日光关防。

## 设计原则

- 新事件仍是低频 MTTH 大名阶段风味事件，每个事件提供两项选择，分别偏向天下秩序、天皇裁可或海门外学。
- 新统一遗产使用独立 `jxp_19_house_legacy_granted`，不争抢既有 `jxp_daimyo_legacy_granted`，因此可以与旧分组遗产并存。
- 加成保持“小而有味”：多为 5% 级经济、外交、军政修正，避免压过路线政府改革和任务终局奖励。

## 测试建议

- 用 `ASA/HTK/IKE/MAE/SBA/YMN/AKM/KKC/STK/TKI/UTN/SOO` 分别开局，等待或控制台触发对应事件：
  - `event jxp_remaining_daimyo.1` 到 `.11`
  - `event jxp_major_daimyo.14`
- 验证对应决议只出现一次并正常扣除点数/金钱。
- 统一日本或切换路线国家后，确认既有 `jxp_daimyo_legacy.*` 仍触发，同时 `jxp_remaining_daimyo.101` 到 `.111` 只触发一次。
- 使用 debug 清理后，确认新决议可以重新测试且新永久 modifier 被移除。
