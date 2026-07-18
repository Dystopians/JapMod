# 《日轮诸道》Agent A 国内社会经济重构基线审计

- 日期：2026-07-17
- 对应总账：`JXP-037`
- 证据等级：`STATIC_AUDIT`；所有 EU4 UI、Crownland、保存重载与 AI 结论均为 `PENDING_RUNTIME`
- 仓库：`C:\Users\Fiber Memory\Documents\GitHub\JapMod-agent-a`
- 分支 / 基线 HEAD：`codex/content-agent-a` / `f9f0fecec9d185177691bb4b4e64f9a3e05b3912`
- 固定原版参考：EU4 `1.37.5.0 Inca (491d)`，只读目录 `D:\Steam\steamapps\common\Europa Universalis IV`

本文是开始批量写入阶层、任务和事件前的强制审计，不取代共享总账。本文所列“可行”只表示 1.37.5 脚本格式和当前仓库拓扑允许构建静态候选；本轮未获得启动 EU4 或 Launcher 的许可。

## 1. 工作树与集成基线

审计开始时 tracked worktree clean。登记 `JXP-037` 后，只有共享总账为 tracked modified；另有两份用户 Prompt 未跟踪，均为输入资料，不得随玩法提交：

| 状态 | 路径 | 处置 |
| --- | --- | --- |
| modified | `japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md` | Lead 登记 `JXP-037` 与 STARTED journal；后续按真实证据继续追加 |
| untracked | `Agent_A_日本内部与宗教系统_Prompt.md` | 保留、不暂存 |
| untracked | `Agent_A_超详细_日本阶层资本主义与国内终局重构_Prompt.md` | 本轮设计输入；保留、不暂存 |

相对整合分支 `codex/integrate-agent-a-b-20260717`（`32be2f1`），当前 HEAD 已增加日本开局总览、信州生成器修复及相应本地化/验证器，摘要为 12 files、约 `+3180/-39`。本轮不得回滚这些变化，也不得 cherry-pick 或重写 Agent B 工作区。

## 2. Estate 技术现状与 1.37.5 试验结论

### 2.1 当前 Mod 状态

主 Mod 当前不存在以下目录，因此没有真正的 JXP estate privilege 或 estate agenda：

- `common/estates/`
- `common/estate_privileges/`
- `common/estate_agendas/`

既有任务、触发器与事件直接读取原版 `estate_nobles`、`estate_church`、`estate_burghers`；三者在主 Mod 中分别约有 56、50、52 个引用点。现有“家系议题”“市场评定”是普通事件/flag，不是原版 Estate UI 中的 agenda。

### 2.2 采用的四阶层方案

采用设计方案 A：三个原版 estate ID 加一个自定义 estate。

| 社会功能 | 运行时 ID | 原因 |
| --- | --- | --- |
| 武家奉公众 | `estate_nobles` | 保留既有任务读取、Crownland、贵族灾难和原版回调 |
| 寺社宗门 | `estate_church` | 保留宗教任务、宗教 estate 回调与路线改宗兼容 |
| 町众豪商 | `estate_burghers` | 保留贸易/城市任务、Crownland 与商人 estate 回调 |
| 百姓惣村 | `jxp_estate_village_communes` | 原版没有无 DLC、无互斥污染的农民 estate；必须独立定义 |

拒绝复用 `estate_vaisyas`：它受 DLC/印度身份约束，且原版 `estate_burghers` 明确在 Vaisyas 存在时退出，会使町众豪商消失。其他特殊 estate 同样带有身份、DLC 或特权污染。

### 2.3 必须生成的完整覆写

Estate 顶层对象不能由另一个文件局部追加 `custom_name`、`privileges` 或 `agendas`。因此三份原版定义必须由生成器读取固定 1.37.5 输入、验证 SHA-256、作锚点注入，再生成 exact-path 完整副本：

| 原版相对路径 | 固定 SHA-256 | 生成内容 |
| --- | --- | --- |
| `common/estates/01_church.txt` | `CCA37F3F5B30595CC2A2DB9FB833A53F1F4551C188EB6341CD0C2FB54C6BF42B` | 日本动态名、新寺社特权与议程 ID |
| `common/estates/02_nobility.txt` | `78BEB182B60985A46E99F8BFF84A46CCCE274CC3944031C7366FE9A71428D9BE` | 日本动态名、新武家特权与议程 ID |
| `common/estates/03_burghers.txt` | `2DD634CEF4522EE8E43E6E34005779B90A806735A6C88B11831BCC30F7034DCD` | 日本动态名、新町众特权与议程 ID |

1.37.5 原版 estate 定义支持多个 `custom_name = { desc = ... trigger = {...} }`，故动态名称本身可行。getter 名由本地化后的 estate 名派生，中文名不适合组成可执行 `[Get...Name]` token；脚本 ID、getter 和动态本地化函数必须保持 ASCII，显示文案使用固定本地化键或 `$ESTATE_NAME$`。

第四 estate 能以增量文件定义，但原版 `events/EstatePrivilegesAndAgendasEvents.txt` 把 Call Diet 的 estate flags、选项和 `start_estate_agenda` 硬编码为 15 个原版 estate。若不覆写，该 estate 永远不会自然获得议程。故生成器还必须固定原版 SHA `D4E2CA0225356737A7D8660E6AAD6C93BBD6AEB53538A24D26A5E4CEBD9DC994`，保留 15 项字节语义并追加第 16 项百姓惣村路径。

原版 `common/scripted_effects/01_scripted_effects_for_estates.txt` 的 `pick_random_estate_if_present`、不满阶层叛军和征地忠诚返还也硬编码 15 个 estate。第五份 exact-path 输入必须固定 SHA `FA3F71509F86EA6B137E104336280F7B8EB49A712EECED918D670829DC04A8F1`，在不改变原 15 分支语义的前提下追加百姓惣村。

### 2.4 原生机制边界

- Crownland 只使用 `land_share`、`change_estate_land_share`、`estate_territory` 与 `crown_land_share`，不建立镜像变量。
- 单国同时持有 privilege 的原版上限是 6；本轮的 10–12 项是候选池，不是同时授予数。
- 第四 estate 若使用 `exempt_from_seize_land`，必须同时提供精确名称 `has_exempt_from_seize_land_for_jxp_estate_village_communes` scripted trigger；首版不启用该 mechanic。
- Estate UI 可滚动，第四张卡会自然换行；首版复用一个原版 estate icon frame，避免覆写已占满的 15 帧 atlas。独立 DDS/GFX 只能作为后续受控视觉切片。
- 路线、宗教、tag 改变必须事务式调用 `jxp_a_reconcile_estates_for_route`；不能只依赖 privilege 的 `is_valid` 自动撤销，因为它可能造成不可控的 loyalty/Crownland 突变。
- EU4 1.37.5 没有一个可增量注册并自动生成 estate 卡按钮的 `common/estate_actions` 目录。12 项互动改为四个国家决议打开阶层事件菜单，每个菜单三项有代价、带冷却的选项；文案不得冒充原生 estate-card 按钮。

## 3. 政府改革与候选面

当前日本政府体系已经包含：

- 原版君主制十一层中的日本化改革轨道；
- 27 项当前可见路线改革；
- 39 项创始家改革；
- 10 个终局权力结构及对应政治 capstone；
- 丰臣、佛教、日本内部战争和殖民继承国的专属 tier-one/后置接线；
- 大量 parked/dormant 历史定义，不能计作玩家可见深度。

全仓 `jxp_` 改革约 455 项，其中约 219 项含经济 modifier。新商业路线只能在现有原版层级内增加受严格 `potential` 控制的候选，不能创建第 12 层或让单层候选爆炸。`jxp_path_commercial_council` 采用一个互斥基础权力结构和三个后续分支，并由中央 reconcile 清除外国、殖民继承国和其他终局泄漏。

## 4. 现有经济内容盘点

### 4.1 可复用任务锚点

| 文件 | 当前经济主题/代表锚点 | 本轮用途 |
| --- | --- | --- |
| `missions/jxp_04_daimyo_missions.txt` | market roads、Sakai/Hakata merchants、artisan guilds | 旧档市场阶段推断；不重复发奖 |
| `missions/jxp_21_daimyo_house_missions.txt` | frontier markets、temple ledgers、temple market council、market towns、free markets、debt relief | 创始家商业遗产输入 |
| `missions/jxp_70_oda_toyotomi_missions.txt` | ODA 乐市乐座、TOY 藏入地/金银座/大坂财政 | ODA/TOY 国内模块输入 |
| `missions/jxp_japan_missions.txt` | 石见银、城下町市场、大坂米账、银绢流通、三都账册 | 市场阶段 1–3 的 canonical 旧任务哨兵 |
| `missions/DOM_Japanese_Missions.txt` | 原版 Ginza、manufactories、markets、estate 任务 | 兼容输入；不修改原版任务 ID |
| `missions/jxp_40_final_state_completion_missions.txt` | IJP 债务宽免、寺内市场等终局完成任务 | IJP 模块输入与重复奖励审查 |
| `missions/jxp_56_final_tag_identity_missions.txt` | CJP/EJP/RFJ 等 charter/国家工程 | 路线 capstone 归属审查 |
| `missions/jxp_03_overseas_missions.txt` | 商馆、太平洋、殖民与海外经营 | Agent B/既有海外边界，只读 |

可复用的 map-safe scripted triggers 包括 `jxp_has_osaka_rice_ledger_network_trigger`、`jxp_has_castle_town_market_network_trigger` 与 `jxp_has_halal_granary_network_trigger`。主 Mod 新条件继续使用这些语义触发器、国家拥有省份与原版锚点，不硬引用地图新增省份。

### 4.2 可复用事件与决议模式

| 文件族 | 当前用途 | 本轮处置 |
| --- | --- | --- |
| `events/jxp_25_daimyo_house_agenda_events.txt` | 市场掮客/寺账等家系议题 | 作为真实 estate agenda 的写作与迁移输入；旧事件保留 |
| `events/jxp_26_founder_legacy_councils.txt`、`jxp_34_daimyo_house_diet_events.txt`、`jxp_35_house_diet_legacy_events.txt` | 家系评定、议会与遗产 | 不冒充新 estate Diet；只读取既有选择 flag |
| `events/jxp_38_founder_reform_pulse_events.txt`、`jxp_43_preunification_memory_events.txt` | 改革脉冲与前统一记忆 | 商业遗产输入；属于永久叠加高风险区 |
| `events/jxp_71_disaster_events.txt` | 米价、救济、灾荒处理模式 | 新德政/米市危机的脚本参考，不复制事件 ID |
| `events/jxp_a_94_daimyo_depth_events.txt` | 67 家成长与永久记忆 | 只读取完成 flag；普通资本任务不得再叠同签名永久全国修正 |
| `decisions/jxp_03_overseas_decisions.txt` 与所有 `jxp_b_*` 海外决议 | 海外扩张/殖民章程 | B 所有，只通过能力接口衔接 |

### 4.3 公司与殖民章程现状

当前没有 `jxp_iface_a_market_stage_*`、`jxp_iface_a_company_*`、统一 company lifecycle、董事状态或国内公司上限。现有“charter/company/factory”字样分别服务任务奖励、B 殖民社会、海外商馆或终局 flavor，不能视作一个公司核心。

已存在、可复用且幂等的 A→B 能力 flags 位于 `jxp_a_91_oda_img_depth_effects.txt`：`jxp_iface_house_government_ready`、`diplomacy_ready`、`maritime_ready`、`logistics_ready`、`frontier_ready`、`religious_ready`、`mass_mobilization_ready` 与 `jxp_iface_buddhist_diplomacy_ready`。新系统只新增 Prompt 规定的最小 `jxp_iface_a_*` 阶段/能力握手，不直接授予 B 的海外成果。

## 5. 永久奖励密度基线

只读扫描 missions/events/decisions/scripted_effects/on_actions 得到：

- 453 次 `duration = -1` country modifier 授予；
- 392 个唯一永久 country modifier；
- 743 个包含经济键的 event modifier 定义；
- 332 种经济签名，其中 104 种重复；
- 高频完全相同小数值包括 31 份 `trade_efficiency = 0.05`、28 份 `advisor_cost = -0.05`、28 份 `global_trade_power = 0.05`、17 份 `production_efficiency = 0.05`。

最大永久授予来源包括 `jxp_43_preunification_memory_events.txt`（74）、`jxp_a_94_daimyo_depth_events.txt`（70）、`jxp_39_founder_idea_legacy_effects.txt`（37）、`DOM_Japanese_Missions.txt`（23）、`jxp_daimyo_legacy_events.txt`（20）和 `jxp_japan_missions.txt`（16）。这些数字包含身份 marker 与规则型状态，不能机械全删；具体归属与首批去重写入 `JXP_REWARD_OWNERSHIP_MATRIX.md`。

## 6. 当前任务列位与冲突结论

当前 12 个本土统一 profile 都恰好占有五个非 generic series。通常 slot 1/2 为各 14 项的 `jxp_japan_state_missions` / `jxp_japan_court_missions`，slots 3–5 由路线专属 series 填充；佛教 profile 使用五列完全替换；TOY 也有独立 3–5 列。开国路线的 slot 4/5 正是 B 边界 `jxp_japan_eastasia_missions` / `jxp_japan_pacific_missions`（文件 `jxp_03_overseas_missions.txt`）。

RSMTS 与当前验证器证明：不能再增加一个与既有 slot 同时 eligible 的独立 series；EU4 按 series 选槽，不会把两个文件的同 slot 任务安全拼接。Prompt 中“35 项、五列×七项”与同一 Prompt 的“A 只拥有列 1–3、B 独占列 4–5”在当前有效树上不可同时实现。采用的等价实现是：保留 35 个逻辑任务和五条主题链，但将它们与每路线 8 个国内任务生成到三个 A 复合 series（15/14/14），实际 slot 仅为 1–3；逻辑列记录在本地化、设计表和 validator 中。B 的 slot 4/5 文件、series 名和任务 ID 保持只读。完整合同见 `JXP_FINAL_MISSION_SLOT_CONTRACT.md`。

## 7. 切换、刷新与迁移入口

- canonical 延迟刷新：`jxp_refresh_route_missions_effect` → hidden `jxp_mission_refresh.1` → 次日唯一 `swap_non_generic_missions`。
- 外部改宗/政府变化：`common/on_actions/jxp_60_mission_runtime_on_actions.txt`。
- 旧迁移：`events/jxp_22_migration_events.txt`、`jxp_23_migration_events.txt`、`jxp_25_migration_events.txt`、`jxp_79_final_state_migration_events.txt` 及路线专属迁移。
- Startup/年度 reconcile 已采用逐国事件与幂等 flag；本轮沿此路径新增一次性 `jxp_a_110` 迁移和有公司时年度 pulse，不新增 monthly/world scan。
- 路线清理：`jxp_clear_all_route_flags_effect`、`jxp_sanitize_route_state_effect`、终局 power-structure sync。
- 佛教 profile 的中央 mission fingerprint 当前缺少完整 profile，属于本轮必须先修的静态缺陷；否则低频修复可能持续把合法佛教树判为无效。

## 8. A/B 文件所有权

### A 可安全新增/生成

- `jxp_a_110`–`jxp_a_114` 命名空间的 estates、privileges、agendas、triggers、effects、modifiers、on_actions、missions、events、decisions、reforms、本地化与定向 validator；
- 三份 pinned vanilla estate exact-path 生成物；
- pinned Call Diet 与 `01_scripted_effects_for_estates.txt` exact-path 生成物；
- A 所有的中央路线刷新、迁移、debug cleanup 与共享 ledger；
- 主/地图兼容 validator 中的 A 合同。

### 必须只读

- 所有 `jxp_b_*` missions/events/decisions/effects/reforms/CB/wargoal/subject/localisation/tests；
- `missions/jxp_03_overseas_missions.txt`；
- `tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt`；
- B 的殖民继承国、殖民社会、独立/东归、海外战争、大陆、朝鲜与中国实现；
- runtime acceptance、oracle、visualizer 与 installed skill（除非后续得到另行授权/产生可复用规则）。

## 9. 静态与运行时证据基线

基线分支在前序合并中通过过主/地图静态门禁，但那不是本轮新内容的证据，也不是游戏内证据。本轮所有生成器必须提供 `--check`，定向测试至少覆盖：pinned inputs、estate 列表与 Call Diet 16 项、48+ privileges、40 agendas、四阶段单调性、35 个逻辑资本任务、公司生命周期、12 路线差异、A/B slot 合同、迁移幂等、无 monthly/world scan、本地化 source→active。

在获得新的明确启动许可前，下列只能保持 `PENDING_RUNTIME`：四张 estate 卡、动态名、Crownland、Diet 第四选项、privilege grant/revoke、议程完成/失败、四危机起止、任务实际换树、公司续约/破产、DLC 开关、主+地图、保存重载、30+10 局观察与 fresh logs。

## 10. 实施决策

1. 建立一个权威社会经济 plan 和确定性 builder；所有大批 gameplay、本地化与 pinned 覆写由它生成，生成物不得手改。
2. 三原版 estate、Call Diet 与 estate 中央 scripted effects 覆写都必须保真比对；原版输入哈希漂移即拒绝生成。
3. 复用三原版 estate + 一自定义农民 estate；不复制四套极端路线 estate。
4. 市场与公司使用离散 flags、estate loyalty/influence、债务/通胀和有限期 modifier；不新增 0–100 条。
5. 每年 pulse 只在国家持有公司/危机/待 reconcile flag 时执行；不遍历世界省份。
6. 35 个逻辑资本任务与 12×8 国内模块由三列 A 复合树承载，列 4/5 永久保留给 B。
7. 普通任务奖励以解锁、事件、互动、有限期推进和省级建设为主；每路线只保留一个国内永久 capstone。
