# Japan Expanded V2 0.28.0：太平洋、地域风味、事件写作与终局政治

- 日期：2026-07-10
- 主 Mod：`0.28.0`
- 伴随地图：`0.1.3-alpha`
- 状态：`STATIC_PASS; PENDING_RUNTIME`

## 工作边界

- 开发 checkout 位于 `C:/Users/meizhanxuan/Documents/GitHub/JapMod`，是普通目录，不是 junction 或符号链接。
- Steam 的 EU4 1.37.5.0 Inca（491d）安装目录只作为只读原版依据；本批次没有在游戏目录创建仓库、Mod 副本或开发联接。
- 未启动 EU4、启动器或 observer，因而本文只声明静态证明，不把脚本结构等同于游戏内结果。

## JXP-010：天命、八纮一宇与 DLC fallback

- `cb_jxp_hakko_ichiu` 新增明确的日本身份 gate，堵住外国继承旧解锁 flag 后获得 CB 的路径。
- 可执行合同固定：任务专属解锁、Mandate of Heaven DLC、天朝皇帝/改革、日本身份、东亚两个 superregion、`take_mandate` 战争目标与 `badboy_factor = 0.5`。
- 无 DLC 路径保留替代收益；没有覆盖原版 CB 定义。
- `vanilla_1_37_5_manifest.json` 对四个直接参照的原版文件作 SHA-256 锁定，避免未来版本漂移被静态门禁误认成已验证事实。
- 新增 `mandate.py` 与 10 项定向 tests。该任务仍为 `IN_PROGRESS`，因为 CB 列表、和约、AE、改革 UI 与 fallback 必须在引擎内验收。

## JXP-011：太平洋日本长期循环

- 新增独立的 0–100 太平洋压力系统，包含进入、周期脉冲、50/85 阈值事件、四类投资、太平洋协约和收缩退出。
- 四类投资分别覆盖马尼拉—长崎、阿拉斯加、加利福尼亚与太平洋朝廷，并按路线提供不同权重和取舍。
- 14 个玩法 modifier 全部有限期；主 Mod 不依赖伴随地图独占的 tag、area 或省份。
- California settlement 的机械签名经交叉审查改为殖民增长与生产效率，避免与既有内容完全重复。
- `overseas_loop.py` 与 12 项定向 tests 通过，`JXP-011` 完成。

## JXP-012：对马、濑户内与琉球地域风味

- 三套地域 gate 优先消费伴随地图的语义 flag，并以主 Mod 可用的历史锚点作 fallback；没有硬引用可选 area，也没有向 `1021` / `4943` 重复发奖。
- 新增三条地图 capstone、三件双选事件、三项 AI 委任决议、三项 debug 入口与七个有限期 modifier。
- 交叉审查把任务与决议统一到 canonical schedule helper：helper 先同步写入两日锁，再于次日触发事件，关闭同日双排队竞态。
- 每个结果先清理六种旧政策，五年后复议不会叠加相反结果；对马两项 modifier 的机械签名也已与旧内容去重。
- `regional_flavor.py` 与 14 项定向 tests 通过，`JXP-012` 完成。

## JXP-013：可干预低频事件

- 对 22 个可见、持续至少四年的单选慢事件新增第二选项；隐藏迁移/清理事件与短期初始化事件不计入目标集。
- 每个新选项重复原完成 flag，提供不同玩法方向并承担明确资源或政策成本，不引入新的持久状态。
- 新中文 source/active localisation 继续使用项目既有 BOM 与 EU4SpecialEscape 管线；叙事正文不直述数值。
- `writing_events.py` 验证目标覆盖、完成态、代价、区别、文案与无新增状态，9 项定向 tests 通过，`JXP-013` 完成。

## JXP-022：十种最终统一状态

- 十种状态均有唯一且互斥的权力结构：新增六项，复用并收紧 RFJ、SJP、IJP、WAK 四项既有基本改革。
- 旧四项改革的 `potential` 不再因 JAP 的 pre-final route flag 提前出现，只在对应 final-state trigger 或自身已持有时保留。
- canonical sync 只处理缺失、外国权力结构或外国 capstone；稳定状态不会清除后再重复添加。
- 新增十条真实政治 capstone 任务和十个唯一永久结果；路线/最终状态变化会清除外态 capstone。
- route clear、外部宗教/政府变化、次日任务 reconcile、debug cleanup 与 0.28.0 旧档迁移均已接线。
- `final_states.py` 对 10/10 状态、10/10 capstone 与 512 种 JAP route flag 向量作静态证明，21 项定向 tests 通过。该任务仍为 `IN_PROGRESS`，等待政府 UI、旧档和状态切换的运行时证据。

## 发布门禁

- 主验证：`26/26`；Clausewitz 解析 `250/250`。
- 单元测试：`208/208`。
- 主任务：`288` 个 ID、`41` 个 series、`192` 个 effective profiles。
- 地图任务：`33` 个 ID、`5` 个 series；联合任务 `321` 个 ID、`46` 个 series、`120` 个伴随地图 tag/DLC profiles。
- 联合内容：`498` events、`287` decisions、`383` scripted callables、`918` modifiers。
- state safety：`538` country flags、`8` province flags、`918` modifiers、`4` disasters、`0` failures。
- 地图、历史、内容、兼容与资产门禁：全部 `0 errors / 0 warnings`；137,382 个可选日期历史连续。

## 仍待运行时验收

获用户明确许可后，仍需在游戏内完成并归档：

1. 1444 冷启动、一天后任务/改革同步与 fresh `error.log`。
2. 十种统一状态旧档迁移、次日任务切换、权力结构 UI 与 capstone 跨路线清理。
3. 八纮一宇 CB 的显示、战争目标、和约、AE、DLC 与无 DLC fallback。
4. WAK、IJP、太平洋网络、灾难与低频事件的 observer 节奏、AI 行为、保存/重载稳定性。
5. 88 省地图的渲染、港口、海峡、标签、书签与日期滑块截图验收。

在获得上述证据前，`JXP-010`、`JXP-022` 及其他 runtime-centric TODO 不得标记为 `DONE`。
