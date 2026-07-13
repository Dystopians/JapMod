# JXP 0.12.0 阶段报告：建国分支别格政府改革

## 本阶段主题

- 以政府改革为版本侧重点，为九条日本建国分支各新增三项高阶可选改革。
- 新增改革层：`jxp_route_institution_special_bureaus`，显示为“日轮国制别格政务”。
- 改革层注册在 `monarchy` 政府类型中，位于路线“枢机”改革之后、创始家“开府家法”之前。

## 新增内容

- 新增文件：`common/government_reforms/jxp_37_route_special_reforms.txt`。
- 新增本地化源与活动本地化：
  - `localisation_source/jxp_37_route_special_reforms_l_english_utf8_source.yml`
  - `localisation/jxp_37_route_special_reforms_l_english.yml`
- 修改 `common/governments/00_governments.txt`，注册 27 个新改革。
- 修改 `common/scripted_effects/jxp_scripted_effects.txt`，把 27 个新改革加入 `jxp_clear_route_reforms_effect`。
- 版本号更新为 `0.12.0`。

## 路线设计

- 守护神国：国法律令所、隐砦铁炮网、择译兰学窗。
- 开国通商：港町商座评议、远洋船手奉行、译官参议局。
- 基督之日轮：王权洗礼籍、信友武库、太平洋布教护持。
- 朱子礼制国家：诸国礼学贡试、国学朱子会通、天下按察台。
- 王政复古：大政会议、亲兵讲武寮、神祇使节制。
- 改革宗日轮：刻印长老规约、荷兰操典契约、海港长老理事会。
- 海峡日轮：港市沙里亚约章、季风船队迪万、铸炮经院。
- 一向净土国：大惣中国约、门徒军役钟、寺子学舍惣。
- 倭寇联盟：朱印私掠法、黑潮提督府、岛港关市盟。

## 设计约束

- 新改革是玩家可选政府改革，不加入 `jxp_grant_route_reforms_effect`。
- 路线切换时统一清理，避免旧路线的高阶改革残留。
- 强度略高于普通原版改革，但避免行政效率、无限纪律等高风险堆叠。
- 文案不写直接机制数值，保持历史制度语气。

## 校验结果

- `check_jxp_japan_coverage.py` 已升级并通过：
  - 每条路线 `hidden_auto = 3`
  - 每条路线 `visible_registered = 16`
  - 每条路线 `unregistered = 0`
  - 新改革层本地化与政府注册均纳入检查。

## 后续测试重点

1. 使用 debug 决议分别强制进入九条路线。
2. 打开政府改革界面，确认“日轮国制别格政务”中只显示当前路线对应的三项改革。
3. 选择其中一项后切换路线，确认旧改革被清理且新路线三选一正常显示。
4. 重点观察改革层是否过多导致 UI 需要滚动；如有显示拥挤，可后续把低阶自动改革改回隐藏载体或重排层级。
