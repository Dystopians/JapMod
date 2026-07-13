# 日轮诸道 0.5.3 阶段修复报告

## 修复主题

- 修复朱子礼制日本转为儒教后未稳定融合神道的问题。
- 修复儒教国教下原版神道事变链不再启动导致的风味断层。

## 关键实现

1. 加固 `jxp_confucian_sync_shinto_effect`：
   - 在儒教国教下幂等调用 `add_harmonized_religion = shinto`。
   - 设置 `jxp_confucian_shinto_syncretism`。
   - 添加 `harmonized_shinto` 作为可见/兜底修正。
   - 保留伊势神宫省份 `4359` 为神道例外。

2. 新增 `jxp_confucian_shinto_bridge_country_trigger`：
   - 允许 `has_harmonized_with = shinto`、`jxp_confucian_shinto_syncretism` 或 `harmonized_shinto` 任一状态作为桥接事件和任务识别条件。

3. 新增 `events/jxp_confucian_shinto_bridge_events.txt`：
   - `jxp_confucian_shinto.0`：隐藏同步/旧存档兜底事件。
   - `jxp_confucian_shinto.1-3`：神儒会通/宋明理学桥接链。
   - `jxp_confucian_shinto.10-12`：城市化桥接链。
   - `jxp_confucian_shinto.20-23`：南蛮贸易桥接链。

4. 新增配套修正和本地化：
   - `jxp_confucian_bridge_shrine_registers`
   - `jxp_confucian_bridge_city_registers`
   - `jxp_confucian_bridge_nanban_edicts`
   - `jxp_confucian_bridge_restricted_ports`

5. 新增调试入口：
   - `jxp_debug_fire_confucian_shinto_1`
   - `jxp_debug_fire_confucian_shinto_10`
   - `jxp_debug_fire_confucian_shinto_20`

## 经验教训

- EU4 v1.37.5 原版神道事变在 `common/incidents/00_isolationism.txt` 中以 `religion = shinto` 锁定；朱子礼制日本改宗儒教后，不能期待原版神道事变继续自然启动。
- 若路线设计要求“儒教融合神道但保留神道历史题材”，应使用 `add_harmonized_religion = shinto` 加隐藏兜底同步，并用 mod 自有事件链承接南蛮贸易、城市化、宋明理学等主题。
- 调试转换、旧存档补丁和任务奖励可能绕过主路线事件，因此融合/任务刷新/机制注册都应走统一 scripted effect。

## 校验

- 已运行 `validate_eu4_mod.ps1`，结果：`OK: No issues found in japan_expanded_v2`。
- 新增 active localisation 已确认 UTF-8 BOM 且无裸 CJK。
