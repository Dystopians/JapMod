# JXP 统一状态任务槽位与 A/B 所有权合同

- 日期：2026-07-17
- 对应总账：`JXP-037`
- 证据等级：`STATIC_PASS; NOT_RUNTIME_PROVEN`
- 引擎规则：EU4 1.37.5 RSMTS；每个有效 profile、每个 slot 最多一个非 generic series

## 1. 最终裁定

EU4 只有五个可见任务槽。Agent A 拥有国内 slots 1–3，Agent B 的海外／大陆内容冻结在 slots 4–5。设计稿中的五条资本主题不能各占一个 UI slot，否则必然覆盖 B 的两列。因此最终采用“共享两列 + 路线一列”的复合结构：

1. 35 个共享资本任务只定义一次，slot 1 为 18 项、slot 2 为 17 项；五条逻辑主题仍由前置、标题、奖励和权威 builder 元数据保留。
2. 十二种既有统一状态各有一条 slot 3 专属 series、8 项任务，共 96 项。
3. “商议日本”不复用共享列，在 slots 1–3 各有 7 项，共 21 项。
4. Agent A 全局唯一任务定义总数为 `35 + 12×8 + 21 = 152`；标准 profile 在游戏中可见 43 项 A 任务，商议 profile 可见 21 项 A 任务。
5. slots 4–5 由冻结 manifest 按整文件或顶层 series 字节哈希保护；A builder 不改写 B 的任务、effect、position 或 localisation。
6. 不采用两阶段换章，也不生成 12 份重复的共享资本任务；这避免任务 ID 冲突、同槽竞争和旧进度分叉。

权威源：

- `tools/jxp_a_socioeconomic_builder/build_missions_routes.py`
- `tools/jxp_a_socioeconomic_builder/frozen_mission_surface.json`
- `tools/jxp_a_socioeconomic_builder/socioeconomic_plan.json`
- 生成物 `missions/zzz_jxp_a_105_socioeconomic_missions.txt`

## 2. 十三个 profile

| Profile | 精确身份 | A slots | B slots |
| --- | --- | --- | --- |
| 未定 JAP | `JAP` 且无本土路线、非佛教、非殖民继承国 | 共享 1–2 + 未定 3 | 冻结 4–5 |
| 锁国 JAP | `JAP + jxp_path_sakoku` | 共享 1–2 + 锁国 3 | 冻结 4–5 |
| 开国 JAP | `JAP + jxp_path_open_trade` | 共享 1–2 + 开国 3 | 冻结 4–5 |
| 佛教 JAP | canonical Buddhist exact trigger | 共享 1–2 + 佛教 3 | 佛教冻结 4–5 |
| KJP | canonical Kirishitan final trigger | 共享 1–2 + KJP 3 | 冻结 4–5 |
| CJP | canonical Confucian final trigger | 共享 1–2 + CJP 3 | 冻结 4–5 |
| EJP | canonical Imperial final trigger | 共享 1–2 + EJP 3 | 冻结 4–5 |
| RFJ | canonical Reformed final trigger | 共享 1–2 + RFJ 3 | 冻结 4–5 |
| SJP | canonical Kaikyo final trigger | 共享 1–2 + SJP 3 | 冻结 4–5 |
| IJP | canonical Ikko final trigger | 共享 1–2 + IJP 3 | 冻结 4–5 |
| WAK | canonical Wokou final trigger | 共享 1–2 + WAK 3 | 冻结 4–5 |
| TOY | `tag = TOY`，非殖民继承国 | 共享 1–2 + 丰臣 3 | 冻结 4–5 |
| 商议 JAP | `JAP + jxp_path_commercial_council` | 商议专属 1–3 | 沿用冻结的神道 4 与未定 horizon 5 |

所有 A series 都有 `potential_on_load = { always = yes }`，实际 `potential` 使用 exact profile trigger。五个殖民继承 tag `NYA/HKK/NJF/OIA/TPF` 被显式排除。

商议路线是一个刻意的兼容例外：旧 `jxp_has_any_route_trigger` 仍属于冻结 B slot 5 合同，不能加入新 flag。故商议 profile 由 A 的 exact trigger、所有旧本土形成入口的显式负条件以及 `jxp_final_state_uncommitted_trigger` 的负条件共同隔离；它只借用 B 已有的神道 slot 4 和未定 horizon slot 5，不让自己落回未定国内模型。

## 3. 任务布局与依赖

| 实际 slot | 定义数 | 作用 |
| ---: | ---: | --- |
| 1 | 18 共享 + 7 商议 | 金银、货币、信用及商议国家结构 |
| 2 | 17 共享 + 7 商议 | 城市、道路、米市、债务与阶层妥协 |
| 3 | 12×8 路线 + 7 商议 | 各国内路线、工场、公司与终局 |

标准路线 slot 3 使用 8 个从早期延伸到晚期的节点；每条路线具有不同的触发器、主要／次要阶层、经济治理模型、四次选择事件、危机代价和唯一永久国内 capstone。普通节点只授予一次性资源、有限期修正、制度、互动、公司或省级发展，不新增第二个永久全国终局。

跨列可见依赖只使用引擎安全的相邻关系；远距离依赖用 `mission_completed` 或 capability flag。60 个被 B slots 4–5 引用的旧 mission ID 被保留在新树中，因此不需要建立会重新参与选树的 duplicate tombstone series。旧 A slots 1–3 series 本体被权威 builder 删除；B slot 4–5 顶层块保持字节不变。

## 4. 冻结面与指纹

`frozen_mission_surface.json` schema 2 当前保护：

- 12 个纯 B／B-reserved mission 文件的整文件 SHA-256；
- 6 个 A/B 混合文件中的 18 个 slots 4–5 顶层 series SHA-256。

运行时指纹由 `tools/jxp_validation/create_mission_runtime_fingerprint_v0242.py` 生成到 `common/scripted_triggers/jxp_60_mission_runtime_triggers.txt`。统一指纹要求：

- A 的 `jxp_a_105_mission_profile_fingerprint_valid_trigger` 成立；
- 每个 profile 精确命中自己的 A slot 3／商议 slots 1–3 锚；
- slots 4–5 命中该 profile 的冻结锚；
- sibling A 锚、generic fallback 和殖民继承国锚为负；
- 佛教与商议 profile 不再漏检。

五殖民继承国继续使用自己的 B profile class，不被国内密度门槛误判。

## 5. 迁移与刷新

中央迁移事务顺序固定为：

1. 首次捕获旧 mission completion 深度并设置 snapshot；
2. 清理 stale pending，但在后置条件成功前不清 snapshot、不提交 schema marker；
3. 重建 founder、统一方法、estate、市场、公司和 exact profile；
4. 调用 canonical `jxp_refresh_route_missions_effect`，完成立即 swap 与次日 retry；
5. 验证五槽指纹、founder／统一方法／profile 一致性；
6. 只回放等价解锁深度，不重复任务的一次性奖励；
7. 成功后才清 snapshot 并写入 `jxp_a_105_mission_schema_v1` 与中央迁移 marker。

中途失败时保留 snapshot，下一次 startup／迁移入口可幂等重试。路线、宗教、政府或 tag 变化先完成身份事务，再刷新任务。离开本土身份时调用完整清理 effect；商议共和国只在正常退出国内路线时恢复君主制，殖民继承清理不会强改 B 的共和国政府。

## 6. 静态与运行时边界

静态候选必须证明：152 个 ID 全局唯一、共享 18/17、十二路线各 8、商议 7/7/7、13 个 exact profile 无同槽竞争、60 个 B 前置锚仍可达、B 字节无漂移、任务 title/desc/reward tooltip 汉化完整、迁移后置提交、清理覆盖所有持久状态、无 monthly/world scan。

仍需独立 EU4 启动许可后才能证明：任务 UI 实际五列、次日刷新、旧进度回放、保存重载、DLC 开关、主 Mod 单独／主+地图组合以及 B 列运行时不丢失。在取得这些证据前，本合同只记录静态实现，不声明可玩或发布完成。
