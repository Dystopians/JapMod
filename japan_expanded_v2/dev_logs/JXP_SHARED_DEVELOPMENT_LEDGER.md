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

- Ledger schema: `2`
- Last updated: `2026-07-17`
- Main Mod version: `0.28.1`
- Companion Map version: `0.1.4-alpha`
- Pinned game: `EU4 v1.37.5.0 Inca (491d)`
- Supported version: `v1.37.5.0`
- Runtime acceptance: `PENDING_USER_APPROVAL`
- Runtime candidate: `80637e065881f0bac4fd424e0c6100c19e8f5da7`
- Runtime matrix SHA-256: `7982e496a9b09c34b4fcd017633a3752ae4de6a9d6fc649badda059d552219e2`
- Host portability: `READY`
- R5 fixture status: `ADMITTED`
- Runtime matrix blockers: `NONE`
- Next executable step: `PREFLIGHT`
- Main static gate: `29/29 checks; 434/434 Clausewitz files; full validation suite 448/448`
- Acceptance-helper source-host proof: `73/73 runtime/oracle unit tests`
- Current-host acceptance helper: `73/73; candidate pin and rebuilt oracle source are current`
- Candidate preflight: `PASS on control 42e1bd3...fa4057a7; candidate ancestry, clean worktree, runtime diff and 12/12 pins verified; repeat after the ledger-only successor before any further deploy`
- Deployed payload manifests: `acceptance current/current-main remains 80637e0: main 411 / 1e4f3540...6594, map 244 / fcd80cd2...4a75; daily runtime is f687ca1: main 630 runtime files / 27781bed...8b0 plus three review artifacts, map 252 / 1016c2ed...fe6`
- Combined static gate: `current f687ca1 slice passes the full no-skip map/history/content/main-compatibility/assets/oracle/main/unit gate at 0 errors / 0 warnings and all 137382 selectable days`
- Main missions: `757 mission IDs; 132 custom series; 196 effective profiles`
- Main ideas: `493 unique groups in one exact-path runtime registry; 50 primary groups plus 31 companion-tail groups`
- Combined missions: `1049 mission IDs; 185 series; 120 companion tag/DLC profiles`
- Combined content inventory: `1126 events; 331 decisions; 829 scripted callables; 1484 modifiers`
- State safety: `752 country flags; 9 province flags; 1484 modifiers; 4 disasters; 0 failures`
- Companion geography: `88/88 japan_region provinces; 137382 selectable days; 299 owner intervals; 70 subject intervals`
- Localisation: `92 active UTF-8-BOM files; 0 raw CJK; 0 missing combined mission localisation keys`
- Daily compatibility profile: `Chinese base -> local JXP-compatible supplementary -> main -> map`; daily runtime payload `f687ca1286c88fd5431d0580b9f1e41b819c5363` and compatibility payload `8397ca4b...fcea` are deployed; 73 external providers converge across 74 colliding paths with 0 divergent providers and 0 stale deployed files, but this daily payload is not yet a matrix-bound runtime candidate

## Live Execution State

This section is the short operational handoff. It never upgrades static evidence to runtime evidence and must be updated whenever host, matrix, fixture, or execution order changes.

### Current Machine

- Repository: `C:\Users\Fiber Memory\Documents\GitHub\JapMod-agent-a`
- Working branch: `codex/content-agent-a`
- Reviewed baseline revision: `3c6f4ead9787fc001ffb6e8d5bd38656da7ac7ff`
- Game root: `D:\Steam\steamapps\common\Europa Universalis IV` (read-only)
- Daily user-data root: `C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV`
- Isolated acceptance root: `C:\JXP_Acceptance` (candidate 80637e0 current main+map and current-main snapshots are deployed but not enabled; do not launch)
- R5 escrow root: `C:\JXP_R5_Escrow\20260713_original_machine`
- Launch authorization: `REQUIRED_BEFORE_NEXT_EU4_START`; the prior single-launch authorization was consumed by the superseded runtime attempt, so no agent may start EU4 again without a new explicit user instruction.
- Production integration worktree: `C:\Users\Fiber Memory\Documents\GitHub\JapMod` still contains unrelated uncommitted map-builder/map-validation work. It is preserved byte-for-byte and must not be reset, overwritten, merged through, or included in this candidate before its owner commits it independently.
- External runtime observation: the user launched and played the daily profile again at approximately `2026-07-14 20:02-20:07`; no agent process control occurred. Fresh unsealed `setup.log` exposed only the 25 selectable groups from `00_basic_ideas.txt` and omitted `MRI_ideas`, `TOY_ideas`, and every final-route group, while `error.log` recorded `Missing Icon 'national_idea8'`. The screenshots independently show MRI and TOY falling back to generic ideas. These logs diagnose the superseded broken deployment only and are not acceptance evidence for the repaired bytes.

### Immediate Execution Queue

1. Immutable payload `80637e0...e8f5da7` and control plane `42e1bd3...fa4057a7` remain the last acceptance-bound candidate; `C:\JXP_Acceptance` still contains those snapshots and they are not enabled.
2. Daily Documents contains merged A/B payload `f687ca12...c5363` plus the rebuilt 73-provider compatibility clone; the isolated acceptance root still contains only candidate `80637e0`.
3. Before any runtime evidence, form a new two-stage candidate/control plane around `f687ca12...c5363`; the existing acceptance candidate must not be relabelled as containing the daily payload.
4. Stop before runtime after deployment: a new explicit authorization is required before any EU4 process is started. JXP-002/022/023 old-save convergence and all UI/runtime assertions remain `IN_PROGRESS`.

Daily payload `f687ca1286c88fd5431d0580b9f1e41b819c5363` contains the merged Agent A/B internal, religious, colonial and continental systems plus the Japanese start-screen chronicles. The validation closure restores the Shinshu crisis's generated fifth stage, preserves stage-gated progression and terminal cleanup in the authoritative generator, and updates final-state mutation anchors for ROOT-scoped Buddhist-aware triggers. It is deployed and statically audited, but it is not yet runtime-proven and does not replace the acceptance matrix candidate until a new two-stage candidate is formed.

The daily deployment is present only in Documents; `C:\JXP_Acceptance` remains pinned to `80637e0`, and no runtime/UI evidence has been collected for the new balance bytes.

### Handoff Delta

- The immutable 0.28.1 payload is `80637e065881f0bac4fd424e0c6100c19e8f5da7`; every future runtime session must bind it through a fresh clean control-plane preflight before evidence collection.
- The daily deployment is now runtime payload `f687ca12...c5363`: main `630 runtime files / 7,754,132 bytes / fingerprint 27781bed...8b0` plus three review artifacts, and map `252 runtime files / 82,963,384 bytes / fingerprint 1016c2ed...fe6`. The immediately superseded main/map directories are preserved at `mod/_jxp_backups/20260717_171443_f687ca1`.
- The checked-in runtime oracle remains byte-current for this payload. Runtime acceptance still requires a new matrix-bound two-stage candidate/control plane; the daily deployment alone is not reusable R1-R13 evidence.
- The isolated acceptance deployment is current for payload 80637e0: main `411 files / fingerprint 1e4f354011129db0a080250f63c194e16873e9aa412f7acfa3b8a7171bac6594`, map `244 files / fcd80cd21a817d158ceb02e388a181dc4fdf275ebab4ed202d568abf1e4f4a75`, plus a distinct current-main snapshot with the same main fingerprint. None is enabled and no launch occurred.
- The active daily playset remains `Chinese base -> jxp_chinese_sup_compat -> main -> map`; the original Workshop supplementary provider is disabled. Compatibility payload `8397ca4b...fcea` contains 5,768 files, converges all 73 external providers, and preserves five dynamic-token plus nine start-screen wrapper keys.
- Static evidence for the merged daily payload is current: main content gate `29/29`, Clausewitz `434/434`, full unit suite `448/448`, state safety `0 hard failures`, six relevant generators with no drift, no-skip combined gate `0 errors / 0 warnings`, oracle `--check` current, compatibility clone `--check` with 0 issues, and active-playset audit `4 layers / 858 runtime files / 74 collisions / 0 divergent / 0 stale / 3 review artifacts`.
- The sole exact-path idea registry contains `493/493` unique groups, including 50 primary groups and a deliberately observable 31-group companion tail. Map groups require exact origin plus daimyo stage, the former second runtime idea file is forbidden, and setup-log evidence must show the stable companion tail rather than demand engine-silent names.
- Fresh and stale idea assignment now share one postcondition-driven transaction: clear any stale repair marker, converge the exact managed group, then commit the marker only after the expected-group trigger succeeds. Route/final identities still remove prior daimyo groups instead of stacking them.
- TOY has one dedicated monarchy foundation and dated kanpaku/taiko government names wired through the authoritative history source for 1586, 1598 and later selectable dates; no republican or free tier-one fallback is statically reachable.
- Route-reform visibility is exact-state scoped, final political reforms have a pinned two-modifier manifest, and the theoretical JXP contribution to any government tier is at most three. Fresh runtime logs must still prove that `countryreformview.cpp:289` no longer appears and that each final state can visibly adopt and retain its unique reform.
- Fresh government identity is now a first-class contract: 36 main daimyo, 30 map daimyo and ASK shogunate must remain monarchies with legitimacy; RYU remains vanilla monarchy/autocracy and is a negative mechanic/retry control. Custom `basic_reform` inventory is forbidden beyond pinned `monarchy_mechanic`.
- R3/R4/R6/R8 and related runtime scenarios require adoption, save/reload, genuine pre-political migration parents, all eight inherited Shinto chains, natural AI behavior and fresh-log evidence. JXP-022/023 also retain an independent P0 gap: old saves already carrying `v0280/v0283/v0260` markers have no markerless startup convergence for the new EoC/non-EoC dual state.
- JXP-019 now also requires R2/R12 evidence that MRI, OTM, RKK and shared-family representatives show their intended columns on a fresh start, preserve old six-stage progress after migration, and reject every generic, shared-family or foreign identity anchor after save/reload.
- Runtime acceptance is `PENDING_USER_APPROVAL`. No current-candidate EU4 session has been run, and the prior single-launch authorization has been consumed; earlier candidates and failed/aborted sessions are historical journal evidence only and must not be reused.
- Agent B's eleven-path gameplay slice is frozen inside the payload and independently validated; B must remain read-only unless a newly discovered runtime defect specifically reopens that scope.
- User runtime review opened release-blocking defects that remain `OPEN` until the required fresh UI/log/save-reload evidence passes. Daily payload f687ca1 contains the current static fixes, while acceptance candidate 80637e0 remains an older isolated snapshot and must not be used as evidence for the new bytes.

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
- 终局日本不得使用通用任务树；十种路线统一状态与独立历史统一状态 TOY 必须保有唯一五-series signature，且 final-tree density 门禁持续有效。
- 任何新增或重排任务必须同时验证主 Mod 192 profiles 与地图 30 tags × 4 DLC states。

### Routes, Religion, Ideas And Reforms

- 路线统一状态包括：uncommitted JAP、Sakoku JAP、Open Trade JAP、KJP、CJP、EJP、RFJ、SJP、IJP、WAK；TOY 是额外的独立历史统一状态，不计入十路线互斥集合。
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

- 主 Mod：44 个自定义 mission series、309 个 mission ID、192 个 effective profile。
- 地图 Mod：5 个精确 slot-3 house series、33 个 mission、120 个 tag/DLC profile。
- 终局任务：十种路线统一状态与独立 TOY 各有唯一五列签名，不得退回 vanilla generic 或 another-route columns。
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
| 0.5 任务树扩展 | 342 个联合任务且拓扑门禁成熟 | 后续以节奏、历史目的与分支质量为主，不以堆数量为主 |
| 1.0 | 内容量、四灾难、九路线循环、大名身份、海外/地域风味与终局政治扩展均已达到静态目标 | 剩余距离集中于获准后的运行时证明与修复闭环 |

## Active TODO

状态只允许 `OPEN`、`IN_PROGRESS`、`BLOCKED`、`DONE`、`DEFERRED`。领取任务时填写唯一 owner；完成时必须写证据并保留稳定 ID，不得删除历史任务。

### Parallel Task Chains A/B

- **A / `CODEX_A` / 本窗口：** `JXP-001`、`002`、`009`、`016`、`017`、`018`、`019`、`020`、`021`、`024`–`030`、`037`。独占 `history/**`、`common/countries/**`、`common/country_tags/**`、`common/ideas/**`、本轮全部大名身份任务与任务刷新接线、净土真宗/佛教日本、陪臣、日本内部战争、国内阶层／市场／公司／资本任务文件、全部 `jxp_70_toyotomi_*` 文件、主/地图生成器与验证工具、`tools/jxp_runtime_acceptance/**`、playset/兼容副本、skill、Documents 部署和本总账。
- **B / `CODEX_B` / 另一 Agent Window：** `JXP-004`、`005`、`008`、`010`、`022`、`023`、`031`–`036`。可编辑其 `jxp_b_*` 殖民社会、殖民国家、独立/东归、海外战争、大陆经略、朝鲜战争和天命平衡专属 missions/events/decisions/CB/wargoal/subject/localisation/tests；不得触碰 A 独占路径、唯一理念注册表、历史文件或本总账。
- **边界例外：** B 可独占 `events/jxp_79_final_state_migration_events.txt` 及与 B 功能同编号的迁移文件；A 独占 `events/jxp_22_migration_events.txt`、`jxp_23_migration_events.txt`、`jxp_23_mission_refresh_events.txt`、`jxp_25_migration_events.txt` 与 `common/on_actions/jxp_60_mission_runtime_on_actions.txt`。需要跨边界时先提交最小接口说明，由 A 完成共享文件接线。
- **交付规则：** B 不编辑本总账、Documents、Launcher 数据或 installed skill，只回报精确 changed paths、静态门禁和未决风险；A 负责联合验证、总账写回和部署。两条链不得同时格式化、生成或改写对方目录。

| ID | Priority | Status | Owner | Scope | Task | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- |
| JXP-001 | P0 | IN_PROGRESS | CODEX_A | Runtime | 主 Mod + 地图 Mod 新战役冷启动验收 | 用户明确许可；1444 冷启动、一天后任务/改革、fresh error.log 均通过 |
| JXP-002 | P0 | IN_PROGRESS | CODEX_A | Migration | 旧存档依次验收十种统一状态的任务、理念、改革迁移 | 保存/重载后 flags、已完成任务与五列树稳定，fresh error.log 无 JXP 错误 |
| JXP-003 | P0 | DONE | CODEX_ROOT | Balance/Compatibility | 逐项重构 19 个 `num_of_cities = 25/30` 地图尺度敏感门槛 | 每项记录历史意图，改为统一度、战略省份、area、发展或合理城市数；联合门禁 0 warning |
| JXP-004 | P0 | IN_PROGRESS | CODEX_B | CJP/Religion | 运行时证明 CJP 单次融合神道、改革中心传播和神道事件桥 | 不重复 harmonize；Ise 等保护地不转；Nanban/urbanization/Neo-Confucian bridge 可触发 |
| JXP-005 | P1 | IN_PROGRESS | CODEX_B | UI | 对大名五家系、十种统一状态与地图任务做视觉布局/政府 UI 验收 | 无断线、空洞、重叠、通用树、缺失 icon 或错误 tier；截图留档 |
| JXP-006 | P1 | DONE | CODEX_ROOT | Route parity | 审计九条路线的任务、事件、决议、改革、调试入口深度 | 生成可比较覆盖报告并补齐明显短板，互斥 gate 无矛盾 |
| JXP-007 | P1 | DONE | CODEX_ROOT | Disasters | 将完整灾难系统扩展到原规划的 4-5 个 | 4 个灾难均使用 scalar lifecycle event，推进/结束/清理/debug 闭合；17/17 state-safety tests 通过 |
| JXP-008 | P1 | IN_PROGRESS | CODEX_B | WAK | 完成倭寇联盟、私掠、港市与海上国家的长期循环 | 有进入、投资、压力、收益、退出与 AI 行为；地图语义范围兼容 |
| JXP-009 | P1 | IN_PROGRESS | CODEX_A | IJP | 完成净土真宗语境下的一向宗压力、灾难及寺社町众国家循环 | 与岛原不误叠，宗教/阶层/地域 gate 合理，讲众增长至政权形成的生命周期、终局任务和事件互相支撑 |
| JXP-010 | P1 | IN_PROGRESS | CODEX_B | Mandate | 审计日本取得天命、八纮一宇改革、CB/AE 与 DLC fallback | 仅任务解锁；无天命 DLC 有替代路径；脚本 effect/CB 经原版实证与运行时验证 |
| JXP-011 | P2 | DONE | CODEX_ROOT | Overseas | 扩展阿拉斯加、加利福尼亚、马尼拉-长崎与太平洋日本循环 | 四类分歧投资、压力/危机/退出闭环、14 个有限期 modifier 与 12 项定向测试均通过；无 companion-only 依赖或永久堆叠 |
| JXP-012 | P2 | DONE | CODEX_ROOT | Regional flavor | 增补对马、濑户内、琉球及伴随地图地域专属任务/事件 | 三套语义 gate、地图 capstone、AI 委任、原子调度与互斥结果清理通过 14 项定向测试；无 1021/4943 重复奖励 |
| JXP-013 | P2 | DONE | CODEX_ROOT | Writing/Events | 为可干预低频事件增加有意义选项并继续历史文案润色 | 22 个可见慢事件均新增有成本的差异选项，完成态/文案/清理合同与 9 项定向测试全通过 |
| JXP-014 | P2 | DONE | CODEX_ROOT | Era attributes | 审计任务、事件、改革、幕府政策、投资对三项时代属性的非决议交互 | 每条路线有多种长期改变方式；刀狩令不与原版幕府行动重复 |
| JXP-015 | P1 | DONE | CODEX_ROOT | Safety | 审计全部 event flags/modifiers 的 debug cleanup 与灾难误触发 | 自动覆盖报告无孤立状态；岛原及后续灾难无明显 false positive |
| JXP-016 | P2 | IN_PROGRESS | CODEX_A | Process | 持续维护本总账、历史索引与 skill 协议 | 每个开发切片同步更新版本、TODO、证据、风险和 Update Journal |
| JXP-017 | P0 | IN_PROGRESS | CODEX_A | Map runtime | 验收 88 省地图渲染、港口、海峡、标签、书签与日期滑块 | 用户许可后按 map implementation report 清单完整执行并归档截图/log |
| JXP-018 | P1 | IN_PROGRESS | CODEX_A | Toyotomi/History | 建立独立丰臣家身份，并统一修复秀吉掌权后的领土、属国、战争与占领史仍沿用织田家的问题 | 专属 tag、旗帜、名称、理念及任务身份完整；1586 交接后领土、属国与四场战争均只使用 TOY；万历朝鲜战争九场战斗、十八省 owner/controller 时间线和十九段占领区间精确；伴随地图、翻译兼容层、旧存档及可选日期保持一致 |
| JXP-019 | P1 | IN_PROGRESS | CODEX_A | Daimyo ideas/missions | 建立全部 67 个日本大名的 tag 专属任务/事件覆盖；重点完成织田政府建设线与今川外交法制线 | 67 家均有不可由他家完整复制的任务、事件、危机与统一遗产；ODA/IMG 达 Tier-S 深度；联合 profile 无 generic fallback、冲突、旧档残留或断链，并有强度分层审计与获准后的 UI/save-reload 证据 |
| JXP-020 | P0 | IN_PROGRESS | CODEX_A | Ideas/UI | 给国家理念结构增加硬性上限，修复理念超限造成的 UI 重叠 | 所有可激活理念组均符合 `start + 7 ideas + bonus` 标准结构；生成器与 validator 对超限 hard fail；获准运行时截图确认无重叠或越界 |
| JXP-021 | P1 | IN_PROGRESS | CODEX_A | Localisation/Names | 将 Mod 中尚未汉化或字节不兼容的日本大名领袖姓名统一修复 | 39+39 中文补充兼容文件、14 主路线文件、60 地图大名文件及丰臣文件均为可逆 canonical EU4SpecialEscape；R2/R3/R9 显示无乱码 |
| JXP-022 | P1 | IN_PROGRESS | CODEX_B | Final tags | 为每个日本终局 tag/统一状态增加专属权力结构政治改革并扩写任务树 | 十种统一状态各有语义匹配且互斥可见的权力结构改革、独特任务签名与足够深度；动态刷新和旧存档迁移闭合，无串线、通用树或错误 tier |
| JXP-023 | P0 | IN_PROGRESS | CODEX_B | Mandate/Bugfix | 修复已满足解锁条件后“八纮一宇”天朝改革仍不显示的 bug | 有天命 DLC 时仅合格的日本天子在正确 UI 看见并可选改革；无提前/外国误显，government mechanics 刷新及旧存档迁移闭合；无 DLC fallback、获准运行时截图与 fresh error.log 共同作为 `JXP-010` 证据 |
| JXP-024 | P0 | IN_PROGRESS | CODEX_A | Balance/Shogunate | 重做“请下宣旨”与大名上洛夺取幕府的成本、命名和参战范围 | 宣旨为高门槛一次性临时宣称；上洛战争不再自动把全部非盟友大名拖入敌方，且无额外稳定/厌战惩罚；新局 UI、战争双方与 fresh log 通过 |
| JXP-025 | P0 | IN_PROGRESS | CODEX_A | IJP/WAK entry | 收紧一向净土国与倭寇联盟的史实成立条件、AI 行为和宗教身份 | IJP 仅由一向一揆时代、灾难与心脏地带状态进入并采用日本净土佛教；WAK 仅由日本文化的西南海路国家进入；ASK/Ainu 负例和自然 AI 通过 |
| JXP-026 | P1 | IN_PROGRESS | CODEX_A | Daimyo reforms | 为统一前的大名/独立大名/幕府画像提供日本专属可见政治改革 | 大名阶段在原版层级中拥有互斥、语义匹配的日本制度选项；终局路线不串入，单层候选不超限，UI 与保存重载通过 |
| JXP-027 | P0 | IN_PROGRESS | CODEX_A | Nested lords | 研究并实现最多一层的陪臣大名、国众从属或寄亲—寄子关系 | 技术试验明确采用原生或伪属国；层级不超过一层，战争召集、容量、倒戈、幕府裁定、灭国/统一清理与保存重载闭合 |
| JXP-028 | P1 | IN_PROGRESS | CODEX_A | Internal wars | 为日本内部合法战争建立受限 AE、战争分数与整合成本体系 | 折扣只适用于统一前日本大名和日本 region；终局/海外不可利用，连续兼并仍有反作用，并以获准后的观察局证明统一速度未失控 |
| JXP-029 | P0 | IN_PROGRESS | CODEX_A | Shinshu religion | 正式建立佛教组独立宗教净土真宗并接入 HNG、本愿寺、IJP、寺内町和门徒武装化 | 宗教 key/UI/业力兼容、0–100 单变量、传播、20 事件家族、HNG/IJP 身份与一次性迁移静态闭合；运行时宗教 UI/保存重载/fresh logs 待证 |
| JXP-030 | P1 | IN_PROGRESS | CODEX_A | Buddhist Japan | 新增与 IJP 不同的佛教日本路线、诸宗席位、施济教育、佛教外交和三种终局国制 | `jxp_path_buddhist` 与既有路线互斥；25–30 项五列任务、最多三席及有代价效果、三终局改革、危机和 Agent B 接口闭合 |
| JXP-031 | P1 | IN_PROGRESS | CODEX_B | Colonial society | 建立海外殖民社会三变量、五类章程、区域内容与共享事件库 | B1–B6 的年度脉冲、南洋/太平洋/北太平洋/美洲 fallback、AI、清理和旧进度迁移闭合，不破坏既有 JXP-011 循环 |
| JXP-032 | P1 | IN_PROGRESS | CODEX_B | Colonial states | 建立四个受控殖民国家、玩家切换、自治与独立危机 | B7–B10 的 tag/政府/五列任务/切换资产/独立阶段可保存可迁移；新理念仅提交源片段与插入合同，由 A 生成唯一注册表 |
| JXP-033 | P1 | IN_PROGRESS | CODEX_B | Colonial wars/return | 实现殖民独立战争、终结旧大陆统治和约、东归革命与两洋联邦 | B10–B12 的 CB/wargoal/peace、反滥用、四类胜利结果和跨太平洋状态闭合，不越权修改 A 的日本内部战争文件 |
| JXP-034 | P1 | IN_PROGRESS | CODEX_B | Continental strategy | 按大名、幕府、终局日本三阶段重做六大战区与征服后治理 | B13 的琉球、朝鲜、满洲/北方、台湾/福建、中国沿海、菲律宾/东南亚任务和四类治理按身份/后勤接口分流 |
| JXP-035 | P1 | IN_PROGRESS | CODEX_B | Korea war | 建立朝鲜战争前置、战时事件、补给和六种结局的完整链 | B14 不篡改 A 所有的 TOY 历史字节；任务/事件读取后勤接口，交战、撤退、傀儡/保护/通商结果与 AI/重载闭合 |
| JXP-036 | P0 | IN_PROGRESS | CODEX_B | China/Mandate | 重构中国、天命、八纮一宇三终局并完成 B 系统 AI、平衡、迁移和联合测试 | B15–B16 的夺取/海上礼仪圈/破除天命互斥，八纮一宇与既有 JXP-010/023 合同兼容，无 DLC fallback、AE/和约/AI/迁移闭合 |
| JXP-037 | P0 | IN_PROGRESS | CODEX_A | Estates/Markets/Companies | 建立日本四阶层、四阶段商业化、共享资本任务、国内公司与十二统一状态的差异化国内终局 | 四阶层及特权/议程/互动/危机、35 项资本任务、40+ 经济事件、公司生命周期、商议日本、迁移/AI/清理/汉化全部静态闭合；获准后以主/地图、DLC 开关、保存重载和观察局证明运行行为 |

## Active TODO Runtime Closure Map

本表是 `runtime_scenarios.json` 对所有非 `DONE` TODO 的精确投影。静态门禁只证明左栏状态；只有右栏全部场景形成当前 matrix 的 sealed READY evidence 后，才可按各 TODO 的验收条件关闭。`JXP-016` 是持续流程义务，在 R13 写回最终总账前保持进行中。

| TODO | Current static position | Required phases | Runtime completion evidence |
| --- | --- | --- | --- |
| JXP-001 | 当前 main/map payload 与 pins 已静态准备；新候选尚未部署到隔离根或日常 playset | `R1` | 冷启动、一天后状态、fresh log 与退出收集全部通过 |
| JXP-002 | 真实 pre-0.24.2 R5 已静态接纳；sole idea registry 与地图旧 `v014` 错误理念的 postcondition 驱动事务重试均已闭合，待真实迁移/重载证明 | `R4 + R5` | 0.25/0.27 与真实 R5 均完成加载、迁移、保存、退出和重载，地图旧标记错误理念也能重试修复 |
| JXP-004 | CJP 单次融合、三中心上限、保护地和八条神道桥静态闭合 | `R6` | 引擎内融合、传播、保护地及神道/理学事件桥逐项成立 |
| JXP-005 | 192 个主 profile 与 120 个地图 profile 的拓扑/资产合同通过 | `R1 + R2 + R3 + R12` | 冷启动、大名、十终局与完整地图 UI 截图均无断线、重叠或错误 tier |
| JXP-008 | WAK 进入、投资、压力、退出、AI 与地图语义合同通过 | `R7` | 有限循环、路线丢失、地图正反例、代际清理与自然 AI 行为通过 |
| JXP-009 | IJP 治理、压力、退出、灾难隔离与地图语义合同通过 | `R8` | 全部单门槛正反例、任务事件、循环清理和自然 AI 行为通过 |
| JXP-010 | 天命取得、八纮一宇 CB/AE 与 DLC fallback 静态合同通过 | `R10 + R11` | 天命 DLC 开/关两条实际引擎路径均通过 |
| JXP-016 | schema-2 总账、外部登记、运行协议和报告索引均受门禁保护 | `R13` | 12 个运行场景 READY 后完成非游戏 release closure 与最终总账写回 |
| JXP-017 | 88 省地图、137,382 日期、港口/海峡/历史 oracle 静态通过；东海陆地区域已更正为“东海道”并受生成源合同保护 | `R1 + R2 + R9 + R12` | 隔离 VFS、六个大名画像、丰臣日期边界和完整地图渲染共同通过 |
| JXP-018 | 1586 ODA/TOY 唯一交接、专属理念/任务/关白太阁政体、属国与双地图逐日合同通过；四场战史、九场战斗、十八省 owner/controller 与十九段占领区间通过精确边界校验；TOY 理念已在权威源与唯一运行注册表中强化检地、刀狩、朝廷名分、奉行/大老治理容量及朱印贸易；日常 73-provider 兼容副本已重建并静态审计通过 | `R4 + R9` | 旧档迁移及正式/补录丰臣转换、日期边界、万历朝鲜战争交战方与占领地显示、保存重载均通过 |
| JXP-019 | 67 个主/地图可选大名、268 个 DLC 画像均有唯一五槽任务归属；13 个主 Tier-A 与 15 个地图 Tier-A 大名拥有精确 tag 的八章历史分支；A1 权威矩阵已逐家固定 Tier S/A/B、政治处境、净新增与目标数量、危机、失败重建、统一遗产、接口、史料和重复风险；A98 已从同一矩阵生成 67 家及 TOY 专属开局家史/策论，并按发现、宗教改革、专制、革命四时代和幕府/大名/统一政权三身份组合显示，非日本国家回退原版总览；ODA 理念已强化快速征服、攻城、火器、乐市乐座及南蛮技术；A2-A5 其余运行内容仍待按矩阵生成 | `R2 + R12` | 完成 A2-A5 后，MRI/OTM/RKK 等重点与普通家系代表的新战役 UI、开局总览、旧档进度迁移、保存重载和 fresh log 均无通用回退、消失、断线或跨家残留 |
| JXP-020 | 45/45 自编理念组结构闭合；单一生成 `00_country_ideas.txt` 含 488 个唯一组、34/34 同名替换、31 个 companion-tail 组与全部关键哨兵；任何第二个 runtime 理念文件或生成漂移均 hard fail；普通/强制同步分离 | `R2 + R3` | 六个大名画像（含 MRI/OTM/RKK）与 TOY、十终局理念 UI 均无默认回退、重叠、溢出或混组，fresh setup/error log 精确显示 `1..25 + 226..513` 且无旧签名 |
| JXP-021 | 14 主路线文件、60 地图大名文件与丰臣文件通过 canonical EU4SpecialEscape/source-active 校验；39+39 兼容副本须随新候选部署重建 | `R2 + R3 + R9` | 六个大名、十种终局状态及丰臣日期边界的统治者/王朝名称均无乱码并能保存重载 |
| JXP-022 | 十种统一状态的新局权力结构、capstone、互斥及 EoC 双态静态闭合；旧 `v0280/v0283` 标记存档的 markerless startup convergence 仍是 P0 | `R3 + R4` | 十状态 UI/生命周期及真实旧档迁移均通过，旧标记错位状态也能幂等自愈 |
| JXP-023 | 八纮一宇仅任务解锁、DLC fallback 与新局 EoC/celestial 双态静态闭合；旧 `v0260`/改革标记错位收敛尚未实现 | `R4 + R10 + R11` | 旧档、有 DLC 和无 DLC 三条实际 UI/引擎路径共同通过，EoC 保留 `celestial_empire` 且八纮一宇可见可选 |
| JXP-024 | 宣旨成本/时效与上洛参战合同已静态修复；当前 runtime matrix 尚未登记本轮新反馈场景 | — | 后续由 runtime matrix 所有者登记场景，验证宣旨 UI/实际宣称类型、上洛 CB 名称、稳定/厌战预览及战争双方 |
| JXP-025 | IJP/WAK 年代、文化、地域、准备度、AI 与净土真宗身份已静态修复；当前 runtime matrix 尚未登记本轮新反馈场景 | — | 后续由 runtime matrix 所有者登记场景，验证历史正例、Ainu/ASK/错误年代/地域负例、宗教同步与自然 AI |
| JXP-026 | 三项统一前日本改革及生命周期已静态接线；当前 runtime matrix 尚未登记本轮新反馈场景 | — | 后续由 runtime matrix 所有者登记场景，验证大名/独立大名/幕府 UI、终局/外国隔离、tier 上限与保存重载 |
| JXP-027 | 陪臣机制处于技术审计阶段；runtime matrix 尚未登记 spike 与正式场景 | — | 先完成静态能力边界，再由 matrix 登记一层关系、战争、倒戈、灭国、统一及保存重载正反例 |
| JXP-028 | 日本内部战争平衡处于设计/基线阶段；runtime matrix 尚未登记观察局 | — | 后续登记国内/海外正反例和至少 20 次观察局，证明折扣不泄漏且统一速度未失控 |
| JXP-029 | 净土真宗与 IJP 宗教重构处于静态实施阶段；现有 R8 只覆盖旧 IJP 循环 | — | 后续扩展 matrix，验证宗教 UI、HNG/IJP 转换、传播、变量、灾难生命周期、保存重载及 fresh logs |
| JXP-030 | 佛教日本路线处于设计矩阵阶段；runtime matrix 尚未登记新路线 | — | 后续登记路线互斥、五列任务、三席上限、三终局改革、危机、外交接口与保存重载 |
| JXP-031 | B1–B6 殖民社会三变量、五章程、四区域、共享事件、AI、清理及 B102 启动迁移已静态实施；尚无运行场景 | — | 后续登记三变量、五章程、四区域、共享事件、AI、迁移与清理运行证据 |
| JXP-032 | B7–B10 殖民国家身份、成立、政体、任务、理念、切换与独立阶段已静态实施；A 中央注册已合入 B HEAD | — | 后续登记 NYA/HKK/NJF/OIA/TPF、玩家切换、政府/任务/理念、独立危机及保存重载 |
| JXP-033 | B10–B12 殖民独立战争、旧大陆统治终结、东归四结果及两洋联邦已静态实施；尚无完整战争运行证据 | — | 后续登记 CB/wargoal/和约、旧大陆统治终结、东归四结果、两洋联邦与反滥用 |
| JXP-034 | B13 大名/幕府/终局三阶段、六大战区、四类征服后治理及 B99→B100 接口已静态实施 | — | 后续登记三阶段身份分流、六战区、四治理与海外接口运行证据 |
| JXP-035 | B14 朝鲜战争前置、补给、战时事件、监视循环与六类结局已静态实施；TOY 历史运行边界尚未验证 | — | 后续登记战前、补给、战时事件、六结局、AI 与保存重载，并复核 TOY 历史不漂移 |
| JXP-036 | B15–B16 中国/天命三终局、八纮一宇限港合同、AI 平衡及海外程序集成迁移已静态实施；现有 R10/R11 仍不足以关闭 | — | 后续扩展 matrix，验证三终局、DLC 开关、CB/AE/和约、AI、迁移与既有 JXP-010/023 兼容 |
| JXP-037 | payload `1ad79d161081d067c76e6eb46d8df9f0128f906d` 已静态实现四阶层、四阶段市场、五公司、152 项 A 任务、十二国内路线、商议终局、事务迁移、退出清理与完整中文；主 validator 30/30、Clausewitz 470/470、地图兼容 0 error/0 warning，但没有游戏内场景 | — | 扩展 runtime matrix，验证阶层/Crownland/议程/五类危机、市场阶段、公司生命周期、十二路线、商议日本、DLC 开关、主+地图、保存重载及长期 AI 节奏 |

## Known Risks

1. **没有当前版本运行时证明。** 0.28.1 + 0.1.4-alpha 尚在静态集成；不得把早期版本冷启动或用户“目前正常”的反馈自动外推到当前所有 profile。
2. **固定城市数不得脱离语义容量。** 25/30 门槛已全部替换；保留的较低门槛必须同时有统一身份、关键省、发展、港口或其他历史容量条件。天明灾难的 `20` 城与 `250` 发展/江户锚点已由 mutation 固定。
3. **CJP 是高风险桥接区。** harmonization、改革中心、神道事件/incident 继承涉及引擎行为，静态检查只能证明结构。
4. **旧存档序列化 mission series。** 即使 `potential` 已禁用，旧 key 也可能残留；不得删除 tombstone 或省略迁移。
5. **动态 UI 刷新。** “获得新任务”必须 immediate swap + next-day reconcile + fingerprint repair；新增路线不得直接散写 swap。
6. **地图硬兼容边界。** 伴随地图覆盖完整地图基础文件；它不能与其他日本地图 overhaul 共存，且必须新开局。
7. **Sakai 双锚点。** `1021` 与 `4943` 语义相邻但不是可互换的同一省，需防重复效果。
8. **dormant reforms。** 306 个旧定义仍保留以兼容/历史用途，任何生成器或手改不得把它们重新注册到 UI。
9. **Chinese localisation pipeline。** source 与 active 文件不可混改；Markdown 日志不得经过 EU4SpecialEscape。
10. **并行 agent 冲突。** Git 已提供提交与 worktree 边界，但总账仍采用 lead-agent 单写者协议；并行分支不得各自改写总账后假设可自动合并。
11. **隔离已证明，但两次 PROBE 均未通过。** 实际进程 argv、fresh isolated logs 与 unchanged daily hashes 已证明 `-userdir=C:\JXP_Acceptance` 和 main+map VFS 生效；隔离目录不继承日常语言与用户偏好属于预期。第一次因缓冲 `Enter` 误入大友开局而 ABORTED；第二次未发送任何输入，但只渲染标题背景、未出现可交互主菜单，并在 fresh log 暴露四个灾难 debug-seed 错误。两者都不能作为 READY 证据；A2 静态修复后仍须取得新的明确许可再跑全新 PROBE。
12. **R5 仅完成静态接纳。** 原问题 `autosave.eu4`、三份命名 0.23.x ZIP 及 sidecars 已通过 `verify-r5-escrow`，当前 matrix 无 blocker；但只有加载、迁移、保存、退出、重载及 fresh logs 全部通过后才是 READY/RUNTIME evidence。禁止手工重标 collection、关闭 `JXP-002`，也禁止合成、改旗、重存或上传原件。
13. **外部证据不属于 Git payload。** R5 存档、ZIP、launcher 数据库、运行日志和截图不得提交或推送；总账只登记内容哈希、保管位置、证据状态与授权边界。路径不可达时按“证据暂不可用”处理，不得以相似文件替代。
14. **PowerShell 文本编码回归。** CJP 与 EJP 的 `leader_names` 实际均为 10 项；旧 validator 因 Windows PowerShell 5.1 默认 ANSI 解码无 BOM UTF-8 而误报 9/6。通用校验器、skill 与回归 fixture 已固定显式 `-Encoding UTF8`；后续脚本不得恢复隐式文本编码，正式 PROBE/R6/R7 仍须以 fresh log 排除真实 `countrydatabase` 错误。
15. **理念运行时注册表尚未重新验收。** 用户截图与 fresh `setup.log` 已证明多文件理念方案会让 MRI/TOY 回退默认理念并触发 `national_idea8`；国家选择界面的预览不能证明实际开局后的 IdeaDatabase 完整。当前 payload 改为唯一生成的 exact-path `common/ideas/00_country_ideas.txt`，静态验证覆盖 pinned vanilla、488 个唯一组、34 个同名替换、45 个主自编源、31 个地图尾部组和关键哨兵；首次分配与地图旧标记修复均以 exact postcondition 驱动，并只在成功后写入 repair marker。旧候选及“安全文件名窗口”结论均不得复用；`JXP-020` 必须保持进行中，并在新候选 R2/R3 以 MRI/OTM/RKK/TOY/终局理念 UI 与 fresh setup/error log 共同关闭。
16. **灾难生命周期与调试注入必须以 fresh log 复核。** 四个灾难的内联 `on_end` 已改为 scalar cleanup event；A2 又把四个 custom-disaster `add_disaster_progress` 从早编译的 scripted-effect 层移入完整隐藏事件，静态门禁现能同时阻止两类回归。此前运行只加载 1/4 灾难，第二次 PROBE 又记录四个 debug progress validation failure；下一次获准 PROBE/R8 必须确认 setup 中注册 4/4，且不存在 `{` namespace、unknown disaster 或 debug progress 错误。
17. **丰臣历史与万历朝鲜战争仍需运行时证明。** 源文件与当前日常全提供者审计均静态证明 `1586.1.1` 后任何已启用来源都不会让 ODA 保有领土或进入四场后继战争；九场战斗、十八省控制权与十九段占领区间已通过逐日边界校验，Jeju/Pyongyang 特例也有硬守卫。但书签战争 UI、实际交战方、地图控制色、任务 UI、姓名显示、保存重载和旧档迁移仍必须在获准后的 R4/R9 证明。A3 已失效，不得继续用于当前验收。
18. **Workshop 翻译 Mod 不是纯 localisation 层。** 中文补充 Mod 同时拥有 ODA country history、48 个日本 province histories、原版日本任务、日本姓名池、四场战史和十七份韩国 province histories。旧的排序修复已被用户运行时结果否定；发布、部署和运行前必须执行 `build_chinese_compat_clone.py --check` 与 `audit_active_playset.py`，证明原 Workshop 项禁用且所有 73 个冲突提供者逐字节收敛。依赖声明或列表顺序不能替代此证明。
19. **兼容副本与姓名生成物会随源更新而过期。** Workshop 补充包、主/地图权威冲突文件、14 个主路线可读姓名源或地图 `history_plan.json` 任一改变后，都必须重建本地兼容副本/活跃姓名文件并更新 oracle。审计会把 source/payload drift、raw UTF-8 CJK、非 canonical 字节和 Documents 部署落后视为硬失败；原 Workshop 补充项必须保持禁用。
20. **自定义 area 的中文显示名可能与海域或原版 area 撞名。** 旧日志证明 `jxp_tokai_area = 东海` 会与 `east_china_sea_area` 冲突；当前生成计划固定为历史地理名“东海道”，验证器同时检查计划、UTF-8 源与生成值，active-playset 审计还会解码全部启用层的 EU4SpecialEscape 后比较实际显示名。新增 area 时不得只看脚本 key，还要审计有效中文显示名。
21. **政府改革先按 `potential` 组装候选，再按 `trigger` 判定可选。** 旧 broad-potential 方案曾让 TOY 同时装入跨路线改革并触发 `countryreformview.cpp:289` 的每层 16 项硬上限。当前 exact-profile 矩阵将任一画像的 JXP 单层候选压到最多 3，但只有获准后的 R3 fresh log 与十状态 UI 能证明引擎端不再截断。
22. **改革 modifier 拼写不能由结构计数证明。** `naval_tradition` 曾在 Clausewitz、注册和深度检查全部通过后才被逐键审计发现；当前十项政治改革已固定精确 20-key/value manifest，并以 `navy_tradition` 变异测试防回归。新增改革必须先在 pinned 1.37.5 原版词汇中命中。
23. **`basic_reform` 是政府类别基础，不是隐藏奖励容器。** 旧 JXP 同时声明 monarchy/republic 的 39 个自定义 basic reforms 会替换大名真实身份，使君主国显示共和传统、令 `has_reform = daimyo` 失效并让任务树退回错误 profile。当前只允许 pinned `monarchy_mechanic`，能力必须挂在已注册的真实改革上；67 个新开局身份、RYU 负例、全部 direct-add callsite 和 fresh UI/log 必须共同通过。用户明确要求本修复只保证新开局，不修复已污染旧档。
24. **JXP-022/023 的旧标记双态收敛尚未实现。** 用户对 39 个非法 `basic_reform` 身份污染明确只要求新开局，但这不等于关闭既有的终局改革/天命旧档合同。已经携带 `v0280/v0283/v0260` 标记、却序列化为 EoC + JXP tier-one 或非 EoC + `celestial_empire`/错误 tier-one 的存档，目前没有 markerless startup canonical sync。地图 `v014` 理念错误已获得静态事务重试：读取并清除旧 marker、按 exact postcondition 收敛、成功后重设；但 R4/R5 尚未提供引擎保存重载证据。JXP-002/022/023 必须保持 `IN_PROGRESS`，不得写成迁移闭合或运行通过。

### User-Reported Defect Queue

这些条目来自当前部署的实际游戏审阅。除非代码修复、定向静态门禁和新的游戏内证据共同通过，否则不得标记为关闭，也不得用国家选择界面预览或旧版本日志替代实际开局后的 UI。

| Defect | Priority | Status | Related TODO | User-visible failure | Required closure |
| --- | --- | --- | --- | --- | --- |
| JXP-BUG-IDEA-FALLBACK-001 | P0 | OPEN | JXP-019 / JXP-020 | 所有大名进入实际游戏后均使用默认理念，而不是已设计的独特理念 | 修复运行时理念注册与首次分配；主/地图代表大名进入游戏后显示精确理念组，保存重载不回退，fresh setup/error log 无 IdeaDatabase 或 `national_idea8` 错误 |
| JXP-BUG-ERA-REWARD-001 | P1 | OPEN | JXP-014 / JXP-019 | 大名任务树多次把天下秩序、天皇裁可、海门外学直接设置为固定值，奖励重复且破坏长期积累 | 遍历全部大名任务奖励，移除无正当迁移用途的硬设值；改为有界增减、阶段性投资或条件奖励，并证明不会回退、跳过或覆盖玩家既有积累 |
| JXP-BUG-TOY-GOVERNMENT-001 | P0 | OPEN | JXP-018 / JXP-022 | 选择丰臣家时初始政治改革仍由玩家自由选择，没有固定为幕府或其他历史合理政体 | 为 TOY 新开局固定唯一、历史合理且与任务/正统性一致的基础政府改革；国家选择与实际开局一致，无自由选择窗口、共和传统或通用改革回退 |
| JXP-BUG-HAKKO-LOC-001 | P0 | OPEN | JXP-021 / JXP-023 | “八纮一宇”天朝改革没有正确显示中文本地化 | 补齐改革名称、说明、条件与效果相关 key 的 canonical source/active 中文管线；天朝改革 UI 无裸 key、问号、英文回退或乱码 |
| JXP-BUG-IMPERIAL-EDICT-BALANCE-001 | P0 | IN_PROGRESS | JXP-024 | “请下宣旨”以极低成本获得全日本永久宣称 | 改为高裁可、高资源、一次性且只授予普通时效宣称；决议与政府互动完全同价，调试可重置 |
| JXP-BUG-FORMATION-GATES-001 | P0 | IN_PROGRESS | JXP-025 | 阿伊努可成立倭寇联盟，足利可随意成立一向净土国并破坏大名政体；IJP 无日本佛教身份 | IJP/WAK 的可见性、允许条件和 AI 入口均绑定年代、文化、地域、灾难/海路准备；IJP 转换固定净土真宗 |
| JXP-BUG-DAIMYO-REFORMS-001 | P1 | IN_PROGRESS | JXP-026 | 大名体制下看不到日本专属政治改革 | 在原版改革层级加入统一前日本制度选项，并以大名阶段 exact potential 隔离终局与外国画像 |
| JXP-BUG-SHOGUN-WAR-001 | P0 | IN_PROGRESS | JXP-024 | “尊皇讨逆”名称不通用，且夺取幕府时把几乎全部非盟友大名自动拉入敌方并显示稳定/厌战惩罚 | 改称“上洛”，保留原版独立型幕府挑战 CB；大名不再自动加入幕府防御战，只能按关系接受召唤或被单独列为共同交战方，且本 Mod 不额外施加稳定/厌战惩罚 |
| JXP-BUG-JAPANESE-NAME-POOL-001 | P1 | IN_PROGRESS | JXP-021 | 日本默认文化姓名池几乎只有皇室/贵族姓氏，随机王朝重复且失真 | 三种日本文化共享扩充的常见地缘姓氏池；生成源、运行文件和静态审计一致，现有皇室姓氏不丢失 |
| JXP-BUG-PACIFIC-CHARTER-TECH-001 | P1 | IN_PROGRESS | JXP-011 | 太平洋敕许状要求外交科技 12，导致已完成海路准备的国家仍被时代门槛卡住 | 决议与任务替代入口均不得含 `dip_tech`；保留港口、海门外学、殖民/航路准备与资源成本，并在部署后的任务/决议 UI 中确认 |

## External Evidence Registry

外部二进制只在此登记，不进入仓库。`FOUND` 只证明原件存在；`STRICT_VALIDATED` 证明固定 hash/schema；`ADMITTED_STATIC_INPUT` 证明当前 matrix 接纳其作为输入；`RUNTIME_PASS` 必须来自获准后的完整 collection。

- R5 source size: `36371037`
- R5 source SHA-256: `9f6dd96a60c7b9f583c22f87e7da2f5c659e2edc14723483a077b7afd73a8bef`

| Evidence ID | Role | Source | Escrow | Size | SHA-256 | State |
| --- | --- | --- | --- | ---: | --- | --- |
| `EXT-R5-SAVE-001` | authentic pre-0.24.2 engine save | `...\save games\autosave.eu4` | `C:\JXP_R5_Escrow\20260713_original_machine\autosave.eu4` | 36,371,037 | `9F6DD96A60C7B9F583C22F87E7DA2F5C659E2EDC14723483A077B7AFD73A8BEF` | `ADMITTED_STATIC_INPUT` |
| `EXT-R5-ZIP-001` | pre-layout-hotfix backup (`0.23.0`) | `japan_expanded_v2_before_mission_layout_hotfix_20260709_154614.zip` | same filename under escrow root | 47,308,072 | `64F11ACE4F049B799B1C9D5CF0FA64D0A75ABF485D90C0DBC0814FC71107485D` | `STRICT_VALIDATED` |
| `EXT-R5-ZIP-002` | pre-series-consolidation backup (`0.23.1`) | `japan_expanded_v2_before_series_consolidation_20260709_161217.zip` | same filename under escrow root | 47,373,265 | `C05C1B9EE8D1AAB31E02B472AE2C8F897CDFA08E07B33B75367EAC1B3984AE3D` | `STRICT_VALIDATED` |
| `EXT-R5-ZIP-003` | pre-reform-visibility backup (`0.23.1`) | `japan_expanded_v2_before_reform_visibility_hotfix_20260709_164900.zip` | same filename under escrow root | 48,071,664 | `CDBCFD3A7ABE5653BC8C44A377912511C6EC864587D0A504AEC21C949F6B6AE4` | `STRICT_VALIDATED` |
| `EXT-R5-PROV-001` | provenance JSON | original-machine recovery | `r5_external_input_provenance.json` | 2,326 | `03DD5ED8504E7D70A33153010CF8A411A66C9FA3BFB23294A4DD94567F0939DA` | `STRICT_VALIDATED` |
| `EXT-R5-HASH-001` | hash manifest | original-machine recovery | `r5_external_input_hash_manifest.txt` | 368 | `9B1018EEBDBF15B6F9101971191D43C6DFAE686CA0D92BA30EBF451E1DFAFA34` | `STRICT_VALIDATED` |
| `EXT-R5-ID-001` | content identity JSON | original-machine recovery | `r5_content_identity.json` | 2,292 | `BC0DCBECE19D32D85F9F50ECFF08350DE6B7A9024A044A2D30A1A8F44C85759D` | `STRICT_VALIDATED` |

Detailed immutable evidence: `jxp_original_machine_r5_recovery_2026_07_13.md` and `jxp_runtime_portability_and_r5_admission_2026_07_13.md`.

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

### 2026-07-17 - SOCIOECONOMIC-RECONSTRUCTION-025 - Complete static Japanese socioeconomic reconstruction (`no version bump`)

- Status: `STATIC_PASS; IN_PROGRESS; NOT_RUNTIME_PROVEN`。
- Scope: 在玩法 payload `1ad79d161081d067c76e6eb46d8df9f0128f906d` 完成 JXP-037 的 A0–A14 静态工程：48 项日本阶层特权、40 项议程、四套评定互动与四场阶层危机；四阶段市场、50 个常规经济事件、五家国内公司及离散章程／董事／审计／困顿／破产生命周期；152 项精确 A 任务（35 共享资本任务、十二路线各八项、21 项商议任务）、十二条差异化国内终局、商议日本危机与四项国制；67 家 founder 分类、旧任务完成度事务迁移、殖民身份排除、完整退出清理、国体图志及全部可读中文 source→active UTF-8 BOM 镜像。Agent B 的海外、殖民、独立、大陆、朝鲜、中国 gameplay、slots 4–5 与本地化保持只读，A 只消费既有接口。
- Authority/Evidence: 社会经济 master 及 estate/economy/missions/integration 分生成器、净土真宗、佛教终局、legacy BOM alias、任务运行时指纹和 debug cleanup registry 均通过 `--check`；非状态定向测试 194/194、状态／灾难定向测试 19/19、live contract subset 5/5。主静态 validator 30/30，470/470 个 gameplay 文件通过 Clausewitz 解析，任务面为 792 IDs／133 series／200 profiles，状态安全为 1,083 个国家旗、9 个省份旗、1,569 个 modifier、9 个 disaster、0 failures；地图组合兼容检查为 0 error／0 warning，`git diff --check` 通过。
- Runtime/TODO: 未启动 EU4、Launcher、dowser、bootstrapper 或 observer，未部署 Documents，未修改 runtime acceptance、oracle、visualizer 或 installed skill。estate UI／图标与 Crownland、议程实际完成／失败、五类灾难节奏、任务五列／次日换树、DLC 开关、主 Mod 单独／主+地图、保存重载、fresh logs、30 局 1444–1650、10 局 1444–1821、商议形成率与玩家路线通关仍为 `PENDING_RUNTIME`；因此 `JXP-037` 保持 `IN_PROGRESS / CODEX_A / NOT_RUNTIME_PROVEN`。

### 2026-07-17 - SOCIOECONOMIC-RECONSTRUCTION-024 - Start Japanese estates and domestic economy reconstruction (`no version bump`)

- Status: `STARTED; BASELINE_AUDIT_IN_PROGRESS; JXP-037_REGISTERED; NOT_RUNTIME_PROVEN`。
- Scope: 接收 `Agent_A_超详细_日本阶层资本主义与国内终局重构_Prompt.md` 的 A0–A14 工程，新建 `JXP-037 / CODEX_A` 承载四个日本阶层、四阶段商业化、共享资本任务、国内公司、十二统一状态国内模块与架空商议日本。Agent B 的殖民继承国、海外地区社会、殖民独立、大陆战区、朝鲜战争、中国终局及其列 4–5 missions/events/CB/reforms/localisation/tests 继续只读；A 仅提供已有或最小自由旗接口。
- Baseline: 工作分支 `codex/content-agent-a`，开始时 HEAD `f9f0fecec9d185177691bb4b4e64f9a3e05b3912`；tracked worktree clean，只有两份用户提供的 Agent A Prompt 未跟踪。主 Mod 当前没有自定义 `common/estates`、`common/estate_privileges` 或 `common/estate_agendas` 目录，既有日本内容仍直接读取原版 nobles/church/burghers；因此先完成 estate 技术 spike、现有经济奖励盘点、任务列位合同和生成器所有权审计，再写 gameplay。
- Runtime/TODO: 本条没有修改玩法、地图、runtime acceptance、oracle、installed skill、Documents 或 Launcher，也没有启动 EU4。Prompt 自身明确不构成启动许可；阶层 UI、Crownland、议程、危机、保存重载、DLC 开关及 30+10 局观察在取得新的明确授权并登记矩阵前均为 `PENDING_RUNTIME`，不得以静态检查替代。

### 2026-07-17 - INTEGRATION-VALIDATOR-DEPLOY-023 - Close merged validation gates and deploy daily payload (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; COMPATIBILITY_CONVERGED; NOT_RUNTIME_PROVEN`。
- Scope: 将已完成的 A/B 集成分支 `32be2f1` 合入 Agent A 的开局总览提交，形成合并提交 `d6a6443`；该集成补齐 B100/八纮一宇新合同、五个殖民 tag 姓名、统一两阶段任务刷新、佛教终局互斥与五列替换拓扑，并从 A94/A96 权威生成器移除或消费孤立状态。完整单测继而暴露两处陈旧 final-state mutation 锚点，以及 `build_shinshu_content.py` 权威源与手改生成物之间的第五阶段漂移；payload `f687ca1286c88fd5431d0580b9f1e41b819c5363` 更新 ROOT-scoped mutation 锚点，把净土真宗各阶段前置旗、灾难结束清理和第五阶段调用全部固定回权威生成器，再重建 `jxp_a_95_shinshu_events.txt`。
- Evidence: `build_daimyo_depth_runtime.py --check` 17/17、`jxp_a_96_buddhist_builder.py --check` 10/10、gameplay names、start screen、debug cleanup、consolidated ideas 与 Shinshu 生成器均无漂移；final-state 39/39、Shinshu 5/5、state-safety mutation 18/18。最终无跳过联合门禁完整通过：地图、历史、内容、主兼容、资产与 oracle 均为 0 error/0 warning，137,382 个可选日期通过；主 validator 29/29、Clausewitz 434/434、全量单测 448/448，状态安全为 752 个国家旗、9 个省份旗、1,484 个 modifier、4 个灾难、0 hard failures。
- Deployment: 从 clean detached worktree 的精确 payload OID 生成 runtime 白名单 staging，逐文件 SHA-256 校验后原子替换日常 Documents；主 Mod 为 630 个 runtime 文件 / 7,754,132 bytes / fingerprint `27781bedfa61fad033c4df772679c4cca845506202392366fa9444530d50b8b0`，另保留 3 个审阅工件，地图为 252 个 runtime 文件 / 82,963,384 bytes / fingerprint `1016c2ed9e3c0e64b281d47b21cb0929643bfd03c1ae7e7c2b96b485fccc2fe6`。旧主/地图目录完整备份在 `mod/_jxp_backups/20260717_171443_f687ca1`。中文兼容副本原子重建并另行备份，payload 为 5,768 files / 20,858,573 bytes / `8397ca4beefe523fcf081c79f3dc32a7b3dfbe94d30ba5f6636a64fdb596fcea`；`--check` 为 73 patches、39 history、39 country names、5 dynamic-token keys、9 start-screen keys、0 issues。实际 playset 审计为 4 layers / 858 runtime files / 74 collisions / 73 external providers converged / 0 divergent / 0 stale / 3 review artifacts。
- Runtime/TODO: 未启动 EU4、Launcher、dowser、bootstrapper 或 observer，未修改 `dlc_load.json`、Launcher 数据库、日常 playset 或 `C:\JXP_Acceptance`。本条只把旧 `7/29` 静态失败闭合为当前 `STATIC_PASS` 并证明 Documents 字节收敛，不构成开局总览、任务 UI、理念、改革、殖民循环或保存重载的游戏内证据；所有相关 TODO/defect 继续 `IN_PROGRESS / NOT_RUNTIME_PROVEN`。现有 acceptance candidate `80637e0` 仍为旧隔离快照，正式运行前必须围绕 f687ca1 形成新的两阶段 matrix-bound candidate，并另获明确启动许可。

### 2026-07-17 - JAPANESE-START-SCREEN-022 - Rewrite Japanese opening chronicles (`no version bump`)

- Status: `STATIC_PASS; 67_DAIMYO_PLUS_TOY; FOUR_AGES; NOT_RUNTIME_PROVEN`。
- Scope: 新增 A98 权威生成器，以既有 `daimyo_depth_plan.json` 生成独立 `customizable_localization` wrapper 与 source→EU4SpecialEscape 本地化。主 Mod 37 家按 tag、地图 30 家按既有 origin flag 取得各自唯一家史与策论，TOY 另消费统一后附录取得关白／太阁专文；发现、宗教改革、专制、革命四时代分别提供默认页引子、天下形势、信仰秩序及幕府／大名／统一政权国制。九个 UI 入口采用新 JXP defined-text，非日本国家经独立 fallback key 调回原版九函数，不覆盖原版 `00_start_screen.txt`；净土真宗另有业力教法说明。不可变主 payload 白名单加入 `customizable_localization`，避免部署时静默遗漏；中文补充兼容生成器新增末序九键 hotfix，使最终 provider 继续指向 JXP wrapper。
- Evidence: `build_start_screen.py --check --game-root <EU4 1.37.5>` 通过，三项生成物无漂移并验证原版两个固定 SHA-256；`test_start_screen` 6/6、`test_chinese_compat` 1/1、`SharedLedgerTests` 14/14 通过，覆盖 67/37/30、TOY、四时代、三身份、非日本 fallback、地图 tag 隔离、source→active 字节、payload 白名单、兼容层九键防覆盖与总账一致性；主静态 validator 的本切片相关项通过 `341/341` Clausewitz 解析、67 家覆盖和 `77` 个 active localisation 编码检查。该 validator 总体仍因既有殖民任务刷新、B 天命文件尚未合入、佛教终局/任务连续性、殖民 tag 姓名空壳及既有孤立 flags 报 `7/29` cells failed，并在输出完整摘要时由命令包装器于 348.2 秒超时，故不记为完整主门禁通过。`git diff --check` 通过。
- Runtime/TODO: 未启动 EU4、Launcher、dowser、bootstrapper 或 observer，未部署 Documents，也未重建当前中文兼容副本。开局 GUI 的实际载入顺序、滚动排版、四时代书签显示、ASK/普通大名/地图大名/TOY 及 FRA 等非日本回退仍待兼容副本重建后、获准后的游戏内证明；时代切换不会主动重弹开局窗，只在该界面再次求值时读取当前时代。`JXP-019` 保持 `IN_PROGRESS / CODEX_A / NOT_RUNTIME_PROVEN`。

### 2026-07-17 - AGENT-B-OVERSEAS-STATIC-021 - Complete B1–B16 static implementation (`no version bump`)

- Status: `STATIC_PASS; B1_B16_IMPLEMENTED; IN_PROGRESS; NOT_RUNTIME_PROVEN`。
- Scope: Agent B 已在 `db65074` 落地 B1–B16，覆盖 `JXP-031`–`JXP-036` 的殖民社会、殖民国家与独立、殖民战争/东归、两洋联邦、大陆经略、朝鲜战争、中国/天命终局及 B102 海外程序启动迁移。A 中央注册提交 `8f6bd07`、天命验证合同 `9f0de76`、逐国启动迁移接线 `544a9db` 分别由 B cherry-pick 为 `203fc80`、`e6ee090`、`db65074`；迁移只沿既有逐国 startup/年度兜底事件执行，继续消费 mission/idea/government registry 接口，未新增 monthly/world scan。八纮一宇静态合同固定为 attacker `badboy_factor = 0.75`、`peace_cost_factor = 1.0`、`deny_annex = yes`，只允许八个已有普通宣称的战略港，并保留 tributary/release/trade 等优先和平选项。
- Evidence: Agent B 在 HEAD `db65074` 报告 100 项定向测试全部通过、81 个 B91–B102 Clausewitz 文件全部解析通过、唯一理念生成器 `--check` 无漂移，以及全部 B 本地化 source→active 对应和 key 唯一性通过。该证据只证明静态结构、生成物与接口收敛，不证明 UI、AI 或战争引擎行为。
- Runtime/TODO: 未获 EU4/Launcher 启动许可，20 局 AI 观察、完整殖民独立/反攻/朝鲜战争、RNW、无 DLC、主 Mod+地图组合运行、保存重载与 fresh logs 均未执行。因此 `JXP-031`–`JXP-036` 全部保持 `IN_PROGRESS / CODEX_B / NOT_RUNTIME_PROVEN`，不得标记 `DONE`。

### 2026-07-16 - AGENT-A-DESIGN-MATRIX-020 - Freeze the 67-daimyo content design (`no version bump`)

- Status: `STATIC_PASS; A1_COMPLETE; A2_A5_NOT_IMPLEMENTED; NOT_RUNTIME_PROVEN`。
- Scope: 新增独立的 Agent A 权威设计源与确定性报告生成器，逐家覆盖主 Mod 37、地图 Mod 30，并把 Prompt 的内容层级固定为 `S=16 / A=13 / B=38`；TOY 作为不计入 67 的统一后 Tier-S 附录。每行均登记初始政治处境、现有精确内容、净新增/目标任务量、新增事件量、独特关键词、内部危机、失败后架空成功、统一遗产、既定共享接口、主要史料和重复风险。现有 28 条八章运行计划保持原权威边界，A1 只读取其基线，不提前改写任务生成物。
- Evidence/Runtime: `build_daimyo_depth.py --check` 通过，新增 5 项定向测试验证 67/37/30 集合、`16/13/38` 分层、来源与接口解析、生成报告逐字节一致及重复 tag mutation 拒绝。报告为 `DESIGN_ONLY`，A2-A5 gameplay 尚未实现；未启动 EU4/Launcher，未修改 Documents、runtime acceptance、oracle、visualizer 或 installed skill，`JXP-019` 保持 `IN_PROGRESS`。

### 2026-07-16 - AGENT-B-OVERSEAS-BATCH-019 - Register colonial and continental program (`no version bump`)

- Status: `STARTED; TODO_REGISTERED; B0_AUDIT_IN_PROGRESS; NOT_RUNTIME_PROVEN`。
- Scope: 根据 Agent B 的 `B0–B16` 执行请求新增 `JXP-031`–`JXP-036`，分别承载殖民社会、殖民国家与独立、殖民战争/东归、大陆经略、朝鲜战争及中国/天命/八纮一宇平衡。旧 `JXP-011` 保持 `DONE`，只代表既有太平洋循环，不被重开或冒充新殖民工程。Agent B 只编辑 `jxp_b_*` 专属 gameplay/localisation/tests 和向 A 提交最小接口；不写总账、ideas、history、Agent A missions、净土真宗/佛教路线、陪臣或日本内部战争文件。
- Runtime/TODO: 六项均为 `IN_PROGRESS / CODEX_B`；当前 runtime matrix 尚未登记新场景，静态实现完成后由 A 统一扩展验收、合并理念源和联合门禁。未启动 EU4/Launcher，未修改 Agent B 工作区。

### 2026-07-16 - AGENT-A-INTERNAL-DEPTH-018 - Start daimyo depth and religion program (`no version bump`)

- Status: `STARTED; A0_WORKTREE_AUDITED; DESIGN_MATRIX_PENDING; NOT_RUNTIME_PROVEN`。
- Scope: 接收 `Agent_A_日本内部与宗教系统_Prompt.md` 的 A0–A13 工程。当前分支 staged/unstaged 均为空，唯一 untracked 是用户提供的 Prompt；其所称净土真宗、IJP/WAK gate、subject、姓名与 ODA/TOY 理念候选已在既往提交中落地，不存在可直接拆分的未提交 gameplay 草稿。继续使用 `JXP-019/024/025/026`，将 IJP 循环 `JXP-009` 转交 `CODEX_A`，新增 `JXP-027`–`JXP-030` 承载陪臣、日本内部战争成本、净土真宗与佛教日本；Agent B 海外独占文件保持只读。
- Evidence/Boundary: 已完整读取 repo/installed skill、root/main/map AGENTS、总账、地图 baseline/contract、最新主/地图报告及 RSMTS；descriptor 与只读 `launcher-settings.json` 均固定 `EU4 v1.37.5.0 Inca (491d)`。尚未修改 gameplay、生成器、运行验收或 Documents，未启动 EU4/Launcher；下一步先交付 67 家设计矩阵与技术能力审计，再按小提交切片实施。

### 2026-07-16 - PACIFIC-CHARTER-BALANCE-017 - Remove diplomatic technology gate (`no version bump`)

- Status: `STATIC_PASS; PAYLOAD_COMMITTED; DAILY_DEPLOYED; COMPATIBILITY_CONVERGED; ORACLE_REBUILD_REQUIRED; PENDING_RUNTIME`。
- Scope: 用户反馈太平洋敕许状的外交科技 12 门槛过苛。运行时 payload `914129bc004ab1ba5a87a94cd423d5061361b438` 同时移除 `jxp_decision_charter_pacific` 的决议允许条件和 `jxp_mission_pacific_charter` 无既有敕许旗标时的替代完成条件中的 `dip_tech = 12`；港口数、海门外学、前置任务、殖民者/马尼拉航路/太平洋中继站准备以及金钱与外交点成本均保持不变。未改后续太平洋任务各自的科技进度，也未改 localisation、地图或旧存档状态。
- Evidence: 改动前相关基线 `15/15`，改动后定向回归 `16/16`；主门禁 `28/28`、Clausewitz `286/286`、完整 validation suite `328/328`。联合地图门禁的 map/history/content/main-compatibility/assets 五段均为 `0 errors / 0 warnings`，随后按设计在 `build_runtime_oracles.py --check` 报告新玩法字节导致的 oracle drift；本切片未重签旧 candidate、runtime matrix 或 oracle，也未把该预期漂移写成联合门禁通过。部署后兼容副本 `--check` 为 `73 patches / 0 issues / 9aa739e4...87810`，active-playset audit 为 `4 layers / 638 runtime files / 73 collisions / 0 divergent / 0 stale / 0 issues`。
- Runtime/Deployment: 在确认目标等于旧 payload、无第二提供者且所有 EU4/Launcher 进程停止后，仅原子替换 Documents 主 Mod 的两份目标文件；旧字节备份位于 `mod/_jxp_backups/pacific_charter_tech_gate_20260716_154209`。未写 `C:\JXP_Acceptance`、playset、Launcher 数据库或兼容副本，未启动 EU4、Launcher、dowser 或 observer。因此 `JXP-BUG-PACIFIC-CHARTER-TECH-001` 保持 `IN_PROGRESS`；正式 runtime evidence 前仍须重建两阶段候选与 oracle，并在任务/决议 UI 目视确认无外交科技条件。

### 2026-07-16 - LAUNCHER-VERSION-METADATA-016 - Align deployed descriptors with EU4 raw version (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; LAUNCHER_RESCAN_PENDING; NOT_RUNTIME_PROVEN`。
- Scope: 本机 `launcher-settings.json` 固定游戏为 `EU4 v1.37.5.0 Inca (491d)`、`rawVersion = v1.37.5.0`，而主 Mod、地图 Mod 与本地中文兼容副本仍输出 `supported_version="1.37.*"`。运行时提交 `7947b15dc1af8e245dcf68a3732ae19073cacde6` 将主/地图内层 descriptor 精确钉到 `v1.37.5.0`；控制提交 `63c318d2a925a74cd8ae7080398040ec0aa9805c` 同步外层 descriptor、兼容副本权威生成器与定向回归测试，未改玩法脚本、版本号、playset 或 Launcher 数据库。
- Evidence: descriptor/兼容生成定向测试 `2/2`、共享总账一致性测试 `1/1`；兼容副本 `--check` 为 `5,767 files / 20,853,689 bytes / 9aa739e4...87810 / 73 patches / 0 issues`；active-playset audit 为 `4 layers / 638 runtime files / 73 collisions / 73 converged / 0 divergent / 0 stale / 3 review artifacts`。部署后逐文件只读核对主、地图、兼容副本的六份内外 descriptor，均为精确 `supported_version="v1.37.5.0"`；daily main 为 `419 files / 59,395,555 bytes / b98e3e65...1cf0`，map 为 `244 files / 82,631,535 bytes / 64b22f99...516`。
- Deployment/Risk: 主/地图旧 descriptor 备份位于 `mod/_jxp_backups/descriptor_warning_fix_20260716_142033`；兼容副本旧目录与外层 descriptor 备份时间戳为 `20260716_142054`。未启动 EU4、Launcher、dowser 或 observer，未写 `launcher-v2.sqlite` 或 `dlc_load.json`；只读查询确认当前 Launcher 缓存的三条 JXP `requiredVersion` 仍为旧 `1.37.*`，因此黄色警告的 UI 消失仍须用户下次启动 Launcher 触发重新扫描后目视确认。

### 2026-07-16 - AGENT-AB-MERGE-DEPLOY-015 - Merge current Agent A/B slices and deploy daily runtime (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; COMPATIBILITY_CONVERGED; NOT_RUNTIME_PROVEN`。
- Scope: 在 `codex/content-agent-a` 以非快进合并 Agent B 提交 `94e1437`，形成合并提交 `3721b2c`，保留 B 工作树中的未跟踪计划/摘要文件且未触碰受保护的生产工作树。随后补齐大名阶段改革测试分类，按运行白名单原子部署主 Mod 与地图 Mod，并因新增日本文化姓名注册表使中文补充兼容碰撞从 72 增至 73，固定 `00_cultures.txt` 与 `00_country_ideas.txt` 均由主 Mod 提供后重建兼容副本。
- Evidence: 合并定向测试 `104/104`；五个权威生成器 `--check` 无漂移；主内容 gate `28/28`、Clausewitz `286/286`；旧全量 wrapper 的其余 325 项通过，唯一旧分类常量失败已由定向 `1/1` 修正，未重复运行完整 mutation suite。日常部署树为 main `419 files / 59,395,552 bytes / 83291f26...a0d1`、map `244 files / 82,631,532 bytes / 157407eb...b1c7f`；兼容 payload `5,767 files / 20,853,686 bytes / 02be8392...b04209`，`73/73` provider 收敛。active-playset audit 为 `4 layers / 638 runtime files / 73 collisions / 0 divergent / 0 stale / 3 review artifacts`，五个 ODA/TOY 书签哨兵通过。
- Deployment: 旧主/地图目录备份为 `mod/_jxp_backups/japan_expanded_v2_before_agents_merge_20260716_135810` 与 `japan_expanded_v2_map_before_agents_merge_20260716_135810`；旧兼容目录与外层 descriptor 备份时间戳为 `20260716_140238`。未写 `dlc_load.json`、`launcher-v2.sqlite` 或 playset，未启动 EU4/Launcher。
- Runtime/TODO: 本条仅证明静态字节、日常部署和外部 provider 收敛，不构成 R1-R12 或任何 `RUNTIME_PASS`。`JXP-018/019/024/025/026` 及相关缺陷继续 `IN_PROGRESS`；新 runtime evidence 前仍须形成矩阵绑定的两阶段候选、完成 preflight，并取得新的明确启动授权。

### 2026-07-16 - PLAYTEST-FEEDBACK-A-SLICE-014 - Finalize five gameplay repairs and ODA/TOY idea rebalance (`no version bump`)

- Status: `STATIC_PASS; SIX_CHANGES_IMPLEMENTED; TODO_AND_DEFECTS_STILL_IN_PROGRESS; NOT_RUNTIME_PROVEN`。
- Scope: 完成高成本且每国一次的普通宣旨、IJP/WAK 严格史实入口与净土真宗同步、三项统一前日本改革、选择性 CTA 的“上洛”战争、三种日本文化的 56 姓氏扩充，以及织田/丰臣权威理念源与唯一运行注册表的差异化强化。宣旨文案明确普通宣称按通常规则消逝，十年只描述附带国家修正；上洛文案明确幕府付出人情或关系代价逐一召集，不声称大名自行判断是否参战。
- Evidence: 理念、幕府 subject contract、日本文化姓名及 gameplay 姓名生成器 `--check` 全部通过；`test_playtest_feedback` 6/6，理念/姓名/IJP/WAK/丰臣定向测试 66/66，政府身份定向测试 2/2；主 Mod 静态 validator 28/28（Clausewitz 286/286），地图 `validate_main_compatibility.py` 为 0 error/0 warning。
- Runtime/TODO: `JXP-024/025/026`、相关五个稳定缺陷、`JXP-018/019` 均继续 `IN_PROGRESS`。本轮未启动 EU4/Launcher、未部署 Documents、未修改 runtime acceptance/oracle/visualizer/installed skill；战争 CTA、AI 自然行为、宗教/改革/姓名 UI 与理念实战平衡仍待后续获准运行证明。

### 2026-07-16 - PLAYTEST-FEEDBACK-FIRST-FIVE-013 - Complete static repair of first five gameplay feedback items (`no version bump`)

- Status: `STATIC_PASS; FIVE_FIXES_IMPLEMENTED; NOT_RUNTIME_PROVEN`。
- Scope: 将“请下宣旨”改为高资源、一次性普通宣称；以严格年代/文化/地域/准备度约束 IJP/WAK 并为 IJP 接入净土真宗；在原版君主制层级加入三项统一前日本改革；把幕府挑战显示为“上洛”并改为选择性召集大名；通过固定原版文化文件哈希的生成器向三种日本文化加入 56 个常见姓氏。
- Evidence: 相关生成器 `--check`、56 项定向测试、主/地图 Clausewitz 解析、主验证门禁与主+地图兼容检查通过；生成器源、运行文件、本地化 source/active 和地图兼容契约一致。本轮未启动 EU4、未修改 Documents、Launcher 或 runtime acceptance。
- Runtime/TODO: 五个稳定缺陷继续保持 `IN_PROGRESS`；战争双方、宗教/改革 UI、自然 AI 与姓名实际显示仍须后续获准运行证明，且需由 runtime matrix 所有者登记对应新场景。

### 2026-07-16 - PLAYTEST-FEEDBACK-FIRST-FIVE-012 - Start first gameplay feedback repair slice (`no version bump`)

- Status: `STARTED; ROOT_CAUSES_LOCATED; IMPLEMENTATION_IN_PROGRESS; NOT_RUNTIME_PROVEN`。
- Scope: 领取用户试玩反馈前五项。已定位“请下宣旨”与政府互动共同调用全日本永久宣称效果；IJP/WAK 成立入口分别允许低秩序八城与任意五港，且宽泛日本政体 trigger 把 Ainu 纳入；IJP 转换没有宗教同步；统一前改革没有任何 JXP 专属候选；幕府夺取战争继承原版 daimyo subject 自动加入宗主防御战；默认日本文化王朝池只有少量皇室/贵族姓氏。
- Evidence: 本条仅记录用户 `USER_OBSERVED` 反馈与静态根因，不声称修复完成。新增 `JXP-024/025/026` 及五个稳定缺陷 ID；本轮不启动 EU4、不修改 Documents 或 Launcher。
- Runtime/TODO: 实现后只运行相关生成器、定向测试、Clausewitz 与联合兼容检查；关键战争双方、宗教 UI、改革 UI 和自然 AI 行为仍须后续获准运行证明。

### 2026-07-16 - ACCEPTANCE-DEPLOYMENT-011 - Materialize immutable acceptance snapshots (`no version bump`)

- Status: `CONTROL_COMMITTED; PREFLIGHT_PASS; ACCEPTANCE_DEPLOYED_NOT_ENABLED; DAILY_DEPLOYMENT_BLOCKED; NOT_RUNTIME_PROVEN`。
- Scope: 从 clean control plane `42e1bd300ba9a90d8b9e49b1e50ec98dfa4057a7` 对 payload `80637e065881f0bac4fd424e0c6100c19e8f5da7` 执行 production preflight，确认 candidate ancestry、runtime-whitelist diff、完整主/地图 manifest、12/12 game/protocol pins 与零相关进程；随后只在 `C:\JXP_Acceptance` 物化 current main+map 和 current-main 不可变快照，未启用 playset。
- Evidence: candidate/live manifests 为 main `411 / 493026a899e5428645964f2018b78c094e02603465408b5d855a7044a8e6cd78`、map `244 / 1d4b8a86243cb27bb1cb7dafe933805f74d662bc3ef6339f595a37287b62779e`，全部 matched；acceptance fingerprints 为 main `1e4f354011129db0a080250f63c194e16873e9aa412f7acfa3b8a7171bac6594`、map `fcd80cd21a817d158ceb02e388a181dc4fdf275ebab4ed202d568abf1e4f4a75`。两次 deploy 均返回 `deployed_not_enabled`、`game_started=false`、`launcher_configuration_modified=false`。
- Runtime/TODO: 日常 Documents 仍是 superseded payload ecb33c1，中文兼容副本也仍对应旧部署。`C:\Users\Fiber Memory\Documents\GitHub\JapMod` 的他人未提交地图改动按计划原样保护；在其所有者提交/释放前，不执行日常原子替换、不重建日常兼容副本，也不启动 EU4。所有 defect/TODO 状态不变。

### 2026-07-16 - CONTROL-RECLOSURE-010 - Rebuild oracle and close static integration (`no version bump`)

- Status: `STATIC_RECLOSURE_PASS; CONTROL_COMMIT_PENDING; NOT_DEPLOYED; PENDING_RUNTIME`。
- Scope: 将 runtime matrix 固定到 payload `80637e065881f0bac4fd424e0c6100c19e8f5da7`，更新部署示例与总账；因 Agent B 的任务奖励源和 Agent A 的地图迁移源改变，按权威源重建 R12 oracle，而不是手改生成 JSON。未改变 payload A 之后的任何 runtime-whitelist 字节。
- Evidence: runtime oracle pack 为 `aa5b986456803b17f0d5bbea92e343e214f5320411def0fff0c20a840f8a30ab`，`--check` current；matrix 为 `7982e496a9b09c34b4fcd017633a3752ae4de6a9d6fc649badda059d552219e2`；acceptance helper `73/73`、总账专项 `14/14`。repo/installed `eu4-modding` skill 均为 `Skill is valid!`，12 个源文件逐字节一致。唯一一次无 skip 联合门禁 exit 0：地图、历史、内容、主兼容和资产均 `0 errors / 0 warnings`，覆盖 88 省、137,382 个日期与 `515 events / 290 decisions / 416 scripted callables / 957 modifiers`；其内嵌主门禁仍为 `28/28`、Clausewitz `283/283`、`317/317`。
- Runtime/TODO: 尚未执行 production preflight、兼容副本重建或 acceptance/Documents 部署；受保护 production 工作树仍有他人未提交地图改动。没有启动游戏，也没有关闭任何 defect 或 TODO；控制面提交后下一步仍是等待该工作树被其所有者释放，再安全部署并请求新的启动许可。

### 2026-07-16 - CONTENT-INTEGRATION-009 - Seal daimyo ideas and Toyotomi government payload (`no version bump`)

- Status: `PAYLOAD_COMMITTED; TARGETED_STATIC_PASS; CONTROL_RECLOSURE_IN_PROGRESS; NOT_DEPLOYED; NOT_RUNTIME_PROVEN`。
- Scope: 确认 Agent B 的最终奖励/八纮一宇本地化提交已在 `codex/content-agent-a` 祖先链中，并保持其任务、事件、改革和路线范围只读。Agent A 封存唯一理念注册表、主/地图大名首次精确分配、终局旧理念清理、地图 `v014` 事务重试，以及 TOY 关白/太阁专属政体与 1586/1598 等日期历史接线；最后把理念 repair marker 改为“清旧 marker → 收敛 exact group → 成功后重设”的可重试事务。production 工作树中的未提交地图构建改动未被 reset、覆盖、暂存或夹带。
- Evidence: 理念、TOY 历史、姓名与大名任务四个权威生成器均 `--check` 无漂移；Agent A 定向测试 `77/77`，事务顺序专项 `14/14`；主门禁 `28/28`、Clausewitz `283/283`、完整单测 `317/317`。immutable runtime payload 为 `80637e065881f0bac4fd424e0c6100c19e8f5da7`；本条尚未声称最终 no-skip 联合门禁、兼容副本、preflight 或部署通过。
- Runtime/TODO: 未启动 EU4、Launcher、dowser、bootstrapper 或 observer，未修改 Documents、日常 playset 或 Launcher 数据。`JXP-BUG-IDEA-FALLBACK-001` 与 `JXP-BUG-TOY-GOVERNMENT-001` 仅完成静态修复，仍为 `OPEN`；Agent A 的八项 TODO 均保持 `IN_PROGRESS`，下一步是控制面收口、联合门禁、兼容重建和安全部署，之后仍须新的明确启动许可。

### 2026-07-15 - RUNTIME-DEFECT-INTAKE-008 - Record four user-visible regressions (`no version bump`)

- Status: `RECORDED; OPEN; NOT_FIXED; RUNTIME_REPORTED`。
- Scope: 将用户对当前部署的四项实际游戏审阅写入共享缺陷队列：全部大名进入游戏后回退默认理念；大名任务奖励反复硬设三项时代属性；丰臣家初始政治改革仍为自由选择而非固定历史政体；“八纮一宇”改革未正确显示中文。
- Evidence: 本条仅登记用户直接运行时报告，尚未取得新截图、fresh logs、存档或代码根因，不将此前静态门禁外推为这些问题已解决。四项分别关联 JXP-019/020、JXP-014/019、JXP-018/022、JXP-021/023。
- Runtime/TODO: `JXP-BUG-IDEA-FALLBACK-001`、`JXP-BUG-ERA-REWARD-001`、`JXP-BUG-TOY-GOVERNMENT-001`、`JXP-BUG-HAKKO-LOC-001` 均为 `OPEN`；下一开发窗口应先复现并修复 P0 理念、TOY 政体和八纮一宇本地化，再处理任务奖励语义。未启动 EU4，未更改 Documents 或 Launcher。

### 2026-07-15 - DEPLOYMENT-CLOSURE-007 - Commit and deploy identity/EoC candidate (`no version bump`)

- Status: `PAYLOAD_COMMITTED; CONTROL_COMMITTED; DEPLOYED_NOT_LAUNCHED; PROVIDER_CONVERGED; PENDING_RUNTIME`。
- Scope: 玩法 payload `ecb33c185fa3ebaf9f51f61e2ab9ab5ab1b096b7` 与控制面 `b257eb7e8072695fa98d0151eb3584ea84dc5ca0` 完成两阶段提交。production preflight 证明 candidate ancestry、clean worktree、runtime diff empty 和 12/12 pins；生成 `current` main+map 与 `current-main` 认证快照后，将同一运行时字节原子覆盖到日常 Documents，旧主/地图备份于 `mod/_jxp_backups/20260715_202030_ecb33c1`，并恢复最新三项 visualizer 审阅工件。
- Evidence: helper runtime manifests 为 main `409 / c365e0784a4f1e7adbb8dfc75709d3656f8ec3ccb43d38428fc6319221f61d04`、map `244 / db7ab35aa9f1c855beca66e40ac7c646ccb92eede83eb9364698ca06191aaa12`；认证 fingerprints 为 `0f292b4cba2256ee0c0cd304d88c846b719a18345e2dd347f97796037883f0ba` 与 `733bef66ea37769c8c5bd35324f0971bf2505743b7c41595232a1f64d9ac317c`。中文兼容 payload 为 `5,767 files / 22,185,723 bytes / f1d48f029d985d06610aea5cd9344f54b1f9c09c2a17b5188a0604a18dc939be`；active-playset audit 为 `4 layers / 631 runtime files / 72 collisions / 72 converged / 0 divergent / 0 stale / 3 review artifacts`，五个 ODA/TOY 书签哨兵与 area label 均无问题。
- Runtime/TODO: `game_started=false`、`launcher_configuration_modified=false`。本次未完成被中止的完整 no-skip 联合重跑，也没有新增运行时证明；主门禁 `28/28`、Clausewitz `281/281`、完整 mutation `306/306`、runtime helper `73/73` 和最后理念身份 focused `13/13` 是当前静态依据。JXP-002/022/023 继续 `IN_PROGRESS`，下一次启动仍须新的明确用户授权。

### 2026-07-15 - IDENTITY-EOC-REGISTRY-002 - Seal fresh-start identities and dual-state Mandate (`no version bump`)

- Status: `PAYLOAD_COMMITTED; TARGETED_STATIC_PASS; CONTROL_RECLOSURE_IN_PROGRESS; NOT_DEPLOYED; NOT_RUNTIME_PROVEN`。
- Scope: 封存玩法 payload `ecb33c185fa3ebaf9f51f61e2ab9ab5ab1b096b7`。保留 39 个非法 basic-reform 载体的新局修复；将地图 30 国理念并入唯一 488 组 exact-path 注册表尾部，并以历史 origin flag + daimyo-stage 双门防止终局叠加；船名池改为 960 个全 VFS 大小写不敏感唯一 ASCII 名称；88 省核心动作按全时间线模拟并保持原版延迟核心语义。日本天子固定保留原版 `celestial_empire`，十个终局状态通过互斥 triggered modifier 镜像原 tier-one 三项数值，capstone 任务和 Mandate gain/loss 均使用双态 canonical sync。可视化审阅器同步展示政治改革、非天朝权力结构和天朝镜像三层，并内嵌 20 个图标。
- Evidence: visualizer `7/7`、final-state `39/39`、government-identity `8/8`、map/daimyo/ship/core/idea `29/29`、runtime/oracle helper `73/73`。总账写回后主门禁 `28/28`、Clausewitz `281/281`、完整 mutation `306/306`，repo/installed skill 均为 `Skill is valid!`。最后修复的联合理念身份审计使用顶层 group 解析 direct tag 与 origin flag，focused suite `13/13`、direct combined compatibility `0 errors / 0 warnings`。runtime matrix 为 `a40f5e78e077239bce92e6ad783d4e0ab8417642e6c007a891345a80b5cac4ea`，oracle pack 为 `27dfc6e39377e095bcdbc5d6f0e4ee5abab4c1c8fa8759568f1fcc1123b59da9`；完整 no-skip 联合门禁被用户中止，本条不冒充其已通过。
- Runtime/TODO: 本条没有启动 EU4，且 prior single-launch authorization 已消耗；部署后也必须等待新的明确启动许可。按用户要求，39-carrier 身份修复不处理已污染旧档。另行承诺的 JXP-002/022/023 仍保持 `IN_PROGRESS`：旧 `v014/v0280/v0283/v0260` 标记后的理念或 EoC 双态错位尚无 markerless/事务式 startup convergence，属于明确 P0，不能记为迁移闭合。

### 2026-07-15 - GOVERNMENT-IDENTITY-HOTFIX-001 - Restore daimyo monarchy identity (`no version bump`)

- Status: `PAYLOAD_COMMITTED; STATIC_RECLOSURE_PASS; CONTROL_COMMIT_PENDING; AUTHORIZED_NOT_STARTED; NOT_DEPLOYED`。
- Scope: 将 39 个误用 `basic_reform = yes` 的 JXP 隐藏载体全部退出政府类别语义：27 个 0.23.2 路线载体与全日本/海洋载体成为 inert tombstone，海洋独有奖励并入既有国家 modifier；十个终局 power structure 改为注册在原版一级层的互斥合法改革。基于 pinned 1.37.5 完整 monarchy reform 文件，仅给真实 `shogunate`、`daimyo`、`indep_daimyo` 加入日轮国体 mechanic；所有终局 direct add 收敛到 exact-state canonical sync。按用户指示不引入旧档修复迁移，只保证新开局。
- Evidence: runtime payload `0dade903b41ce7e8da7ee919a60b3f1c14f2db7b` 已提交。主结构门禁 `28/28`、Clausewitz `280/280`；新身份检查为 main `37/37` + map `30/30`，即 `66 daimyo + 1 shogunate`，另有 RYU `monarchy + autocracy` 与 TOY 历史控制。完整 core mutation suite `287/287`，runtime/oracle helper suite `73/73`；包括毛利共和国、1444 前日期块、提前终局改革、缺失 mechanic 与 RYU 每日重试回归。runtime oracle 已按新 payload 重建；无跳过联合门禁 exit 0，地图/历史/内容/兼容/资产均为 `0 errors / 0 warnings`。
- Runtime/TODO: 用户已授权一次 EU4 启动，但尚未使用。控制面提交和部署完成后，在同一 main+map 进程中验证 MRI/OTM/RKK 的 monarchy+daimyo+legitimacy+正确任务/理念，ASK 的 shogunate/JXP 双 mechanic，RYU 的 autocracy/legitimacy/无 JXP retry，以及一个终局改革；退出后读取 fresh logs。没有真实 UI/log 前不关闭 JXP-001/JXP-005/JXP-019。

### 2026-07-15 - DAIMYO-DEPLOYMENT-003 - Exact payload deployment (`no version bump`)

- Status: `DEPLOYED_NOT_LAUNCHED; PROVIDER_CONVERGED; STATIC_PASS; PENDING_RUNTIME`。
- Scope: 以 clean control plane 对 immutable payload `3f4e29bf4e69f41db49e6821070e6a83c34f59c2` 完成 production preflight，并在 `C:\JXP_Acceptance` 生成 current main/map 与 current-main 认证快照。随后从认证快照将 0.28.1 主 Mod 与 0.1.4-alpha 地图 Mod 原子替换到日常 Documents；旧目录完整备份为 `mod/_jxp_backups/20260715_045804_daimyo_0281`。纯 runtime 替换后另行恢复三项主可视化审阅工件，重建本地中文补充兼容副本并保持原 Workshop 补充项禁用。
- Evidence: preflight 证明 candidate ancestor、clean repository、runtime-whitelist diff empty、12/12 pins 和零相关进程。主/地图 runtime manifests 分别为 `407 / 3acf0650ad5edefc62996dae6516ece66a3ac7405fb6a90876b68828744f926f` 与 `245 / e68e737809204bf23f2684c6d439bec034ffc09af27cd0b8c5d9016b92637b08`，repo、isolated 与 daily 三面逐字节一致。兼容副本为 `5,767 files / 22,159,205 bytes / 68815c49ecbbbddb3f3fe409fa1f16f0b0c6615e41f753445aea7a8b8372a21a`，72 patches、39 history、39 country-name 与 5 token hotfix 均通过。daily audit 为 `4 layers / 630 runtime files / 72 converged / 0 divergent / 0 stale / 3 current review artifacts`；五个 1586/1598/1600/1615 ODA/TOY 哨兵无回归。整个过程 `game_started=false`、`launcher_configuration_modified=false`。
- Runtime/TODO: 未启动 EU4、Launcher、dowser、bootstrapper 或 observer，也未读取新部署产生的引擎日志或把静态部署写成运行通过。JXP-019 继续 `IN_PROGRESS / CODEX_A`；下一步必须由用户重新明确授权启动后执行 PROBE 与 R2/R12，验证新战役任务列、旧档进度迁移、保存重载和 fresh log。

### 2026-07-15 - DAIMYO-MISSION-IMPLEMENTATION-002 - Exact Tier-A identity branches (`0.28.1` + `0.1.4-alpha`)

- Status: `STATIC_PASS; PAYLOAD_COMMITTED; CONTROL_PLANE_IN_PROGRESS; NOT_DEPLOYED; PENDING_RUNTIME`。
- Scope: 将 JXP-019 从“每个大名有非通用六章家系模板”提升为可执行的强度分层。主 Mod 的 ASK/CSK/DTE/HJO/IMG/MRI/OTM/OUC/SMZ/SOO/TKD/TKG/UES 与地图 Mod 的 ARI/AZI/HNG/KRD/MOG/MTS/MTU/MYO/NBS/RKK/RZJ/STM/STO/TGR/UKT 各获得精确 tag、slot 3、八阶段历史支线；其余 30 个地图大名和主 Mod 次级大名继续使用互斥共享家系列。单一 JSON 计划确定性生成任务、触发器、修正、本地化、清理与一次性迁移；迁移在刷新前记录旧六章完成深度，执行 canonical immediate + delayed swap 后再回放对应新任务。runtime fingerprint 除要求正确新锚点外，显式拒绝四个通用任务锚点、旧共享家系列和异家专属列。
- Evidence: immutable runtime payload 为 `3f4e29bf4e69f41db49e6821070e6a83c34f59c2`。主门禁 `27/27`、Clausewitz `279/279`、任务 `413 IDs / 57 series / 192 profiles`；67 个可选大名、268/268 tag-DLC 画像、28/28 Tier-A 精确八章分支、559 flags 与 957 modifiers 均通过。核心变异测试 `278/278`，runtime/oracle helper `72/72`。无 skip 联合门禁 exit 0：地图/历史/内容/兼容/资产均 `0 errors / 0 warnings`，30 个地图 tag x 4 DLC 状态为 15 个专属八章 + 15 个共享家系画像，联合可视化为 `566 missions / 77 series` 且 0 缺失本地化。repo/installed skill 已同步并通过 `Skill is valid!`。
- Runtime/TODO: 未启动 EU4、Launcher、dowser、bootstrapper 或 observer。JXP-019 保持 `IN_PROGRESS / CODEX_A`；仍须完成控制面提交、provider convergence 与 Documents 原子部署，并在新的明确启动许可后以 R2/R12 证明 MRI/OTM/RKK 等新战役 UI、旧档六章进度迁移、保存重载和 fresh log 均无通用回退、任务消失、断线或异家残留。

### 2026-07-15 - DAIMYO-MISSION-AUDIT-001 - Reopen all-daimyo mission coverage (`no version bump`)

- Status: `IN_PROGRESS; STATIC_ROOT_CAUSE_CONFIRMED; PENDING_IMPLEMENTATION; PENDING_RUNTIME`。
- Scope: 根据玩家对毛利任务树的实测反馈复核全部 67 个主/地图可选大名。现有新战役抽象拓扑虽能给每个 profile 填满五列，但除织田/丰臣外，主 Mod 十三个 Tier-A 大名和地图十五个 Tier-A 大名仍与同家系标签共用六任务 slot-3 模板；旧 `JXP-019` 的“历史重要大名拥有更深专属分支”验收并未由验证器执行，故此前 `DONE` 结论回退。另发现 mission runtime fingerprint 只检查每列一个正向 anchor，未拒绝旧档中残留的 vanilla generic series，不能单凭 fingerprint 证明保存档树已净化。
- Ownership: `JXP-019` 重开为 `IN_PROGRESS / CODEX_A`；本窗口接管本轮主/地图大名任务、fingerprint、迁移、验证器、本地化、可视化与部署。B 链保持冻结，不并发改写这些路径。
- Runtime/TODO: 本条只记录已确认的合同缺口；尚未改 gameplay，也未启动 EU4、Launcher、dowser、bootstrapper 或 observer。完成实现和全静态门禁后，仍须取得新的明确启动许可，逐类验证毛利及全部大名的新战役 UI、旧档刷新、保存重载和 fresh `error.log`，才可把 `JXP-019` 再次标为 `DONE`。

### 2026-07-15 - LEDGER-HANDOFF-001 - Current candidate reconciliation (`no version bump`)

- Status: `CONTROL_PLANE_RECONCILED; STATIC_PASS; RUNTIME_UNCHANGED; PENDING_USER_APPROVAL`。
- Scope: 将 `Handoff Delta` 从混杂 A2/A3、旧 PROBE、旧隔离指纹的历史叙述收敛为当前唯一身份：last preflighted control plane `210a89e...b8fa`、immutable payload `9a245ad8...e814ac`、401/239 runtime manifests、72 条兼容碰撞与 14 条待运行闭环。旧候选和失败/中止 PROBE 仍完整保留在本 Journal 中，但不再作为当前交接事实。同步把 JXP-018 与 Known Risks 的现行 provider-convergence 口径从 71 修正为 72；未改任何运行时脚本、资产、descriptor、playset 或 Documents 部署。
- Evidence: 变更前工作树 clean；payload 是当前 HEAD 祖先，runtime-whitelist diff empty。收敛后主门禁 `27/27`、Clausewitz `274/274`、全量 validation `276/276`，无 skip 联合地图门禁 exit 0，地图/历史/内容/兼容/资产均 `0 errors / 0 warnings`。第一次主门禁在 Journal 尚未补入时仅以 `ledger.journal_snapshot_date` 失败，其余 `26/27` 全通过；补入本条后守卫恢复闭合。随后在 clean `ce2ebb5...e7629` 上复跑 production preflight：candidate ancestry、401/239 live manifests、12/12 pins、runtime diff 与 process guard 全通过，`ready_for_safe_deploy=true`；R5 escrow 为 `ADMITTED_STATIC_INPUT`。兼容副本独立 `--check` 为 `72 patches / 0 issues`，daily audit 为 `4 layers / 618 runtime files / 72 collisions / 72 converged / 0 divergent / 0 stale / 3 review artifacts`。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer，也没有生成当前 payload 的新日志、UI、存档或重载证据。九项已完成 TODO 不回退；`JXP-001/002/004/005/008/009/010/016/017/018/020/021/022/023` 保持 `IN_PROGRESS`，下一步仍须取得新的明确启动许可后执行 PROBE 与 R1-R13。

### 2026-07-14 - DEPLOYMENT-CLOSURE-005 - Exact payload and provider convergence (`no version bump`)

- Status: `DEPLOYED_NOT_LAUNCHED; PROVIDER_CONVERGED; STATIC_PASS; PENDING_RUNTIME`。
- Scope: 从 clean control plane 对 payload `9a245ad8de85b22d4023644eee0b831c18e814ac` 执行 production preflight，生成隔离 `current` 与 `current-main` 不可变快照，并将同一主/地图 payload 原子写入 daily Documents。旧主/地图目录保存在 `mod/_jxp_backups/20260715-014313_0a34ac0184`。纯 runtime snapshot 不含审阅工具，故另将 `generate_visualizer.py`、`jxp_visualizer.html`、`test_generate_visualizer.py` 作为非运行时伴随工件逐字节恢复到 daily main，并把三者纳入 active-playset 守卫。单文件理念注册表使中文补充 Mod 的真实碰撞数由 71 增至 72；compat builder 现明确要求 `common/ideas/00_country_ideas.txt` 由主 Mod 提供，而不是只放宽计数。
- Evidence: preflight 证明 candidate ancestor、clean repository、runtime diff empty、12/12 pins 和零相关进程；隔离 main/map 指纹分别为 `a6db6b6f...68330`、`f714b153...1132`。compat rebuild 与独立 `--check` 均为 `72 patches / 39 history / 39 country-name / 5 token hotfix / 0 issues`，payload identity `68815c49...2a21a`。daily active-playset audit 为 `4 layers / 618 runtime files / 72 collisions / 72 converged / 0 divergent / 0 stale / 3 current review artifacts`；五个 ODA/TOY 哨兵均无 post-1586 ODA，TOY 计数 `26/33/1/1/0`。可视化 HTML 为 `39,191,393` bytes、SHA-256 `06231aff...b732`。部署守卫专项 `6/6` 通过；部署后主门禁 `27/27`、Clausewitz `274/274`、全量 `276/276`，无 skip 联合门禁 exit 0，地图/历史/内容/兼容/资产均 `0 errors / 0 warnings`。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer，没有采集新的 setup/error/game 日志，也没有把静态部署升级为运行证明。`JXP-001/002/004/005/008/009/010/017/018/020/021/022/023` 与持续流程项 `JXP-016` 均保持原状态；下一步仍须取得新的明确启动许可后从 PROBE/R1-R13 继续。

### 2026-07-14 - CANDIDATE-PAYLOAD-004 - Ideas and exact-profile reform payload (`no version bump`)

- Status: `STATIC_PASS; PAYLOAD_COMMITTED; CONTROL_PLANE_IN_PROGRESS; NOT_DEPLOYED; PENDING_RUNTIME`。
- Scope: 创建 immutable payload `9a245ad8de85b22d4023644eee0b831c18e814ac`。理念运行面由五个分散文件收敛为唯一生成的 exact-path `common/ideas/00_country_ideas.txt`；十项终局政治改革进入原版 `absolute_rule_vs_constitutional` 层并有 0.28.3 一次性旧档迁移。27 项路线改革的 `potential` 从 broad Japanese 改为 exact final-state + self fallback，并补 TOY 保持 tag 时的锁国/开国精确分支。R3/R4/R6/R8/R13 分别扩展到实际采用改革、真实 pre-political 0.28 迁移、八条神道桥双阶段、自然 AI 惣门行为及十七父链。终局改革另固定精确 20 项 modifier manifest，修正 WAK 的 `navy_tradition` 键；可视化生成器新增完整的十改革审阅页与内嵌 PNG。
- Evidence: payload 后 runtime-whitelist diff empty；理念生成器 `--check` 与 `13/13` 专项通过，注册表为 `457/457 unique groups / 45 authored / 34 replacements / 1 runtime file`。Agent B 冻结切片 `95/95`，主门禁 `27/27`、Clausewitz `274/274`、独占全量 validation `275/275`、R8 AI 合同加入后的 runtime helper/oracle `72/72`。visualizer `6/6`，十改革与十个内嵌图标完整且无裸 ID/路线 flag，companion-root 可选采集回归通过。无 skip 联合地图门禁独立复跑 exit 0（122.1s），`511 events / 290 decisions / 394 callables / 929 modifiers`，地图/历史/内容/兼容/资产均 `0 errors / 0 warnings`，88 省与全部 137,382 个可选日期通过。matrix `da4e4fb5709994e48ad06e69dd9c5c401955a0a18b448adeab477f266580b91a`，oracle `768462c4ce12782342cdcad3083737dec7a18d6b64f94cf2e9fbdf60bc4685d4`。
- Runtime/TODO: Agent A/B 均未启动、控制或关闭 EU4/Launcher。payload 尚未写入 Documents，兼容副本尚未针对 `00_country_ideas.txt` 重建；`JXP-001/002/004/005/008/009/010/017/018/020/021/022/023` 与持续流程项 `JXP-016` 均保持原状态。下一步是完成可视化/skill/ledger 控制面提交、clean preflight、精确部署和 provider-convergence audit；随后仍须另获启动许可。

### 2026-07-14 - IDEA-REGISTRY-003 - Single exact-path national-idea registry (`no version bump`)

- Status: `STATIC_INTEGRATION_PASS; ORACLE_CURRENT; PENDING_FULL_GATES; NOT_DEPLOYED; PENDING_RUNTIME`。
- Scope: 依据用户实际开局截图及 fresh `setup.log`，废止 `00_0_jxp_*` 与 `00_basic_z*_jxp_*` 两代多文件排序方案。五份可读理念源移出 runtime `common/ideas`，新增确定性生成器，将 pinned vanilla `00_country_ideas.txt` 与 45 个 JXP 自编组按同 key 替换后生成唯一运行文件；MRI、TOY、十终局路线及全部大名由同一 IdeaDatabase 注册表提供。同步整合十种终局状态在 `absolute_rule_vs_constitutional` 层的互斥可见政治改革、0.28.3 一次性迁移及 R3 状态矩阵；“八纮一宇”继续使用稳定日本身份 `potential` 与动态解锁 `trigger`，避免候选缓存不刷新。
- Evidence: 生成器 `--check` 通过；理念定向测试 `13/13`，注册表静态合同为 `457/457 unique groups / 45 authored / 34 same-key replacements / 1 runtime file`。终局状态定向测试 `28/28`，Agent B 独立复验相关切片 `95/95`；改革检查识别 `27 route + 39 founder + 10 final-state`，十状态 visibility/selectability 矩阵与 `always = yes` 误显变异均通过。runtime oracle pack `f79bde04e92c4660baec8d0d9316ad76f2ec788d4bcd212ee53cd7eb9293d75b` byte-current，matrix 为 `833ed590252ea5ae11f74b881db6dceb2812dddfa29b38298104238fa27c8a70`。
- Runtime/TODO: Agent 未启动、控制或关闭 EU4/Launcher。新单文件理念注册表尚未部署，也没有引擎内证明；`JXP-020/JXP-022/JXP-023` 均保持 `IN_PROGRESS`。完整主门禁、全量单测、地图联合门禁、兼容副本重建、两阶段 candidate 与 Documents 部署仍待本切片后续完成；启动必须另获明确许可。

### 2026-07-14 - IDEA-REGISTRY-002 - Complete registry recovery and Imjin display literals (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; COMPAT_REBUILT; USER_OBSERVED_FAILURE_SUPERSEDED; PENDING_RUNTIME`。
- Scope: 依据用户新一轮实际游玩日志根治 TOY 默认理念、MRI 理念堆叠及 `national_idea8`。三份 37 大名同名理念覆盖由危险的 `00_0_jxp_*` 改至 `00_basic_z1/z2/z3_jxp_*` 安全窗口；新增覆盖全部 46 个主 Mod 管理 tag 的 v0.28.2 一次性强制理念归一、完整 debug 清理和旧路线迁移互锁。runtime scanner 现在拒绝少于 479 组、缺失关键 JXP 理念或关键理念重复的 fresh `setup.log`，playset 审计同时拒绝 Documents 中任何仓库已删除的运行时孤儿文件。战史生成器升级 schema 4，将四个战争名和九个战役名生成为 canonical BOM-free EU4SpecialEscape 中文字面量。
- Evidence: 用户旧部署的 fresh `setup.log` 仅有 `14` 组理念并缺 `TOY_ideas/CJP_ideas/...`；fresh `error.log:502` 含 `national_idea8`，新 scanner 均精确命中。修复后主门禁 `27/27`、Clausewitz `276/276`、核心测试 `265/265`；理念合同为 `45/45` 结构正确、`5/5` 文件在 basic registry 之后、`34/34` 同名覆盖在原版来源之前、`3` 个受控 swap。兼容副本 `5,766 files / 22,097,348 bytes / 3d130bef...6035`，71 个外部冲突全部收敛；daily main 已部署 12 个相关文件、规范化 22 个战史/省史文件并删除 3 个旧 `00_0` 文件，两个 Imjin provider 均解码为“壬辰倭乱”。
- Runtime/TODO: Agent 未启动、控制或关闭 EU4/Launcher。旧日志只证明旧部署失败，不证明当前修复已被引擎加载；`JXP-018/JXP-020` 仍为 `IN_PROGRESS / CODEX_A`。Agent B 正在独立处理两份政府改革文件，故当前 playset 的 `2 stale` 仅作为并行集成状态，不得宣称完整候选 ready。提交授权已收到；先提交 A checkpoint、接收 B handoff，再形成新的 immutable candidate，启动仍需另行授权。

### 2026-07-14 - IMJIN-HISTORY-001 - Toyotomi war sides and Korean occupation chronology (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; PLAYSET_AUDITED; PENDING_RUNTIME`。
- Scope: 将丰臣身份修复扩展到全部相关势力和领土状态。四份 1586 年后战史的交战方与增减参战动作统一由 `ODA` 改为 `TOY`，万历朝鲜战争九场战斗的参战国同步修正；釜山与忠州战场分别校正到 `2745`、`4229`。十八份韩国省份历史保持 `owner = KOR`，以十九段半开区间精确表达 `controller = TOY` 的日军占领；移除济州错误占领，补入平壤 1592-1593 占领，并验证 SMZ/MRI/CSK 在入场日均为 TOY 属国。生成器 manifest 升至 schema 3，并固定 41 份原版战史/省史源文件。
- Evidence: 新 `imjin` validator 与六项 mutation 回归通过；完整主门禁 `27/27`、Clausewitz `274/274`、core tests `259/259`。无 skip 联合地图门禁 `0 errors / 0 warnings`，覆盖 88 省、299 owner intervals、70 subject intervals 与 137,382 个可选日期。日常 playset 为 `4 layers / 617 runtime files / 71 converged / 0 divergent / 0 stale`；兼容副本为 5,766 文件、22,097,387 bytes、SHA-256 `80e7d7b3324befce297d53d88cc3de6bc7747c4d5517cdfbd37a9558264635ed`，全部二十二份新增运行时文件与 Documents 部署逐文件哈希一致。repo/installed skill 均通过 `quick_validate.py`。
- Runtime/TODO: 未启动、控制或关闭 EU4/Launcher。静态合同已覆盖四场战争、九场战斗、十八省和十九段占领，但用户可见的书签交战方、战争界面与地图控制色仍待新 immutable candidate 及另行授权后的 `R4 + R9`；`JXP-018` 保持 `IN_PROGRESS / CODEX_A`。

### 2026-07-14 - PLAYSET-AREA-001 - Effective translated-area collision guard (`no version bump`)

- Status: `STATIC_PASS; DAILY_AUDITED; PENDING_RUNTIME`。
- Scope: 将 `MAP-AREA-001` 的生成源检查扩展到实际启用 VFS。`jxp_validation/playset.py` 现在从原版与全部 launcher-enabled layer 递归读取 `l_english`，兼容 UTF-8、CP1252 与 UTF-8 包装的 EU4SpecialEscape，抽取所有 `*_area` 显示名，并仅对 JXP 自定义 area 的跨 key 同名作硬失败。新增真实字节回归：`东海道` 与 `东海` 可共存，旧 `jxp_tokai_area = 东海` 必须触发 `playset.area_localisation_collision`；无关第三方区域重名不扩大为 JXP blocker。
- Evidence: 定向 playset 测试 `3/3`；实际日常审计为 `4 layers / 595 runtime files / 50 converged / 0 divergent / 0 stale / 9 custom area keys / 86 area-localisation files / 0 custom label collisions`，五个 ODA 哨兵仍全为 `0`，TOY 为 `26/33/1/1/0`。完整主门禁 `26/26`、Clausewitz `252/252`、core tests `253/253`；无 skip 联合地图门禁 `0 errors / 0 warnings`，覆盖 88 省、299 owner intervals、70 subject intervals 与全部 137,382 个可选日期。
- Runtime/TODO: 未启动、控制或关闭 EU4/Launcher；本条只把旧日志暴露的根因固化为有效 playset 静态守卫，不构成地图 UI 或 fresh log 证明。`JXP-017` 继续 `IN_PROGRESS / CODEX_A`，旧 A3 仍 stale，必须先形成新候选并另获启动许可。

### 2026-07-14 - MAP-AREA-001 - Tokaido localisation collision (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; PENDING_RUNTIME`。
- Scope: 只读审计用户最近一次 `error.log` 时发现引擎把 `jxp_tokai_area` 与 `east_china_sea_area` 判为同名。根因是地图生成计划把日本陆地历史区域“东海道”缩写成了中文海域名“东海”。已将 `localisation_plan.json`、生成 UTF-8 源和 EU4SpecialEscape 活跃本地化统一改为“东海道”，并在 `validate_history.py` 增加 area 计划/源精确一致、重复显示名和东海道语义守卫，两项 mutation 测试覆盖正确值与旧错误值。
- Evidence: 定向测试 `9/9`，完整主门禁 `26/26`、Clausewitz `252/252`、core tests `252/252`，无 skip 联合地图门禁 `0 errors / 0 warnings`，runtime oracle `804c597c...865c3` 与 matrix `fe4f51a0...02fd1` 当前；R5 escrow 在该 matrix 下仍为 `ok / ADMITTED_STATIC_INPUT`。活动 playset 仍为 `4 layers / 595 files / 50 converged / 0 divergent / 0 stale`。部署文件 SHA-256 `B7201AA2...3B386`，备份 `jxp_playset_backups/20260714_185000_tokai_area_label`；只读 preflight 12/12 pinned game files 匹配，当前 map manifest `239 / c347f40c...21596`。repo/installed skill 均 `Skill is valid!` 且 `SKILL.md` SHA-256 同为 `29D1724F...DBCFC`。
- Runtime/TODO: 未启动或控制 EU4/Launcher。旧日志只能证明旧译名曾触发错误，不能证明新译名已被引擎加载；`JXP-017` 继续 `IN_PROGRESS / CODEX_A`，等待新候选 R1/R12 fresh log 与地图 UI 证据。

### 2026-07-14 - TOYOTOMI-COMPAT-001 - Provider convergence and canonical ruler names (`no version bump`)

- Status: `STATIC_PASS; DAILY_DEPLOYED; PENDING_RUNTIME`。
- Scope: 用户运行时再次证明仅调整 `dlc_load.json` 顺序不能消除 ODA/TOY 共存，因此明确 supersede `TOYOTOMI-VFS-001` 的 first-wins 推断。新增本地中文补充兼容副本构建/审计器，把 ODA country history、`DOM_Japanese_Missions.txt` 与 48 个省份历史共 50 条冲突全部替换为 JXP 权威字节；原 Workshop 补充项已禁用。另将 39 份补充包日本国家历史、39 份姓名池、14 份主路线国家文件和 60 份地图新大名文件统一为可逆 BOM-free EU4SpecialEscape，并为主路线保留 14 份 UTF-8 可读源。R9 扩为七日期/十九截图的五列丰臣身份合同，R2/R3/R9 共同承担姓名运行时关闭证据。
- Parallel handoff: TODO 已按文件所有权拆成 A/B 两链。`CODEX_A` 独占历史、国家、理念、丰臣、地图生成/历史、验证/验收、skill、Documents 和本总账；`CODEX_B` 独占 CJP/UI/WAK/IJP/Mandate/final-tag 的路线任务、事件、决议、改革和对应资源。B 不写本总账或日常配置，跨边界接线由 A 完成。
- Evidence: compatibility clone audit 为 `50 patches / 39 history / 39 country pools / 0 issues`，source identity `e8ef527e...8507ad`，payload identity `d4612e25...1f835`；active playset audit 为 `4 layers / 595 runtime files / 50 converged / 0 divergent / 0 stale deployed`，五个哨兵 possible ODA 均为 `0`、TOY 为 `26/33/1/1/0`。74 个新增姓名文件逐文件部署哈希一致，备份为 `jxp_playset_backups/20260714_180431_toyotomi_names`。姓名门禁为 `77 encoded gameplay files / 14 source pairs / 114 history literals / 276 monarch / 480 leader / 0 issues`；主门禁 `26/26`、Clausewitz `252/252`、core tests `250/250`，无 skip 联合地图门禁 `0 errors / 0 warnings` 并覆盖 137,382 个日期；repo/installed skill 均 `Skill is valid!` 且对应文件字节一致。R5 escrow 在 matrix `4448bf4c...d59dd` 下复验 `ok / ADMITTED_STATIC_INPUT`。只读 preflight 证明 12/12 pinned game files 与四层日常 playset 正确，只因未提交的 74 个 runtime bytes 拒绝旧 A3；当前 live manifests 为 main `378 / b6f81c7d...1c199`、map `239 / 131a24bf...8ef5`。acceptance helper 为 `63/65`，仅两项按设计拒绝尚未提交的新 runtime bytes 与旧 A3 snapshot，不能写成当前候选通过。
- Runtime/TODO: agent 未启动 EU4/Launcher；只观察到用户自启 PID `19872` 后自然退出，未操控且不作为 runtime evidence。Agent A 的静态修复、日常部署和验证切片已完成；`JXP-018`、`JXP-021` 仍为 `IN_PROGRESS / CODEX_A`，因为游戏可见身份、姓名、任务与存读档证据尚未在新候选上采集。旧 A3 candidate 与隔离快照均 stale；先接收 Agent B 的独立链交付，再取得新的 commit authorization，不能直接启动 PROBE。

### 2026-07-14 - TOYOTOMI-VFS-001 - Effective playset priority and bookmark regression (`no version bump`)

- Status: `STATIC_PASS; DAILY_PLAYSET_REPAIRED; ISOLATED_RECONFIGURED_NOT_STARTED; RUNTIME_PENDING`。
- Scope: 以用户 1598/1615 截图为失败基线审计实际日常 playset，确认中文补充 Mod 并非纯本地化层，而是抢先覆盖了 ODA country history、旧日本 province history 与原版日本任务。备份 `dlc_load.json`/`launcher-v2.sqlite` 后，把 active first-wins 顺序改为 `map > main > Chinese supplementary > Chinese base`；同时从 A3 鉴权快照重新部署落后的 239-file map payload。新增真实 playset VFS auditor、固定 1586/1598/1600/1615 交接哨兵、旧顺序反例回放、R9 七日期/十九截图身份合同，并让隔离验收 helper 与日常顺序采用同一语义。repo 与 installed `eu4-modding` skill 同步记录该规则。
- Evidence: 修复前备份回放为 `4 layers / 595 runtime files / 50 collisions / 50 wrong winners / 60 issues`，精确重构 `1598.5.23 ODA=18, TOY=18` 与 `1615.6.3 ODA=1, TOY=0`；当前日常 VFS 为 `0 wrong winners / 0 stale deployed files`，五个固定日期的 ODA 均为 0，TOY 依次为 `26/33/1/1/0`。当前 daily `dlc_load.json` 为 `148 / 75D2F3C2...2725`，SQLite 为 `176128 / 0B370B3D...75F4`；隔离 PROBE receipt 为 `107F2BBB...E253`，其 `dlc_load.json` 为 `168 / 73A828AB...4EC5`。主门禁 `26/26`、Clausewitz `252/252`、core tests `248/248`；无 skip 的主/地图联合门禁 `0 errors / 0 warnings`，覆盖 137,382 个可选日期；acceptance helper `65/65`，runtime oracle sources `258/258`。
- Runtime/TODO: `agent_game_started=false`；修复后检测到用户自行启动的日常进程，但未操控或关闭。其 fresh setup 仅证明 TOY/丰臣文件已注册，未形成 sealed UI/checklist，因此没有把静态 VFS 或外部日志写成游戏内通过；`JXP-018` 保持 `IN_PROGRESS`，仍需新许可下的 R4/R9 书签、姓名、任务 UI、保存与重载证明。此前只检查源计划而未检查实际 VFS 的静态结论已被本条明确 supersede。

### 2026-07-14 - TOYOTOMI-DEPLOY-001 - A3 production preflight and Documents deployment (`no version bump`)

- Status: `STATIC_PASS; CANDIDATE_READY; DAILY_AND_ISOLATED_DEPLOYED_NOT_STARTED; AWAITING_LAUNCH_PERMISSION`。
- Scope: 从 clean control plane `12df909115bdd5dab524760977d32e196e83e6c7` 对 payload A3 运行 production preflight，确认祖先关系、runtime diff、完整主/地图 manifest、12 项原版 pin 与零相关进程；随后保留日常绝对路径 outer descriptor，只把 A3 的 378 个 runtime 文件经 staging、逐文件 SHA-256 和原子 rename 写入 Documents 主 Mod，并把旧目录完整移入 `_jxp_backups`。同一 A3 另部署为隔离 current main/map 与 current-main 快照，并仅更新隔离 PROBE playset；未修改日常 Launcher 数据。
- Evidence: preflight `ok=true / ready_for_safe_deploy=true`；daily target `C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\japan_expanded_v2` 为 `378/378` 文件，backup 为 `japan_expanded_v2_before_toyotomi_fix_20260714_115213`。隔离 main/map fingerprints 为 `59e4baeef57c...db6c` / `953faa7de3e2...6b8`，configure receipt `2c744761...9cf5`，isolated `dlc_load.json` `168 / b2506e9c...a54d`。部署后完整联合门禁再次通过：main `26/26`、Clausewitz `252/252`、tests `246/246`，map/compat/assets/oracle 全部 `0 errors / 0 warnings`。
- Runtime/TODO: `game_started=false`，未获得任何引擎内书签、任务 UI、姓名显示或保存重载证据；`JXP-018` 保持 `IN_PROGRESS`。下一步必须由用户重新明确授权 PROBE，不能把部署或静态门禁写作运行时通过。

### 2026-07-14 - TOYOTOMI-SUCCESSION-001 - Exclusive ODA/TOY handoff and full historical identity (`no version bump`)

- Status: `STATIC_PASS; PAYLOAD_A3_COMMITTED; CONTROL_PLANE_IN_PROGRESS; RUNTIME_NOT_RUN`。
- Scope: 接管原版 `ODA` country history，在 `1582.6.21` 保留羽柴秀吉继位、于 `1586.1.1` 将残余织田身份切换为织田信雄，并与主/地图所有 province 和 subject 区间使用同一丰臣交接日；`TOY` 从大名阶段移入独立统一历史 profile，新增 realm/court/horizon 三栏共 21 个任务，与共享 slots 1/2 组成完整五栏树。新增可读国史/国家源文件与 gameplay-name 生成器，使 ODA/TOY 的统治者、王朝及姓名池成为中文补丁所需的无 BOM 原始 EU4SpecialEscape 字节；生成器、parser、逐日边界、任务签名和字节合同均有 hard-fail validator 与 mutation tests。
- Evidence: payload A3 `6d439b9bdf0898cee84014ac38b4de776c630d1a`；main manifest `378 / ba579836...6bc1`，map manifest `239 / 3e2d301e...bac0`，runtime diff empty。主门禁 `26/26`、Clausewitz `252/252`、missions `309 / 44 / 192`、core tests `246/246`；完整伴随地图门禁 `0 errors / 0 warnings`、137,382 日期与 33 个 Toyotomi companion ownership intervals 全通过；repo/installed skill 均为 `Skill is valid!` 且三份本切片文件逐字节一致。
- Runtime/TODO: 未启动 EU4/Launcher，未取得书签、姓名显示、任务 UI、保存重载或旧档迁移证明；`JXP-018` 保持 `IN_PROGRESS`，仍需 R4/R9。A2 已 superseded；完成 control-plane commit、production preflight 与 A3 redeploy 后，仍需新的明确 PROBE 启动许可。

### 2026-07-14 - CANDIDATE-REDEPLOY-002 - Payload A2 deployed after disaster-seed remediation (`no version bump`)

- Status: `STATIC_PASS; CANDIDATE_READY; DEPLOYED_NOT_STARTED; AWAITING_LAUNCH_PERMISSION`。
- Scope: control plane `8bbc7e5b8ceeb4d96c920bb75ae19792d260a8b9` 从 clean worktree 对 payload A2 `962bfaee183aec3fb2c8e608f034032be20529d8` 重跑 production preflight，证明 A2 为祖先、runtime diff empty、主/地图完整 manifest matched 与 12/12 pinned game/protocol files matched。随后只向 `C:\JXP_Acceptance` 物化 exact A2 的 current main/map 与 current-main 快照，并配置 PROBE；未启动游戏，未修改日常 Launcher 配置。
- Evidence: main `377 / 3a9f61c7...74f26`、fingerprint `b8437104...28ec`；map `239 / 3e2d301e...bac0`、fingerprint `7fbf9864...5bbd`。PROBE receipt `F2FBFD99...C719`，isolated `dlc_load.json` `168 / ABB77D5D...09DF`。daily `dlc_load.json` 与 `launcher-v2.sqlite` 仍为 `147 / D317B6EE...AF72` 与 `176128 / A27BF04D...A30`；相关进程为零。helper `63/63`、oracle `6/6`、主门禁 `26/26`/`251/251`/`242/242`、联合门禁 `0 errors / 0 warnings`、repo/installed skill `11/11` mirror 均通过。
- Runtime/TODO: 部署不是运行时证明，不关闭任何 runtime TODO。两个既有 PROBE 许可均已消耗；在新的明确许可之前不得启动 EU4、Launcher 或 observer。

### 2026-07-14 - PROBE-RUNTIME-002 - Isolated main-menu failure and custom-disaster load-order repair (`no version bump`)

- Status: `PROBE_FAILED; ISOLATION_PASS; DAILY_CONFIG_UNCHANGED; STATIC_REMEDIATION_PASS; PENDING_CONTROL_PLANE_AND_NEW_PERMISSION`。
- Scope: 用户授权的 session `20260714T161050Z_probe_default_a490fa8b` 只启动 pinned `eu4.exe -userdir=C:\JXP_Acceptance`；未发送输入、未进入或加载战役，并通过正常窗口关闭结束。标题背景出现但交互主菜单未出现，manual main-menu assertion 因而失败。fresh `error.log` 记录四个 custom-disaster `add_disaster_progress` validation failure；A2 将四个 debug seed 改为 scripted effect 分发完整隐藏事件，再由事件层注入进度。collector 同时收窄 `map_initialization` 规则，避免把 vanilla `failed_province_purchase` 当作地图初始化失败。
- Evidence: collection `AA1B815F...8104`、seal `0E905401...A939`，状态 `AUTOMATED_CHECK_FAILED`；daily `dlc_load.json` 与 `launcher-v2.sqlite` 仍分别为 `D317B6EE...AF72` 与 `A27BF04D...A30`。Payload A2 为 `962bfaee183aec3fb2c8e608f034032be20529d8`，main/map manifest 为 `377 / 3a9f61c7...74f26` 与 `239 / 3e2d301e...bac0`。主门禁 `26/26`、`251/251`、`242/242`；联合门禁 `0 errors / 0 warnings`、120 profiles、137,382 日期、509 events。repo 与 installed skill 已同步 custom-disaster load-order 经验。
- Runtime/TODO: 本次失败不关闭任何 runtime TODO，也不证明主菜单或灾难已在引擎中修复。现有启动授权已消耗；先提交控制面并在不启动游戏的前提下部署 A2，之后必须获得新的明确许可才能重跑 PROBE。

### 2026-07-14 - CANDIDATE-CONTROL-001 - Clean control plane and isolated deployment completed (`no version bump`)

- Status: `STATIC_PASS; CANDIDATE_READY; DEPLOYED_NOT_STARTED; AWAITING_LAUNCH_PERMISSION`。
- Scope: control-plane B 提交 matrix/oracle/ledger/manual/tooling/tests/skill 与两份已索引阶段报告，未改变 payload A 的任何 runtime whitelist byte。production preflight 从 clean control plane 重新验证 A 为祖先、repository clean、runtime diff empty、主/地图完整 manifest matched 与 12/12 game pins；随后仅向 `C:\JXP_Acceptance` 物化 exact revision A 的 current main/map 和 current-main 快照，并配置 PROBE playset。
- Evidence: preflight `ok=true`、`ready_for_safe_deploy=true`、相关进程为零；main `377 / caddf421...eb1a`、map `239 / 3e2d301e...bac0`。部署指纹为 main `f210d5a65ea8...596d`、map `46303fcd4d55...4843`；PROBE receipt `6c477831...c733`，isolated `dlc_load.json` `20617576...5600`。helper `50/50`、oracle `6/6`、主门禁 `26/26`/`251/251`/`241/241`、联合门禁 `0 errors / 0 warnings`、repo/installed skill 11/11 mirror 均通过。R5 在 matrix `a8525b36...5c35` 下重新为 `ADMITTED_STATIC_INPUT`。daily 两个配置 hash 未变，`game_started=false`。
- Runtime/TODO: 这些结果只证明不可变候选、隔离部署和静态输入准备，不证明主菜单或任何玩法。下一步必须取得新的明确启动许可，从 schema-5 PROBE 开始；不得复用 aborted session 或旧截图/log。

### 2026-07-14 - CANDIDATE-PAYLOAD-001 - Immutable payload A formed under explicit authorization (`no version bump`)

- Status: `PAYLOAD_COMMITTED; MANIFEST_MATCH; CONTROL_PLANE_B_IN_PROGRESS; RUNTIME_NOT_RUN`。
- Scope: 用户明确回复“授权提交”后，严格只暂存主/地图 runtime whitelist，创建 payload A `f42fd308587289a3d5ec1b7aab788fe6f6c8d1b5`。A 包含 19 个 Git 变更记录：灾难生命周期与 modifier 修复、三组同名大名理念前置重命名、精确理念 trigger、普通/强制理念同步与旧档迁移、隐藏地图事件完整壳及主/地图 state-safety 修复；总账、matrix、oracle、工具、测试、skill、阶段报告和外部证据均未进入 A。
- Evidence: A 后从 Git OID 经认证重新物化全部运行白名单；main 为 `377 files / caddf4218f068e785ec6e6054aa4ca6ca8ee0d348403a6dbfa65fa7574eaeb1a`，map 为 `239 files / 3e2d301e4c0e66943c8764957fa79de3423f620e2eb4c0ff224d21ce16c0bac0`，两者均与 live worktree 完全一致。matrix 已改为 pin A，新的 matrix SHA-256 为 `a8525b36227f77902d10600f74a6f6ca3951c181c020729d6997950a38a95c35`；R12 oracle pack 在该 candidate-only 变更后仍 byte-current。运行 helper `50/50` 与 runtime oracle contract `6/6` 均已在 A 身份下通过。
- Runtime/TODO: A 只是不可变游戏 payload，不是部署或运行证据。B 必须只提交控制面并证明 `git diff --quiet A -- <all runtime roots>`；之后 production preflight ready、部署和新的独立启动许可缺一不可。

### 2026-07-14 - SESSION-ABORT-001 - Stale sealed sessions cannot strand the active lock (`no version bump`)

- Status: `STATIC_PASS; HISTORICAL_ABORT_AUTHENTICATED; COLLECTION_STILL_FAILS_CLOSED; PENDING_USER_COMMIT_AUTHORIZATION`。
- Scope: 复核 schema-5 控制面绑定时发现，原 `abort-session` 虽不比较 live control-plane OID，却仍经通用校验读取 current scenario、matrix hash、candidate 与 VFS coverage；若 B 在运行后更新这些字段，合法旧 session 会被判 stale 并无法释放 active nonce。session 校验现分为 current-contract 与 sealed-identity 两层：observe/collect/parent evidence 继续要求 current matrix，只有 abort 与已认证的 partial-collection recovery 使用 sealed identity；后者仍要求 exact schema、session seal、规范 evidence root、记录路径和 active nonce，不会把旧 session 升格为 evidence。
- Evidence: 新回归同时令 `_current_candidate_revision`、`_scenario`、`_scenario_matrix_sha256` 不可调用并改变 `DAILY_VFS_COVERAGE`，确认 recovery identity 与 `abort-session` 仍成功且 active lock 被释放；同一 session 的 `collect` 在控制面 OID 漂移时先行拒绝。定向 lifecycle/PROBE 测试 `3/3`，完整 helper `49/50`、逻辑 `49/49`；唯一失败仍为四个新 runtime 文件未 tracked。Python 编译通过；未部署、未启动、未改 daily 配置。
- Runtime/TODO: 此修复只保证失败会话可安全收尾，不使旧 collection、旧 schema 或漂移后的运行获得当前证据资格。下一步授权边界不变：先明确授权提交并形成 A/B，再独立授权新 PROBE。

### 2026-07-14 - SESSION-CONTROL-001 - Runtime session binds the immutable control plane (`no version bump`)

- Status: `STATIC_PASS; SESSION_SCHEMA_5; COLLECTION_FAILS_CLOSED; PENDING_USER_COMMIT_AUTHORIZATION`。
- Scope: 补齐两阶段 candidate 协议在运行会话期间的 TOCTOU 缺口。`before-session` 现在要求 clean control-plane B、重新证明 ready payload A，并把 B 的 exact OID 写入 session；`collect` 在复制证据前再次要求同一个 clean B 与同一个 A。运行期间即使只改 README、matrix、oracle、ledger 或测试也会拒绝收集；`abort-session` 不依赖 live Git 仍停留在 B，可在漂移后认证旧 session 并释放 active nonce。session/seal/lock/process-observation/abort 升为 schema 5，collection 及 R13 保持 schema 4；旧 schema-4 session 只保留历史身份，不原地升级。
- Evidence: Python 编译通过；部署候选、session 控制面漂移、PROBE immutable collection 与 receipt/lock/abort 四项定向回归 `4/4`；完整 helper `49/50`，逻辑 `49/49`，唯一失败仍是四个新 runtime 文件未 tracked。主门禁 `26/26`、Clausewitz `251/251`、core tests `241/241`；无跳过联合门禁 `0 errors / 0 warnings`、120 profiles、137,382 日期与 505 events/289 decisions/391 callables/918 modifiers 全通过。production preflight 以 12/12 game pins matched 但 repository/runtime manifests 不一致而按预期返回 not-ready；`git diff --check` 为零输出。repo/installed skill 各 11 文件逐字节一致并分别 `Skill is valid!`。相关进程为零，daily `dlc_load.json` 与 `launcher-v2.sqlite` 仍为 147 / 176,128 bytes 及既有 SHA-256；未部署、未启动 EU4/Launcher、未改 daily 配置、未形成 candidate。
- Runtime/TODO: 这是运行证据工具的 fail-closed 加固，不构成 PROBE 或 R1-R13 证据，不关闭任何 runtime TODO。下一步仍须用户明确授权 Git 提交，严格形成 payload A 与 control-plane B；随后 production preflight ready 后另行取得新的启动许可。

### 2026-07-14 - PREFLIGHT-CANDIDATE-001 - Candidate identity promoted to production gate (`no version bump`)

- Status: `STATIC_PASS; STALE_CANDIDATE_FAILS_CLOSED; PENDING_USER_COMMIT_AUTHORIZATION`。
- Scope: 修复 production `preflight` 只验证 game pins、进程和路径，却在 matrix 仍指向旧 candidate 时错误返回 `ready_for_safe_deploy=true` 的缺口。新 gate 同时要求控制面工作树 clean、candidate 为控制 HEAD 祖先、portable outer descriptors 与全部 runtime path 无差异、主/地图完整 manifest 逐字节匹配。`deploy --label current/current-main` 重复该证明，要求 clean control-plane commit，并强制显式 revision 等于 matrix candidate；省略 revision 不能把 HEAD/B 当成 payload。README 与 repo/installed skill 同步该规则。
- Evidence: 在真实工作树执行 production readiness 得到预期拒绝：candidate `2BF24123...` 是 HEAD `1B68BB35...` 的祖先，但 repository clean=false、runtime diff clean=false；main 为 live `377 / CADDF421...EB1A` 对 candidate `376 / 90177418...D878`，map 为 live `239 / 3E2D301E...BAC0` 对 candidate `239 / 5FA96B69...2631`，均 matched=false。新增 clean/mismatch ancestry、preflight wiring、dirty control plane 与 wrong revision deploy 测试通过；完整 helper `48/49`，逻辑 `48/48`，唯一剩余失败仍是四个新 runtime 文件尚未 tracked。
- Runtime/TODO: 此结果证明旧候选现在会被工具阻止，不证明新候选或任何游戏行为。`Next executable step` 改为 `AWAITING_COMMIT_AUTHORIZATION`；获得许可后严格形成 A/B 两提交并复跑 gate，只有 production preflight 转为 ready 才能部署。启动许可仍须在部署完成后另行取得。

### 2026-07-14 - CANDIDATE-SEAL-001 - Two-stage immutable candidate protocol (`no version bump`)

- Status: `STATIC_PASS; TWO_STAGE_SEAL_GUARDED; PAYLOAD_IDENTITY_RECORDED; PENDING_USER_COMMIT_AUTHORIZATION`。
- Scope: 审计 `runtime_scenarios.json` 内嵌 candidate OID 的自引用边界，确定新候选必须分为 payload commit A 与 control-plane commit B：A 固化全部 runtime whitelist；B 只把 matrix、oracle、ledger、README 与测试固定到 A，且不得改变任何 runtime byte。将该规则同步写入 runtime README、repo skill、installed skill 与详细 reference，并新增 README 回归测试。当前 22 个 runtime 变更路径已分类，其中三组旧理念文件删除与 `00_0_jxp_*` 新路径替换成对，另有精确理念 trigger；开发报告、工具、测试与 skill 不进入游戏 payload。
- Evidence: 当前 worktree runtime manifest 为 main `377 files / 4,043,251 bytes / CADDf4218f068e785ec6e6054aa4ca6ca8ee0d348403a6dbfa65fa7574eaeb1a`，map `239 files / 82,501,199 bytes / 3E2D301E4C0E66943C8764957FA79DE3423F620E2EB4C0FF224D21CE16C0BAC0`。新增两阶段测试与首启输入测试均通过；完整 helper `46/47`，逻辑 `46/46`，唯一红灯仍为四个 runtime 新文件未 tracked。repo/installed skill 各 11 文件、零差异并分别 `Skill is valid!`；未启动、未部署、未提交。
- Runtime/TODO: commit A/B 尚未获得授权，记录的 manifest 只是待封存工作树身份，不是 immutable candidate。授权后必须先核对 A 的 runtime manifest 与上述身份一致，再在 B 后证明 `git diff --quiet A -- <runtime roots>`；若 A 后任何 runtime byte 改变则整对重做。之后仍需新的 PROBE 启动许可。

### 2026-07-14 - PROBE-MANUAL-001 - First-run input and isolated-preference guard (`no version bump`)

- Status: `STATIC_PASS; OPERATOR_CONTRACT_HARDENED; PENDING_IMMUTABLE_CANDIDATE_AND_PERMISSION`。
- Scope: 将无效 PROBE 暴露的实际操作风险补入 runtime acceptance 的权威 README：`-userdir` 不继承 daily Documents 的语言、缩放、显示、音频与玩法偏好属于预期，Mod 是否加载必须看 fresh isolated logs 与主菜单；首启语言控件只能在确认可见焦点后用指针点击，禁止缓冲 `Enter`、`Space` 或在主菜单继续输入。新增空白规范化回归测试，保证 Markdown 换行不影响检查，同时阻止关键警告被后续改写删除。未改变 matrix、candidate、playset、descriptor 或游戏内容。
- Evidence: 新定向测试 `test_probe_manual_forbids_buffered_first_run_input` 通过；完整 acceptance helper 为 `45/46`，新增及既有逻辑 `45/45` 全通过，唯一失败仍是四个新 runtime 文件尚未进入 Git tracked set。当前 oracle snapshot 红灯仍只来自缺少同内容 immutable candidate；没有启动进程、没有写 daily 配置，也没有把旧 aborted PROBE 重标为 READY。
- Runtime/TODO: 此加固降低下一次 PROBE 再次误入战役的风险，但不是运行时证据，不关闭任何 TODO。下一步仍为获得明确提交授权、形成新 candidate 并重新部署；之后另行取得启动许可，从 PROBE 开始。

### 2026-07-14 - CANDIDATE-PREFLIGHT-001 - Immutable candidate readiness audit (`no version bump`)

- Status: `STATIC_PASS; PRECOMMIT_READY; PENDING_USER_COMMIT_AUTHORIZATION; RUNTIME_NOT_RUN`。
- Scope: 在不提交、不部署、不启动 EU4/Launcher 的边界内，重新审计当前工作树、运行时白名单、旧文件到 `00_0_jxp_*` 的三组迁移、共享总账、repo/installed skill 镜像、host pins 与 R5 escrow。三份理念新文件除两行加载顺序说明外，其余 611/529/471 行分别与旧文件逐行一致；第四个新 runtime 文件是精确理念身份 trigger。六个未跟踪文件中只有这四个进入 runtime payload，两个 R5/portability 阶段报告继续作为已索引开发证据，外部存档、日志、截图和 launcher 数据均不在 Git 发布面。
- Evidence: host `preflight` 返回 `ok=true`、12/12 pins 匹配、`game_started=false`、`launcher_configuration_modified=false`；R5 verifier 在 matrix `46EEAC35...834A` 下返回 `ADMITTED_STATIC_INPUT`。无跳过联合门禁再次得到 main `26/26`、Clausewitz `251/251`、core tests `241/241`，地图 `0 errors / 0 warnings`、120 profiles 与 137,382 日期通过；`git diff --check` 为零输出。repo 与 installed skill 均为 11 文件、零差异，并分别 `Skill is valid!`。验收 helper 为 `44/45`，唯一失败是四个新 runtime 文件尚未 tracked；oracle contract 的唯一 live 检查失败是工作树字节尚无同内容 immutable Git snapshot，二者均不得在提交前降级或豁免。
- Runtime/TODO: 未形成新 candidate，也未复用旧 `2bf24123...`；所有要求 R1-R12 的 TODO 保持 `IN_PROGRESS / PENDING_RUNTIME`。下一步只能在用户明确授权 Git 提交后形成新 immutable candidate、重建 oracle/manifest 并重新部署；随后还需新的独立启动许可，从 PROBE 开始采集证据。

### 2026-07-13 - IDEA-RUNTIME-001 - Same-key national-idea precedence and idempotent migration (`no version bump`)

- Status: `STATIC_PASS; ROOT_CAUSE_IDENTIFIED; RUNTIME_MATRIX_HARDENED; PENDING_IMMUTABLE_CANDIDATE_AND_PERMISSION`。
- Scope: 由无效 PROBE 的 fresh `setup.log` 追到 `OTM_ideas` 实际加载原版 `Unite the Clans ... Kunikuzushi` 七理念，确认 EU4 1.37.5 对自由国家理念组采用文件顺序 first-match；将三个覆盖原版同名组的 JXP 文件改为 `00_0_jxp_*` 前置，新增九终局 tag 的精确理念触发器，把日常同步改为“目标组缺失才 swap”，并把旧存档叠组清理隔离到 v0.28.1 强制迁移。伴随地图新增 30 tag 精确身份触发器和 v0.14 迁移；废弃不再参与判断的 `jxp_route_ideas_synced_v0241`。R2 从五画像扩为六画像，加入 OTM 三界面截图、fresh `setup.log` 证据及原版大友序列 blocker；R3 明确要求标题、七槽与全部 tooltip 同组。未启动游戏、未改 daily 配置、未改 descriptor 版本。
- Evidence: 主门禁 `26/26`、Clausewitz `251/251`、core tests `241/241`；34/34 同名理念覆盖均先于固定原版来源，68/68 可选大名具备精确理念身份。联合地图门禁为 `0 errors / 0 warnings`，120 profiles、137,382 日期通过，runtime oracle SHA-256 为 `B1D3B0CF6364D8C10D93DC6A7BBAF43E1736BEBCEE9AC40322B6603DEF4134F3`。验收 helper 的新增 OTM blocker 通过，整体 `44/45`，唯一失败是四个新 runtime 文件尚未进入 Git tracked set；oracle contract `7/8`，唯一失败是 live bytes 尚无同内容 Git snapshot。R5 在 matrix `46EEAC35...834A` 下重新返回 `ADMITTED_STATIC_INPUT`，且 `game_started=false`。repo/installed skill 均 `Skill is valid!`，本切片三文件 SHA-256 逐字节一致，兼容入口对当前项目实际返回 `26/26 PASS`。
- Runtime/TODO: `JXP-020` 保持 `IN_PROGRESS / PENDING_RUNTIME`；旧 immutable candidate `2bf24123...` 不含此修复。形成新候选需要用户另行授权 Git 提交；之后仍须取得新的明确启动许可，从 PROBE 重跑，R2/R3 截图与 fresh logs 通过前不得声称 `national_idea8` 已在引擎内关闭。

### 2026-07-13 - RUNTIME-PROBE-001 - Isolated launch diagnosis and parser remediation (`no version bump`)

- Status: `PROBE_ABORTED; ISOLATED_USERDIR_AND_MAIN_MAP_LOAD_PROVEN; NO_READY_RUNTIME_EVIDENCE; STATIC_REMEDIATION_PASS; PENDING_NEW_CANDIDATE_AND_PERMISSION`。
- Scope: 消耗用户明确的 `授权 PROBE`，以 pinned `eu4.exe -userdir=C:\JXP_Acceptance` 启动一次可见隔离探针。实际 argv 完全匹配；隔离 `setup.log`/`error.log` 直接列出主 Mod 与地图 Mod，解释了为何日常语言/偏好没有加载。首启语言界面的一个 `Enter` 在长加载后传播并误入 1444 大友开局，故没有 main-menu screenshot，session 当场 ABORT 而非伪报 PASS。根据 fresh log 修复四类 event-modifier 键、灾难 inline `on_end`、三个隐藏地图事件的完整 shell，并将这些规则写入 repo/installed `eu4-modding` skill 与通用 validator；未修改原版目录、daily launcher/playset、descriptor 版本或外部 R5 原件。
- Evidence: session `20260714T040029Z_probe_default_af1bdced` SHA-256 `E38A2A7DB07547867A516A333308A7B6700F67132C6EA580505C0E27F4571994`，abort SHA-256 `F0452BC962CEE3F9E0DB69575E7839962A78419F2F8193802E48B3559EEE04F3`；daily `dlc_load.json` 仍为 147 bytes / `D317B6EE...AF72`，`launcher-v2.sqlite` 仍为 176,128 bytes / `A27BF04D...A30`。修复后主门禁 `26/26`、Clausewitz `250/250`、core tests `236/236`；联合地图门禁 `0 errors / 0 warnings`，120 profiles、137,382 日期和 runtime oracle 均通过；repo/installed skill 均 `Skill is valid!` 且三份改动文件逐字节一致。
- Runtime/TODO: 本次只证明隔离路径与两个 Mod 被加载，不证明 main menu、任务、改革、理念 UI、灾难玩法或任何 R1-R12 场景。`JXP-001` / `004` / `005` / `008` / `009` / `017` / `020` 等运行项保持开放；`national_idea8` 仍是 blocker 风险。旧 runtime candidate `2bf24123...` 不含本次修复，不得重用；必须先形成新 immutable candidate、重新部署，再取得新的明确启动许可。

### 2026-07-13 - LEDGER-006 - Active TODO runtime closure projection (`no version bump`)

- Status: `STATIC_PASS; 13/13_ACTIVE_TODOS_MAPPED; MATRIX_PROJECTION_GUARDED; PENDING_USER_APPROVAL`。
- Scope: 在唯一共享总账中新增 `Active TODO Runtime Closure Map`，逐项记录 13 个活动 TODO 的当前静态位置、必需 R1-R13 阶段和实际关闭证据；明确 WAK/IJP 的静态循环合同不能替代 R7/R8 自然 AI 与引擎节奏证明。`shared_ledger.py` 现在解析当前 matrix，拒绝活动 TODO 漏行、重复、非活动残留或阶段集合漂移；repo/installed skill 同步要求把闭环表保持为 matrix 的精确投影。
- Evidence: 机器审计得到 `13` 个活动 TODO、`13/13` 已映射、`0` 个无场景活动项和 `0` 个指向非活动 TODO 的场景；live、phase-drift、missing-row 定向测试 `3/3` 通过。主门禁 `26/26`、Clausewitz `250/250`、core tests `233/233`；联合地图门禁保持 `0 errors / 0 warnings`。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer；TODO 状态未因新增映射而改变。下一步仍须取得用户明确许可，从 PROBE 开始按映射执行，不得跳过 R7/R8 或以静态 PASS 关闭运行时条目。

### 2026-07-13 - LEDGER-005 - Explicit UTF-8 validator contract (`no version bump`)

- Status: `STATIC_PASS; FALSE_COUNTRYDATABASE_ADVISORY_CLOSED; SKILL_MIRRORED; PENDING_USER_APPROVAL`。
- Scope: 修复 `validate_eu4_mod.ps1` 在 Windows PowerShell 5.1 下以默认 ANSI 读取无 BOM UTF-8 EU4 文本的根因；descriptor、script、localisation、tag、country pool、mission/event `.gfx` 查询全部改为显式 UTF-8，并同步修复 `scaffold_eu4_mod.ps1` 对 `launcher-settings.json` 的读取。新增一份使用 EJP 风格十项中文姓氏的无 BOM fixture 回归测试和一份覆盖全部 skill PowerShell 路径型文本读取的编码合同，并把规则同步进 repo/installed `eu4-modding` skill 与 reference。未改 gameplay、地图、descriptor、版本、runtime candidate、matrix 或外部证据。
- Evidence: 定向回归 `2/2` 通过；通用 validator 对主 Mod 返回 `OK: No issues found`；主门禁 `26/26`、Clausewitz `250/250`、core tests `231/231`；repo/installed skill 均 `Skill is valid!`，受控文件 `11/11` 逐字节一致。CJP/EJP 原文件各有十项 `leader_names`，不再出现 9/6 误报。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer；运行时 TODO 状态不变。正式 fresh log 仍由获准后的 PROBE/R6/R7 证明，静态无警告不得冒充引擎运行结果。

### 2026-07-13 - LEDGER-004 - Current-host portability and R5 static admission (`no version bump`)

- Status: `STATIC_PASS; HOST_PORTABILITY_READY; R5_ADMITTED_STATIC_INPUT; MATRIX_BLOCKERS_NONE; PENDING_USER_APPROVAL`。
- Scope: 将 acceptance root 固定为 `C:\JXP_Acceptance`，更新 current Git/Python/Windows/package pins 与 README/PROBE argv；R5 matrix 固定原档 filename/size/SHA/header、13 个 completed missions、五槽任务和六类 BOM 计数。新增只读 `verify-r5-escrow`，严格绑定三份备份和三个 sidecar；matrix SHA-256 为 `44969E94D0EF349C0554681E5B8789E12A6D0A431300C010D319DD2BB9C7A268`，R5/R13 blockers 现为 `NONE`。
- Evidence: R5 verifier 返回 `ADMITTED_STATIC_INPUT`，内容身份 SHA-256 `E39CCED590778C9CFAFEB91B07F19CED8071C14723BAE95B8B1C6EF9C7224C0D`；acceptance helper `56/56`；主门禁 `26/26`、Clausewitz `250/250`、core tests `229/229`；联合地图门禁 `0 errors / 0 warnings`，覆盖 120 profiles 与 137,382 日期；external-toolchain baseline 12 records 匹配；repo/installed skill 均 `Skill is valid!` 且 `11/11` 文件逐字节一致；`git diff --check` 通过。preflight 12/12 pins 匹配；隔离 main/map 指纹为 `0D908FF8AE38...` / `9AA1589FFD69...`，PROBE 收据和隔离 `dlc_load.json` 分别为 `DB5E3D7F...` / `B8729255...`，daily 两文件前后 hash 不变。完整证据见 `jxp_runtime_portability_and_r5_admission_2026_07_13.md`。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer，也未创建 `before-session`、PROBE session 或 collection。`ADMITTED_STATIC_INPUT` 不等于迁移修复或 `RUNTIME_PASS`，Active TODO 状态不变；当前唯一下一步是取得用户明确启动许可。

### 2026-07-13 - LEDGER-003 - Schema-2 live state and original-machine R5 registry (`no version bump`)

- Status: `STATIC_FORENSIC_EVIDENCE; PORTABILITY_REVIEW_REQUIRED; R5_FOUND_NOT_ADMITTED; PENDING_USER_APPROVAL`。
- Scope: 将唯一共享总账升级为 schema 2，新增 current-machine/live execution state、严格有序的下一步队列和 external evidence registry；自动门禁扩大到全部 `JXP-001..023`、schema/live fields、R5 exact identity 与倒序 journal。新增只读历史报告 `jxp_original_machine_r5_recovery_2026_07_13.md`，未创建第二份 current TODO/status。
- R5 evidence: 原始 `autosave.eu4` 为 36,371,037 bytes / SHA-256 `9F6DD96A60C7B9F583C22F87E7DA2F5C659E2EDC14723483A077B7AFD73A8BEF`；三份命名 ZIP 的 hash/版本均登记。save header、JAP/open-trade、13 个 completed JXP missions、五槽 DOM+JXP 共存和六个 BOM-prefixed series 计数与 0.24.1 报告相符。原件及 sidecars 位于 `C:\JXP_R5_Escrow\20260713_original_machine`，未修改或上传。
- Portability baseline: 当前主机 helper 实测 52 项中 1 failure + 15 errors，均来自旧 profile acceptance root、trusted Git 或 external-toolchain pin；旧主机 `52/52` 只保留为历史证明。候选 root 为 `C:\JXP_Acceptance`，必须经 reviewed portability patch 后才能使用。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer；matrix 中 R5/R13 blocker 尚未变更，所有 Active TODO status/owner 保持不变，`JXP-016` 继续 `IN_PROGRESS / PROJECT`。本记录不构成 R5 admission、READY collection、`RUNTIME_PASS`、启动许可或上传许可。

### 2026-07-13 - HANDOFF-001 - Original-machine continuation and GitHub publication (`no version bump`)

- Status: `STATIC_PASS; PORTABLE_HANDOFF_PREPARED; PENDING_RUNTIME; R5_EXTERNAL_FIXTURE_REQUIRED`。
- Scope: 在根 `AGENT_HANDOFF_GUIDE.md` 中加入可直接复制的原机器 continuation prompt，并将当前线性开发历史纳入既有 draft PR #1 的 fast-forward 交接路径；prompt 只规定取得当前 Git/ledger 真相、skill 镜像、R5 防伪取证、host-portability、权限、运行顺序与完成标准，不建立第二份 current TODO/status。
- Original-machine boundary: 原 Windows profile 路径含空格，当前 helper 固定的交接机 roots 不可直接复用。原机器必须先只读封存真实 autosave/三份命名 ZIP，并按 JAP/open-trade/DOM+JXP mission serialization/JXP completed missions/六个 BOM series 与 pre-0.24.2 来源链复核内容身份，再对实际 game/daily/repo/acceptance roots 做受审查 portability 切片；任何 root/matrix/toolchain 变化后必须在最终 matrix SHA 下从 PROBE 起重跑，禁止用宽松路径参数、junction、旧 collection 或手工重标绕过 guard。
- Evidence: `git diff --check` 通过；主 Mod release gate `26/26`、Clausewitz `250/250`、core unit tests `221/221`；无 `-SkipMainModValidation` 的联合 map/history/content/compat/assets gate 为 `0 errors / 0 warnings`，覆盖 88 省、120 profiles 与全部 137,382 个可选日期；acceptance-helper tests `52/52`；runtime oracle `--check` 为 current；repo/installed skill 均 `Skill is valid!` 且 `11/11` 文件逐字节镜像。Current Snapshot 的联合事件实测数由陈旧 `498` 修正为 `500`；没有改玩法、地图、descriptor、runtime payload candidate、场景 blocker 或版本。
- Runtime/TODO: 没有启动 EU4、Launcher、dowser、bootstrapper 或 observer，没有生成或声称新的运行时证据；`JXP-016` 保持 `IN_PROGRESS / PROJECT`，其余 Active TODO status/owner 不变。R5 仍只能来自原机器真实未修改原件，prompt 本身不构成启动或上传许可。

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
- Evidence: acceptance helper `52/52` 通过（新增 CommonMark separator/fence alias、nested bool→int replay、Git tracked/untracked/ignored drift、Git batch body/OID authentication 与 bounded corrupt-read recovery、candidate revision runtime-whitelist/OID-authenticated chunked staging 与 bounded write-readback recovery、live-before-cleanup/post-clean deterministic-ephemeral lifecycle、pre/post temp-state TOCTOU guard、non-injectable authority、streaming stdout/stderr/timeout、aggregate input/whole-tree cap、exact skill-script allow-list 对抗测试）；isolated runner 已在 safe root 临时目录实测 Python `3.13.1` 与 NumPy/Pillow/PyYAML `2.4.2/12.3.0/6.0.3`，随后安全清除临时目录。oracle byte-for-byte `--check`、主模组门禁及不带 `-SkipMainModValidation` 的联合 map/history/content/compat/assets 门禁均通过；repo/installed `eu4-modding` skill 验证且镜像一致；`git diff --check` 通过。v2 clean-HEAD 全受控 gate 按设计只能在本 ledger 与 baseline 提交后执行，其结果由 sealed execution/handoff 承载而不反写受守护输入，避免用修改证据文件来追认自身。
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

- `JXP_AGENT_A_SOCIOECONOMIC_BASELINE_AUDIT.md` - JXP-037 国内阶层、市场、公司与任务重构的实现前静态基线审计。
- `JXP_AGENT_A_SOCIOECONOMIC_HANDOFF.md` - JXP-037 A/B 接口、生成器、迁移与静态/运行时边界 handoff。
- `JXP_FINAL_MISSION_SLOT_CONTRACT.md` - 统一状态任务 A slots 1–3 / B slots 4–5、指纹、tombstone 与迁移权威合同。
- `JXP_REWARD_OWNERSHIP_MATRIX.md` - 理念、任务、改革、阶层、公司与国内 capstone 的奖励主要所有者及首批去重合同。
- `jxp_0_22_0_working_plan.md` - 0.22.0 集成工作计划。
- `jxp_0_26_0_route_attribute_parity_audit.md` - 0.26.0 九路线与时代属性深度审计。
- `jxp_agent_a_daimyo_design_matrix_0_29_0.md` - Agent A 67 大名独特化权威设计矩阵；仅为静态设计合同。
- `jxp_current_progress_against_original_plan_2026_07_09.md` - 原始规划对照快照；已由本总账接管当前状态。
- `jxp_hotfix_debug_decision_ui_freeze.md` - 调试决议界面卡死热修复。
- `jxp_japan_map_refinement_feasibility_plan_0_23_2.md` - 日本地图细化可行性与实施计划。
- `jxp_main_map_compatibility_audit_2026_07_10.md` - 主 Mod/八十八国地图联合兼容审计。
- `jxp_master_todo_from_original_plan.md` - 旧主 TODO；已冻结，由本总账接管。
- `jxp_original_machine_r5_recovery_2026_07_13.md` - 原开发机 R5 原件恢复、内容身份与主机移植基线。
- `jxp_runtime_portability_and_r5_admission_2026_07_13.md` - 当前主机移植、R5 严格静态接纳与门禁结果。
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
