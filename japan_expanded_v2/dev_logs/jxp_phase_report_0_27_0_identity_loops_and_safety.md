# 日轮诸道 0.27.0：身份、路线循环与状态安全收口

日期：2026-07-10
主 Mod：`0.27.0`
伴随地图：`0.1.2-alpha`
固定参考：EU4 `1.37.5.0 Inca (491d)`
证据：`STATIC_PASS; PENDING_RUNTIME`

本切片在独立 Git checkout 中完成；Steam 游戏根目录始终只读，未启动 EU4、启动器或 observer。本文是历史阶段证据，当前状态仍以 `JXP_SHARED_DEVELOPMENT_LEDGER.md` 为准。

## 工作区与发布边界

- 开发仓库保持在 Steam 安装目录之外；游戏目录中没有 Git/JapMod 开发副本、junction 或 symlink。
- 两份 portable `.mod` 仍只使用 `path="mod/..."`，没有提交用户名或主机绝对路径。
- 主/地图版本分别提升到 `0.27.0` / `0.1.2-alpha`；地图历史、理念、任务和旧档迁移均随版本更新。
- 主、地图与联合静态可视化均由仓库生成器重建；联合视图收录 46 个任务组、308 个任务、269 个决议、490 个事件，缺失本地化为 0。

## 丰臣身份与历史链（JXP-018）

- 新增独立 `TOY` tag、128×128 RGB 旗帜及确定性 Pillow 源、中文君主/将领池、国家理念、六节点织田—丰臣身份任务、决议、事件、modifier 与五大老改革。
- 1586.1.1 作为丰臣姓名与政权身份节点；canonical transition 在变 tag 前记录 ODA lineage，随后同步理念、任务、政府 mechanics 与旧档迁移 flag。
- 主历史生成器以原版 1.37.5 为只读输入，确定性生成 18 个省份覆盖、24 个丰臣属国区间与 `Japanese_alliances.txt`：普通领地在 1600.10.21 转入德川，Settsu 1021 保留至 1615.6.4。
- 伴随地图 source/生成历史含 33 个丰臣所有权/核心区间、70 个属国区间；137,382 个可选日期、299 个所有权区间均连续。
- 历史节点参考：大阪市关于 1583 大坂城营建、国立剧场资料关于 1586 丰臣赐姓、东京大学关于 1582–1615 丰臣政权研究范围，以及大阪市关于关原后大坂丰臣领的说明：
  - <https://www.city.osaka.lg.jp/keizaisenryaku/page/0000669869.html>
  - <https://www2.ntj.jac.go.jp/dglib/contents/learn/edc18/ehon/yomoyama/y4/a.html>
  - <https://www.u-tokyo.ac.jp/biblioplaza/ja/D_00079.html>
  - <https://www.city.osaka.lg.jp/chuo/page/0000636470.html>

## 姓名与大名身份（JXP-019 / JXP-021）

- 主 Mod 七个终局国家及伴随地图 30 个大名的 country history、君主池与将领池完成中文显示名审计；保留明确的非日本姓名。
- 姓名门禁覆盖 82 个 history literal、276 个 monarch-pool entry、480 个 leader-pool entry、30 个地图生成 source record 与 source/active localisation 对，问题数为 0。
- 可选大名矩阵为主 38 + 地图 30 = 68 tags；272/272 个 tag×DLC profile 均有五列非通用任务树、exact-tag `free = yes` 理念和唯一身份 slot-3 owner。
- 地图 30 个 tag 从一个共享理念组迁移为 30 个 `start + 7 + bonus` 组；旧共享组保留 `always = no` tombstone。五个既有地图身份 series 从 3 项扩到 6 项，未更换 series key 或增加 slot 竞争。
- v012 地图迁移使用唯一 `swap_free_idea_group = yes` 与 canonical 双阶段任务刷新；形成 JAP/终局 tag 后再由主 Mod canonical helper 接管。
- 固定原版词表审计发现并修复无效 modifier `fort_defense`，统一为 1.37.5 的 `defensiveness`；主 712 + 地图 427 个理念 modifier entry 均对照 414 个原版合法键。

## 九路线与时代属性（JXP-006 / JXP-014）

- 先修复刀狩令与原版 `daimyo_vassal`、`subject_sword_hunt`、`overlord_sword_hunt` 的重复入口，并用逐项 mutation 固化。
- Sakoku / Open Trade / EJP：3 个原生议政事件、3 个主动决议、3 个 debug 入口；9 项可见改革各有独立属性取舍。
- KJP / CJP / RFJ / SJP：4 个原生事件、4 个主动决议、4 个 debug 入口；12 项可见改革各有独立属性取舍。
- WAK 与 IJP 由各自长期循环提供多种长期属性变化方式。所有新增 route modifier 均有限期，并同时纳入 route exit、跨路线 stale cleanup 与 canonical debug reset。
- `jxp_wokou.1` / `jxp_ikko.1` 均改为防御性互斥 trigger，并在写路线 flag 前调用 canonical clear；正常形成、旧 flag 和 debug 调用均有测试覆盖。

## WAK / IJP 长期循环（JXP-008 / JXP-009）

- WAK：三项 1825 日可重复投资、0–100 海盟压力、周期收益/争议/85+危机、海上奉行国与解散船团两条退出路径、11 个有限期 modifier。
- IJP：三项 1825 日寺社町众治理选择、0–100 会众压力、50/85 分层事件、寺社町众国与解散武装联盟两条退出路径、11 个有限期 modifier。
- 两循环均有 AI 权重、route 丢失一日清理、public lifecycle helper、专用 debug 入口和 0–100 clamp mutation。
- IJP 启动决议在路线次日 reconcile 完成前保持隐藏，避免玩家同日投入被 canonical 路线清理吞掉；专用 mutation test 固定此竞态保护。
- WAK 只消费 `jxp_map_compat_wokou_waters`，IJP 只消费 `jxp_map_compat_ikko_heartland`；两者都保留原版 area/港口/寺内町 fallback，不硬依赖伴随地图对象。

## 灾难与状态生命周期（JXP-007 / JXP-015）

- Shimabara、Ikko 启动事件不再在所有选项中立即设置 resolved；改为 active 状态、至少 365 天处理期、organic recovery、玩家/AI 结算决议和 end/debug cleanup。
- 新增 1651 庆安浪人危机与 1783 天明饥馑，总数达到 4；二者分别使用统一身份、江户锚点、年代、军事/财政/人力复合压力的窄 trigger。
- 联合状态审计从 246 个 hard failures 降至 0：删除 75 个无消费者 flag（126 个写点）与 2 个孤儿 modifier，补齐 legacy-detail debug toggle，并集中清理 31 个 flag、59 个国家 modifier、16 个省份 modifier。
- 最终 inventory：535 个 country flags、6 个 province flags、887 个 modifier definitions、4 个 disasters；孤立写、悬空读、生命周期缺口和 debug cleanup 缺口均为 0。

## 可执行门禁

最终静态证据：

```text
Main release gate: 21/21 PASS
Clausewitz gameplay scripts: 234/234
Unit tests: 142/142
Main missions: 278 IDs / 41 series / 192 profiles
Daimyo matrix: 68 tags / 272 profiles / 68 idea identities / 68 identity series
State safety: 535 country flags / 887 modifiers / 4 disasters / 0 failures
Companion map/history/content/compat/assets: 0 errors / 0 warnings
Companion history: 137,382 selectable days / 299 owner intervals / 70 subject intervals
Combined content inventory: 490 events / 269 decisions / 323 scripted callables / 887 modifiers
Skill quick validation: valid
git diff --check: PASS
```

新增 mutation suites 分别覆盖丰臣 4 项、路线 6+10 项、WAK 11 项、IJP 18 项、状态/灾难 14 项、大名覆盖 8 项；完整测试总数以上述 142 为准。

## 状态与剩余风险

- `JXP-006`、`JXP-007`、`JXP-014`、`JXP-015`、`JXP-019`、`JXP-021` 的静态 acceptance 已完成。
- `JXP-008` / `JXP-009` 保留 `IN_PROGRESS`，等待获许可后的事件节奏、AI observer、tooltip、存读档和 route-loss cleanup 运行时证明。
- `JXP-018` 保留 `IN_PROGRESS`，等待 ODA→TOY 任务/决议、历史书签、政府 UI、理念/任务刷新与旧档迁移运行时证明。
- `JXP-020` / `JXP-023` 继续等待理念 UI 与八纮一宇改革 UI/fresh log 证据。
- 本切片没有把静态结果描述为游戏内结果；运行时总状态仍为 `PENDING_USER_APPROVAL`。
