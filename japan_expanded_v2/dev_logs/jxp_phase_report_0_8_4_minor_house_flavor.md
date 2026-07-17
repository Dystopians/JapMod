# 日轮诸道 0.8.4 阶段报告：余下小大名一族一策补强

## 背景

0.8.3 已补齐 `ASA/HTK/IKE/MAE/SBA/YMN/AKM/KKC/STK/TKI/UTN` 与 `SOO` 的单家族事件、决议和统一遗产。继续审计后，仍有 12 个小大名主要停留在 0.7 的分组风味层面，缺少“一家一策”的专属内容。

## 本阶段完成

- 新增 `events/jxp_20_minor_house_events.txt`。
- 新增 `decisions/jxp_20_minor_house_decisions.txt`。
- 新增 `common/event_modifiers/jxp_20_minor_house_modifiers.txt`。
- 新增并生成本地化：
  - `localisation_source/jxp_20_minor_house_l_english_utf8_source.yml`
  - `localisation/jxp_20_minor_house_l_english.yml`
- 扩展 `jxp_debug_clear_event_state_effect`，清理 `jxp_20` 新增 flag 和 modifier。
- 版本提升为 `0.8.4`。

## 新增覆盖

- `AMA`：月山富田城账、月山阴影、尼子月山之制。
- `HSK`：堺町管领评议、堺町评议、细川堺町议政。
- `SHN`：大宰府通事、大宰府来书、少贰大宰府通交。
- `OGS`：诹访马奉行、诹访马声、小笠原弓马山路。
- `KTB`：伊势王统请文、伊势请文、北畠伊势王统。
- `AKT`：虾夷地互市代官、北海互市、安东北海互市。
- `CBA`：香取神前军役、香取誓刀、千叶香取武门。
- `ISK`：丹后港奉行、丹后海雾、一色丹后海道。
- `ITO`：日向四十八城、日向四十八砦、伊东日向城网。
- `KNO`：濑户内水先众、濑户内潮路、河野濑户内水军。
- `TTI`：大和寺社约、奈良寺钟、筒井大和寺社法。
- `RFR`：陆奥九户关门、陆奥九户、南部陆奥关门。

## 设计说明

- 每家都有一个大名阶段低频事件，两项选择分别偏向家法秩序、朝廷/寺社名分或海路通交。
- 每家都有一个一次性决议，给予 20 年风味修正并推动一到两个时代属性。
- 每家统一日本或进入路线国家后，会触发一次独立补充遗产事件，授予永久小修正。
- `jxp_20_minor_house_legacy_granted` 独立于旧的 `jxp_daimyo_legacy_granted` 和 0.8.3 的 `jxp_19_house_legacy_granted`，因此不会抢占原本的分组遗产或 0.8.3 家族遗产。

## 测试建议

- 分别以 `AMA/HSK/SHN/OGS/KTB/AKT/CBA/ISK/ITO/KNO/TTI/RFR` 开局，检查专属决议可见且只可执行一次。
- 控制台测试：
  - `event jxp_minor_house.1` 到 `event jxp_minor_house.12`
  - 统一后测试 `event jxp_minor_house.101` 到 `event jxp_minor_house.112`
- 使用 debug 清理后确认这些决议、事件与 legacy 可重新测试。
