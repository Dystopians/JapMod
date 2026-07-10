# JXP 0.9.7 阶段报告：开府遗策决议链全覆盖

## 本阶段目标

- 修复 `jxp_decision_convene_founder_legacy_council` 只覆盖 14 个创始大名来源的问题。
- 让所有 37 个被 `jxp_is_major_daimyo_tag_trigger` 承认的大名，在统一日本后都能通过“追定开府遗策”获得专属事件选择和 20 年遗策修正。
- 将此类具体决议链纳入自动覆盖校验，避免被宽泛的 legacy/event/reform 覆盖误判。

## 新增与修改

- `jxp_26_founder_legacy_triggers.txt`
  - `jxp_has_founder_legacy_council_origin_trigger` 从 14 个 origin 扩展到 37 个 origin。
- `jxp_26_founder_legacy_councils.txt`
  - 决议分派从 `jxp_founder_legacy.1` 到 `.14` 扩展到 `.37`。
  - 使用 `if` + `else_if` 顺序链，防止旧存档多 origin flag 时一次点击排入多个事件。
- `events/jxp_26_founder_legacy_councils.txt`
  - 新增 `jxp_founder_legacy.15` 至 `.37`。
  - 每个事件均为两个选项，分别偏向天下秩序、天皇裁可或海门外学中的一种制度取向。
- `common/event_modifiers/jxp_26_founder_legacy_council_modifiers.txt`
  - 新增 46 个 20 年临时国家修正。
- `localisation_source/jxp_26_founder_legacy_councils_l_english_utf8_source.yml`
  - 新增事件、选项、修正名称和说明。
- `localisation/jxp_26_founder_legacy_councils_l_english.yml`
  - 已重新生成 EU4SpecialEscape 兼容 active localisation。
- `common/scripted_effects/jxp_debug_effects.txt`
  - 新增 23 个 seen flag 清理。
  - 新增 46 个 jxp_26 临时修正清理。
- 版本号升至 `0.9.7`。

## 覆盖的大名来源

- 既有 14 家：ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG/SOO。
- 新增 23 家：AMA/ASA/HSK/HTK/IKE/MAE/SBA/YMN/RFR/KTB/AKM/AKT/CBA/ISK/ITO/KKC/KNO/OGS/SHN/STK/TKI/UTN/TTI。

## Skill 与校验更新

- `check_jxp_japan_coverage.py` 新增 `Founder legacy council coverage`：
  - 检查每个大名来源是否在 scripted trigger 中；
  - 检查决议 dispatch 是否指向对应事件；
  - 检查事件是否有统一日本、origin flag、shared taken flag guard；
  - 检查每个事件是否有两个选项；
  - 检查每个事件添加的两个修正是否定义、本地化、debug 清理；
  - 检查 per-origin seen flag 是否 debug 清理。
- `modding-reference.md` 记录经验：
  - 宽泛的 unified legacy 事件、家门永久修正、政府改革不能替代具体 player-facing 决议链校验。

## 已验证

- `validate_eu4_mod.ps1`：通过。
- `check_mission_series_overlap.py`：通过。
- `check_jxp_japan_coverage.py`：通过。
  - Daimyo coverage：37/37 OK。
  - Route reform coverage：9/9 路线 OK。
  - Founder house reform coverage：37/37 OK。
  - Founder legacy council coverage：37/37 OK。
- `quick_validate.py`：skill 通过。
- `jxp_26` active localisation：BOM=True，RawCJK=0。
- EU4 原版目录残留检查：RootResidualCount=0。

## 接续重点

- 下一阶段可继续增强“家门 x 宗教/路线”的交叉事件：
  - 大友 + 吉利支丹/开国；
  - 北畠 + 朱子礼制/王政；
  - 宗氏 + 海峡/倭寇；
  - 岛津 + 海门外学/琉球；
  - 毛利/河野 + 濑户内海权。
- 可为部分大名添加“统一日本后的二段任务奖励”，但必须保持 mission slot <= 5 且不与现有路线 profile 重叠。
- 若继续微调理念，应按 tag 对照史实材料，同时保留完整 idea group 覆盖，避免局部覆盖造成原版理念残缺。
