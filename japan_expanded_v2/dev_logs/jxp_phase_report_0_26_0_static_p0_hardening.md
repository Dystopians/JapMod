# 日轮诸道 0.26.0：地图尺度、理念 UI 与八纮一宇静态收口

日期：2026-07-10
主 Mod：`0.26.0`
伴随地图：`0.1.1-alpha`
证据等级：`STATIC_PASS; PENDING_RUNTIME`

## JXP-003：19 个地图尺度敏感门槛

所有活动 `num_of_cities = 25/30` 已按任务的历史目的改为具名语义 trigger，不按 `88/48`
机械放大，也不引用伴随 Mod 才存在的 tag、area、mission 或 `4942-4981` 省份。

| 原内容 | 新语义 |
| --- | --- |
| 破武家之国 | 天下秩序 50 + 宗教统一 80% |
| 神社城下町 | 5 个同时具备寺庙与市场网络的日本省份 |
| 礼制户口普查 | 8 个地方行政办事处 |
| 洁食仓廪法 | 6 个生产/会计网络省份 |
| 定天下国是 | 250 发展、肥前/北方门户与四国控制，外层仍要求两京 |
| 一统诸岛 | 250 发展、西方/北方门户与四国控制，外层仍要求京都/武藏 |
| 承继新国 | 天下秩序 75、250 发展与武藏控制 |
| 更始日本 | 天下秩序 75 + 日本地区全部直辖/非主权属国控制 |
| 驿站登记 | 8 个地方行政办事处 |
| 边疆家法入地方 | 4 个地方行政办事处 |
| 大坂米账 | 6 个生产/会计网络省份，继续以 `1021` 为唯一兼容锚点 |
| 城下市场 | 8 个市场网络省份 |
| 召集天下评定 | 天下秩序 50 + 朝廷承认 30 |
| 遍听诸藩奏议 | 6 个地方行政办事处 |
| 边港登记 | 冲绳、肥前、渡岛或对马中的至少一个战略边港 |
| 同朋共同体 | 天下秩序 75 + 宗教统一 90% |
| 纂修神典 | 京都、伊势 + 6 个寺庙网络省份 |
| 国司巡察 | 京都、武藏、肥前、渡岛、伊势与四国巡察圈 |
| 奉币使诸社 | 京都、伊势 + 6 个寺庙网络省份 |

`map_scale.py` 现在 hard fail 任何重新出现的 25/30 城市门槛、伴随专属引用、缺失/重复的
语义 trigger、20 个 trigger body 的结构缩水，或 19 个调用点的数量/文件/正向
`trigger`/`allow` 归属漂移；
mutation 测试证明把任一合同退化为 `always = yes` 会使发布门禁失败。

## JXP-020：国家理念结构硬上限

- 主 Mod `common/ideas` 的 44 个可激活理念组已全量纳入发布门禁，不再只检查 7 个终局组。
- 缺失/重复 `start`、`bonus`、`trigger`、`free`，`free != yes`，理念数不等于 7，
  异常顶层成员、重复理念或重复理念组均会 hard fail。
- 伴随地图的 1 个理念组使用生成器唯一 7-key 清单，并在地图历史门禁中重新验证。
- 当前 45/45 个项目理念组均符合 `start + 7 ideas + bonus`；本轮无需改理念数值。
- UI 截图仍属 `PENDING_RUNTIME`，因此 `JXP-020` 保持 `IN_PROGRESS`。

## JXP-023：“八纮一宇”改革可见性

- `potential` 只保留稳定的日本政体身份；DLC、天朝皇帝和任务/解锁 flag 均由 `trigger` 动态检查。
- 解锁效果会调用唯一 `jxp_reconcile_hakko_ichiu_reform_visibility_effect`，补写旧档 flag，
  并对合格的日本天朝皇帝调用 `regenerate_government_mechanics = yes`。
- `on_startup`、`on_government_change` 与一日 catch-up 共同覆盖“先完成任务、后取得天命”、
  已有解锁 flag 但候选列表未刷新的旧档，以及已是天朝时完成任务三种顺序。
- 改革 `trigger` 再次检查日本政体，防止外国误选；无 Mandate of Heaven DLC 时保留
  `jxp_mandate_claim_fallback`、天朝外交和日轮朝廷承认奖励。
- validator 现在检查稳定/dynamic gate 分层、任务奖励的 DLC guard、缓存刷新、启动/政体变化迁移、
  无 DLC fallback 和动态 tooltip 安全。
- 实际天朝 UI 截图与 fresh `error.log` 仍属 `PENDING_RUNTIME`，因此 `JXP-023` 保持 `IN_PROGRESS`。

## 静态证据

- 主门禁：`13/13`；Clausewitz `180/180`；回归测试 `67/67`。
- 理念：主 Mod `44/44`；伴随地图 `1/1`。
- 地图尺度：`19/19` 语义替换、`20/20` 固定 body 合同；活动 `num_of_cities = 25/30` 为 `0`。
- 联合门禁：map/history/content/main compatibility/assets/mission overlap/严格通用检查全部
  `0 errors / 0 warnings`；30 tags × 4 DLC profiles 闭合；联合 inventory 为
  `466 events / 215 decisions / 252 scripted callables / 832 modifiers`。
- 联合命令使用隔离的 Python 3.13 环境，并由 `requirements-validation.txt` 与脚本预检声明、
  校验 NumPy/Pillow 兼容范围；缺少合格版本或依赖时会在正式门禁前给出可执行的安装提示。
- 联合门禁调用仓库内 pinned `skills/eu4-modding/scripts`，避免已安装 skill 漂移改变当前提交的证据。
- 未启动 EU4 或启动器，不将上述结果表述为游戏内验收。

## 迁移与兼容边界

- 门槛语义化不改 mission ID、series、坐标或完成记录，无需任务树迁移。
- 理念内容未变，旧档继续由现有 canonical `swap_free_idea_group` 路径处理。
- 八纮一宇新增 `jxp_hakko_visibility_reconciled_v0260` 一次性状态；调试清理同步清除。
- 88 省伴随地图仍必须与主 Mod 同时启用、仅限新战役，并与其他日本地图 overhaul 不兼容。
