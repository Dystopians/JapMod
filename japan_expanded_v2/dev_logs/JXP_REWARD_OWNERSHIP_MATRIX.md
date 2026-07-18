# JXP 奖励所有权与去重矩阵

- 日期：2026-07-17
- 对应总账：`JXP-037`
- 状态：`STATIC_PASS; NOT_RUNTIME_PROVEN`
- 范围：日本本土理念、任务、改革、estate、市场、公司和国内终局；Agent B 海外成果只登记边界，不重平衡

本矩阵为“同一种能力只能有一个主要所有者”的权威合同。规则型状态、兼容 marker 和任务指纹不因没有数值而被删除；普通任务不再用重复永久小数值模拟制度。

## 1. 总体归属规则

| 能力 | 主要所有者 | 允许的次级表达 | 禁止重复 |
| --- | --- | --- | --- |
| 家族长期基础能力 | 国家理念 | 创始家任务的解锁/一次资源/有限期推进 | 同签名永久家系 modifier |
| 大名成长与领国建设 | 大名任务 | 省级建设、事件选择、10–20 年修正 | 统一后再永久复制同一能力 |
| 统一后的唯一家门制度 | 创始家改革 | 一次迁移与显示 flag | founder council/diet/memory 再叠同类永久值 |
| 社会集团权利 | Estate privilege | loyalty/influence、agenda、危机 | 路线改革再复制相同 estate 数值 |
| 国体规则与候选 | 路线/权力结构改革 | 任务负责解锁与清理 | 普通任务永久复制国体 modifier |
| 商业化阶段 | 35 项资本任务 + 四阶段 flags | 有限期事件、建筑/省级状态 | 新建资本主义 0–100 条或永久贸易值堆叠 |
| 公司收益与风险 | 公司章程、董事和年度事件 | 公司任务解锁、有限期审计结果 | 普通任务直接永久给“公司收益” |
| 海外具体业务 | Agent B | A 提供能力/阶段接口 | A 复制殖民、独立、朝鲜/大陆奖励 |
| 最终国家工程 | 每路线一个国内 capstone + B 一个对外 capstone | 唯一永久全国结果 | 同路线多个永久经济终局 |

处理重复时按以下顺序：保留规则解锁；删除重复小数值；永久全国加成降为 10/20 年；全国值改省级或条件值；任务改为解锁互动/公司/agenda/reform；只有唯一最终国家工程可保留新的永久全国奖励。

## 2. 国家理念登记

唯一运行时注册表是 `common/ideas/00_country_ideas.txt`；权威源位于 `tools/jxp_validation/idea_sources/`。本轮不得创建第二个 runtime ideas 文件。下列 81 组均保持严格 `start + 7 ideas + bonus`，其长期家族/国家能力优先于任务与改革中的重复小数值。

| 权威源 | 理念组 | 主要所有权 |
| --- | --- | --- |
| `00_basic_z1_jxp_15_daimyo_ideas.txt` | ODA, TKG, TKD, UES, HJO, MRI, SMZ, OTM, DTE, ASK, CSK, OUC, IMG, SOO | 主要大名家风长期基线 |
| `00_basic_z2_jxp_17_minor_daimyo_ideas.txt` | AMA, HSK, SHN, OGS, KTB, AKT, CBA, ISK, ITO, KNO, TTI, RFR | 中型大名家风长期基线 |
| `00_basic_z3_jxp_18_remaining_daimyo_ideas.txt` | ASA, HTK, IKE, MAE, SBA, YMN, AKM, KKC, STK, TKI, UTN | 其余主 Mod 大名家风长期基线 |
| `jxp_map_daimyo_ideas.txt` | fallback `jxp_map_new_daimyo_ideas`；ANK, ARI, ASN, AZI, DHO, HCS, HNG, HNM, KMP, KRD, KYO, MKM, MOG, MTS, MTU, MYO, NBS, NHT, OSK, RKK, RZJ, SGR, SMA, STM, STO, TGR, TGS, UKT, WKT, YMC | 地图 30 家长期基线；主注册表集中生成 |
| `jxp_70_toyotomi_ideas.txt` | TOY | 检地、刀狩、朝廷名分、奉行/大老容量、朱印贸易 |
| `jxp_route_ideas.txt` | KJP, CJP, EJP, RFJ, SJP, IJP, WAK | 七个终局国体长期身份 |
| `jxp_b_colonial_state_ideas.txt` | NYA, HKK, NJF, OIA, TPF | Agent B 殖民继承国；A 只维持唯一注册表生成，不重平衡 |

原版 `JAP_ideas` 继续由 pinned vanilla registry 拥有；未定、锁国、开国 JAP 的新任务不能用永久纪律/贸易/生产等数值覆盖它。

## 3. 大名任务与创始家层

### 3.1 大名任务所有权

| 文件/系列 | 主要能力 | 本轮规则 |
| --- | --- | --- |
| `jxp_04_daimyo_missions.txt` | 领国法、道路、市场、工匠、接触 | 作为成长和阶段推断；奖励以限时/一次资源为主 |
| `jxp_21_daimyo_house_missions.txt` | 五类家系路线与市场/寺社/边疆身份 | 只产生一个 founder legacy 分类接口 |
| `jxp_81_major_daimyo_identity_missions.txt` | 主要大名独特成长 | 不再向统一后复制永久家风数值 |
| `jxp_a_91_oda_img_depth_missions.txt`、`jxp_a_94_daimyo_depth_missions.txt` | 67 家 Tier-A/深度内容 | 既有任务 ID 保留；经济永久奖励列为审查输入 |
| 地图大名 slot 3 | 30 家地图身份 | 不由国内终局生成器改写 |

### 3.2 39 项创始家改革

所有创始家改革仍是统一后“唯一家门制度遗产”的主要所有者：

`AKM_harima_castle_roads`、`AKT_ezochi_brokers`、`AMA_gassan_toda_law`、`ASA_ichijodani_council`、`ASK_muromachi_office`、`CBA_katori_muster`、`CSK_tosa_ichiryo_gusoku`、`DTE_oshu_cavalry_envoys`、`generic_renovated_japan`、`HJO_odawara_cadasters`、`HSK_sakai_kanrei_compact`、`HTK_wakae_retainer_law`、`IKE_himeji_stewards`、`IMG_tokaido_lawbooks`、`ISK_tango_port_wardens`、`ITO_hyuga_fort_network`、`KKC_aso_rite_council`、`KNO_setouchi_pilot_law`、`KTB_ise_court_law`、`MAE_kaga_million_koku`、`MRI_setouchi_admiralty`、`ODA_azuchi_statutes`、`OGS_suwa_horse_archery`、`OTM_funai_arsenal`、`OUC_yamaguchi_court`、`RFR_mutsu_nine_gates`、`SBA_buei_offices`、`SHN_dazaifu_brokerage`、`SMZ_satsuma_gunnery`、`SOO_tsushima_wakan`、`STK_hitachi_warrior_rolls`、`TKD_koshu_military_law`、`TKG_mikawa_fudai_code`、`TKI_mino_river_offices`、`toyotomi_five_regents`、`TTI_yamato_temple_compact`、`UES_kanto_justice`、`UTN_nikko_barrier_guard`、`YMN_roku_bun_ichi_domain`。

对应 `jxp_26/34/35/38/39/43/52` council、diet、pulse、idea-legacy 与 memory 事件只保留选择、风味、短期过渡和接口，不再与上述改革叠同签名永久全国值。

经济遗产另按 67 个大名 origin 全覆盖地归入五类：城市市场、海商港口、官僚检地、共同体寺社、边疆资源。37 个主 Mod origin 直接分类；30 个地图 origin 只通过既有 `jxp_map_origin_*` 语义旗被主 Mod 消费，不硬引用地图 tag。每国 reconcile 后恰一类，外交型家系明确归官僚类，未知输入不以“商业”作默认兜底。

## 4. 十一阶与路线改革归属

当前原版君主制十一层分别承载：基础权力结构、家臣/贵族、官僚、宗教、军事、评议、行政成长、经济、正统、宪制、权力分立。日本候选集中在 `jxp_84_japanese_government_track.txt` 与 tier 02–11 vanilla override 生成物。

| 层/主题 | 当前日本候选族 | 主要所有权 |
| --- | --- | --- |
| Tier 1 权力结构 | daimyo/shogunate/TOY、十终局、佛教、B 殖民 | 国体身份；新商议日本只在此增一互斥基础结构 |
| Tier 2 家臣 | kokujin oaths、fudai/direct investiture、相关 founder | 武家权利与直属化规则 |
| Tier 3 官僚 | gundai/daikan、branch castles、路线行政 | 地方治理与行政容量规则 |
| Tier 4 宗教 | religious arbitration、temple settlement、路线宗教 | 宗门自治/国家任命规则 |
| Tier 5 军事 | ashigaru、hatamoto、artillery、funade、军事 founder | 军役与军制；公司任务不得复制 |
| Tier 6 评议 | lordly arbitration、elders、domain assembly | 公议/议会结构 |
| Tier 7 行政成长 | yuhitsu、fudai magistracy、public authority、founder | 奉行、审计与容量 |
| Tier 8 经济 | guild charters、red seals、rakuichi、coinage、new fields、route economy | 经济规则/制度解锁；资本任务不永久复制数值 |
| Tier 9 正统 | arms/general peace/service compact/common security | 统一方式与社会契约 |
| Tier 10 宪制 | 十终局政治改革、佛教/ODA、fallback | 每状态国内政治 capstone |
| Tier 11 权力分立 | inspectors、collegial offices、direct appeal | 最终中央制衡 |

27 项可见路线改革及其后续 `jxp_14/18/24/27/32/37/40/44/46/51/53` 定义族继续拥有“国体规则”，而不是通用经济小数值。Parked/dormant 定义不计入可玩奖励，也不得因本轮生成器意外重新注册。

## 5. 终局权力结构与政治 capstone

| 状态 | 权力结构/基础改革所有者 | 既有政治 capstone 所有者 | 新国内经济 capstone |
| --- | --- | --- | --- |
| 未定 JAP / 诸州公议 | `jxp_uncommitted_realm_council_reform` | final uncommitted consensus | 天下公议财政 |
| 锁国 JAP | `jxp_sakoku_bakuhan_council_reform` | final sakoku constitution | 锁钥通商国宪 |
| 开国 JAP | `jxp_open_maritime_cabinet_reform` | final open cabinet | 海外资本国家（仅国内制度；海外成果归 B） |
| KJP | `jxp_kirishitan_estates_general_reform` | final Kirishitan estates | 王权与教权财用协约 |
| CJP | `jxp_confucian_censorate_reform` | final Confucian censorate | 经世监察财政 |
| EJP | `jxp_imperial_daijokan_reform` | final imperial daijokan | 太政官国家财政 |
| RFJ | `jxp_reformed_japan_reform` | final Reformed synod | 盟约商业宪制 |
| SJP | `jxp_kaikyo_japan_reform` | final Kaikyo diwan | 港务迪万财用 |
| IJP | `jxp_ikko_commonwealth_reform` | final Ikko somon | 同行经济宪章 |
| WAK | `jxp_wokou_admiralty_reform` | final Wokou admiralty | 海军府财用 |
| TOY | `jxp_toyotomi_kampaku_taiko_reform` | Taiko testament | 太阁国家财用 |
| 佛教 JAP | `jxp_a_96_buddhist_*` settlement | Buddhist mutual law | 王法佛法财用 |
| 商议 JAP | 中性 `jxp_a_105_commercial_council_state_reform`，随后互斥替换为 `jxp_a_105_commercial_shogunate_reform` / `jxp_a_105_commercial_merchant_council_reform` / `jxp_a_105_commercial_company_empire_reform` | 三分支之一 | 天下会社国 |

每状态新增的国内 capstone 只允许一个永久全国 modifier；其他 7 个路线国内任务只解锁制度、公司、agenda/interaction、一次资源、有限期修正或省级建设。

## 6. Estate、市场与公司计划所有权

| 系统 | 主所有者 | 持久状态 | 清理/迁移 |
| --- | --- | --- | --- |
| 武家奉公众 | `estate_nobles` + `jxp_a_*` privileges/agendas | 引擎 estate loyalty/influence/Crownland | route reconcile；不镜像变量 |
| 寺社宗门 | `estate_church` + `jxp_a_*` privileges/agendas | 同上 | 改宗/路线 reconcile |
| 町众豪商 | `estate_burghers` + `jxp_a_*` privileges/agendas | 同上 | 公司/路线 reconcile |
| 百姓惣村 | `jxp_estate_village_communes` | 同上 | tag/政府/殖民退出时 disable/cleanup |
| 商市成网 | `jxp_a_market_stage_1` | 单调 flag + 一次奖励 flag | startup 推断；普通路线不降级 |
| 信用成制 | `stage_2` | 同上 | bankruptcy 只触发危机，不普通降级 |
| 工场成业 | `stage_3` | 同上 | 同上 |
| 会社成国 | `stage_4` | 同上 | 特殊崩溃/革命才可受控降级 |
| 五家国内公司 | company core + charter/director flags | 离散 active/renewal/audit/distress flags | 到期、破产、国有化、拆分、tag/route cleanup |
| 五家海外公司 | Agent B | A 只设 requested/capability interfaces | B 不存在时无害清除请求 |

## 7. 家系议程、路线—家系事件与压力循环

| 现有层 | 当前角色 | 本轮主要所有者调整 |
| --- | --- | --- |
| `jxp_25_daimyo_house_agenda_events` | 旧式家系议题事件 | 保留家风选择；真正社会诉求转入 estate agendas |
| `jxp_29/30/31/33` route-house | 路线与家系共鸣/完成 | 保留叙事与三属性选择；不新增通用永久经济值 |
| `jxp_71/75` route parity | 路线低频纠偏 | 只提供有限期取舍 |
| WAK/IJP/太平洋 pressure loops | 路线压力与投资 | 维持既有 owner；公司 core 只读取，不复制其海外收益 |
| 新 estate crises | 四社会集团冲突 | 灾难/事件链 owner；结局改变 privilege/reform/董事，不常驻叠值 |

## 8. 永久省份 modifier 归属

当前共有 43 次永久省份授予、30 个唯一 ID。以下国内实体可继续由省份拥有：

- 港市/商馆：`jxp_nagasaki_factory`、`jxp_malay_factory` 等明确地点；
- 宗教/教育中心：`jxp_kyoto_renewed`、`jxp_ise_pilgrim_roads`、各 reform center；
- IJP/防御实体：`jxp_ikko_terauchi_town`、`jxp_ishiyama_fortress`；
- 宗教港区：`jxp_muslim_port_quarter`、`jxp_hirado_congregation`。

新矿山、藏屋敷、工场、公司总部优先使用唯一省份 modifier 或建筑条件，且提供迁都、失去省份、公司破产与 debug 清理。B 的 `jxp_b_92_*_port` 五类永久省份状态完全只读。

## 9. 首批确定去重项

| 重复/叠加 | 现状 | 处理合同 |
| --- | --- | --- |
| TOY 五大老改革 | founder reform 与关白/太阁 tier-one 原同为 tax `+5%`、capacity `+10%` | 已实施：tier-one 保留丰臣国体；founder reform 改为武家忠诚、顾问池与 `jxp_toyotomi_regents_council` 属性，由武家评定／谱代奉行特权消费，不再复制税收与容量 |
| 城下市场 | `jxp_castle_town_markets` 与 `jxp_24_daimyo_market_roads` 同为 trade/prod `+5%` | 旧大名任务成为 stage-1 推断与市场互动解锁；不再永久叠值 |
| IJP/寺院债务宽免 | `jxp_24_temple_debt_relief` 与 `jxp_24_ikko_debt_remission` 同签名 | 普通寺院项改为 agenda/有限期；IJP 国内模块拥有路线式德政结局 |
| TOY/IMG 市场签名 | `jxp_70_toyotomi_market_charters`、`osaka_granaries`、`jxp_a_img_regular_markets` 同签名 | IMG 保留大名成长；TOY 两任务分别解锁藏屋敷与公司/粮仓，不再两份永久相同值 |
| 三都账册 | 冻结 B-reserved 任务仍会授予 `jxp_three_capitals_ledgers` 永久 tax/prod `+10%` | 已实施中央兼容转换：任务完成后一次性撤销旧永久值，改授 20 年财政整理；不改冻结任务字节；永久公共信用归资本 capstone |
| 佛教寺院信用 | 冻结 B-reserved 任务仍会授予 `jxp_a_buddhist_temple_credit` 永久 interest `-0.5` + trade `+5%` | 已实施中央兼容转换：一次性改授 20 年过渡；寺院信用由 privilege／董事路线表达，佛教 capstone 保留唯一长期制度 |
| ODA 市场叠层 | ODA idea + Azuchi founder + 市场任务 | 理念拥有长期商业能力，founder 拥有国制，任务只解锁乐市互动/阶段 |
| TOY 市场叠层 | TOY idea + 三任务 + 两相同 reform | 理念拥有长期能力，tier-one 拥有丰臣身份，任务解锁藏入地/奉行/朱印公司 |
| IJP/WAK 多层永久经济值 | 理念、任务、路线改革、宪制并存 | 理念/改革分工；普通国内任务改解锁或限时；各保留一个国内 capstone |
| 重复授予调用 | `jxp_70_toyotomi_taiko_testament`、`jxp_35_legacy_court_domain_law` 各有两处 | 先证明分支互斥；统一走 idempotent grant effect，已持有时不重复 |

其余 392 个永久 country modifier 不在本轮机械删除。新生成内容实施“普通资本任务不得 `duration=-1`”和“每 profile 恰一国内经济 capstone”硬门禁；商业灾难的六个永久结局彼此互斥，属于宪制结局而非可叠加任务奖励。遗留层按后续独立回归切片处理。

## 10. Agent B 边界

Agent B 拥有 `jxp_03_overseas_missions.txt`、所有 `jxp_b_*` 殖民/大陆 missions、events、decisions、effects、reforms、CB/wargoal/subject、本地化和 `jxp_b_colonial_state_ideas.txt` 的玩法数值。A 只提供幂等 flags：estate ready、market stages、company core/charter、domestic capstone、四类 founder legacy、public credit、company-state route。任何 B 文件未消费的接口都必须在 A 单独运行时无副作用。
