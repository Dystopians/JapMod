# 日轮诸道 0.8.1 阶段报告：可见路线政府改革层

## 背景

0.8.0 已为九条日本建国路线新增 27 项路线改革，但这些改革使用 `basic_reform = yes`，本质是自动授予的隐形制度包。它们能提供修正，却不能稳定满足“显示在政府改革列表”的体验。

## 本阶段完成

- 新增 `common/governments/00_governments.txt`，来源为本机 EU4 v1.37.5 原版文件，并只在君主制 `reform_levels` 底部追加三层 mod 专属改革层。
- 追加改革层：
  - `jxp_route_institution_foundations`：日轮国制根本。
  - `jxp_route_institution_administration`：日轮国制行政。
  - `jxp_route_institution_command`：日轮国制军政。
- `common/government_reforms/jxp_18_route_reforms_extra.txt` 中 27 项 0.8 新改革已移除 `basic_reform = yes`，现在作为普通可见改革接入政府改革列表。
- 既有 `jxp_grant_route_reforms_effect` 会在路线选择、tag 转换、debug 强制路线和旧档补救事件中自动授予当前路线对应的三项可见改革。
- 既有 `jxp_clear_route_reforms_effect` 会在路线切换时清除这些可见改革，避免旧路线残留。
- `localisation_source/jxp_18_route_reforms_l_english_utf8_source.yml` 已加入三层改革层标题，并重新生成 active localisation。

## 可见路线改革分布

- 锁国：参勤交代道中、海岸番所、秘传洋书会。
- 开国：银座会计所、异国炮术契约、敕许商馆网。
- 吉利支丹：神学校与译馆、慈悲会病院、长崎护教水军。
- 朱子礼制：诸藩讲学试、王化律令、三教评议所。
- 王政复古：国学寮、国司再任制、王政亲征军。
- 改革宗：印书会院、町会信约、契约商船队。
- 海教：季风迪万、瓦合甫仓廪、香料护航众。
- 一向一揆：惣门评定、门徒义仓、讲中足轻。
- 倭寇：黑潮掟法、列岛自由港、跳帮船手众。

## 兼容性说明

- 这是一次有意识的政府结构合并：为了让改革出现在正常政府改革列表，必须把改革 key 接入 `common/governments/00_governments.txt` 的 `reform_levels`。
- 未修改 EU4 原版目录；复制后的文件只位于 mod 内。
- 后续若 EU4 版本更新到 1.38+，需要重新比较原版 `00_governments.txt` 并重做这三层插入。

## 测试建议

- 用任意日本统一路线进入国家路线后，打开政府改革界面，检查底部是否出现三层“日轮国制”改革层。
- 用 debug 强制路线分别测试 `KJP/CJP/EJP/RFJ/SJP/IJP/WAK`，确认当前路线只显示并选中对应三项改革。
- 切换路线或运行 debug 清理后，检查旧路线三项改革是否被移除。
