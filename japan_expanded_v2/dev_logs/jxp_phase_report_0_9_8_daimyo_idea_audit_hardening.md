# 日轮诸道阶段报告：0.9.8 大名理念完整性审计与校验固化

日期：2026-07-09

## 本阶段定位

本阶段是维护与质量门槛版本，不新增新的游戏内机制。目标是把 0.9.2 已完成的大名理念重写成果转化为可重复验证的自动检查，防止后续分支开发时出现理念组残缺、描述漏 key、trigger 对错 tag 等隐蔽问题。

## 已完成内容

- 审计 37 个大名国家理念组：`ODA/TKG/TKD/UES/HJO/MRI/SMZ/OTM/DTE/ASK/CSK/OUC/IMG/SOO/AMA/ASA/HSK/HTK/IKE/MAE/SBA/YMN/RFR/KTB/AKM/AKT/CBA/ISK/ITO/KKC/KNO/OGS/SHN/STK/TKI/UTN/TTI`。
- 确认每个大名理念组均具备完整 `start`、`bonus`、`trigger = { tag = <TAG> }`、`free = yes` 与 7 条顶层理念。
- 确认每个理念组、传统、野心、七条理念及其描述均有 `localisation_source` key。
- 将上述规则加入 `eu4-modding` skill 的 `check_jxp_japan_coverage.py`，新增 `Daimyo national idea completeness` 报告段。
- 更新 `eu4-modding` 参考文档，记录大名理念覆盖不能只检查 `<TAG>_ideas` 是否存在，必须做括号深度感知的完整结构校验。

## 当前全局任务对应进度

- 大名国家特殊事件、特殊决议、家族建国遗产与统一日本加成：已由 0.9.1 至 0.9.7 覆盖，并通过专用校验。
- 大名理念微调与说明：0.9.2 已完成，本阶段确认 37 个 tag 的结构和本地化完整。
- 各日本建国分支政府改革：0.9.0、0.9.5、0.9.6 已完成路线改革、路线国家状态改革与开府家法改革层。
- 后续重点建议：继续把每个 founder-house 改革与路线改革组合做游戏内 tooltip 体验测试，并补充少量路线与创立家族交叉事件。

## 校验结果

通过：

- `check_jxp_japan_coverage.py`
  - `Daimyo coverage`：37/37 全 OK。
  - `Daimyo national idea completeness`：37/37 全 OK。
  - `Route reform coverage`：9 条路线均为 `3 hidden_auto + 11 visible_registered + 0 unregistered`。
  - `Founder house reform coverage`：37/37 全 OK。
  - `Founder legacy council coverage`：37/37 全 OK。

## 注意事项

- `localisation_source` 中的理念源文件为正常 UTF-8 中文文本；PowerShell `Get-Content` 在部分环境下可能以系统默认编码显示成乱码，应优先用 Python/UTF-8 读回或使用 `rg` 检查。
- 本阶段只写入本地 mod 与 skill 文件，未修改 EU4 原版目录。
