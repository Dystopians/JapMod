# JXP 0.12.1 阶段报告：开府家法改革脉冲事件

## 本阶段主题

- 继续推进大名与创始家差异化，让“开府家法”政府改革不再只是静态国家修正。
- 新增五个统一日本后的低频制度事件，按创始家风格触发：
  - 武家型
  - 朝廷型
  - 海商型
  - 边地型
  - 寺社町市型

## 新增内容

- 新增触发器：`common/scripted_triggers/jxp_38_founder_reform_pulse_triggers.txt`
  - 按五类家风检查已选择的 `jxp_reform_founder_*` 政府改革。
- 新增事件：`events/jxp_38_founder_reform_pulse_events.txt`
  - `jxp_founder_reform_pulse.1` 至 `.5`。
  - 每个事件有两个选项，分别偏向中央制度化或保留/转用创始家旧例。
- 新增修正：`common/event_modifiers/jxp_38_founder_reform_pulse_modifiers.txt`
  - 共 10 个 15 年修正。
- 新增清理 effect：`common/scripted_effects/jxp_38_founder_reform_pulse_effects.txt`
  - 被 `jxp_debug_clear_event_state_effect` 调用。
- 新增本地化：
  - `localisation_source/jxp_38_founder_reform_pulse_l_english_utf8_source.yml`
  - `localisation/jxp_38_founder_reform_pulse_l_english.yml`
- 版本号更新为 `0.12.1`。

## 设计要点

- 事件不只检查 `jxp_origin_*` 旗标，而是检查玩家是否已在政府改革中选择对应的创始家改革。
- 五类事件覆盖全部 37 个大名来源，但不为每个大名复制一个模板事件，避免事件池膨胀。
- 选项会轻微牵动三项时代属性，并给予中期修正。
- 文案保持历史制度语气，不直接写机制数值。

## 覆盖工具更新

- `check_jxp_japan_coverage.py` 新增 `Founder reform pulse coverage`。
- 覆盖脚本会：
  - 从创始家改革定义中反查每个 `jxp_origin_*` 的改革 key；
  - 从家风触发器中读取五类大名来源；
  - 确认新触发器覆盖对应改革；
  - 检查事件、MTTH、双选项、修正、本地化与 debug 清理。

## 校验结果

- `validate_eu4_mod.ps1`：通过。
- `check_mission_series_overlap.py`：通过。
- `check_jxp_japan_coverage.py`：通过，新增 `Founder reform pulse coverage` 全部 OK。
- `quick_validate.py`：skill 校验通过。
- 活动本地化 `jxp_38_founder_reform_pulse_l_english.yml`：UTF-8 BOM 存在，无裸 CJK，使用 EU4SpecialEscape 转义。
- 原版 EU4 目录残留检查：未发现误写的 `jxp_*` 文件。

## 游戏内测试建议

1. 以任意大名统一日本。
2. 在政府改革界面选择对应“开府家法”改革。
3. 可用 debug 决议强制推进路线和时代属性，也可自然等待。
4. 观察低频事件是否只出现一次，并确认两个选项都能正常给予修正与时代属性变化。

## 剩余风险

- 尚未进行游戏内 UI 实测。
- 如果玩家没有选择“开府家法”改革，这些事件不会触发；这是有意设计。
