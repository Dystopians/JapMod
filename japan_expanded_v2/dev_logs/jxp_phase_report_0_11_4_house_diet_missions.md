# JXP 0.11.4 阶段报告：家法评定入制任务

## 本阶段完成

- 新增统一日本后的家法评定任务列：`missions/jxp_36_house_diet_legacy_missions.txt`。
- 任务组使用稳定的统一日本 tag/路线 tag 作为 `potential`，避免因为事件刚设置的旗标尚未刷新任务树而导致任务不可见。
- 新增三项任务：
  - `jxp_mission_house_diet_into_realm`：要求已完成“编入天下法度”的家法整合。
  - `jxp_mission_house_law_local_offices`：读取十种家法遗产修正，承接不同大名家法选择。
  - `jxp_mission_house_law_state_doctrine`：要求稳定国家与较高时代属性，将家法升格为国家制度。
- 新增任务奖励修正：
  - `jxp_36_integrated_house_diet_records`
  - `jxp_36_house_law_local_offices`
  - `jxp_36_house_law_state_doctrine`
- 新增完整中文本地化源文件与已转义活动本地化：
  - `localisation_source/jxp_36_house_diet_missions_l_english_utf8_source.yml`
  - `localisation/jxp_36_house_diet_missions_l_english.yml`
- 更新 debug 清理效果，移除新任务链带来的三个修正。
- 更新 `check_jxp_japan_coverage.py`，加入家法任务链覆盖检查。
- 更新 `eu4-modding` skill 参考经验：任务若消费近期事件/决议设置的旗标，应保持任务组 `potential` 稳定，并把新旗标放进首个任务的 `trigger`。

## 校验结果

- `validate_eu4_mod.ps1`：通过。
- `check_mission_series_overlap.py`：通过，无路线任务槽位重叠。
- `check_jxp_japan_coverage.py`：通过，新增 `House diet mission coverage` 全部 OK。
- `quick_validate.py`：skill 校验通过。
- 活动本地化 `jxp_36_house_diet_missions_l_english.yml`：UTF-8 BOM 存在，无裸 CJK，使用 EU4SpecialEscape 转义。
- 根目录残留检查：未在 EU4 原版目录发现误写的 `jxp_*` 文件。

## 测试路线建议

1. 以任意大名开局。
2. 召开家法评定，选择一家法路线。
3. 完成统一并进入任意日本建国分支。
4. 使用“编入天下法度”决议。
5. 在任务界面确认家法任务链出现并可依次完成。

## 剩余风险

- 尚未完成游戏内 UI 实测；重点观察任务列是否在可见槽位中显示，以及 `required_missions` 连线是否自然。
