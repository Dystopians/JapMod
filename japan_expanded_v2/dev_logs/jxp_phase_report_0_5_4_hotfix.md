# 日轮诸道 0.5.4 Hotfix 阶段报告

## 修复目标

- 修复朱子礼制日本错误触发原版共和国低传统独裁事件的问题。
- 修复 CJP 存档中残留其他路线 flag 导致任务树显示开国/太平洋任务的问题。
- 修复 CJP 任务 UI 中补充任务包抢占主线 slot，导致主线任务列不可见的问题。

## 已完成改动

- 新增 `jxp_force_monarchical_route_effect`：
  - 清除 `presidential_despot_reform`、`military_dictatorship_reform`。
  - 对路线 tag 强制回到 monarchy，避免原版 `republics.3` 误触发。
- 新增 `jxp_clear_route_modifiers_effect` 与 `jxp_sanitize_confucian_route_effect`：
  - 清空互斥 `jxp_path_*` flag。
  - 移除旧路线 modifier。
  - 只保留 `jxp_path_confucian` 与 `jxp_route_confucian`。
  - 重新同步儒教、神道融合、天皇神宫保护、政府机制与任务树。
- 新增隐藏维护事件 `jxp_realm.4`：
  - 对 CJP 或朱子路线旧存档自动修复政府、宗教、路线 flag、神道融合和任务树。
- 政府机制承载改革加入 `cannot_become_dictatorship = yes`：
  - `jxp_japanese_polity_reform`
  - `jxp_reformed_japan_reform`
  - `jxp_kaikyo_japan_reform`
  - `jxp_ikko_commonwealth_reform`
  - `jxp_wokou_admiralty_reform`
  - `jxp_oceanic_sun_reform`
- 临时禁用 `jxp_domestic_institution_missions` 默认显示：
  - 该任务包与 CJP 神道融合列同占 slot 4。
  - 后续版本应将其中合理任务逐项并入主 CJP 任务列，而不是作为独立同 slot mission series 激活。
- 清理 `descriptor.mod` 的 UTF-8 BOM；确认当前非 localisation 脚本文件无 BOM。
- 更新 `eu4-modding` skill 经验：
  - 路线切换必须清理旧 route flag 与 route modifier。
  - mission slot 是互斥资源，同路线同 slot 会造成 UI 吞列/错列。
  - 兼容共和国的政府机制改革若不想触发原版独裁链，应加 `cannot_become_dictatorship`。

## 校验结果

- `validate_eu4_mod.ps1` 通过。
- 当前未发现 descriptor、flag TGA、本地化 BOM、裸 CJK 转义等静态问题。

## 游戏内复测建议

- 载入出现问题的 CJP 存档，走日历 2-3 天，让 `jxp_realm.4` 隐藏维护事件触发。
- 打开任务界面确认 CJP 不再显示 `琉球门户`、`太平洋敕许` 等开国路线列。
- CJP 任务树应优先显示：
  - 公共国家整顿列。
  - 公共朝廷/经济列。
  - 朱子礼制主线列。
  - 神道融合特色列。
  - 朱子/王政帝国列。
- 确认不再触发原版 `独裁者的崛起` 事件。
