# JXP 0.9.6 阶段报告：开府家法政府改革层

## 本阶段目标

- 修复“路线/任务看似存在，但统一日本后的创始来源制度层不足”的结构性缺口。
- 将“由哪一家大名建立日本”的长期国家记忆，独立于锁国、开国、吉利支丹、朱子礼制、王政复古、改革宗、海峡伊斯兰、一向一揆、倭寇等路线之外。
- 把此层明确显示在政府改革列表中，作为新版本政府改革侧重点的一部分。

## 新增内容

- 新增政府改革层：`jxp_founder_house_constitution`（开府家法）。
- 新增 37 个大名来源专属政府改革，覆盖：
  - ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG/SOO
  - AMA/ASA/HSK/HTK/IKE/MAE/SBA/YMN/RFR/KTB/AKM/AKT
  - CBA/ISK/ITO/KKC/KNO/OGS/SHN/STK/TKI/UTN/TTI
- 新增 1 个无来源 fallback 改革：`jxp_reform_founder_generic_renovated_japan`，用于原始 JAP 或迁移存档未记录大名来源的情况。
- 新增脚本清理效果：`jxp_clear_founder_house_reforms_effect`。
- Debug 事件状态清理已调用该效果，避免清除 origin flags 后政府界面残留旧家法改革。
- 版本号升至 `0.9.6`。

## 设计原则

- 路线改革回答“日本成为何种国家”；开府家法回答“哪一家门奠基了这个日本”。
- 开府家法改革不在普通路线切换时清除，因此大友开国、织田王政、北畠朱子礼制等组合都能保留创始家门味道。
- 每个家门改革只通过对应 `jxp_origin_<tag>` 出现，并要求 `jxp_is_unified_japan_state_trigger = yes`，防止大名阶段提前露出。
- 改革强度略高于普通原版改革，但控制在两项中等加成内，避免与路线改革形成失控叠加。

## 修改文件

- `common/governments/00_governments.txt`
- `common/government_reforms/jxp_28_founder_house_reforms.txt`
- `common/scripted_effects/jxp_28_founder_house_reforms_effects.txt`
- `common/scripted_effects/jxp_debug_effects.txt`
- `localisation_source/jxp_28_founder_house_reforms_l_english_utf8_source.yml`
- `localisation/jxp_28_founder_house_reforms_l_english.yml`
- `descriptor.mod`
- `../japan_expanded_v2.mod`

## Skill 与校验更新

- `eu4-modding` 参考文档新增“founder-house reforms”模式：
  - 创始家门改革应与路线改革正交；
  - 按 origin flag 窄门控；
  - 普通路线切换不清除；
  - debug 清 origin 时必须清改革。
- `check_jxp_japan_coverage.py` 新增 Founder house reform coverage：
  - 检查每个预期大名 tag 是否有唯一改革；
  - 检查是否注册进 `common/governments`；
  - 检查 potential 是否包含统一日本和 origin flag；
  - 检查本地化；
  - 检查 debug 清理。

## 已验证

- `validate_eu4_mod.ps1`：通过。
- `check_mission_series_overlap.py`：通过。
- `check_jxp_japan_coverage.py`：通过，37/37 大名来源开府家法改革 OK。
- `quick_validate.py`：skill 通过。
- 新 active localisation：BOM=True，RawCJK=0。
- EU4 原版目录残留检查：RootResidualCount=0。

## 接续重点

- 继续向后续版本推进时，可在开府家法改革基础上增加：
  - 家门专属任务后续奖励；
  - 家门专属事件低频 MTTH；
  - 家门与宗教路线的交叉事件，例如“大友吉利支丹日本”“北畠朱子礼制日本”“宗氏海峡伊斯兰日本”等。
- 若未来增加新大名 tag，必须同步更新：
  - `jxp_is_major_daimyo_tag_trigger`
  - origin 记录效果
  - 理念与本地化
  - 大名阶段事件/决议
  - 统一后 legacy
  - 开府家法政府改革
  - debug 清理
  - coverage checker
