# jxp 0.15.0 阶段报告：路线枢密院政府改革

日期：2026-07-09

## 本阶段目标

- 收束上一阶段的大名专属事件奖励检查。
- 以“每一个日本建国分支的特色政府改革”为 0.15.0 重点，为所有路线增加新的可见可选政府改革层。

## 已完成

- 修复 `jxp_20_shn_hakata_wind_books` 使用的无效修正键：`naval_tradition` 改为 EU4 1.37.5 可用的 `navy_tradition`。
- 将 `jxp_19` 与 `jxp_20` 的 23 个新增事件奖励修正加入 `jxp_debug_clear_event_state_effect`。
- 强化 `check_jxp_japan_coverage.py`：
  - `early_daimyo_event_reward_report` 现在扫描 `jxp_07_major_daimyo_events.txt`、`jxp_17_minor_daimyo_events.txt`、`jxp_19_remaining_daimyo_flavor_events.txt`、`jxp_20_minor_house_events.txt`。
  - 覆盖检查会验证事件奖励修正定义、本地化、debug 清理，并拒绝旧的共享 `jxp_daimyo_*` 奖励池。
  - 路线可见改革下限从每路线 24 个提高到 27 个。
- 新增可见政府改革层 `jxp_route_institution_privy_councils`，显示为“诸道枢密院”。
- 为 9 条日本建国/路线分支各新增 3 个互斥可选改革，共 27 个：
  - 锁国线：三家枢议、海防检疫局、内典天文寮。
  - 开国线：外洋通商内阁、外式军议所、海殖交易会。
  - 吉利支丹线：宗徒枢议院、慈悲诸藩网、罗马字文书院。
  - 朱子礼制线：礼法台谏院、神儒学校盟、东亚律令局。
  - 王政复古线：太政枢密局、神祇使节网、亲兵贡赋司。
  - 改革宗线：长老枢法院、印经海图局、盟约操练局。
  - 海桥/伊斯兰线：协商枢密院、季风关税会、经院铸炮局。
  - 一向一揆线：惣村枢议所、公仓寺社司、门徒守备盟。
  - 倭寇线：黑潮枢密水师、岛关牙行法庭、海主军役契。
- 这些新改革均不加入 `jxp_grant_route_reforms_effect`，避免自动叠加；玩家需要在政府改革界面选择。
- 全部新改革已注册到 `common/governments/00_governments.txt`，并加入 `jxp_clear_route_reforms_effect` 的路线切换清理。
- 新增/生成本地化：
  - `localisation_source/jxp_46_route_privy_council_reforms_l_english_utf8_source.yml`
  - `localisation/jxp_46_route_privy_council_reforms_l_english.yml`
  - `localisation_source/jxp_47_early_daimyo_reward_desc_overrides_l_english_utf8_source.yml`
  - `localisation/jxp_47_early_daimyo_reward_desc_overrides_l_english.yml`
- 描述文案遵循“机制数值交给 tooltip，描述只写历史制度氛围”的原则。
- 描述符版本更新为 `0.15.0`。

## 校验结果

- `check_jxp_japan_coverage.py`：通过。
  - 37/37 大名覆盖通过。
  - 早期大名事件奖励覆盖通过：
    - `jxp_07_major`：14/14 事件，28/28 修正，28/28 本地化，28/28 清理。
    - `jxp_17_minor`：7/7 事件，14/14 修正，14/14 本地化，14/14 清理。
    - `jxp_19_remaining`：11/11 事件，22/22 修正，22/22 本地化，22/22 清理。
    - `jxp_20_minor_house`：12/12 事件，24/24 修正，24/24 本地化，24/24 清理。
  - 路线改革覆盖通过：9 条路线均为 `hidden_auto = 3`、`visible_registered = 27`、`unregistered = 0`。
- `validate_eu4_mod.ps1`：通过，无结构问题。
- `check_mission_series_overlap.py`：通过，无路线任务槽位重叠。
- active `jxp_4x` 本地化检查：8 个文件均有 UTF-8 BOM，且无原始 CJK 字符。

## Skill 更新

- `eu4-modding` 参考文档新增：
  - 全大名事件奖励覆盖不能只检查 grouped MTTH 事件，必须区分 dedicated single-tag namespaces。
  - 成熟路线改革层应注册、清理、本地化、提高覆盖阈值，并避免加入自动授予效果。

## 后续建议

- 进入游戏后用任一路线控制台强制路线，例如 `jxp_debug_force_confucian_route_effect` 对应的调试决议，确认“诸道枢密院”在政府改革界面显示且仅出现当前路线的 3 个选项。
- 下一阶段可以继续把这些改革与路线任务奖励或低频事件相互挂钩，例如完成关键任务后给某一改革额外事件、或让路线枢密院改革影响三大时代属性的回摆事件。
