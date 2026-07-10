# 日轮诸道 0.7.0 阶段报告：大名个性化

## 本阶段目标

- 从 0.6.0 的路线政府改革，推进到 0.7.0 的“大名差异化”。
- 重点补强：
  - 各主要大名的特殊事件。
  - 各主要大名的特殊决议。
  - 特定家族统一/成立日本后的遗产事件与永久加成。
  - 大名国家理念微调，使理念更贴合各 tag。
- 保持追加式结构，不改 EU4 原版目录，不使用 `replace_path`。

## 已完成内容

### 大名出身记录

- 新增/扩展主要大名判定与出身 flag：
  - `ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG/SOO`
- 相关文件：
  - `common/scripted_triggers/jxp_04_daimyo_triggers.txt`
  - `common/scripted_effects/jxp_04_daimyo_effects.txt`
  - `common/scripted_effects/jxp_scripted_effects.txt`
- 出身记录会在：
  - 日本机制初始化时记录。
  - 大名机制确保时记录。
  - 路线转 tag 前记录。
  - 统一遗产隐藏事件中补记录。

### 大名特殊事件

- 新增 `events/jxp_07_major_daimyo_events.txt`。
- 新 namespace：`jxp_major_daimyo`。
- 覆盖 13 个主要大名：
  - `ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG`
- 每个事件有独立 seen flag，避免无限刷。
- 事件以低频 MTTH 触发，配合大名阶段、港口、稳定度、年份等条件。
- 本地化：
  - `localisation_source/jxp_07_major_daimyo_l_english_utf8_source.yml`
  - `localisation/jxp_07_major_daimyo_l_english.yml`

### 大名特殊决议

- 新增 `decisions/jxp_15_daimyo_flavor_decisions.txt`。
- 新增 `common/event_modifiers/jxp_15_daimyo_flavor_modifiers.txt`。
- 覆盖 13 个主要大名：
  - `ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG`
- 每个决议包含：
  - `potential`
  - `allow`
  - `effect`
  - `ai_will_do`
  - 一次性 `jxp_15_*_taken` flag
  - 20 年家风修正
- 本地化：
  - `localisation_source/jxp_15_l_english_utf8_source.yml`
  - `localisation/jxp_15_l_english.yml`

### 大名理念微调

- 新增 `common/ideas/jxp_15_daimyo_ideas.txt`。
- 覆盖并微调 14 个同名理念组：
  - `ODA_ideas`
  - `TKG_ideas`
  - `TKD_ideas`
  - `UES_ideas`
  - `HJO_ideas`
  - `MRI_ideas`
  - `SMZ_ideas`
  - `OTM_ideas`
  - `DTE_ideas`
  - `ASK_ideas`
  - `CSK_ideas`
  - `OUC_ideas`
  - `IMG_ideas`
  - `SOO_ideas`
- 每组改用 `jxp_<tag>_*` idea key，并补齐名称与描述。
- 本地化：
  - `localisation_source/jxp_15_daimyo_ideas_l_english_utf8_source.yml`
  - `localisation/jxp_15_daimyo_ideas_l_english.yml`

### 统一日本后的家族遗产

- 新增/整合 `events/jxp_daimyo_legacy_events.txt`。
- 新增/扩展 `common/event_modifiers/jxp_07_daimyo_legacy_modifiers.txt`。
- 统一/路线国家包括：
  - `JAP/KJP/CJP/EJP/RFJ/SJP/IJP/WAK`
- 覆盖 14 个出身：
  - `ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG/SOO`
- 机制：
  - 大名阶段记录 origin flag。
  - 成为统一日本或路线国家后触发一次隐藏 catch-up。
  - 派发对应明面事件。
  - 授予一个永久但中等强度的家族遗产修正。
  - 设置 `jxp_daimyo_legacy_granted` 防止重复。
- Debug 清理已覆盖：
  - origin flags
  - legacy seen flags
  - legacy modifiers
- 本地化：
  - `localisation_source/jxp_07_daimyo_legacy_l_english_utf8_source.yml`
  - `localisation/jxp_07_daimyo_legacy_l_english.yml`

### 版本与清理

- `descriptor.mod` 与外层 `japan_expanded_v2.mod` 已更新为 `version="0.7.0"`。
- 曾出现临时重复的 `jxp_16_daimyo_legacy_*` 实现，已删除并整合进主线 `jxp_daimyo_legacy`。
- 已确认 EU4 原版目录未残留 `jxp_*` 新文件。

## 与全局目标对应

- 已推进：
  - “各个大名国家特殊事件”。
  - “各个大名国家特殊决议”。
  - “特定家族或大名统一日本的特殊事件和加成”。
  - “微调各大名理念，使其更符合 tag”。
  - “增加多样性特殊性”。
- 仍待继续：
  - 小大名与冷门大名尚未全覆盖。
  - 大名事件目前主要是低频 MTTH 风味事件，尚未深度接入任务树分支。
  - 统一遗产是一次性永久修正，尚未做后续事件链。
  - 尚未进行进游戏开档实测或观察局。

## 测试与检查

- 已运行：
  - `validate_eu4_mod.ps1`
  - `check_mission_series_overlap.py`
  - 原版目录残留 `jxp_*` 文件检查
- 需进游戏测试：
  - 用 `ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG/SOO` 开局抽查。
  - 大名阶段确认专属决议显示、扣费、加修正。
  - 等待或控制台触发 `jxp_major_daimyo.*` 事件，确认文本与选项正常。
  - 成立 `JAP` 或路线国家后，确认只触发一条对应 `jxp_daimyo_legacy.*` 遗产事件。
  - 读档确认 legacy flag 和 modifier 不重复、不丢失。
