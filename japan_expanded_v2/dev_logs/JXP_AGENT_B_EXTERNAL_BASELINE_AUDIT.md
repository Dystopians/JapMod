# Agent B 海外国家体系扩展基线审计

审计时间：2026-07-17（America/Los_Angeles）  
证据类别：只读静态基线；不构成游戏内运行证据  
权威状态：本文件只记录本轮实施前的历史基线；当前状态仍以 `JXP_SHARED_DEVELOPMENT_LEDGER.md` 为准。

## 1. Git 与并行状态

- 工作树：`.integration-agent-ab-loc`
- 分支：`codex/fix-reform-names-and-ui-localisation`
- 基线 HEAD：`622d2928348800a084a43245c48deccaf678425e`
- 基线提交说明：`feat: add Japanese names for the Americas`
- 未暂存修改：
  - `japan_expanded_v2/common/province_names/japanese_g.txt`
  - `japan_expanded_v2/tools/jxp_b_province_name_builder/america_japanese_names.json`
  - `japan_expanded_v2/tools/jxp_b_province_name_builder/build_america_province_names.py`
  - `japan_expanded_v2/tools/jxp_validation/tests/test_jxp_b_america_province_names.py`
- 未跟踪文件：
  - `japan_expanded_v2/tools/jxp_b_province_name_builder/generated_japanese_g_america_utf8_source.txt`
- 上述五项均属于前一轮“美洲日式地名与中文显示名”生成切片，本轮必须保存，不得覆盖或混入海外政治生成器。
- Agent A 工作树基线为 `f9f0fecec9d185177691bb4b4e64f9a3e05b3912`；审计时只修改共享总账，并有两份用户 Prompt 未跟踪，没有观察到与本轮 B 游戏文件相撞的活动内容改动。
- Agent A 独占面保持不变：第 1—3 任务列、estate/特权/议程、国内市场、国内公司核心、国内经济事件、奖励所有权矩阵、唯一理念注册表和共享总账。

## 2. 静态测试基线

本轮编码前只运行 B 相关定向测试：

```text
python -m unittest
  jxp_validation.tests.test_colonial_expansion
  jxp_validation.tests.test_continental_strategy
  jxp_validation.tests.test_korea_campaign
  jxp_validation.tests.test_china_endgames
  jxp_validation.tests.test_overseas_program_integration
  jxp_validation.tests.test_jxp_b_america_province_names
```

结果：`59 tests / OK`。未启动 EU4、Launcher 或观察局。

## 3. 殖民社会底层

- 三项长期状态已经存在并集中初始化、增减与 0—100 clamp：
  - `jxp_b_colonial_identity`
  - `jxp_b_metropole_control`
  - `jxp_b_local_compact`
- 所有权文件：
  - `common/scripted_effects/jxp_b_91_colonial_society_effects.txt`
  - `common/scripted_triggers/jxp_b_91_colonial_society_triggers.txt`
  - `events/jxp_b_91_colonial_society_events.txt`
- 年度 pulse 为单国自续事件，间隔 365 日；没有现成的月度世界扫描。
- 五种互斥宪章已经存在：朱印日本町、军屯、信仰共同体、自由港、海军站。改革宪章需行政/外交点与金钱，并保留二十年制度代价。
- 共享事件库已有 36 个可见事件（`jxp_colonial_society.101–136`）及一个隐藏分派事件，已覆盖第二代出生、回流、双语、土地、公民、代表、宗教、民兵、税制和公司债务等主题。
- 缺口：没有母国路线遗产、离散政治派系、十项共享政治决议或五国“国体图志”。

## 4. 五个殖民继承国

| 国家 | 当前任务 | 当前事件 | 当前决议 | 当前一级改革 | 当前专属灾难 |
| --- | ---: | ---: | ---: | ---: | ---: |
| NYA 新大和合众国 | 30 | 10 | 1（形成） | 4 | 0 |
| HKK 北辰海国 | 15 | 8 | 1（形成） | 3 | 0 |
| NJF 南洋日本町联邦 | 15 | 8 | 1（形成） | 4 | 0 |
| OIA 大洋诸岛盟 | 15 | 8 | 1（形成） | 3 | 0 |
| TPF 两洋联邦 | 0 独立任务 | 5 | 0 | 1 | 0 |

- NYA 的五个任务系列都以 `NYA OR TPF` 为 potential，TPF 当前实际继承 NYA 的 30 项任务；这与本轮规格相反。
- TPF 已有独立 tag、旗帜、理念源、三年财政评议和永久治理代价，但没有独立任务树、四改革选择、制宪危机或解体路径。
- HKK/NJF/OIA 各有五列，每列只有三项任务，仍是浅层树。
- 五国本地化 source/active 当前成对完整：B94 为 165/165 keys，B95 为 330/330，B98 为 67/67；active 文件有 UTF-8 BOM 并使用 EU4SpecialEscape。

## 5. 国家形成、玩家切换与理念注册

- NYA/HKK/NJF/OIA 均使用固定 tag 的 `switch_tag`；EU4 1.37.5 原版 `events/disaster_ming_crisis.txt` 有相同效果范例。
- 动态殖民国 fallback 没有伪装成自动切换：本地化明确要求使用原版“释放殖民地并扮演”按钮。
- 固定 tag 切换只静态证明了脚本形状；AI 接管、军舰、债务、顾问、保存重载与一次性启动金尚无运行证据。
- 殖民国家理念写在 `tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt`；运行时唯一注册表仍由 Agent A 的生成器统一产出。B 不直接编辑 `common/ideas/00_country_ideas.txt`。

## 6. 特殊战争与东归

- 殖民自治战争已有独立、自治章程、贸易自主、恢复本土控制四种结果，wargoal 不开放普通土地要求。
- 当前原版 `po_independence` 胜利不会自动调用 `jxp_b_96_mark_full_independence_effect`；战争后可能残留危机标志和缺少 B 独立接口，需在单国和平/战争结束钩子中幂等收敛。
- “终结日本新世界统治”已有殖民起源与新大陆/大洋洲筛选、四十年再殖民限制和非吞地 wargoal；但清理宗主宣称仍使用 `every_province` 全球扫描，违反本轮性能边界，必须改为只遍历战败方已筛选 subject 的已拥有省份。
- 东归革命已有解放海外、旧大陆成员国、两洋联邦、迁都东归四种非吞并结果；没有免费核心，但固定 1020 设都路径仍待运行验证。

## 7. 大陆经略与第二代治理

- B99 已有六战区：琉球、朝鲜、满洲/北方、台湾/福建、中国沿海、菲律宾/东南亚；并按十二种日本终局状态应用不同 doctrine modifier。
- 战区入口有稳定、财政、港口、科技、海陆军与破产刹车；没有全亚洲永久宣称。
- 四种治理已经存在：军事奉行区、地方王统安堵、贡贸客户区、国司直辖；当前只给予 7300 日省级/国家 modifier。
- 缺口：没有二十年内三次评议、转型冷却、终局分化、旧 modifier/event target 清理，也没有十二路线各自五项大陆、五项海外任务与对外 capstone。

## 8. 朝鲜渡海役

- 当前是十个线性准备决议、五项 0—100 准备变量、18 个战争压力事件、六种战后结局。
- 渡海 CB 使用正常征服成本的惩罚版：AE ×1.5、和平费 ×1.25；没有免费永久宣称。
- 缺口：未聚合为五个玩家可读阶段；未从旧任务 `mission_completed` 重建阶段；战争主题少两项；无战后二十年开始的漂流民送还—对马调停—倭馆恢复—通信使—文化贸易—长期和平链。
- 当前 wargoal 开放对 KOR 的普通省份要求，却没有将可索取省份限制到 `korea_region`，需增加地理白名单与反整吞测试。

## 9. 中国三终局与八纮一宇

- B100 已有奉受天命、海上礼仪圈、海邦新秩序三条互斥入口及有/无 Mandate DLC fallback。
- 当前仍是“选路 + 一次完成”的骨架，缺少长期朝贡、驿路、官员、文化冲突、沿海联盟和公司政治事件链。
- 八纮一宇现有安全合同：实际日本天朝皇帝、需要 Mandate DLC、八个战略港白名单、已有普通宣称、AE ×0.75、和平费 ×1、`deny_annex = yes`，优先朝贡/释放/归还/贸易，并带治理容量、州维护与叛乱代价。

## 10. 琉球、对马、北方、台湾与公司

- 五家地区公司均未实现；目前只有五种殖民宪章和 B92 区域原语。
- 琉球、北方、台湾只有通用战区/B92 选择；对马只有少量东亚通事事件。
- 缺口：琉球八事件与王国选择、对马宗氏/倭馆/双重中介链、北方先住民族持续事件与强制劳役后果、台湾当地社会/福建商人/海禁/王朝更替链。
- `jxp_iface_b_overseas_company_active`、`jxp_iface_b_ryukyu_compact_active`、`jxp_iface_b_northern_compact_active` 尚不存在。

## 11. RNW、DLC、AI 与性能

- B92/B94/B95 已有 `is_random_new_world = yes`、`continent = new_world` 的固定地图 fallback；当前证据仍是字符串级静态检查。
- Mandate DLC 有/无已静态覆盖；殖民、政府改革和 estate 相关 DLC-off 尚无 B 专属矩阵。
- AI 决议已有破产、贷款和部分路线刹车，但没有表驱动证明强宗主自治、相对实力、运输船、目标强度、锁国低殖民倾向、TPF 低概率和东归极低概率。
- 运行矩阵尚未登记 JXP-031–036 的玩家切换、保存重载、RNW、五国灾难、特殊战争或观察局场景。

## 12. 高风险完整文件覆写

- `common/governments/00_governments.txt`：完整原版注册表覆写；新增改革只能做最小定向注册并由集成测试固定。
- `common/ideas/00_country_ideas.txt`：唯一生成注册表；B 禁止手改。
- `missions/Japanese_Missions.txt`、`missions/DOM_Japanese_Missions.txt`：钉死原版任务覆写；B 新内容不得借复制整文件接入。
- 地图 Mod 的 map/history/tag 文件和主 Mod 的 A 第 1—3 列均不在本轮写入范围。

## 13. 本轮实施边界

- 继续复用三项殖民状态、五宪章、既有独立战争、六战区、朝鲜战役和中国三终局；不创建第二套长期变量或第二套战争体系。
- 新增内容优先使用 `jxp_b_110+` 独立文件和 B 公共接口；需要接入既有 formation/startup/pulse 的地方只做最小补丁。
- 所有玩家可见文字先写 `localisation_source` 可读 UTF-8，再生成 active UTF-8 BOM EU4SpecialEscape。
- 本轮不启动 EU4；所有“保存重载、AI 观察、UI、战争引擎”结论保持 `PENDING_RUNTIME`。
