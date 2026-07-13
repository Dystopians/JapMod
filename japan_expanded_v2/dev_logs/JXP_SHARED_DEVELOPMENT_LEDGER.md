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
- Last updated: `2026-07-13`
- Main Mod version: `0.28.0`
- Companion Map version: `0.1.3-alpha`
- Pinned game: `EU4 v1.37.5.0 Inca (491d)`
- Supported version: `1.37.*`
- Runtime acceptance: `PENDING_USER_APPROVAL`
- Main static gate: `26/26 checks; 221/221 core unit tests; 52/52 acceptance-helper tests`
- Combined static gate: `0 errors; 0 warnings`
- Main missions: `288 mission IDs; 41 custom series; 192 effective profiles`
- Combined missions: `321 mission IDs; 46 series; 120 companion tag/DLC profiles`
- Combined content inventory: `498 events; 289 decisions; 385 scripted callables; 918 modifiers`
- State safety: `538 country flags; 8 province flags; 918 modifiers; 4 disasters; 0 failures`
- Companion geography: `88/88 japan_region provinces; 137382 selectable days; 299 owner intervals; 70 subject intervals`
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
- 任何新增或重排任务必须同时验证主 Mod 192 profiles 与地图 30 tags × 4 DLC states。

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

- 主 Mod：41 个自定义 mission series、288 个 mission ID、192 个 effective profile。
- 地图 Mod：5 个精确 slot-3 house series、33 个 mission、120 个 tag/DLC profile。
- 终局任务：十种统一状态各有唯一五列签名，不得退回 vanilla generic 或 another-route columns。
- 政府改革：27 个路线选择 + 39 个 founder 选择，全部语义注册在前 11 个原版 monarchy tiers；306 个旧定义保持 dormant，不得误重新暴露。
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
| 0.2 宗教分支 | KJP/CJP/RFJ/SJP 等已成体系，四路线改革互动已对齐 | 当前版本仍需运行时节奏与 UI 证明 |
| 0.3 海外与东亚 | 天命/八纮一宇静态合同、四支太平洋循环及东亚地域风味已闭合 | 仍需运行时验证 CB/和约/AE、DLC fallback 与长期节奏 |
| 0.4 民众与海寇 | IJP/WAK 均有压力、投资、危机、退出与 AI 静态闭环 | 仍需 observer、存读档和运行时节奏证明 |
| 0.5 任务树扩展 | 321 个联合任务且拓扑门禁成熟 | 后续以节奏、历史目的与分支质量为主，不以堆数量为主 |
| 1.0 | 内容量、四灾难、九路线循环、大名身份、海外/地域风味与终局政治扩展均已达到静态目标 | 剩余距离集中于获准后的运行时证明与修复闭环 |

## Active TODO

状态只允许 `OPEN`、`IN_PROGRESS`、`BLOCKED`、`DONE`、`DEFERRED`。领取任务时填写唯一 owner；完成时必须写证据并保留稳定 ID，不得删除历史任务。

| ID | Priority | Status | Owner | Scope | Task | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- |
| JXP-001 | P0 | IN_PROGRESS | CODEX_ROOT | Runtime | 主 Mod + 地图 Mod 新战役冷启动验收 | 用户明确许可；1444 冷启动、一天后任务/改革、fresh error.log 均通过 |
| JXP-002 | P0 | IN_PROGRESS | CODEX_ROOT | Migration | 旧存档依次验收十种统一状态的任务、理念、改革迁移 | 保存/重载后 flags、已完成任务与五列树稳定，fresh error.log 无 JXP 错误 |
| JXP-003 | P0 | DONE | CODEX_ROOT | Balance/Compatibility | 逐项重构 19 个 `num_of_cities = 25/30` 地图尺度敏感门槛 | 每项记录历史意图，改为统一度、战略省份、area、发展或合理城市数；联合门禁 0 warning |
| JXP-004 | P0 | IN_PROGRESS | CODEX_ROOT | CJP/Religion | 运行时证明 CJP 单次融合神道、改革中心传播和神道事件桥 | 不重复 harmonize；Ise 等保护地不转；Nanban/urbanization/Neo-Confucian bridge 可触发 |
| JXP-005 | P1 | IN_PROGRESS | CODEX_ROOT | UI | 对大名五家系、十种统一状态与地图任务做视觉布局/政府 UI 验收 | 无断线、空洞、重叠、通用树、缺失 icon 或错误 tier；截图留档 |
| JXP-006 | P1 | DONE | CODEX_ROOT | Route parity | 审计九条路线的任务、事件、决议、改革、调试入口深度 | 生成可比较覆盖报告并补齐明显短板，互斥 gate 无矛盾 |
| JXP-007 | P1 | DONE | CODEX_ROOT | Disasters | 将完整灾难系统扩展到原规划的 4-5 个 | 每个灾难窄触发、推进/结束/清理闭合，并有 debug 验收入口 |
| JXP-008 | P1 | IN_PROGRESS | CODEX_ROOT | WAK | 完成倭寇联盟、私掠、港市与海上国家的长期循环 | 有进入、投资、压力、收益、退出与 AI 行为；地图语义范围兼容 |
| JXP-009 | P1 | IN_PROGRESS | CODEX_ROOT | IJP | 完成一向宗压力/灾难及寺社町众国家循环 | 与岛原不误叠，宗教/阶层/地域 gate 合理，终局任务和事件互相支撑 |
| JXP-010 | P1 | IN_PROGRESS | CODEX_ROOT | Mandate | 审计日本取得天命、八纮一宇改革、CB/AE 与 DLC fallback | 仅任务解锁；无天命 DLC 有替代路径；脚本 effect/CB 经原版实证与运行时验证 |
| JXP-011 | P2 | DONE | CODEX_ROOT | Overseas | 扩展阿拉斯加、加利福尼亚、马尼拉-长崎与太平洋日本循环 | 四类分歧投资、压力/危机/退出闭环、14 个有限期 modifier 与 12 项定向测试均通过；无 companion-only 依赖或永久堆叠 |
| JXP-012 | P2 | DONE | CODEX_ROOT | Regional flavor | 增补对马、濑户内、琉球及伴随地图地域专属任务/事件 | 三套语义 gate、地图 capstone、AI 委任、原子调度与互斥结果清理通过 14 项定向测试；无 1021/4943 重复奖励 |
| JXP-013 | P2 | DONE | CODEX_ROOT | Writing/Events | 为可干预低频事件增加有意义选项并继续历史文案润色 | 22 个可见慢事件均新增有成本的差异选项，完成态/文案/清理合同与 9 项定向测试全通过 |
| JXP-014 | P2 | DONE | CODEX_ROOT | Era attributes | 审计任务、事件、改革、幕府政策、投资对三项时代属性的非决议交互 | 每条路线有多种长期改变方式；刀狩令不与原版幕府行动重复 |
| JXP-015 | P1 | DONE | CODEX_ROOT | Safety | 审计全部 event flags/modifiers 的 debug cleanup 与灾难误触发 | 自动覆盖报告无孤立状态；岛原及后续灾难无明显 false positive |
| JXP-016 | P2 | IN_PROGRESS | PROJECT | Process | 持续维护本总账、历史索引与 skill 协议 | 每个开发切片同步更新版本、TODO、证据、风险和 Update Journal |
| JXP-017 | P0 | IN_PROGRESS | CODEX_ROOT | Map runtime | 验收 88 省地图渲染、港口、海峡、标签、书签与日期滑块 | 用户许可后按 map implementation report 清单完整执行并归档截图/log |
| JXP-018 | P1 | IN_PROGRESS | CODEX_ROOT | Toyotomi/History | 建立独立丰臣家身份，修复秀吉掌权后仍沿用织田家的历史与玩法链 | 专属 tag、旗帜、名称、理念及任务身份完整；秀吉路线在正确节点转为丰臣，任务、理念、政府、属国和旧存档迁移不丢失；伴随地图可选日期保持一致 |
| JXP-019 | P1 | DONE | CODEX_ROOT | Daimyo ideas/missions | 建立全部日本大名的理念与任务覆盖矩阵，按历史影响力分层扩展；织田家加入“天下布武”专属主线 | 主/地图全部可选大名均有非通用理念与身份任务；历史重要大名拥有更深且较强的专属分支；联合 profile 无 generic fallback、冲突或断链，并有强度分层审计 |
| JXP-020 | P0 | IN_PROGRESS | CODEX_ROOT | Ideas/UI | 给国家理念结构增加硬性上限，修复理念超限造成的 UI 重叠 | 所有可激活理念组均符合 `start + 7 ideas + bonus` 标准结构；生成器与 validator 对超限 hard fail；获准运行时截图确认无重叠或越界 |
| JXP-021 | P1 | DONE | CODEX_ROOT | Localisation/Names | 将 Mod 中尚未汉化的日本大名领袖姓名统一汉化为中文 | 审计 country history、scripted monarch/heir/consort、将领/提督与姓名池；零遗留应汉化的罗马字日本人名，且 source/active 本地化管线通过 |
| JXP-022 | P1 | IN_PROGRESS | CODEX_ROOT | Final tags | 为每个日本终局 tag/统一状态增加专属权力结构政治改革并扩写任务树 | 十种统一状态各有语义匹配且互斥可见的权力结构改革、独特任务签名与足够深度；动态刷新和旧存档迁移闭合，无串线、通用树或错误 tier |
| JXP-023 | P0 | IN_PROGRESS | CODEX_ROOT | Mandate/Bugfix | 修复已满足解锁条件后“八纮一宇”天朝改革仍不显示的 bug | 有天命 DLC 时仅合格的日本天子在正确 UI 看见并可选改革；无提前/外国误显，government mechanics 刷新及旧存档迁移闭合；无 DLC fallback、获准运行时截图与 fresh error.log 共同作为 `JXP-010` 证据 |

## Known Risks

1. **没有当前版本运行时证明。** 0.28.0 + 0.1.3-alpha 只有完整静态证明；不得把早期版本冷启动或用户“目前正常”的反馈自动外推到当前所有 profile。
2. **固定城市数不得脱离语义容量。** 25/30 门槛已全部替换；保留的较低门槛必须同时有统一身份、关键省、发展、港口或其他历史容量条件。天明灾难的 `20` 城与 `250` 发展/江户锚点已由 mutation 固定。
3. **CJP 是高风险桥接区。** harmonization、改革中心、神道事件/incident 继承涉及引擎行为，静态检查只能证明结构。
4. **旧存档序列化 mission series。** 即使 `potential` 已禁用，旧 key 也可能残留；不得删除 tombstone 或省略迁移。
5. **动态 UI 刷新。** “获得新任务”必须 immediate swap + next-day reconcile + fingerprint repair；新增路线不得直接散写 swap。
6. **地图硬兼容边界。** 伴随地图覆盖完整地图基础文件；它不能与其他日本地图 overhaul 共存，且必须新开局。
7. **Sakai 双锚点。** `1021` 与 `4943` 语义相邻但不是可互换的同一省，需防重复效果。
8. **dormant reforms。** 306 个旧定义仍保留以兼容/历史用途，任何生成器或手改不得把它们重新注册到 UI。
9. **Chinese localisation pipeline。** source 与 active 文件不可混改；Markdown 日志不得经过 EU4SpecialEscape。
10. **并行 agent 冲突。** Git 已提供提交与 worktree 边界，但总账仍采用 lead-agent 单写者协议；并行分支不得各自改写总账后假设可自动合并。
11. **运行时隔离协议尚未获引擎证明。** 对 pinned EU4 1.37.5 的静态逆向已证明只允许 lower-case、non-repeated、非空的 `-userdir=C:\Users\meizhanxuan\Documents\JXP_Acceptance`；CLI 非空值优先于 game-root `userdir.txt`，后者再优先于 Documents 默认值。旧 `...\Europa Universalis IV - JXP Acceptance` 路径会在 Paradox option parser 中被空格后的 `-` 截断成日常根，普通外层 shell quotes 不能保护，故已永久禁用。正式验收仍须在用户明确许可后做可见协议探针，证明实际 VFS 写入与主机安全策略；只允许场景 exact owned descriptors，排除中文补丁、Graphical Map Improvements 与所有无关 Mod，且默认 `launcher-v2.sqlite` / `dlc_load.json` 必须保持 hash 不变。
12. **pre-0.24.2 真实旧档缺口。** 当前 Git 最早完整源码仍是 `6e461e2` / `0.25.0`。已穷尽扫描 719,834 个本机唯一文件、220 个可解压/流式检查的 `.eu4` 存档、4,055 个有效 ZIP、113 个其他 archive、5,542 个 UnityFS bundle、33 个本地 Workshop Mod，以及 Git refs/reflog/fsck、GitHub refs/branches/PR/releases/actions/artifacts/forks、cloud cache、回收站、浏览器 history 与 Recent，均未找到 JXP pre-0.24.2 payload 或 serialization。旧开发机仍是唯一真实来源：0.23.1 报告记录两份 ZIP，0.23.2 报告记录第三份 ZIP 与原问题 `autosave.eu4`，0.24.1 报告记录 DOM/JXP 同时序列化和六个 BOM-prefixed series。仓库可由 `8a59626` / `0.27.0` 生成十状态迁移输入，但 R5 必须取得旧机原档/任一命名 ZIP 后由引擎生成真实失败档；禁止合成、改旗或重命名伪造。

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

### 2026-07-13 - RUNTIME-PREP-004 - Runtime evidence proof-chain hardening (`no version bump`)

- Status: `STATIC_PASS; LOCATION_GUARDS_HARDENED; SAFE_PROBE_CONFIGURED_NOT_LAUNCHED; PENDING_EXPLICIT_LAUNCH_PERMISSION; R5_EXTERNAL_FIXTURE_REQUIRED`。
- Scope: 在不启动 EU4、Launcher、dowser 或 observer 的前提下，修复 acceptance userdir 位置链剩余风险，并把 PROBE、R1-R12 与非运行 R13 的 executable/argv、canonical roots、artifact 格式与角色、人工断言、fixture、跨 phase 输入、oracle、parent lineage 及不可覆盖结果收敛为 schema-4 机器可审计证据链。
- Baseline finding: schema-3 collection 只证明 snapshot/config/fresh-log/后缀计数卫生，不能证明矩阵人工结论；任意 daily decoy、纯文本伪 `.png/.eu4`、未关联的 phase save 或缺失 fixture execution 仍可误得 collection gate。现有未运行 R1 session `20260713T154227Z_r1_6e237503` 仅保留为 dry/superseded 基线，无 active lock/seal，不得兼作 protocol probe 或正式 R1 证据。
- Location/protocol closure: Windows Documents 改为 Shell 当前 `FOLDERID_Documents`（只用 `KF_FLAG_DONT_VERIFY`，不再误取 default path），repo/game/daily/safe 四根固定为 `C:\Users\meizhanxuan\Documents\GitHub\JapMod`、`D:\Steam\steamapps\common\Europa Universalis IV`、`C:\Users\meizhanxuan\Documents\Paradox Interactive\Europa Universalis IV`、`C:\Users\meizhanxuan\Documents\JXP_Acceptance`；全部目录祖先拒绝 symlink/junction/reparse，session 只允许 recorded canonical evidence root 的直接子目录。旧含空格减号根继续以 `DO_NOT_USE_AS_USERDIR.txt` 标为历史禁用；helper 全部生产入口会拒绝它。
- Exact roots/pins: preflight 重新确认 EU4 `1.37.5.0 Inca (491d)` 的 `eu4.exe`、空 `userdir.txt`、`launcher-settings.json` 与九个 gameplay 文件共 `12/12` 匹配；daily 根由 pinned launcher `gameDataPath` 与 Known Folder 双向确定，四根及全部祖先现场无 reparse。唯一准许运行参数保持 pinned executable 加单个小写非重复 `-userdir=C:\Users\meizhanxuan\Documents\JXP_Acceptance`；`observe-process` 必须从实际 Win32 process 读取并按 `CommandLineToArgvW` 精确比对，工具没有 launch surface。
- Safe-root state: 7/7 根级 `DEBUG_FIXTURE_SETUP` 文件逐字节/manifest/UTF-8/no-BOM 验证安装；新增 church/burgher 缺失负向只能从同一 otherwise-eligible R8 parent save 各自分叉。旧隔离 `dlc_load.json` 键顺序已只在 safe root 内迁移，schema-4 `configure-playset PROBE` 收据固定 current main `0d908ff8ae38...` 后 current map `9aa1589ffd69...`、`disabled_dlcs=[]`；oracle/toolchain 收口后仅在 safe root 重签，收据内部 `receipt_sha256` 字段为 `34caa7ca36d360339ca985d6ca6c351d84e4f3a8ca47b59e8853897cf507d4b3`，收据文件 SHA-256 为 `efdf6fdb76a39af8fb8ce2c6f709218fffaf6652bb03cf5d301011e2bf9b363d`。daily Launcher 配置未改，daily `mod` acceptance 条目为 0，无 active session/process。
- Schema-4 evidence: `before-session` 必须携带用户明确启动许可引用，并封存 12 pins、Git-object 重建 payload、exact playset/DLC、完整 daily VFS、受限 isolated surfaces、输入/父 collection/fixture、session 与 manifest seal；`observe-process` 是唯一运行中写入。`collect` 要求 canonical manifest、全部 exact named roles、terminal PASS/FAIL/BLOCKED attestation、完整 supporting-role union、fixture before/after save 与 parent hash closure；`abort-session` 只在进程停止后写 sealed abort 并安全释放 nonce lock。矩阵共 17 个 phase/closure contracts、335 个 artifact roles、71 个 assertions（其中运行协议 65、R13 6）、34 个 parent roles、15 个 input roles、8 次 fixture uses。
- Artifact decoders: screenshot 不再只认 magic/后缀；PNG 验 CRC/chunk/filter/zlib/palette/index，JPEG 验 DQT/DHT/SOF/SOS table binding 并经 Windows GDI+ 全像素解码，BMP 验 DIB/compression/palette/bitfield/pixel array 并全解码，TGA 验 raw/RLE 与精确像素数。`.eu4` 拒绝 token/header spoof、非有限/重复 JSON、ZIP traversal/encryption/bomb/任意 member，并验证 text Clausewitz 平衡与 canonical fields 或 binary token/meta framing；真实 3840x2160 PNG、binary/text EU4 ZIP 与大 text autosave 样本均通过。
- R12 oracle: 新增 deterministic generator 与 strict `oracle_contract.py`；pack schema `jxp_runtime_oracle_pack/v1`、SHA-256 `8a2141cd4c1cc94d729d539d47f01db5e636fb1c206b2393fe9aaf253973ad22`，固定 main 12 + map 180 + vanilla 66 = 258 个 live source pins 与 semantic matrix SHA-256 `730bf1c7f0ec03b7be0827a5ddb641254cc8d2bc3881cf279c58610625cadcd5`，其中可部署 runtime-member 子集另与 candidate Git snapshot 交叉验证。282 typed cases（88 render、12 bookmark、45 boundary、6 slider、37 event、5 origin、88 unification、1 lifecycle）严格展开为 19 roles / 697 evidence bindings；五个 typed checklist 必须逐 case PASS、UTC reviewer、exact pointer/object hash 与非空 observed，live source、deployable candidate subset、session copy 及 collect 时重验闭合。
- R13 closure: `close-release` 是独立非运行路径，要求 16 个 READY parent collections、10 个 distinct strict semantic JSON artifacts 与 separate six-assertion manifest；assertion-result 必须精确展开 65 个 parent PASS，lineage 必须覆盖 collection/session/contract/artifact/assertion/snapshot/input/upstream-parent/fixture/oracle hashes。六类 v3 gate declaration 不再是通过依据：每次首次或 replay 都当场以固定 argv、`shell=False`、WinAPI 系统路径、显式 nested PowerShell、完整最小环境和前后 process/payload/toolchain guard 执行 7 个静态进程，拒绝 game/Launcher/dowser/bootstrapper/`-userdir`/skip-main argv。v2 toolchain 另把工具输入与独立 `toolchain_revision` 的完整 Git HEAD 精确树绑定（tracked drift 与 ignored/untracked 一律拒绝），installed skill 必须等于 Git-derived repo skill；Git 外 Python/stdlib/DLL/Windows PowerShell modules/cmd/Git/quick validator/NumPy/Pillow/PyYAML 则逐字段匹配 Git-tracked approved baseline。Python 子进程统一经 `-I -S -B` runner，stdlib 在前、Git validator roots 居中、仅三份 distribution exact files 的临时副本在后，caller site/`.pth`/cwd/`PYTHONPATH` 无导入权。execution 封存完整 effective env、stdout/stderr base64、size/framed hash、cwd/UTC/exit/marker proof；输出在双 pipe drain 过程中即限制单进程 1 MiB、总计 4 MiB，11 份 closure input 在解析/复制前共享 8 MiB，staged/replay 整树限 32 MiB。replay 重新执行当前 gates 作为授权、独立复验历史 seal 且绝不覆盖。canonical ledger v2 receipt 只接受唯一真实 Update Journal heading 下唯一 exact `jxp-r13-journal-json` object；只把 CommonMark LF/CRLF/CR 当换行，控制/Unicode 伪分隔、reserved-info alias、Markdown fence 内伪 heading/block、未闭合 fence、duplicate 与 raw HTML 均 fail closed，并逐字段 exact-type 绑定 status/candidate/matrix/parent lineage/16 ordered parent hashes/blockers/no-game/no-overclaim/UTC 与 entry hash。daily receipt 复核真实 final VFS；12 项 automated results（parent + 10 artifacts + manual manifest）由验证结果计算，不能无条件写 true。R13 有任何 matrix blocker 时在 parent seal/gates/output 前 fail-fast，不生成 blocked closure。
- Evidence: acceptance helper `52/52` 通过（新增 CommonMark separator/fence alias、nested bool→int replay、Git tracked/untracked/ignored drift、streaming stdout/stderr/timeout、aggregate input/whole-tree cap、exact skill-script allow-list 对抗测试）；isolated runner 已在 safe root 临时目录实测 Python `3.13.1` 与 NumPy/Pillow/PyYAML `2.4.2/12.3.0/6.0.3`，随后安全清除临时目录。oracle byte-for-byte `--check`、主模组门禁及不带 `-SkipMainModValidation` 的联合 map/history/content/compat/assets 门禁均通过；repo/installed `eu4-modding` skill 验证且镜像一致；`git diff --check` 通过。v2 clean-HEAD 全受控 gate 按设计只能在本 ledger 与 baseline 提交后执行，其结果由 sealed execution/handoff 承载而不反写受守护输入，避免用修改证据文件来追认自身。
- Guardrails/TODO: runtime payload candidate 保持 `2bf24123e41f86324cfc6b9780b9a89cd3919c6e` 不变；没有启动 EU4、Launcher、dowser 或 observer，没有执行 `before-session` 或创建 PROBE session，没有新增 `RUNTIME_PASS` 或伪造外部 R5 fixture。当前 matrix 中 R5 `r5_authentic_pre0242_fixture_unavailable` 与其 R13 parent blocker 会有意阻止 READY R5，并使 `close-release` 在无输出前拒绝；取得真实旧档后必须经 review 更新两项 blocker，并在新 matrix SHA 下重跑 PROBE/R1-R12，旧 collection 不得跨 hash 重标。全部 Active TODO status/owner 暂不改变。

### 2026-07-13 - RUNTIME-PREP-003 - Safe userdir, deterministic fixtures, and route-loop hardening (`no version bump`)

- Status: `STATIC_PASS; SAFE_ROOT_REDEPLOYED_NOT_LAUNCHED; PENDING_USER_APPROVAL; R5_EXTERNAL_FIXTURE_REQUIRED`。
- Scope: 在不启动 EU4、Launcher、dowser 或 observer 的前提下，修复 acceptance userdir 位置歧义，穷尽 pre-0.24.2 真实 fixture 来源，加固 playset/DLC/日常配置证据链，并收紧 R7 WAK 与 R8 IJP 的十年 charter 生命周期和负向 gate。
- Userdir protocol: pinned `eu4.exe` SHA-256 为 `9AD3EFE1AF169F40EE577F9DAE5DEBBC87AF6FB8B5450FB345EBF110DC4D771A`，空 `userdir.txt` 为 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`。静态逆向证明旧 `Documents/Paradox Interactive/Europa Universalis IV - JXP Acceptance` 会因空格后的 `-` 被截断到日常根；新 canonical 根固定为无空格普通目录 `C:\Users\meizhanxuan\Documents\JXP_Acceptance`，helper 拒绝非 ASCII、空白、quote 及非 canonical fixture 目标。旧根仅保留历史内容并写有 `DO_NOT_USE_AS_USERDIR.txt`；没有将其重新用于验收。
- Tooling: `preflight` 现固定 2 个协议文件与 9 个玩法文件；session/collection schema 升至 3。`configure-playset` 在进程停止、版本/组件/revision/dependency/phase 全部精确匹配后，只原子写隔离根 `dlc_load.json`，R11 使用 pinned Mandate of Heaven disabled mask；`before-session` 记录日常两个配置文件的 size/mtime/SHA-256，`collect` 同时要求隔离配置精确相等和日常 hash 不变。`install-fixtures` 只接受 canonical 根，先全量 conflict preflight，再 staging + no-clobber hard-link commit；partial copy、末项冲突及中途 commit 故障均无目标/temp 残留。
- Runtime setup fixtures: 新增 5 个 UTF-8/no-BOM、manifest 固定 hash 的根级 `run` effects，覆盖 R4 0.25 天子准备、R6 四类受保护转教目标、R8 no-heartland/restore-heartland 与 R10 foreign-emperor same-unlock。全部只能标注 `DEBUG_FIXTURE_SETUP`，发布 payload whitelist 排除 `tools`，不得据此声称自然历史、事件 cadence、真实任务奖励或正常状态形成。
- Gameplay hardening: IJP route 明确要求 Shinto；commons 同时要求 church/burgher estate 存在且 loyalty 分别不低于 40/35。WAK/IJP active trigger 与各自 3650-day charter 绑定，canonical start 在 day 3651 调度 generation-safe expiry；旧 timer 遇到新 charter 必须 no-op，route/religion/disaster/charter 失效由隐藏清理闭合。矩阵改为验证 estate presence + loyalty，并区分旧代清零与合法新代成套状态，不再把 MTTH 1 day 或随机 observer milestone 误写成固定结果。
- Fixture search: 扫描 719,834 个唯一文件、220 个 `.eu4`、4,055 个有效 ZIP、113 个其他 archive、5,542 个 UnityFS bundle、33 个本地 Workshop Mod，以及全部可达本机/Git/GitHub/cloud/browser/recycle/recent 来源，JXP pre-0.24.2 命中为 0。真实线索仅存在旧机：`jxp_phase_report_0_23_1_mission_renderer_hotfix.md` 记录 ZIP 1/2，`jxp_phase_report_0_23_2_government_reform_visibility_hotfix.md` 记录 ZIP 3 与旧 autosave，`jxp_phase_report_0_24_1_runtime_state_hotfix.md` 记录目标 serialization；R5 继续等待外部原件，禁止伪造。
- Candidate/deployment: runtime payload 固定提交 `2bf24123e41f86324cfc6b9780b9a89cd3919c6e`。新安全根中的 current-main 指纹为 `0d908ff8ae38f079950ebefc3db6929c0a803705ba4eb7478244818abd86a04b`（376 files），current-map 为 `9aa1589ffd6991359c0be969f8b217ebe8feaa7a4c7b3f2d4c143c68c1c56e30`（239 files）；legacy-025 `ce3648eda2d11eebb97333cd0256a3d54bbf6556f5c27cf7feafd0387f366337`（294 files）与 legacy-027 `51067cab6acbe9914d8d1b995ad79392a2212ae17dd812ae79de634367adb015`（356 files）仍为精确普通快照。日常 `mod` 根 acceptance 条目为 0。
- Baseline: R1 隔离配置只启用新 main+map descriptors，SHA-256 为 `473BE71D84F7CEC93E49A3E59304695E4D32AE89FB1D29A38828A547006F1995`；schema-3 before-session 位于 `C:\Users\meizhanxuan\Documents\JXP_Acceptance\jxp_runtime_evidence\20260713T154227Z_r1_6e237503`。它记录日常 `dlc_load.json` 为 86 bytes / `BD29774AF54FFFB7804E72DAD37C4BAE5AB370E42413768878F846C217106404`，`launcher-v2.sqlite` 为 118784 bytes / `131EEF30058C5AABA7250463E0EE6994B106850A685AEE4F01AA779F80E2D3C5`；基线后只读复核仍完全一致。
- Evidence: pinned preflight `11/11`；主门禁 `26/26`、Clausewitz `250/250`、主单测 `221/221`；R7/R8 定向 mutation `39/39`；acceptance helper `19/19`；5/5 fixture Clausewitz parse/hash/UTF-8/no-BOM 通过；联合 map/history/content/compat/assets 门禁 `0 errors / 0 warnings`，覆盖 120 profiles 与全部 137,382 个可选日期。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser 或 observer，没有新增 `RUNTIME_PASS`；真实 VFS 探针与 R1-R12 仍待用户明确启动许可。全部 Active TODO status/owner 保持不变；R5 原件未取得前 `JXP-002` 不得关闭。

### 2026-07-13 - RUNTIME-PREP-002 - Runtime evidence integrity and matrix hardening (`no version bump`)

- Status: `STATIC_PASS; ISOLATED_REDEPLOYED_NOT_ENABLED; PENDING_USER_APPROVAL`。
- Scope: 仅加固 `tools/jxp_runtime_acceptance/` 的 README、helper、R1-R13 场景矩阵与测试；未改玩法、地图、descriptor 版本或 release content。
- Snapshot correction: 审计发现 `RUNTIME-PREP-001` 的递归 `gfx` 白名单包含 `source` / `preview` / `backup*` 开发目录，当前主快照还包含 Git 忽略的 `gfx/flags/source/__pycache__/build_toyotomi_flag.cpython-313.pyc`。旧主 `d184753285c7...`、旧地图 `29dcb6e01d93...`、旧 0.27 主 `e7df9d31a951...` 的内容 hash 虽自洽，但不能从所记录 Git revision 重现，故其历史部署记录保留但 acceptance-evidence 资格撤销；核对 owned marker、descriptor path、目标根与全部 reparse 状态后，三套旧 payload/descriptor 已从日常 `mod` 目录安全退役。
- Tooling: runtime manifest 现排除 source/preview/backup、构建脚本、源图与 bytecode，并拒绝 Windows drive/UNC/backslash、archive escape、symlink 与 junction；部署复用及 `before-session` 强制核对 exact marker、canonical owned path、manifest/file set、逐文件 hash、clean 40-char source revision、component/version/dependency/phase。当前场景绑定候选提交 `028e667a12c3ab24f539b492a1b1da0afaa0ac4d`；session schema 2 拒绝旧/缺字段记录，R13 只允许发布收口而不能伪装游戏会话。`collect` 只扫描本 session 实际变化的 fresh logs，复核 payload/playset/场景 DLC 的全部观测状态，并只以不同且 fresh 的 screenshot/save 满足最低数量；clean collection gate 仍不替代人工 UI/引擎断言。
- Matrix: R4 新增真实 `0.25.0`（`6e461e2e47a839a77b2e376ce61ceb317d393320`）与 `0.27.0`（`8a5962628014e696bda764bcad10bfd3faee188e`）生成阶段及 current migration 阶段；R6 拆分新地图局与真实旧 CJP 档；R3/R7/R8/R9/R10/R11/R12 补齐 capstone 清理、双 1825-day 周期、负向 gate、正式任务事件接线、日期选择边界、同基线 AE、DLC log 状态、88 省统一及全年运行合同。R5 继续只接受外部真实 pre-0.24.2 fixture，禁止合成或改旗伪造。
- Deployment: 候选提交 `028e667a12c3ab24f539b492a1b1da0afaa0ac4d` 的 current-main `e2708062178e01cc2d0337ac34c37ef6f33ed952916d9e93de9e284343021845`（376 files）与 current-map `1a89f41ae351e29c9d851d64598407801ce893fd2b9fed4af224a52211bbd01f`（239 files），以及 legacy-025 `ce3648eda2d11eebb97333cd0256a3d54bbf6556f5c27cf7feafd0387f366337`（294 files）和 legacy-027 `51067cab6acbe9914d8d1b995ad79392a2212ae17dd812ae79de634367adb015`（356 files）已作为普通目录部署到专用 `Documents/Paradox Interactive/Europa Universalis IV - JXP Acceptance` 根且未启动、未启用到日常配置；全部 current manifest 文件受 Git 跟踪且开发材料为 0。隔离根另保存 current main+map、current main、MoH-disabled current main、legacy-025 与 legacy-027 的精确 `dlc_load` 模板。
- Configuration safety: 部署和旧快照退役后，默认 `launcher-v2.sqlite` SHA-256 仍为 `131EEF30058C5AABA7250463E0EE6994B106850A685AEE4F01AA779F80E2D3C5`；默认 `dlc_load.json` 仍为中文补丁 + GMI，SHA-256 `BD29774AF54FFFB7804E72DAD37C4BAE5AB370E42413768878F846C217106404`；日常 `mod` 目录中的 acceptance 条目为 0。
- Evidence: pinned preflight `9/9`；主门禁 `26/26`、Clausewitz `250/250`、主单测 `211/211`、acceptance helper `13/13`；联合 map/history/content/compat/assets 全部 `0 errors / 0 warnings`；current runtime manifests 为主 376 / 地图 239 files，Git-tracked 100%、development material 0。
- Runtime: 未启动 EU4、Launcher、dowser 或 observer；`userdir` 隔离语法仅有静态二进制证据，仍待用户明确许可后的协议探针，因此没有新增 `RUNTIME_PASS`。
- TODO: `JXP-001` / `002` / `004` / `005` / `008` / `009` / `010` / `017` / `018` / `020` / `022` / `023` 全部保持 `IN_PROGRESS / CODEX_ROOT`；`JXP-016` 保持 `IN_PROGRESS / PROJECT`。R5 外部 fixture 未取得前，`JXP-002` 不得关闭。

### 2026-07-13 - RUNTIME-PREP-001 - Deterministic acceptance preparation (`no version bump`)

- Status: `STATIC_PASS; DEPLOYED_NOT_ENABLED; PENDING_USER_APPROVAL`。
- Scope: `CODEX_ROOT` 为 `JXP-001` / `002` / `004` / `005` / `008` / `009` / `010` / `017` / `018` / `020` / `022` / `023` 建立 R1-R13 去重运行矩阵、不启动游戏的 pinned preflight、普通目录快照部署、playset 隔离守卫、fresh log/screenshot/save 归档与 blocker 扫描；`JXP-016` 继续承担最终收口。
- Debug reliability: 修复 `jxp_debug_return_jap_baseline_effect` 的“先初始化后清标记”顺序错误并补 `TOY -> JAP`；新增 Hakko 天朝身份 scaffold 与 ODA 丰臣正式决议前置 scaffold。两者均由静态合同禁止伪造任务解锁、改革通过或 `ODA -> TOY` 正式转换。
- Tooling: 新增 `tools/jxp_runtime_acceptance/`；CLI 只有 `preflight` / `deploy` / `before-session` / `collect`，没有 launch 命令，且不写 `launcher-v2.sqlite` / `dlc_load.json`。部署 payload 白名单排除 tools、dev_logs、localisation_source、源图与备份，外层 descriptor 在完整复制和逐文件 SHA-256 验证后最后写入。
- Environment: 已只读确认 `launcher-settings.json` 为 EU4 `v1.37.5.0`，用户数据根为 `Documents/Paradox Interactive/Europa Universalis IV`；部署前无 JXP 本地 descriptor，当前日常 playset 仍只启用中文补丁与 Graphical Map Improvements，正式验收必须另建排除二者的专用 playset。
- Legacy fixtures: 已证明不可变提交 `8a5962628014e696bda764bcad10bfd3faee188e` 是可生成十状态真实输入的 `0.27.0`；最早完整源码仅到 `0.25.0`，仓库和本机存档均无 pre-0.24.2 JXP fixture，因此明确记录外部证据缺口而不合成假档。
- Deployment: 干净提交 `839af69bf4fe40607c7411f7f591b4e0c557ad77` 的当前主 `0.28.0` 普通快照 `d184753285c7edbd82e4310a18fdb01ad28d4fd09a1797fbdf1c51e0116bd9f5`（467 files）、地图 `0.1.3-alpha` 快照 `29dcb6e01d93ffc4dd40785d296a3ce7623f5e0dd42f1cfca47eb3c1d215f84c`（361 files）、旧版主 `0.27.0` 快照 `e7df9d31a9519a8c28216483f706dea3f4ac30ec27a614c7dffeb7a9d107b22d`（446 files）已放入用户 `mod` 目录但未启用；三者均为普通目录，无 link/junction。已验证并删除仅用于提交前核对的两个 `+dirty` 临时 current 快照。
- Configuration safety: 部署后 `launcher-v2.sqlite` 仍为 2026-02-09 文件，SHA-256 `131EEF30058C5AABA7250463E0EE6994B106850A685AEE4F01AA779F80E2D3C5`；`dlc_load.json` 仍为原中文补丁 + GMI，SHA-256 `BD29774AF54FFFB7804E72DAD37C4BAE5AB370E42413768878F846C217106404`。
- Evidence: pinned preflight `9/9` vanilla hashes；主门禁 `26/26`、Clausewitz `250/250`、主单测 `211/211`、acceptance helper `7/7`；联合 map/history/content/compat/assets 全部 `0 errors / 0 warnings`；联合 inventory `498 events / 289 decisions / 385 scripted callables / 918 modifiers`；state safety `538 country flags / 8 province flags / 918 modifiers / 4 disasters / 0 failures`；历史连续 `137,382` 天。
- Runtime: 未启动 EU4、启动器或 observer；当前 descriptor 仅 `DEPLOYED_NOT_ENABLED`，没有任何新运行时证据。
- TODO: 所有运行时项保持 `IN_PROGRESS / CODEX_ROOT`；获得明确启动许可并实际完成对应 R 批次前，任何一项都不得改为 `DONE`。

### 2026-07-10 - RELEASE-028 - Pacific, regional, writing, and final-state politics (`0.28.0` + `0.1.3-alpha`)

- Status: `STATIC_PASS; PENDING_RUNTIME`。
- Scope: 收紧八纮一宇 CB 的日本身份门槛并固化原版 1.37.5 天命合同；新增四支太平洋网络、对马/濑户内/琉球语义地域链、22 个低频事件代价选项，以及十种统一状态的唯一权力结构、政治 capstone 与旧档同步接线；地图伴随任务同步扩为 33 项。
- Cross-review fixes: 地域事件改为同步写锁后次日触发，五年复议先清理六种旧结果；California/对马修正去除与既有内容相同的机械签名，防止同日双排队、政策重叠与奖励克隆。
- Evidence: 主门禁 `26/26`、Clausewitz `250/250`、单元测试 `208/208`；地图联合门禁全项 `0 errors / 0 warnings`；主/联合任务 `288 / 321`；联合内容 `498 events / 287 decisions / 383 scripted callables / 918 modifiers`；state safety `538 country flags / 8 province flags / 918 modifiers / 4 disasters / 0 failures`；历史连续 `137,382` 天。
- Runtime: `PENDING_USER_APPROVAL`；未启动 EU4、启动器或 observer；天命 CB/和约/AE、政府 UI、旧档迁移、任务次日切换、路线转换与长期节奏仍待游戏内验收。
- TODO: `JXP-011` / `JXP-012` / `JXP-013` 改为 `DONE`；`JXP-010` / `JXP-022` 保持 `IN_PROGRESS` 等待运行时证据；`JXP-016` 继续由 `PROJECT` 维护。
- Evidence report: `jxp_phase_report_0_28_0_pacific_regions_and_final_states.md`。

### 2026-07-10 - BACKLOG-BATCH-FINAL-STATIC - Remaining static backlog (`no version bump`)

- Status: `IN_PROGRESS; PENDING_RUNTIME`。
- Scope: `CODEX_ROOT` 领取 `JXP-010` / `JXP-011` / `JXP-012` / `JXP-013` / `JXP-022`；并行审计天命/CB/DLC fallback，扩展海外与地域循环、低频事件选项，以及十种终局统一状态的权力结构与任务深度。
- Runtime: 继续保持 Steam 游戏根只读，不启动 EU4、启动器或 observer；需要游戏内证明的 acceptance 仍保留 `PENDING_USER_APPROVAL`。
- TODO: 上述五项进入 `IN_PROGRESS / CODEX_ROOT`；子 agent 不直接编辑本总账。

### 2026-07-10 - RELEASE-027 - Identity, loops, parity, and state safety (`0.27.0` + `0.1.2-alpha`)

- Status: `STATIC_PASS; PENDING_RUNTIME`。
- Scope: 新增丰臣独立身份与 1586–1615 主/地图历史链；完成 68 大名理念/身份任务矩阵与中文姓名；将灾难扩到 4 个；补齐九路线原生循环和时代属性互动；完成 WAK/IJP 压力循环；把联合 flag/modifier lifecycle 审计从 246 项失败降到 0；重建主、地图与联合静态可视化。
- Evidence: 主门禁 `21/21`、Clausewitz `234/234`、单元测试 `142/142`；地图联合门禁全项 `0 errors / 0 warnings`；state safety `535 country flags / 6 province flags / 887 modifiers / 4 disasters / 0 failures`；68 tags / 272 profiles；137,382 天历史连续；skill validator 通过。
- Runtime: `PENDING_USER_APPROVAL`；未启动 EU4、启动器或 observer；WAK/IJP 节奏、TOY 迁移、理念/政府 UI 与 fresh log 仍待运行时验收。
- TODO: `JXP-006` / `JXP-007` / `JXP-014` / `JXP-015` / `JXP-019` / `JXP-021` 改为 `DONE`；`JXP-008` / `JXP-009` / `JXP-018` / `JXP-020` / `JXP-023` 保持 `IN_PROGRESS`；`JXP-016` 继续由 `PROJECT` 维护。
- Evidence report: `jxp_phase_report_0_27_0_identity_loops_and_safety.md`。

### 2026-07-10 - BACKLOG-BATCH-IJP - Ikko commonwealth loop (`no version bump`)

- Status: `STARTED; STATIC_BASELINE_PASS`。
- Scope: `CODEX_ROOT` 领取 `JXP-009`；在四灾难合同与全局状态安全门禁闭合后，补齐一向宗压力、寺社町众治理、共同体收益/代价和退出循环。
- Evidence: 四灾难合同 `4/4`，state safety `0` hard failures，主门禁 `17/17`；未启动 EU4 或启动器。
- Runtime: `PENDING_USER_APPROVAL`；本批次只做静态实现与联合验证。
- TODO: `JXP-009` 进入 `IN_PROGRESS / CODEX_ROOT`；子 agent 不直接编辑本总账。

### 2026-07-10 - BACKLOG-BATCH-EXPAND - WAK and all-daimyo coverage (`no version bump`)

- Status: `STARTED; STATIC_BASELINE_PASS`。
- Scope: `CODEX_ROOT` 领取 `JXP-008` 与 `JXP-019`；在丰臣、姓名、路线与灾难切片收拢期间，并行实现倭寇长期循环并建立主/地图全部可选大名的理念、身份任务与强度分层合同。
- Evidence: 当前主门禁 `16/16`；丰臣定向测试 `4/4`、路线定向测试 `6/6`；未启动 EU4 或启动器。
- Runtime: `PENDING_USER_APPROVAL`；本批次只做静态实现与联合验证。
- TODO: `JXP-008` / `JXP-019` 进入 `IN_PROGRESS / CODEX_ROOT`；子 agent 不直接编辑本总账。

### 2026-07-10 - BACKLOG-BATCH-START - Route, safety, names, and Toyotomi audit (`no version bump`)

- Status: `STARTED; STATIC_BASELINE_PASS`。
- Scope: `CODEX_ROOT` 领取 `JXP-006` / `JXP-007` / `JXP-014` / `JXP-015` / `JXP-018` / `JXP-021`；并行审计九路线与时代属性、灾难和状态清理、全日本姓名汉化，以及丰臣身份/历史迁移链。
- Evidence: 前一静态切片提交 `3f38f37`；主门禁 `13/13`、Clausewitz `180/180`、单元测试 `67/67`；地图联合门禁全项 `0 errors / 0 warnings`，工作树在领取前干净。
- Runtime: `PENDING_USER_APPROVAL`；审计与实现阶段不启动 EU4 或启动器。
- TODO: 上述六项进入 `IN_PROGRESS / CODEX_ROOT`；子 agent 不直接编辑本总账。

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
- 这些报告保留历史价值，但任何与当前 0.28.0 架构冲突的实现描述均由后续报告和本总账 supersede。
- Evidence: Historical Report Index 中 0.4.1-0.21.2 全部阶段报告。

## Historical Report Index

下列文件全部保留为历史证据。验证器要求两个 `dev_logs` 目录中除本总账外的每个文件都出现在本索引中。

### Main Mod Reports

- `jxp_0_22_0_working_plan.md` - 0.22.0 集成工作计划。
- `jxp_0_26_0_route_attribute_parity_audit.md` - 0.26.0 九路线与时代属性深度审计。
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
- `jxp_phase_report_0_27_0_identity_loops_and_safety.md` - 0.27.0 丰臣/大名身份、路线循环、灾难与状态安全收口。
- `jxp_phase_report_0_28_0_pacific_regions_and_final_states.md` - 0.28.0 太平洋、地域风味、事件写作与终局政治静态收口。
- `jxp_state_disaster_safety_audit_2026_07_10.md` - 运行时状态生命周期、灾难触发与调试清理静态审计。

### Companion Map Reports

- `BASELINE_LOCK.txt` - 地图版本、ID、发展、像素、历史与兼容硬锁。
- `jxp_map_date_slider_audit_0_1_0.md` - 0.1.0 全日期滑块历史审计。
- `jxp_map_implementation_report_0_1_0.md` - 0.1.0 八十八国地图实施报告。
