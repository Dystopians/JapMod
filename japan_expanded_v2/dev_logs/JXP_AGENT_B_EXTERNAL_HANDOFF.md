# Agent B 殖民继承国、大陆经略与跨太平洋重构交接报告

编制日期：2026-07-18（America/Los_Angeles）
证据等级：`STATIC_SAFE / PENDING_RUNTIME`
权威说明：本文件是实施交接报告，不替代 `JXP_SHARED_DEVELOPMENT_LEDGER.md`；共享总账仍由 lead/Agent A 维护。

## 1. 实际 HEAD

- 工作树：`.integration-agent-ab-loc`
- 分支：`codex/fix-reform-names-and-ui-localisation`
- 本报告编制时的玩法内容 HEAD：`b51e3fb317c5cd31f0e8a9a7ecd2ae2d75c43afd`
- 任务起始基线：`622d2928348800a084a43245c48deccaf678425e`
- 本报告自身所在的文档提交无法在其正文中自指；最终交付消息应以 `git rev-parse HEAD` 给出的文档提交为准。
- 没有启动 EU4 或 Launcher，因此本报告不作 `RUNTIME_CONFIRMED` 声明。

## 2. 基线审计

只读基线记录在 `JXP_AGENT_B_EXTERNAL_BASELINE_AUDIT.md`，提交为
`4724d87765cd4e23d77a77ed0fa99f7c85a5051e`。主要基线缺口如下：

- NYA 已有30项任务，HKK/NJF/OIA 各15项，TPF 没有独立任务树并继承 NYA。
- 五个殖民继承国没有完整国体危机，HKK/NJF/OIA 深度不足。
- 三项殖民社会变量已经存在，但没有母国遗产、派系显示和共享政治行动。
- 五家海外公司、四地区长期外交、十二路线对外签名任务、第二代治理评议均不存在。
- 朝鲜渡海役仍是十个散列准备决议，没有五阶段叙事、地理白名单和战后二十年和解链。
- 中国三终局只有入口与一次完成骨架。
- 玩家切换、RNW、DLC、AI、保存重载与战争引擎只有静态证据。

实施复用了既有三变量、五宪章、特殊战争、六战区和中国三终局，没有另造第二套长期数值或第二套战争体系。

## 3. 新增和修改文件

以下为 `4724d87..b51e3fb` 的玩法文件清单。`A` 表示新增，`M` 表示最小接入或扩展。

### 3.1 政府、状态、触发器与战争

```text
M common/cb_types/jxp_08_cb_types.txt
M common/cb_types/jxp_b_100_china_endgames_cb_types.txt
M common/cb_types/jxp_b_101_korea_campaign_cb.txt
M common/cb_types/jxp_b_96_colonial_independence_cb.txt
M common/cb_types/jxp_b_97_end_metropole_rule_cb.txt
M common/cb_types/jxp_b_98_eastward_revolution_cb.txt
M common/cb_types/jxp_b_99_continental_strategy_cb.txt
M common/event_modifiers/jxp_b_95_secondary_states_modifiers.txt
A common/event_modifiers/jxp_b_112_external_modifiers.txt
A common/event_modifiers/jxp_b_113_external_modifiers.txt
A common/event_modifiers/jxp_b_115_external_route_modifiers.txt
M common/government_reforms/jxp_b_94_new_yamato_reforms.txt
M common/government_reforms/jxp_b_95_secondary_colonial_reforms.txt
M common/government_reforms/jxp_b_98_transpacific_state_reform.txt
M common/governments/00_governments.txt
A common/on_actions/jxp_b_110_colonial_state_crisis_on_actions.txt
A common/on_actions/jxp_b_117_external_reconcile_on_actions.txt
A common/opinion_modifiers/jxp_b_112_external_opinions.txt
A common/opinion_modifiers/jxp_b_113_external_opinions.txt
A common/scripted_effects/jxp_b_110_colonial_depth_effects.txt
A common/scripted_effects/jxp_b_112_external_effects.txt
A common/scripted_effects/jxp_b_113_external_effects.txt
A common/scripted_effects/jxp_b_115_external_route_effects.txt
A common/scripted_effects/jxp_b_117_external_reconcile_effects.txt
M common/scripted_effects/jxp_b_100_china_endgames_effects.txt
M common/scripted_effects/jxp_b_101_korea_campaign_effects.txt
M common/scripted_effects/jxp_b_102_overseas_program_effects.txt
M common/scripted_effects/jxp_b_94_new_yamato_effects.txt
M common/scripted_effects/jxp_b_95_secondary_states_effects.txt
M common/scripted_effects/jxp_b_96_colonial_independence_effects.txt
M common/scripted_effects/jxp_b_97_end_metropole_rule_effects.txt
M common/scripted_effects/jxp_b_98_transpacific_state_effects.txt
M common/scripted_effects/jxp_b_99_continental_strategy_effects.txt
M common/scripted_effects/jxp_generated_debug_cleanup_effects.txt
M common/scripted_effects/jxp_scripted_effects.txt
A common/scripted_triggers/jxp_b_110_colonial_depth_triggers.txt
A common/scripted_triggers/jxp_b_112_external_triggers.txt
A common/scripted_triggers/jxp_b_113_external_triggers.txt
A common/scripted_triggers/jxp_b_117_external_reconcile_triggers.txt
A common/scripted_triggers/jxp_b_118_external_fallback_triggers.txt
M common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt
M common/scripted_triggers/jxp_b_101_korea_campaign_triggers.txt
M common/scripted_triggers/jxp_b_102_overseas_program_triggers.txt
M common/scripted_triggers/jxp_b_97_end_metropole_rule_triggers.txt
M common/wargoal_types/jxp_b_101_korea_campaign_wargoal.txt
```

### 3.2 决议、事件与任务

```text
A decisions/jxp_b_110_colonial_state_decisions.txt
A decisions/jxp_b_111_colonial_state_actions.txt
A decisions/jxp_b_112_overseas_company_decisions.txt
A decisions/jxp_b_113_regional_diplomacy_decisions.txt
A decisions/jxp_b_115_external_route_interactions.txt
A decisions/jxp_b_118_external_fallback_decisions.txt
M decisions/jxp_b_100_china_endgames_decisions.txt
M decisions/jxp_b_101_korea_campaign_decisions.txt
M decisions/jxp_b_94_new_yamato_decisions.txt
M decisions/jxp_b_95_secondary_colonial_states_decisions.txt
M decisions/jxp_b_99_continental_strategy_decisions.txt
A events/jxp_b_110_colonial_migration_events.txt
A events/jxp_b_110_colonial_state_depth_events.txt
A events/jxp_b_110_colonial_state_guide_events.txt
A events/jxp_b_111_colonial_state_crisis_events.txt
A events/jxp_b_111_secondary_state_depth_events.txt
A events/jxp_b_112_overseas_company_events.txt
A events/jxp_b_113_china_endgame_depth_events.txt
A events/jxp_b_113_postconquest_governance.txt
A events/jxp_b_113_regional_diplomacy_events.txt
A events/jxp_b_114_transpacific_depth_events.txt
A events/jxp_b_115_external_route_events.txt
A events/jxp_b_117_external_reconcile_events.txt
A events/jxp_b_118_external_fallback_events.txt
M events/jxp_b_101_korea_campaign_events.txt
A missions/jxp_b_114_transpacific_federation_missions.txt
M missions/jxp_03_overseas_missions.txt
M missions/jxp_09_religious_route_missions.txt
M missions/jxp_11_branching_missions.txt
M missions/jxp_40_final_state_completion_missions.txt
M missions/jxp_56_final_tag_identity_missions.txt
M missions/jxp_a_96_buddhist_missions.txt
M missions/jxp_b_94_new_yamato_missions.txt
M missions/jxp_b_95_secondary_colonial_states_missions.txt
M missions/jxp_japan_missions.txt
```

`jxp_a_96_buddhist_missions.txt` 的改动已获用户明确授权，且只在原有第4、5列末端追加 B115 佛教对外任务；没有改变 Agent A 第1—3列或其既有任务效果。

### 3.3 本地化、生成器与测试

```text
A localisation_source/jxp_b_110_colonial_state_depth_l_english_utf8_source.yml
A localisation_source/jxp_b_112_external_l_english_utf8_source.yml
A localisation_source/jxp_b_113_external_l_english_utf8_source.yml
A localisation_source/jxp_b_115_external_routes_l_english_utf8_source.yml
A localisation_source/jxp_b_117_external_reconcile_l_english_utf8_source.yml
A localisation_source/jxp_b_118_external_fallback_l_english_utf8_source.yml
M localisation_source/jxp_b_101_korea_campaign_l_english_utf8_source.yml
A localisation/jxp_b_110_colonial_state_depth_l_english.yml
A localisation/jxp_b_112_external_l_english.yml
A localisation/jxp_b_113_external_l_english.yml
A localisation/jxp_b_115_external_routes_l_english.yml
A localisation/jxp_b_117_external_reconcile_l_english.yml
A localisation/jxp_b_118_external_fallback_l_english.yml
M localisation/jxp_b_101_korea_campaign_l_english.yml
A tools/jxp_b_colonial_depth_builder/build_colonial_state_depth.py
A tools/jxp_b_external_route_builder/build_external_routes.py
A tools/jxp_validation/jxp_b_external_fallback_scenarios.json
A tools/jxp_validation/tests/test_b117_external_engine_contract.py
A tools/jxp_validation/tests/test_colonial_state_depth.py
A tools/jxp_validation/tests/test_external_depth.py
A tools/jxp_validation/tests/test_external_fallbacks.py
A tools/jxp_validation/tests/test_external_route_missions.py
M tools/jxp_validation/tests/test_colonial_expansion.py
M tools/jxp_validation/tests/test_korea_campaign.py
M tools/jxp_validation/tests/test_overseas_program_integration.py
```

所有新增或修改的中文先写入 `localisation_source`，再生成带 UTF-8 BOM 的 EU4SpecialEscape active 文件；定向检查确认 active 中没有裸 CJK、裸 key 或 source/active key 漂移。

## 4. 母国遗产矩阵

母国路线只在殖民继承开始时记录一次；后续母国改道不会重写既有遗产。重复或旧档叠加通过优先级清理为唯一标志。

| 遗产 | 记录条件 | 殖民叙事方向 |
| --- | --- | --- |
| 未定国是 | 尚未选定最终路线 | 诸州公议、地方自治与多路并存 |
| 锁国 | `jxp_path_sakoku` | 四口互市、近海守备与有限外交通道 |
| 开国 | `jxp_path_open_trade` | 朱印商贸、远洋舰队与移民章程 |
| 佛教 | `jxp_path_buddhist` | 护法外交、寺院移民与施药救济 |
| 吉利支丹 | KJP/吉利支丹路线 | 本地神职、东方教会与反保护权依附 |
| 儒教 | CJP/儒教路线 | 礼仪、学宫与海上经世网络 |
| 皇道 | EJP/皇道路线 | 朝廷使节、国司任期与外朝裁断 |
| 改革宗 | RFJ/改革宗路线 | 会众自治、自由海法与反垄断 |
| 海峡苏丹国 | SJP/海峡路线 | 卡迪、牙人与多法域港市 |
| 一向门徒 | IJP/一向路线 | 惣村互助、义仓与合作殖民 |
| 倭寇船盟 | WAK/倭寇路线 | 自由港、私掠问责与船主自治 |
| 丰臣 | TOY | 兵站、有限保护、撤军与和解责任 |

`jxp_iface_a_company_state_route` 没有实际 A 侧 writer，本轮没有伪造该接口；其情形回落到真实存在的路线/科技/港口条件。

## 5. 殖民国家共享政治框架

- 继续使用并只使用三项既有 0—100 状态：`jxp_b_colonial_identity`、`jxp_b_metropole_control`、`jxp_b_local_compact`。
- 普通事件和决议通过既有有界 `add_*` helper 增减，不直接重置玩家积累；初始化、迁移和集中 clamp 保持幂等。
- 派系不增加第四个长期变量，而由三变量、改革和当前国体派生为五个互斥显示标志：议会派、会社派、军务派、当地派、王党派。
- 新增十项共享政治行动，均支付行政/外交点并推动地方盟约，不提供无成本永久增益。
- “国体图志”事件根据实际主导派系动态说明当前政治结构。
- 清理效果覆盖派系标志、危机状态、公司、路线 capstone、地区协约和迁移 pending 标志。

## 6. NYA 新大和合众国

- 任务：35项、五列；主题为西岸立足、地方盟约与公民、联邦政治、太平洋经济、独立与东归。
- 事件：20项可见深度事件，并保留原有殖民社会共享事件。
- 决议/行动：10项 NYA 专属政治行动，另有共享政治行动与国体图志。
- 一级改革：诸港联邦议会、边疆军务共和国、海商合众国、大洋王政，四者互斥且在注册表中只占合法一级改革位置。
- 危机：新大和国体危机，以年度单国 pulse 评估身份、控制、盟约和改革，不新增第五个以上的全局 disaster 定义；结局要求妥协、付费整顿或承受长期代价。
- 任务不再与 TPF 共用 potential；TPF 已从 NYA 树完全分离。

## 7. HKK 北辰海国

- 任务：28项、五列；寒港生存、北方社会、会社与政府、北太平洋、自治终局。
- 事件：16项，覆盖阿伊努中介、冬储、毛皮、俄国竞争、混合船员和公司治理。
- 决议/行动：5项专属行动。
- 改革：北海评议国、寒地会社国、边疆幕府三项互斥改革。
- 危机：北海会社专政；公司、军务和当地中介之间存在可付费的退出与让权路径。

## 8. NJF 南洋日本町联邦

- 任务：30项、五列；日本町网络、多宗教社会、当地王权、商社海权、联邦与独立。
- 事件：18项，覆盖通事行会、王权特许、朱印信用、浪人契约、季风救济和多宗教协商。
- 决议/行动：7项专属行动。
- 改革：日本町联邦、商馆评议国、多宗教港市国、海商王政四项互斥改革。
- 危机：诸港离心；地方港市和日本移民不能被单一中央无代价压服。

## 9. OIA 大洋诸岛盟

- 任务：28项、五列；星路航海、岛屿王统、移民社会、舰队贸易、联盟政治。
- 事件：16项，覆盖王统协约、领航学校、礁海关税、混合舰队、港税和风灾盟约。
- 决议/行动：5项专属行动。
- 改革：诸岛王统盟、港湾评议盟、远洋水军盟三项互斥改革。
- 危机：航路断裂；补给、岛屿自治和共同舰队必须重新议价。

## 10. TPF 两洋联邦

- 独立任务：35项、五列，不再继承 NYA；旧大陆成员国、海外成员国、两洋财政、双都宪法、联邦存亡各成一列。
- 事件：22项，覆盖双都、成员席位、财政、旧大陆/海外主导、解体和重建。
- 决议/行动：10项专属行动。
- 改革：双都联邦、旧大陆主导联邦、海外州权邦联、两洋执政府四项；旧存档已有替代宪法时，B 侧迁移会在 A 注册握手完成后移除兼容默认改革，避免同阶叠加。
- 危机：两洋宪制危机；可妥协、改宪或解散，解散标志会隐藏 TPF 专属任务与改革，而不是继续保留免费联邦收益。
- 形成、解体和旧档收敛使用后置幂等迁移，不直接修改 A 的中央注册文件。

## 11. 五家海外公司

| 公司 | 主要范围 | 成立代价与约束 | 长期循环 |
| --- | --- | --- | --- |
| 南洋朱印会社 | 越南、吕宋、暹罗、马来、香料群岛 | 100外交点、500金、8轻船；须获当地许可 | 设馆接受/拒绝、五年评议、续资/重整/撤销 |
| 北海互市会社 | 北海道、千岛、桦太、阿留申、北彼岸 | 75行政点、75外交点、450金 | 寒港补给、先住民族条约、毛皮价格和俄国竞争 |
| 台湾闽海会社 | 台湾、福建与闽海航路 | 125外交点、550金、10港口 | 海禁、海盗、商人董事与沿海政权更替 |
| 大洋开拓会社 | 太平洋岛链 | 125外交点、600金、10运输船 | 泊地、淡水、粮仓、岛屿王权与航路断裂 |
| 新大陆会社 | 美洲及跨太平洋港路 | 100行政点、150外交点、750金，且须有殖民/彼岸能力 | 土地契约、制造、代表权、财政崩裂 |

- 公司章程不自动吞并、造核、割地或建立属国；当地国家有接受和拒绝选项。
- 五家公司有永久 active modifier，但只持续到显式退出/解散；章程方向20年，业务投资与董事会5年，撤出代价5年。
- `jxp_iface_b_overseas_company_active` 由实际活跃公司派生；全部退出后清除。
- A 侧公司接口没有现成 writer，因此成立能力采用固定 fallback：外交科技9、8港口、500金，再叠加公司各自成本。没有假读不存在的接口。

## 12. 十二条终局对外模块

每个实际 profile 均有至少5项大陆签名和5项海外签名，196个有效任务 profile 静态无同槽竞争、单元格冲突或不可达前置。

| 路线 | 大陆侧 | 海外侧与 capstone |
| --- | --- | --- |
| 未定 JAP/诸州公议 | 对马、琉球、海东公议、通商约、共同守护 | 共同商馆、代表请愿、殖民预算、议席、万国公议 |
| 锁国 JAP | 海岸奉行、松前、对马通事、琉球礼仪、烽火海防 | 出岛、唯一窗口、漂流民送还与近海防卫；不要求殖民 |
| 开国 JAP | 朱印贸易、远洋海军、殖民开拓三方向 | 只能选一条主线和一条有限副线；贸易/开拓由任务成典，海军由严格决议 capstone 成典 |
| 佛教 JAP | 朝鲜佛寺使、中华经卷、琉球法灯、佛教保护国、诸宗海外席位 | 南海僧坊、寺院移民、施药院航路、护法海路、四海法灯；不要求征服佛教国家 |
| KJP | 长崎主教区、罗马使节、朝鲜教徒、中华教会港、东方主教会议 | 菲律宾、澳门、教会殖民地、本地神职、东方教会同盟 |
| CJP | 朝鲜使节、三教簿、不断祀、学宫使节、日本国王名分 | 翻译馆、银丝航路、三都账簿、城下市场、经世礼仪圈 |
| EJP | 琉球使、虾夷使、朝鲜使、朝廷海东使节、国司海疆 | 神祇使、皇室殖民章程、海外国司、亲征/外朝、太政官外朝 |
| RFJ | 改革宗居留、和兰学堂、盟约共同体、海外会众、自由海洋法 | 巴达维亚协约、敕许公司、自由海共同体、宗会宪制、盟约舰队 |
| SJP | 堺马来牙人、卡迪港庭、海峡协定、穆斯林港保护、季风护航 | 海教居留、朝觐簿、南海盟约、苏丹海法、季风迪万 |
| IJP | 共同体盟约、同行海路、寺内町侨民、共同义仓、受压门徒 | 寺院义仓、共同船厂、海外惣村、合作殖民地、同行诸国盟 |
| WAK | 对马通事、琉球文书、破除海禁、沿海岛主、海上保护费 | 黑潮书札、岛屿法庭、自由港、私掠札、东海船盟 |
| TOY | 大坂、聚乐第、堺奉行、藏入地账、太阁遗训 | 琉球、对马、渡海准备、东亚议和、天下和平；既有任务不重排，由专门章程收束 |

所有路线 capstone modifier 均为7300日，不是永久叠加。路线切换集中清理相关 flags/modifiers。RNW 下这些正常世界任务树不激活，改用第22节的简化 fallback。

## 13. 朝鲜五阶段映射

十个旧准备动作迁移为五个玩家可读的宏阶段；旧完成状态通过稳定任务/准备标志重建，不把高进度向下重置。

| 阶段 | 新宏决议 | 吸收的旧准备 |
| --- | --- | --- |
| 一：通交与名分 | 议定渡海名分 | 对马通事、通信使、假道与朝贡要求 |
| 二：名护屋兵站 | 总编名护屋兵站 | 名护屋仓廪、运输船名簿、渡海军粮 |
| 三：诸家军役 | 编定诸家军役 | 诸大名出兵额、轮换、总大将与军役契约 |
| 四：海峡与攻城 | 整备海峡与攻城 | 攻城器械、海峡护航、船队与后路 |
| 五：大陆介入 | 裁量大陆援朝 | 明/清援朝风险、最终兵站与十年开战窗口 |

准备完成后才授予渡海 CB；逾期不开战会解散兵站和军役，不允许永久无成本待发。

## 14. 朝鲜战争事件和结局

- 战争事件共20个主题节点：外交破裂、釜山登陆、粮道、地方抵抗、水军、明/清援军、寒冬、疫病、诸将争功、军纪与暴行、俘虏工匠、和谈、再征、国内财政、继承震荡、撤军、长期占领、船队疲敝等。
- 暴行、掳掠和强迁没有纯正面选项；短期军资伴随长期外交、抵抗、腐败或国内秩序代价。
- 六种结局均以后续实际状态为前提：

| 结局 | 约束 |
| --- | --- |
| 海峡通商和约 | 不转移土地，十五年外交与通商恢复 |
| 南部保护区 | 只承认正常和约已得据点/臣属，高自治并负担军港费用 |
| 扶植王统 | 只在 KOR 已通过正常和约成为属国时可用，二十年承担重建 |
| 高自治直辖 | 只作用于已实际拥有的朝鲜省份，不给核心，提高自治并承担二十年抵抗 |
| 战略撤退 | 支付撤军与欠饷，以有限后勤经验换取较低厌战 |
| 灾难性失败 | 承担稳定、财政、腐败和国内反对的二十年代价 |

## 15. 战后恢复外交

- 和平后等待7300日再启动长期恢复，不把停战即刻写成和解。
- 六个年度步骤依次为漂流民送还、对马调停、倭馆恢复、通信使、文化贸易、长期和平。
- 若任一步骤发生战争，链条延后365日，而不是丢失状态或错误完成。
- 最终设置 `jxp_iface_b_korea_reconciliation_complete`，重复 on_action/事件调用保持幂等。
- 此链已有脚本与静态测试，尚无20年实际运行证据。

## 16. 第二代治理流程

| 初始模式 | 20年核心取向 | 5/10/15年评议 | 第20年结局 |
| --- | --- | --- | --- |
| 军事奉行区 | 驻军、道路和纪律，治理成本高 | 军法、地方官与军费复议 | 正常化或自治安置 |
| 地方王统安堵 | 留用王统、旧法与地方官 | 官员、议席与威信复议 | 受保护王统或常制化 |
| 贡贸客户区 | 港务、贡贸与开放账册 | 收益、地方董事与商债复议 | 客户区常制或自治贸易 |
| 国司直辖州县 | 官僚直辖、税籍与州县 | 官员成本、腐败和地方抵抗复议 | 直辖常制或让渡自治 |

- 初始与最终 modifier 均有期限；没有免费核心、自动吞并或永久行政效率。
- 只遍历当前国家已拥有且带治理标记的省份，不做世界扫描。
- 转型、提前退出和终局都清理旧 event target、模式标志与互斥 modifier。

## 17. 琉球、对马、北方和台湾

| 地区 | 深度 | 设计结果 |
| --- | ---: | --- |
| 琉球 | 8阶段 | 琉球王统、朝贡礼仪、日本海防与当地拒绝权并存；协约为双边永久状态，可清理 |
| 对马 | 6阶段 | 宗氏、通事、倭馆和双重中介；不是把对马简化为普通港口 |
| 北方 | 6阶段 | 阿伊努首领、互市、渔场、冬季救济与强制劳役后果；合作协约永久，强制路线20年负担 |
| 台湾/闽海 | 6阶段 | 当地社会、福建商人、海禁、海盗与王朝更替；协约和军屯为不同成本路线 |

公共接口包括 `jxp_iface_b_ryukyu_compact_active`、`jxp_iface_b_tsushima_mediation_active`、`jxp_iface_b_northern_compact_active`、`jxp_iface_b_taiwan_compact_active`，均有本地化和集中清理。

## 18. 中国三终局

每条终局由一次选择扩展为五阶段长期计划，只有完成相应计划的 route-specific flag 后，原有 B100 终局才可完成。

| 终局 | 五阶段核心 | 最终制度 |
| --- | --- | --- |
| 奉受东亚天命 | 受命礼、贡道、官僚、文教、边疆常制 | 奉天承运之制；有 Mandate DLC 时依真实天命，无 DLC 时只给日轮朝仪 fallback |
| 海上礼仪圈 | 四海诸使、港口护航、通事书契、海东大会、海上仲裁 | 海东礼仪公议，不要求各邦承认同一天子 |
| 海邦新秩序 | 海禁批判、沿海保护、自由港、商贸联盟、常设海权 | 海岸自由港同盟，承担海军和外交敌意 |

三条计划互斥、分阶段付费，并有永久最终制度 modifier；选择另一终局会集中清理旧计划和中间状态。

## 19. 八纮一宇平衡

本轮保留并重新纳入测试的安全合同：

- 只能由实际日本天朝皇帝、完成任务专属解锁且拥有 Mandate 内容时使用。
- 目标只限8个预先钉死的东亚战略港，且必须已有普通宣称。
- `aggressive_expansion = 0.75`，战争分数费用保持 `1.0`；不是廉价广域吞并。
- 双方均禁止整国吞并；优先朝贡、释放国家、归还核心和贸易和约。
- 未整合异俗海岸带来治理容量、州维护和叛乱负担。
- 本轮没有扩大港口白名单，没有增加免费核心或宣称。

## 20. 玩家切换技术与启动资产

- 固定切换只对 NYA/HKK/NJF/OIA 提供，且目标必须仍是当前宗主的属国并达到殖民认同50。
- 首次切换只授予 `jxp_iface_colonial_self_rule` 和一次性100金启动资产；不修改科技组，不免费增加行政/外交/军事科技，也不复制宗主资产。
- 每个固定 tag 的一次性启动标志防止反复领取。
- 动态殖民国继续明确提示使用原版“释放殖民地并扮演”按钮；没有伪造不可靠的动态 `switch_tag`。
- TPF 通过后续形成路线进入，不在初始四国切换菜单中直接凭空生成。

## 21. 特殊 CB 和和平条款

| 战争 | 白名单与禁止项 |
| --- | --- |
| 殖民自治战争 | 不开放普通吞地；自治、贸易自主、恢复控制或独立均由专用结果收束 |
| 终结本土统治 | 只处理战败方已筛选的新大陆/大洋洲殖民属国；不再用世界 `every_province` 扫描 |
| 东归革命 | 解放海外、旧大陆成员国、两洋联邦、迁都东归均不免费吞并日本或授予全境核心 |
| 朝鲜渡海役 | `allowed_provinces = korea_region`，禁止整吞；正常战果和成本，不得跳过五阶段后勤 |
| 奉表问鼎 | 只争天命/释放/归还，不索取领土 |
| 海上礼仪 | 贸易、释放、归还为主；少数已有普通宣称港口仅获有限 AE 优惠，战争分数不降 |
| 破除旧命 | 不夺天命，不提供广域低价征服 |
| 八纮一宇 | 8港、已有宣称、75% AE、100%战争分数、禁止整吞 |

所有 B96—B101 与八纮一宇入口都接入 B118 AI 战争准备刹车；玩家不受 AI-only 判断误伤。

## 22. RNW 和 DLC fallback

- `map_setup_random` 下不加载依赖固定东亚/太平洋地理的 B115 正常路线任务。
- B118 提供 RNW 简化决议与事件，以殖民能力、港口和动态彼岸锚点替代固定美洲/岛屿 ID。
- `jxp_b_external_fallback_scenarios.json` 登记正常世界、RNW、无 Mandate、无殖民能力等场景，当前状态均为 `PENDING_RUNTIME`。
- Mandate 有/无 DLC 的三终局 fallback 保持区分：无 DLC 不伪称天朝皇帝或授予天命。
- 政府改革、殖民与任务相关 DLC 条件在静态 profile 中覆盖；尚未进行实际 DLC-off 冷启动。

## 23. 永久奖励表

| 表面 | 永久内容 | 平衡/退出条件 |
| --- | --- | --- |
| 母国遗产 | 一个无直接数值的身份标志 | 只记录一次；重复标志清理为唯一值 |
| 五国宪制 | 当前选中的一级政府改革 | 同阶只能选一项；TPF 解体可移除联邦体系 |
| 海外公司 | 公司 active modifier | 只持续到有序退出、破产解散或集中 cleanup；成立与续资均付费 |
| 地区协约 | 琉球、对马、北方、台湾的合作协约 | 双边状态；路线清理/关系终止可移除；强制路线仅20年 |
| 中国终局 | 三者之一的长期制度 modifier | 五阶段付费且互斥，选择/清理会移除其他终局 |
| 路线 capstone | 无永久奖励 | 全部为7300日 |
| 第二代治理 | 无永久行政效率/核心化奖励 | 初始20年，结局 modifier 仍为有限期 |
| 朝鲜结局 | 无免费核心或永久吞并奖励 | 15—20年代价/收益并存 |

新增表面没有永久 `discipline`、`administrative_efficiency`、`core_creation`、免费殖民者或全域宣称。

## 24. AI 观察数据

本轮没有获准启动 EU4，因此实际观察局样本为 `0`，不得把静态权重写成 AI 运行结论。

静态已覆盖：破产、贷款、负稳定、战争状态、厌战、兵力、人力、海军、运输船、相对实力、路线和目标强度；锁国殖民、TPF、东归和高风险公司均采用低基础概率或硬刹车。玩家入口通过 AI-only scripted trigger 分离。观察局仍需 lead 按正式运行矩阵补充成立率、破产率、战争胜率、公司存续率和联邦解体率。

## 25. 性能证据

- 新系统没有 `on_monthly_pulse` 世界扫描。
- 殖民国危机使用单国年度 pulse；公司、治理、朝鲜和解和中国长期计划使用有界 delayed event。
- 第二代治理只使用 `every_owned_province` 且要求本国治理标记。
- “终结本土统治”从世界省份扫描改为战败方筛选属国及其已拥有省份。
- 定向测试拒绝新递归 `every_country`/`every_province` 世界循环。
- 静态状态安全检查通过883个国家标志、9个省份标志、1535个 modifier 和4个已注册 disaster；本轮五国危机没有突破项目4—5个 disaster 的安全上限。
- 尚无真实帧时、月度 tick 或超长观察局性能数据。

## 26. 玩家切换和存档证据

静态迁移合同如下：

- `jxp_b_102_overseas_program_migrated` 与 `jxp_b_110_colonial_depth_migrated` 是事务完成标志，不是先写 marker 再尝试修复。
- A 的既有中央注册事件先调用 B startup migration，再消费 mission/idea/government 握手。
- B 自有 `jxp_b_110_colonial_migration.1` 等待任务锚点和所有 A 握手 postcondition 后，才提交迁移 marker。
- TPF 旧档已有替代宪法或已解体时，B 后置 finalizer 移除 A 兼容默认改革并重建政府机制。
- 旧准备状态通过稳定任务/标志重建；普通任务不直接重置三项长期变量。

尚缺：实际切换后的顾问、债务、舰队、军队、科技、AI 接管、保存/重载、旧档一日收敛和 UI 证据。此前旧档禁令下没有处理真实旧存档。

## 27. 与 Agent A 的接口

- 没有修改 estate、特权、议程、国内市场、国内公司核心、国内经济事件、奖励矩阵、唯一理念注册表或 Agent A 第1—3任务列。
- 用户明确授权的唯一 A 命名玩法文件改动是 `jxp_a_96_buddhist_missions.txt` 第4、5列 B115 追加。
- A 中央殖民注册文件保持原样；B 通过自己的后置迁移事件收束。
- 实际存在并可本地化的 A 公司提示 key 为 `jxp_iface_a_company_core_ready` 与 `jxp_iface_a_company_charter_active`，但没有稳定 writer/consumer 合同，B 不把它们当成立硬条件。
- `jxp_iface_a_market_stage_1..4`、`jxp_iface_a_public_credit_ready`、四种 founder legacy、`jxp_iface_a_domestic_capstone_complete`、`jxp_iface_a_company_state_route` 均未发现可依赖 writer，因此使用科技9、港口8、金库500和实际路线 fallback。
- B 输出的公共接口均幂等并有清理：母国遗产、殖民改革、对外 capstone、大陆 doctrine、海外公司、TPF 宪法、第二代治理、朝鲜和解、琉球/北方等地区协约。

## 28. 理念源片段

- 本轮没有直接修改 `common/ideas/00_country_ideas.txt`。
- 五国理念仍由唯一源片段 `tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt` 进入中央生成器。
- 当前源 SHA-256：`20322F0699B700F487A2D050E5E11DD490D9CD38B7CD57C9C31DACAF4C907AB7`。
- 源中包含且只包含 NYA/HKK/NJF/OIA/TPF 五组；NYA 定居增长键为 EU4 1.37.5 合法的 `global_colonial_growth = 10`，没有使用无效的 `global_settler_increase`。
- 唯一运行时理念注册表的生成与最终接入仍由 Agent A/lead 所有。

## 29. 已知风险

1. 全部成果仅为静态安全，未做 EU4 冷启动、UI、战争和平、AI观察或保存重载。
2. 五国“危机”因项目 disaster 总量安全合同实现为年度状态机，而非五个新注册 disaster；玩法循环完整，但缺少原版灾难进度条 UI。
3. RNW、无 DLC 与动态殖民国 fallback 尚未在引擎内确认。
4. 朝鲜20年和解链、治理20年评议和公司多轮续资尚未用长时间 observer 证明。
5. `JXP_AGENT_B_EXTERNAL_BASELINE_AUDIT.md` 尚未被 lead 写入共享总账历史报告索引；本报告提交后也需一并索引。
6. 地图联合门禁的 `runtime_oracle_pack.json` 因主 Mod 新内容发生预期漂移；该文件由 lead/Agent A 所有，本轮没有越权重生成。
7. A 的商议日本/公司国家路线接口缺少 writer，因此当前使用明确 fallback；未来 A 接口落地后可单独接入，不应伪造现状。
8. 平衡数值通过预算与静态禁项检查，但殖民国事件频率、公司续资压力、朝鲜远征成功率和终局耗时仍需试玩调校。
9. 活跃中文本地化通过生成检查，但无游戏内字体、换行和动态 tooltip 截图。

## 30. 每个提交 hash

| 顺序 | 提交 | 内容 |
| ---: | --- | --- |
| 1 | `4724d87765cd4e23d77a77ed0fa99f7c85a5051e` | 基线审计 |
| 2 | `74d869f1d660446882d4f700955b8ea4d0a6e885` | 五个殖民继承国、TPF、母国遗产、共享政治与一次性迁移 |
| 3 | `b51e3fb317c5cd31f0e8a9a7ecd2ae2d75c43afd` | 海外公司、地区外交、朝鲜、中国、治理、十二路线、AI/RNW/DLC fallback |
| 4 | 本文件所在提交 | 最终32项交接报告；精确 hash 由最终消息给出 |

前置相关提交：`895e798b39555f2421393371a9a4be6b3e2e15cc` 完成美洲日式地名中文显示；不属于本轮玩法重构，但应在合并链中保留。

## 31. 推荐合并顺序

1. 从包含 `895e798` 的当前集成基线开始。
2. 合并 `4724d87`，保留审计证据。
3. 合并 `74d869f`，先落五国身份、任务、改革、危机和迁移。
4. 合并 `b51e3fb`，再落公司、治理、战争、地区与路线模块。
5. 合并本报告提交。
6. 由 lead 在同一控制面提交中：索引两份 Agent B 报告、更新共享总账、重生成并审查 map runtime oracle。
7. 静态控制面干净后，按正式矩阵运行 fresh/RNW/DLC-off/player-switch/save-reload/AI observer；每个失败单独重开缺陷切片。

不要在 B 分支直接手改共享总账或 oracle，也不要把 `b51e3fb` 后的文档 HEAD误当成已经运行确认的 release payload。

## 32. `JXP_AGENT_B_EXTERNAL_HANDOFF.md` 与验证收据

本文件即要求的 `japan_expanded_v2/dev_logs/JXP_AGENT_B_EXTERNAL_HANDOFF.md`。

提交前验证记录：

- 105项定向测试：`OK`。
- 主 Mod 通用严格解析：`OK: No issues found`。
- 主 JXP 静态门禁：28/29；471/471 gameplay scripts、898任务、137 series、196 profiles、883国家标志、1535 modifiers、4 disasters、98 active localisation files均通过。唯一失败为基线报告尚未写入共享总账索引。
- 地图门禁：map/history/content/main compatibility/assets 均为0错误0警告；任务系列重叠检查与地图 Mod 通用严格解析均通过。
- 地图门禁停止项：`runtime_oracle_pack.json` 漂移，需 lead 重生成；没有修改 oracle。
- `git diff --check`：通过。
- debug cleanup registry：在最终新增迁移事件前已通过 current check；后续只新增不引入新状态的 B 迁移事件。一次重复全量扫描因长时间无输出按任务边界主动终止，不把它虚报为第二次通过。
- EU4/Launcher：未启动。
- 运行时状态：所有 player-switch、save/reload、RNW、DLC-off、AI observer、UI 与长周期循环均为 `PENDING_RUNTIME`。
