# JXP Shared Development Ledger

> 本文件是“日轮诸道”主 Mod 与“日本八十八国地图”伴随 Mod 的唯一共享开发总账。
> 所有 agent、subagent 和新会话在修改项目之前必须先读本文件；完成工作时必须在同一开发切片内更新本文件。
> 旧阶段报告是不可变历史证据，不再承担“当前状态”职责。

## Read This First

- Portable repository: `https://github.com/Dystopians/JapMod`；checkout 根目录记为 `<repo>`。
- Canonical ledger: `<repo>/japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md`
- Main Mod root: `<repo>/japan_expanded_v2`
- Companion Map root: `<repo>/japan_expanded_v2_map`
- Game root: host-specific EU4 v1.37.5.0 install，始终仅作只读参考。
- Skill: 优先读取 `<repo>/skills/eu4-modding/SKILL.md`；原始本机环境可回退到 `C:/Users/Fiber Memory/.codex/skills/eu4-modding/SKILL.md`。
- 先读根目录 `AGENTS.md`、本总账、与任务直接相关的阶段报告；涉及地图时再读地图 `BASELINE_LOCK.txt` 与联合兼容合同。
- 不得在没有用户明确许可时启动 EU4 或启动器。静态验证通过不得写成“游戏内已验证”。
- 并行开发时由主 agent 独占更新本总账；subagent 只提交证据与补丁摘要，避免并发覆盖。

## Current Snapshot

- Ledger schema: `1`
- Last updated: `2026-07-10`
- Main Mod version: `0.26.0`
- Companion Map version: `0.1.1-alpha`
- Pinned game: `EU4 v1.37.5.0 Inca (491d)`
- Supported version: `1.37.*`
- Runtime acceptance: `PENDING_USER_APPROVAL`
- Main static gate: `13/13 checks; 67/67 unit tests`
- Combined static gate: `0 errors; 0 warnings`
- Main missions: `272 mission IDs; 40 custom series; 188 effective profiles`
- Combined missions: `287 mission IDs; 45 series; 120 companion tag/DLC profiles`
- Combined content inventory: `466 events; 215 decisions; 252 scripted callables; 832 modifiers`
- Companion geography: `88/88 japan_region provinces; 137382 selectable days; 273 owner intervals; 56 subject intervals`
- Localisation: `0 missing combined mission localisation keys`

## Source Of Truth

发生冲突时按以下顺序裁决：

1. 游戏脚本、生成器、描述符与可执行验证器决定“代码实际是什么”。
2. 本总账决定“当前目标、开放 TODO、风险、测试状态和交接规则是什么”。
3. `japan_expanded_v2_map/tools/jxp_map_validation/main_compatibility_contract.json` 决定主 Mod 与地图 Mod 的机器可执行接口。
4. `japan_expanded_v2_map/dev_logs/BASELINE_LOCK.txt` 决定地图基线、ID、像素、历史与硬兼容边界。
5. 阶段报告记录当时已完成的工作和证据；后续报告与本总账可明确标记其结论为 superseded。
6. `jxp_master_todo_from_original_plan.md` 与 `jxp_current_progress_against_original_plan_2026_07_09.md` 从本总账建立之日起冻结为历史快照；不得继续维护第二份“当前 TODO”。

## Non-Negotiable Rules

### Filesystem And Runtime

- 原版目录只读；所有项目写入限于 Git checkout、Documents 下明确的开发 Mod 副本与 `eu4-modding` skill。
- 不使用 `replace_path`，除非未来另有明确、经过审计的总转换需求。
- 不执行破坏性清理，不覆盖来历不明的用户改动，不把生成缓存写入原版目录。
- 未经用户明确许可，不启动 EU4、启动器或观察局；日志中必须区分 `STATIC_PASS`、`RUNTIME_PASS` 与 `PENDING_RUNTIME`。

### Main And Companion Compatibility

- 本会话及后续同项目会话中的每一项主 Mod 玩法改动都必须兼容 `japan_expanded_v2_map`。
- 主 Mod 不得直接引用仅由伴随地图提供的 tag、省份 ID、area、mission ID 或其他可选对象；只能消费自由 country/global/province flag 或主 Mod 自己定义的接口。
- 地图 Mod 拥有其 30 个 tag、精确 slot-3 任务指纹、origin flags、地图 area、省份历史、语义地理 flags 与对应迁移。
- 主 Mod 拥有共享 slots `1/2/4/5`、通用刷新 helper、时代属性、终局 tag、路线系统与主内容。
- 地图拆分原版 area 后，使用语义 province flag 恢复岛原、一向宗、濑户内、倭寇等宏观范围；不得让主 Mod 硬依赖新 area 名。
- `1021` 是 Settsu/大坂/堺兼容锚点，`4943` 是堺外围；新增堺内容不得向两者重复发放同一奖励。
- 地图 Mod 必须新开战役，并与其他覆盖日本地图位图、area/region、Nippon 节点或相同历史的地图 Mod 明确不兼容。

### Mission Trees

- 严格遵守 skill 中的 RSMTS-1.37.5；语法和 DAG 正确不等于 EU4 能正确渲染。
- 所有承诺完整国策的 profile 必须恰有 slots `1..5` 五个自定义非通用 owner，无 generic fallback、cell collision、inactive prerequisite 或 series overlap。
- 独立五列树默认使用 slot `1/3/5` 奇数行、slot `2/4` 偶数行；同列可见边默认前进两行，斜线只能移动一个相邻 slot 与一行。紧凑日本例外必须由固定原版案例和 effective topology 共同证明。
- mission block 在每个 series 中必须按 `position` 严格递增声明；远距离逻辑依赖改用隐藏 `mission_completed` 条件，避免断线和跨越。
- 每个 mission 必须同时有 `<id>_title` 与 `<id>_desc`；裸 `<id>` 仅可作为旧内容兼容别名。
- 动态路线只通过 canonical immediate + next-day two-phase refresh；旧存档 series key 必须保留同名 inactive tombstone，位置或所有权变化必须有一次性迁移。
- 终局日本不得使用通用任务树；十种统一状态必须保有唯一五-series signature，且 final-tree density 门禁持续有效。
- 任何新增或重排任务必须同时验证主 Mod 188 profiles 与地图 30 tags × 4 DLC states。

### Routes, Religion, Ideas And Reforms

- 统一状态包括：uncommitted JAP、Sakoku JAP、Open Trade JAP、KJP、CJP、EJP、RFJ、SJP、IJP、WAK。
- route/tag/religion 变化必须同步任务、自由理念组与政府 mechanics；不得依赖可选理念替换弹窗完成强制路线身份。
- CJP 只融合一次神道教，保留日本神道风味链的 Confucian bridge，并以原生儒教改革中心在非受保护神宫地区传播；静态结构与运行时结果必须分开记录。
- 玩家可选改革的 `potential` 只放稳定身份，动态路线/任务解锁放 `trigger`；路线变化后调用 `regenerate_government_mechanics = yes`。
- 所有可见日本改革只注册在原版前 11 个 monarchy tiers，并按制度主题归类；炮术归军事学说、商港归经济、祭祀归政教、评定归议会。
- 终局 tag 的理念必须由唯一 tag-triggered free idea group 提供；变 tag 后通过 canonical `swap_free_idea_group = yes` 同步。

### Localisation, Art And Prose

- 活跃中文 localisation 使用 UTF-8 BOM 与项目既有 EU4SpecialEscape 工作流；普通 Markdown 日志保持普通 UTF-8，不得转义。
- 事件、任务与决议正文采用 EU4 历史叙述风格；直接数值、花费与 modifier 交给 tooltip/effect，不写入叙事正文。
- 所有新图片先查阅同类原版资源，再使用 ImageGen 生成高分辨率源图并确定性后处理；格式、尺寸、颜色模式、alpha 与 `.gfx` 注册必须通过资产门禁。

## Architecture Snapshot

### Core Systems

- 三项时代属性：`jxp_tenka_order`、`jxp_imperial_sanction`、`jxp_oceanic_opening`，范围设计为 0-100。
- canonical initialization、route sync、mission refresh、idea sync、reform sync 与 debug cleanup 由主 Mod 统一拥有。
- 低频回拉事件负责缓和极端时代属性；有国家意志介入空间的事件应提供有代价的替代选项。
- 30 个地图大名通过五类 origin flag 接入主 Mod 的家系评定、遗产、议程、路线共鸣与通用 founder fallback。

### Mission And Government State

- 主 Mod：40 个自定义 mission series、272 个 mission ID、188 个 effective profile。
- 地图 Mod：5 个精确 slot-3 house series、15 个 mission、120 个 tag/DLC profile。
- 终局任务：十种统一状态各有唯一五列签名，不得退回 vanilla generic 或 another-route columns。
- 政府改革：27 个路线选择 + 38 个 founder 选择，全部语义注册在前 11 个原版 monarchy tiers；306 个旧定义保持 dormant，不得误重新暴露。
- 改革图标：35 个已验证 57×57 RGBA DDS sprite family。

### Companion Map State

- 日本区域 88 省；新增 ID `4942-4981`；`max_provinces = 4982`。
- 22 个日本 area；1444 总发展 `500`（tax `190`、production `168`、manpower `142`）。
- 30 个新大名；五类起源：warrior、court、maritime、frontier、temple_market。
- 四个语义地理接口：`jxp_map_compat_shimabara_belt`、`jxp_map_compat_ikko_heartland`、`jxp_map_compat_setouchi`、`jxp_map_compat_wokou_waters`。
- 全日期历史门禁覆盖 1444-11-11 至 1821-01-01 的 137,382 个可选日期。

### Original Roadmap Alignment

| Roadmap | Current state | Remaining distance |
| --- | --- | --- |
| 0.1 MVP | 结构和内容量已超过目标 | 当前版本仍需完整运行时验收 |
| 0.2 宗教分支 | KJP/CJP/RFJ/SJP 等已成体系 | 事件、灾难、决议深度仍需路线对齐 |
| 0.3 海外与东亚 | 任务与风味已有广泛骨架 | 天命、八纮一宇、DLC fallback 与太平洋循环需专项验收/扩展 |
| 0.4 民众与海寇 | IJP/WAK 框架与终局任务已存在 | 一向宗灾难、倭寇经济/私掠循环和地域专属内容仍偏薄 |
| 0.5 任务树扩展 | 287 个联合任务且拓扑门禁成熟 | 后续以节奏、历史目的与分支质量为主，不以堆数量为主 |
| 1.0 | 内容量达到或超过原数值目标 | 运行时证明、灾难数量、路线等深度与发布整理尚未完成 |

## Active TODO

状态只允许 `OPEN`、`IN_PROGRESS`、`BLOCKED`、`DONE`、`DEFERRED`。领取任务时填写唯一 owner；完成时必须写证据并保留稳定 ID，不得删除历史任务。

| ID | Priority | Status | Owner | Scope | Task | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- |
| JXP-001 | P0 | OPEN | UNCLAIMED | Runtime | 主 Mod + 地图 Mod 新战役冷启动验收 | 用户明确许可；1444 冷启动、一天后任务/改革、fresh error.log 均通过 |
| JXP-002 | P0 | OPEN | UNCLAIMED | Migration | 旧存档依次验收十种统一状态的任务、理念、改革迁移 | 保存/重载后 flags、已完成任务与五列树稳定，fresh error.log 无 JXP 错误 |
| JXP-003 | P0 | DONE | CODEX_ROOT | Balance/Compatibility | 逐项重构 19 个 `num_of_cities = 25/30` 地图尺度敏感门槛 | 每项记录历史意图，改为统一度、战略省份、area、发展或合理城市数；联合门禁 0 warning |
| JXP-004 | P0 | OPEN | UNCLAIMED | CJP/Religion | 运行时证明 CJP 单次融合神道、改革中心传播和神道事件桥 | 不重复 harmonize；Ise 等保护地不转；Nanban/urbanization/Neo-Confucian bridge 可触发 |
| JXP-005 | P1 | OPEN | UNCLAIMED | UI | 对大名五家系、十种统一状态与地图任务做视觉布局/政府 UI 验收 | 无断线、空洞、重叠、通用树、缺失 icon 或错误 tier；截图留档 |
| JXP-006 | P1 | OPEN | UNCLAIMED | Route parity | 审计九条路线的任务、事件、决议、改革、调试入口深度 | 生成可比较覆盖报告并补齐明显短板，互斥 gate 无矛盾 |
| JXP-007 | P1 | OPEN | UNCLAIMED | Disasters | 将完整灾难系统扩展到原规划的 4-5 个 | 每个灾难窄触发、推进/结束/清理闭合，并有 debug 验收入口 |
| JXP-008 | P1 | OPEN | UNCLAIMED | WAK | 完成倭寇联盟、私掠、港市与海上国家的长期循环 | 有进入、投资、压力、收益、退出与 AI 行为；地图语义范围兼容 |
| JXP-009 | P1 | OPEN | UNCLAIMED | IJP | 完成一向宗压力/灾难及寺社町众国家循环 | 与岛原不误叠，宗教/阶层/地域 gate 合理，终局任务和事件互相支撑 |
| JXP-010 | P1 | OPEN | UNCLAIMED | Mandate | 审计日本取得天命、八纮一宇改革、CB/AE 与 DLC fallback | 仅任务解锁；无天命 DLC 有替代路径；脚本 effect/CB 经原版实证与运行时验证 |
| JXP-011 | P2 | OPEN | UNCLAIMED | Overseas | 扩展阿拉斯加、加利福尼亚、马尼拉-长崎与太平洋日本循环 | 各路线有合理分歧，避免单纯永久 modifier 堆叠 |
| JXP-012 | P2 | OPEN | UNCLAIMED | Regional flavor | 增补对马、濑户内、琉球及伴随地图地域专属任务/事件 | 使用语义地理接口，避免硬引用可选 area，且不重复奖励 1021/4943 |
| JXP-013 | P2 | OPEN | UNCLAIMED | Writing/Events | 为可干预低频事件增加有意义选项并继续历史文案润色 | 选项有真实取舍；叙事不直述点数/修正；debug cleanup 覆盖新 flags/modifiers |
| JXP-014 | P2 | OPEN | UNCLAIMED | Era attributes | 审计任务、事件、改革、幕府政策、投资对三项时代属性的非决议交互 | 每条路线有多种长期改变方式；刀狩令不与原版幕府行动重复 |
| JXP-015 | P1 | OPEN | UNCLAIMED | Safety | 审计全部 event flags/modifiers 的 debug cleanup 与灾难误触发 | 自动覆盖报告无孤立状态；岛原及后续灾难无明显 false positive |
| JXP-016 | P2 | IN_PROGRESS | PROJECT | Process | 持续维护本总账、历史索引与 skill 协议 | 每个开发切片同步更新版本、TODO、证据、风险和 Update Journal |
| JXP-017 | P0 | OPEN | UNCLAIMED | Map runtime | 验收 88 省地图渲染、港口、海峡、标签、书签与日期滑块 | 用户许可后按 map implementation report 清单完整执行并归档截图/log |
| JXP-018 | P1 | OPEN | UNCLAIMED | Toyotomi/History | 建立独立丰臣家身份，修复秀吉掌权后仍沿用织田家的历史与玩法链 | 专属 tag、旗帜、名称、理念及任务身份完整；秀吉路线在正确节点转为丰臣，任务、理念、政府、属国和旧存档迁移不丢失；伴随地图可选日期保持一致 |
| JXP-019 | P1 | OPEN | UNCLAIMED | Daimyo ideas/missions | 建立全部日本大名的理念与任务覆盖矩阵，按历史影响力分层扩展；织田家加入“天下布武”专属主线 | 主/地图全部可选大名均有非通用理念与身份任务；历史重要大名拥有更深且较强的专属分支；联合 profile 无 generic fallback、冲突或断链，并有强度分层审计 |
| JXP-020 | P0 | IN_PROGRESS | CODEX_ROOT | Ideas/UI | 给国家理念结构增加硬性上限，修复理念超限造成的 UI 重叠 | 所有可激活理念组均符合 `start + 7 ideas + bonus` 标准结构；生成器与 validator 对超限 hard fail；获准运行时截图确认无重叠或越界 |
| JXP-021 | P1 | OPEN | UNCLAIMED | Localisation/Names | 将 Mod 中尚未汉化的日本大名领袖姓名统一汉化为中文 | 审计 country history、scripted monarch/heir/consort、将领/提督与姓名池；零遗留应汉化的罗马字日本人名，且 source/active 本地化管线通过 |
| JXP-022 | P1 | OPEN | UNCLAIMED | Final tags | 为每个日本终局 tag/统一状态增加专属权力结构政治改革并扩写任务树 | 十种统一状态各有语义匹配且互斥可见的权力结构改革、独特任务签名与足够深度；动态刷新和旧存档迁移闭合，无串线、通用树或错误 tier |
| JXP-023 | P0 | IN_PROGRESS | CODEX_ROOT | Mandate/Bugfix | 修复已满足解锁条件后“八纮一宇”天朝改革仍不显示的 bug | 有天命 DLC 时仅合格的日本天子在正确 UI 看见并可选改革；无提前/外国误显，government mechanics 刷新及旧存档迁移闭合；无 DLC fallback、获准运行时截图与 fresh error.log 共同作为 `JXP-010` 证据 |

## Known Risks

1. **没有当前版本运行时证明。** 0.26.0 + 0.1.1-alpha 只有完整静态证明；不得把早期版本冷启动或用户“目前正常”的反馈自动外推到当前所有 profile。
2. **其余固定城市数条件仍需节奏审计。** `JXP-003` 已将 19 个 25/30 门槛全部语义化；较低的固定门槛（如 20）由 `JXP-006` 按路线节奏继续判定。
3. **CJP 是高风险桥接区。** harmonization、改革中心、神道事件/incident 继承涉及引擎行为，静态检查只能证明结构。
4. **旧存档序列化 mission series。** 即使 `potential` 已禁用，旧 key 也可能残留；不得删除 tombstone 或省略迁移。
5. **动态 UI 刷新。** “获得新任务”必须 immediate swap + next-day reconcile + fingerprint repair；新增路线不得直接散写 swap。
6. **地图硬兼容边界。** 伴随地图覆盖完整地图基础文件；它不能与其他日本地图 overhaul 共存，且必须新开局。
7. **Sakai 双锚点。** `1021` 与 `4943` 语义相邻但不是可互换的同一省，需防重复效果。
8. **dormant reforms。** 306 个旧定义仍保留以兼容/历史用途，任何生成器或手改不得把它们重新注册到 UI。
9. **Chinese localisation pipeline。** source 与 active 文件不可混改；Markdown 日志不得经过 EU4SpecialEscape。
10. **并行 agent 冲突。** Git 已提供提交与 worktree 边界，但总账仍采用 lead-agent 单写者协议；并行分支不得各自改写总账后假设可自动合并。

## Validation Matrix

### Mandatory Static Gates

主 Mod 每个玩法切片：

```powershell
$repo = '<repo>'
$game = '<EU4 game root>'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\skills\eu4-modding\scripts\validate_jxp_mod.ps1" `
  -ModPath "$repo\japan_expanded_v2" `
  -GameRoot $game
```

主 Mod + 伴随地图联合发布面，每个玩法或地图切片：

```powershell
$repo = '<repo>'
$game = '<EU4 game root>'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\japan_expanded_v2_map\tools\validate_all.ps1" `
  -GameRoot $game `
  -MainMod "$repo\japan_expanded_v2"
```

Skill 修改后：

```powershell
$repo = '<repo>'
& '<python>' '<skill-creator>/scripts/quick_validate.py' "$repo\skills\eu4-modding"
```

### Evidence Classes

| Mark | Meaning | May claim |
| --- | --- | --- |
| `STATIC_PASS` | 解析、合同、拓扑、资产、历史、单测全部通过 | 结构上满足门禁；不可声称游戏 UI/引擎已运行 |
| `RUNTIME_PASS` | 经用户许可启动并按清单运行，fresh log 与截图通过 | 仅限实际测试过的版本、profile 和场景 |
| `USER_OBSERVED` | 用户在游戏中报告结果 | 有价值但范围按用户实际测试限定 |
| `PENDING_RUNTIME` | 尚未获许可或尚未测试 | 必须保留为开放 TODO |

## Handoff Protocol

### Before Editing

1. 读取 `eu4-modding/SKILL.md`、目标 Mod 根目录 `AGENTS.md`、本总账与相关阶段报告。
2. 涉及地图时读取 `BASELINE_LOCK.txt` 和 `main_compatibility_contract.json`。
3. 核对内外 descriptor 版本、本总账 Current Snapshot 与工作目录是否一致。
4. 在 Active TODO 中领取已有 ID；若确属新目标，追加新 ID，不复用或重编号。
5. 记录 owner、改为 `IN_PROGRESS`，并在 Update Journal 写一条 `STARTED`。并行 subagent 不直接编辑总账。
6. 运行与改动相关的最小基线检查，确认失败不是改动前已有状态。

### During Editing

1. 尊重现有文件与生成器所有权；生成文件必须改生成源并验证 idempotence。
2. 每个新知识先判断是项目事实还是通用 EU4 经验：项目事实写总账/合同，通用经验写 skill。
3. 任何主玩法改动都同步审计伴随地图；不得把联合验证推迟到版本末尾。
4. 若触及 missions、route flags、ideas、reforms 或 map positions，必须同时设计 old-save migration 或明确“仅新战役”。
5. 不启动游戏。若静态工具无法证明关键行为，将 TODO 标记为 `PENDING_RUNTIME`，由主 agent 向用户请求许可。

### Before Handoff Or Final Response

1. 运行完整主门禁与地图联合门禁；skill 有变化则运行 skill validator。
2. 更新 Current Snapshot 的版本、统计与 runtime 状态；不要保留预测数字。
3. 更新 TODO status/owner/evidence；没有证据不得标 `DONE`。
4. 在 Update Journal 顶部追加一条含日期、版本、文件范围、验证结果、运行时状态和剩余风险的记录。
5. 新增阶段报告时，将文件加入 Historical Report Index；验证器会拒绝漏索引。
6. 向下一位 agent 明确说明：已改什么、没改什么、静态/运行时各证明到哪里、首要下一个 TODO 是什么。

## Update Journal

按时间倒序追加；旧记录不可静默重写。版本未变化时写 `no version bump`。

### 2026-07-10 - RELEASE-026 - Static P0 hardening (`0.26.0`)

- Status: `STATIC_PASS; PENDING_RUNTIME`。
- Scope: 完成 `JXP-003` 的 19 个地图尺度语义门槛；完成 `JXP-020` 的 45 组理念静态结构合同；补齐 `JXP-023` 的解锁、改革候选缓存刷新、旧档迁移和无 DLC fallback。
- Evidence: 主门禁 `13/13`、Clausewitz `180/180`、单元测试 `67/67`；地图联合门禁全部 `0 errors / 0 warnings`；`19/19` 调用点与 `20/20` 固定语义合同、`44/44 + 1/1` 理念组闭合。
- Runtime: `PENDING_USER_APPROVAL`；未启动 EU4 或启动器；理念 UI 与八纮一宇天朝 UI/fresh log 仍需运行时验收。
- TODO: `JXP-003` 改为 `DONE`；`JXP-020` / `JXP-023` 保持 `IN_PROGRESS / CODEX_ROOT`；`JXP-016` 继续由 `PROJECT` 维护。
- Evidence report: `jxp_phase_report_0_26_0_static_p0_hardening.md`。

### 2026-07-10 - P0-STATIC-START - Static P0 remediation (`no version bump`)

- Status: `STARTED; STATIC_BASELINE_PASS`。
- Scope: `CODEX_ROOT` 领取 `JXP-003` / `JXP-020` / `JXP-023`；分别重构 19 个地图尺度敏感门槛、强制国家理念 `start + 7 ideas + bonus` 结构，以及闭合“八纮一宇”改革的可见性、迁移与 DLC fallback。
- Evidence: 改动前主门禁 `12/12`、单元测试 `40/40`；工作分支 `codex/complete-todo-backlog`，基线工作树干净。
- Runtime: `PENDING_USER_APPROVAL`；本切片不启动 EU4 或启动器。
- TODO: `JXP-003` / `JXP-020` / `JXP-023` 进入 `IN_PROGRESS`；`JXP-016` 继续由 `PROJECT` 维护。

### 2026-07-10 - REPO-001 - GitHub source import and agent handoff (`no version bump`)

- Status: `STATIC_PASS; PENDING_RUNTIME`。
- Scope: 将主 Mod、八十八国伴随地图、两份 portable launcher descriptor 与完整 `eu4-modding` skill 导入 `Dystopians/JapMod`；新增根 `AGENTS.md` 与 `AGENT_HANDOFF_GUIDE.md`，明确仓库入口、安装方式、验证矩阵、Git 工作流与交接清单；排除游戏本体、Workshop、备份与 Python 缓存。
- Evidence: 仓库副本主门禁 `12/12`、单元测试 `40/40`；地图联合门禁 `0 errors / 0 warnings`；嵌入 skill `quick_validate.py` 为 `Skill is valid!`。
- Runtime: `PENDING_USER_APPROVAL`；本切片未启动 EU4 或启动器。
- Handoff: 实时状态仍只属于本总账；根指南只解释接入与流程，不建立第二份 TODO。后续工作从稳定 `JXP-*` 项领取，并使用分支/worktree 提交。

### 2026-07-10 - LEDGER-002 - User-requested content backlog (`no version bump`)

- Status: `STATIC_PASS`。
- Scope: 新增 `JXP-018` 至 `JXP-023`，覆盖丰臣家、全大名理念/任务分层、理念 UI 上限、领袖姓名汉化、终局国家权力结构与任务，以及“八纮一宇”改革显示缺陷。
- Evidence: 主门禁 `12/12`、单元测试 `40/40`；地图联合门禁 `0 errors / 0 warnings`；总账识别 `23` 个稳定 TODO 与 `73` 份历史报告；未改玩法文件或 descriptor。
- Runtime: `PENDING_USER_APPROVAL`；本切片不启动 EU4。
- TODO: `JXP-016` 持续维护；新增六项均为 `OPEN / UNCLAIMED`，其中 `JXP-023` 为 `JXP-010` 的明确 P0 缺陷子项。

### 2026-07-10 - LEDGER-001 - Shared development ledger (`no version bump`)

- Status: `STATIC_PASS`。
- Scope: 建立唯一总账、主/地图 `AGENTS.md`、总账一致性校验与 skill 强制入口。
- Evidence: 主门禁 `12/12`、单元测试 `40/40`；地图联合门禁 `0 errors / 0 warnings`；skill `quick_validate.py` 通过；73 份历史报告全部被索引。
- Runtime: `PENDING_RUNTIME`；本切片不需要且未获许可启动 EU4。
- TODO: `JXP-016`。

### 2026-07-10 - COMPAT-001 - Main/map compatibility hardening (`0.25.0` + `0.1.1-alpha`)

- Status: `STATIC_PASS`。
- 修复 13 个无效文化键、地图任务指纹循环、错误 maritime trigger、地图 origin 接入、slot-3 奇偶布局、旧存档地图迁移和四类语义地理桥。
- 为 34 个 0.25 mission 补齐 canonical `_title`；联合 287 mission 的 `_title/_desc` 均闭合。
- 主门禁 11/11、37/37；地图联合门禁 0 error/0 warning；未启动 EU4。
- Evidence: `jxp_main_map_compatibility_audit_2026_07_10.md`。

### 2026-07-10 - RELEASE-025 - Final-tag missions and reforms (`0.25.0`)

- Status: `STATIC_PASS; PENDING_RUNTIME`。
- 十种统一状态拥有唯一五列任务签名；新增六个路线 series 与 34 个 mission，主任务总数 272。
- 路线改革可见性按十种状态模拟；0.25.1 migration 同步任务、理念与政府 mechanics。
- Evidence: `jxp_phase_report_0_25_0_final_tag_missions_and_reforms.md`。

### 2026-07-10 - MAP-010 - Japan 88-province companion (`0.1.0-alpha`, later `0.1.1-alpha`)

- Status: `STATIC_PASS; PENDING_RUNTIME`。
- 88 省、22 area、30 新大名、15 任务、全日期历史与确定性图像资源完成；地图合同与兼容边界锁定。
- Evidence: map `jxp_map_implementation_report_0_1_0.md`、`jxp_map_date_slider_audit_0_1_0.md`、`BASELINE_LOCK.txt`。

### 2026-07-09 to 2026-07-10 - RELEASE-022-024 - Structural consolidation (`0.22.0` to `0.24.2`)

- Status: `STATIC_PASS; later slices supersede earlier runtime assumptions`。
- 前 11 级改革重整、图标门禁、CJP bridge、任务候选/刷新/拓扑/renderer 修复、37 大名五列树、终局非通用树、理念同步和旧 key tombstone 已建立。
- Evidence: 对应 `jxp_phase_report_0_22_0_*` 至 `jxp_phase_report_0_24_2_*`。

### Earlier milestones - RELEASE-004-021 (`0.4.1` to `0.21.2`)

- 核心时代属性、路线/宗教分支、大名与家系风味、任务、理念、低频事件、评定、路线/创立家政府改革、枢密院、高官与 UI guardrails 逐步完成。
- 这些报告保留历史价值，但任何与当前 0.26.0 架构冲突的实现描述均由后续报告和本总账 supersede。
- Evidence: Historical Report Index 中 0.4.1-0.21.2 全部阶段报告。

## Historical Report Index

下列文件全部保留为历史证据。验证器要求两个 `dev_logs` 目录中除本总账外的每个文件都出现在本索引中。

### Main Mod Reports

- `jxp_0_22_0_working_plan.md` - 0.22.0 集成工作计划。
- `jxp_current_progress_against_original_plan_2026_07_09.md` - 原始规划对照快照；已由本总账接管当前状态。
- `jxp_hotfix_debug_decision_ui_freeze.md` - 调试决议界面卡死热修复。
- `jxp_japan_map_refinement_feasibility_plan_0_23_2.md` - 日本地图细化可行性与实施计划。
- `jxp_main_map_compatibility_audit_2026_07_10.md` - 主 Mod/八十八国地图联合兼容审计。
- `jxp_master_todo_from_original_plan.md` - 旧主 TODO；已冻结，由本总账接管。
- `jxp_phase_report_0_4_1.md` - 0.4.1 阶段报告。
- `jxp_phase_report_0_4_2.md` - 0.4.2 阶段报告。
- `jxp_phase_report_0_5.md` - 0.5 阶段报告。
- `jxp_phase_report_0_5_1.md` - 0.5.1 热修复报告。
- `jxp_phase_report_0_5_2.md` - 0.5.2 热修复报告。
- `jxp_phase_report_0_5_3.md` - 0.5.3 阶段修复报告。
- `jxp_phase_report_0_5_4_hotfix.md` - 0.5.4 热修复报告。
- `jxp_phase_report_0_6_0_route_reforms.md` - 0.6.0 建国分支政府改革。
- `jxp_phase_report_0_7_0_daimyo_flavor.md` - 0.7.0 大名个性化。
- `jxp_phase_report_0_8_0_route_reforms.md` - 0.8.0 路线改革扩展。
- `jxp_phase_report_0_8_1_visible_route_reforms.md` - 0.8.1 可见路线改革层。
- `jxp_phase_report_0_8_2_remaining_daimyo_ideas.md` - 0.8.2 剩余大名理念。
- `jxp_phase_report_0_8_3_daimyo_house_flavor.md` - 0.8.3 家名风味与遗产。
- `jxp_phase_report_0_8_4_minor_house_flavor.md` - 0.8.4 小大名一族一策。
- `jxp_phase_report_0_8_5_coverage_audit.md` - 0.8.5 覆盖审计门禁。
- `jxp_phase_report_0_8_6_daimyo_house_missions.md` - 0.8.6 大名家系任务。
- `jxp_phase_report_0_8_7_unified_house_ordinances.md` - 0.8.7 统一后家法。
- `jxp_phase_report_0_8_8_unified_house_followups.md` - 0.8.8 统一后家法事件。
- `jxp_phase_report_0_9_0_route_reform_expansion.md` - 0.9.0 路线政府改革扩展。
- `jxp_phase_report_0_9_1_daimyo_house_agendas.md` - 0.9.1 大名家系议程。
- `jxp_phase_report_0_9_2_daimyo_idea_rebalance.md` - 0.9.2 大名理念再平衡。
- `jxp_phase_report_0_9_3_founder_legacy_councils.md` - 0.9.3 创立家遗产评定。
- `jxp_phase_report_0_9_4_founder_legacy_extension.md` - 0.9.4 创立家遗产扩展。
- `jxp_phase_report_0_9_5_route_state_and_doctrine_reforms.md` - 0.9.5 路线状态与教义改革。
- `jxp_phase_report_0_9_6_founder_house_reforms.md` - 0.9.6 开府家法改革。
- `jxp_phase_report_0_9_7_founder_legacy_council_full_coverage.md` - 0.9.7 开府遗策全覆盖。
- `jxp_phase_report_0_9_8_daimyo_idea_audit_hardening.md` - 0.9.8 大名理念审计固化。
- `jxp_phase_report_0_9_9_route_house_compromise.md` - 0.9.9 路线与家风评议。
- `jxp_phase_report_0_10_0_route_house_resonance.md` - 0.10.0 路线家风低频共鸣。
- `jxp_phase_report_0_10_1_specific_route_house_combos.md` - 0.10.1 具体家族路线组合。
- `jxp_phase_report_0_10_2_major_route_house_combos.md` - 0.10.2 主要大名路线组合。
- `jxp_phase_report_0_11_0_route_capstone_reforms.md` - 0.11.0 路线高阶改革。
- `jxp_phase_report_0_11_1_all_origin_route_house_combos.md` - 0.11.1 全起源路线组合。
- `jxp_phase_report_0_11_2_daimyo_house_diets.md` - 0.11.2 大名家法评定。
- `jxp_phase_report_0_11_3_house_diet_legacy.md` - 0.11.3 家法入国制。
- `jxp_phase_report_0_11_4_house_diet_missions.md` - 0.11.4 家法评定任务。
- `jxp_phase_report_0_12_0_route_special_reforms.md` - 0.12.0 路线别格改革。
- `jxp_phase_report_0_12_1_founder_reform_pulses.md` - 0.12.1 创立家改革脉冲。
- `jxp_phase_report_0_13_0_route_government_reforms.md` - 0.13.0 路线政府改革重点。
- `jxp_phase_report_0_13_1_daimyo_idea_identity_pass.md` - 0.13.1 大名理念身份。
- `jxp_phase_report_0_13_2_early_daimyo_event_rewards.md` - 0.13.2 前统一事件奖励身份。
- `jxp_phase_report_0_13_3_preunification_policy_memory.md` - 0.13.3 前统一政策记忆。
- `jxp_phase_report_0_13_4_minor_policy_memory.md` - 0.13.4 小家政策记忆。
- `jxp_phase_report_0_13_5_full_policy_memory.md` - 0.13.5 全前统一政策记忆。
- `jxp_phase_report_0_14_0_route_program_reforms.md` - 0.14.0 路线纲领改革。
- `jxp_phase_report_0_15_0_route_privy_councils.md` - 0.15.0 路线枢密院改革。
- `jxp_phase_report_0_16_0_daimyo_idea_identity_pass2.md` - 0.16.0 大名理念身份第二轮。
- `jxp_phase_report_0_17_0_daimyo_idea_decloning.md` - 0.17.0 大名理念去同质化。
- `jxp_phase_report_0_19_0_legacy_cabinet_and_sovereign_projects.md` - 0.19.0 遗产内阁与国家工程。
- `jxp_phase_report_0_20_0_major_founder_house_policy.md` - 0.20.0 主要创立家政策事件。
- `jxp_phase_report_0_21_0_route_high_offices.md` - 0.21.0 路线高官改革。
- `jxp_phase_report_0_21_1_reform_consolidation_plan.md` - 0.21.1 政府改革整合计划。
- `jxp_phase_report_0_21_2_ui_bugfix_pass.md` - 0.21.2 UI 修复与门禁。
- `jxp_phase_report_0_22_0_government_missions_confucian.md` - 0.22.0 政府、任务与 CJP 整合。
- `jxp_phase_report_0_23_0_mission_refresh_topology_ideas.md` - 0.23.0 任务刷新、拓扑与理念。
- `jxp_phase_report_0_23_1_confucian_incident_hakko_tooltip.md` - 0.23.1 儒教神道继承与八纮一宇 tooltip。
- `jxp_phase_report_0_23_1_mission_renderer_hotfix.md` - 0.23.1 任务 renderer 修复。
- `jxp_phase_report_0_23_2_government_reform_visibility_hotfix.md` - 0.23.2 政府改革可见性修复。
- `jxp_phase_report_0_23_3_mission_renderer_geometry_hotfix.md` - 0.23.3 renderer 几何修复。
- `jxp_phase_report_0_23_4_reform_semantic_reclassification.md` - 0.23.4 改革语义重分类。
- `jxp_phase_report_0_24_0_daimyo_and_final_tag_mission_expansion.md` - 0.24.0 大名与终局 tag 任务扩展。
- `jxp_phase_report_0_24_1_runtime_state_hotfix.md` - 0.24.1 理念与任务运行态修复。
- `jxp_phase_report_0_24_2_mission_runtime_and_spacing_hotfix.md` - 0.24.2 任务刷新与间距修复。
- `jxp_phase_report_0_25_0_final_tag_missions_and_reforms.md` - 0.25.0 终局任务身份与改革可见性。
- `jxp_phase_report_0_26_0_static_p0_hardening.md` - 0.26.0 地图尺度、理念 UI 与八纮一宇静态收口。

### Companion Map Reports

- `BASELINE_LOCK.txt` - 地图版本、ID、发展、像素、历史与兼容硬锁。
- `jxp_map_date_slider_audit_0_1_0.md` - 0.1.0 全日期滑块历史审计。
- `jxp_map_implementation_report_0_1_0.md` - 0.1.0 八十八国地图实施报告。
