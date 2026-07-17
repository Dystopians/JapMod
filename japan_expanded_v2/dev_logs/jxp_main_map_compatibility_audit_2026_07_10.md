# 主 Mod / 日本八十八国地图兼容性审计

日期：2026-07-10  
主 Mod：`japan_expanded_v2` 0.25.0  
伴随地图：`japan_expanded_v2_map` 0.1.1-alpha  
EU4：1.37.5.0

## 结论

两 Mod 现已作为一个联合发布面接受静态校验。已遍历活动事件、任务、
决议、灾难、scripted trigger/effect、理念、政府改革、tag、历史文化与
地图地理锚点。所有能够静态确认的兼容故障均已修复；联合门禁为
`0 error / 0 warning`。本次没有启动 EU4，运行时结论仍需用户批准后的
游戏内验收。

从本阶段起，本项目的默认规则是：主 Mod 的每次玩法修改都必须兼容
`japan_expanded_v2_map`，并同时通过主门禁与地图联合门禁。

## 已修复故障

1. **13 个西日本新大名的无效文化键**
   - `saigoku` 是原版文化文件中的注释称呼，不是可执行键。
   - `RKK/KYO/WKT/TGS/NHT/ANK/HNG/AZI/MYO/STO/UKT/HCS/YMC` 已改为
     原版有效键 `japanese`，并重新生成 30 个国家文件。

2. **地图大名任务树的无限刷新风险**
   - 主 Mod 原指纹只认可 37 个原版大名的家系锚点，地图大名的专属
     slot 3 会被误判为损坏。
   - 主 Mod 现在只验证共享 slots `1/2/4/5`，通过自由 origin flag
     识别伴随地图来源；地图 Mod 自己精确验证 slot 3，并拥有低频修复。
   - 同时修复了不存在的 `jxp_has_sea_house_origin_trigger`，统一为真实
     定义 `jxp_has_maritime_house_origin_trigger`。

3. **30 个地图 origin 与主家系系统断开**
   - 30 个 `jxp_map_origin_*` 已按武家、朝廷、海商、边疆、寺社市场五类
     接入主 Mod 的 grouped house triggers。
   - 因此家中评定、家系议程、路线妥协/共鸣、遗产内阁和家系理念遗产
     均可识别地图来源。
   - 精确 founder reform 仍只属于原 37 家；地图来源保留通用改造日本
     founder reform。校验器会阻止 map flags 误入
     `jxp_has_major_daimyo_origin_trigger`，避免通用回退被错误关闭。

4. **地图 slot 3 的非法奇偶布局**
   - 五个地图家系系列由 rows `2/4/6` 改为 slot 3 合法的 `1/3/5`。
   - `jxp_map_runtime_migration_v011` 对现有地图大名存档执行一次 canonical
     双阶段任务刷新；之后由精确指纹按需修复，不会持续循环。

5. **area 拆分造成的历史范围丢失**
   - 伴随地图在启动时为扩展省份写入四类无界面 province flag：
     `jxp_map_compat_shimabara_belt`、`jxp_map_compat_ikko_heartland`、
     `jxp_map_compat_setouchi`、`jxp_map_compat_wokou_waters`。
   - 主 Mod 通过这些语义旗标恢复岛原灾难/九州神学校、西九州与琉球
     倭寇海路、濑户内水军以及一向宗旧宏观区域的覆盖。
   - 主 Mod 不直接引用可选地图的 area、省份或 tag，因此单独加载仍安全。

6. **异常多 origin 存档叠加地图永久遗产**
   - `jxp_map.100` 已由五个独立 `if` 改为确定顺序的
     `if/else_if`，最多授予一个永久遗产。

7. **0.25 新增任务缺少规范标题键**
   - 联合可视化发现 34 个新增任务只有裸 `<mission_id>` 文本，没有原版
     规范的 `<mission_id>_title`。
   - 已保留旧键并补齐 34 个 `_title` 兼容别名，重新生成中文转义文本；
     主门禁与联合门禁现在强制每个任务同时具有 `_title` 和 `_desc`。

## 联合静态证明

- 30 个地图 tag × 4 种 DLC 状态，共 120 个大名 profile：每个 profile
  恰有 slots `1..5` 五个非通用 owner，无 generic fallback、series overlap、
  cell collision、失活前置或 renderer topology 错误。
- 30 个 tag 恰好分属五个 origin 类别；每个 tag 只命中一个地图理念组，
  与原版及主 Mod tag 无冲突。
- `japan_region` 恰含 88/88 计划省份。
- 保留锚点 `1015/1020/1021/1028/4182/4183/4193/4359/4651` 的 ID 与名称
  分别保持 Okinawa/Kyoto/Settsu/Musashi/Hizen/Iwami/Oshima/Ise/Tsushima。
- 合并目录中 466 个事件 ID、215 个决议 ID、231 个 scripted callable、
  832 个 modifier，以及全部任务 ID/series ID 无跨 Mod 冲突。
- 联合可视化覆盖 45 个任务组、287 个任务，缺失本地化键为 0。
- 地图 descriptor 的 dependency 与主 Mod 显示名精确一致。
- 地图历史验证覆盖 137382 个可选日期、273 个连续所有权区间与
  56 个 subject 区间。

## 尚存风险 / TODO

1. 活动脚本仍有 19 处 `num_of_cities = 25/30`。在 48 省原图中分别约为
   52.1%/62.5%，在 88 省地图中约为 28.4%/34.1%。这些条件合法且不会
   造成崩溃，但统一、终局与路线任务会偏早。
2. 不应按 `88/48` 机械放大。下一内容阶段应逐项按“完全统一、阶段扩张、
   核心城市、area 数、总发展”重新解释并替换。
3. `1021` 仍作为 Settsu/大坂/堺兼容锚点；地图新增 `4943` 表现堺外围。
   当前不构成功能错误，但新增堺内容时须避免把两者当作同一省重复奖励。
4. 静态工具不能证明引擎接受 on_startup、任务 swap 与地图渲染；未经用户
   明确许可不得启动游戏。运行时验收应使用两 Mod 独立 playset 和新存档。

## 验证命令与结果

- 主 Mod `validate_jxp_mod.ps1`：11/11 checks，37/37 unit tests。
- 地图 `tools/validate_all.ps1`：地图、全日期历史、内容、联合兼容、资源、
  通用 Mod 校验和主 Mod 门禁全部通过，0 error / 0 warning。
- Skill `quick_validate.py`：`Skill is valid!`
- 联合可视化：287 个任务，`0 missing localisation keys`。
- 未启动 EU4；未修改游戏根目录。

联合合同与执行器：

- `japan_expanded_v2_map/tools/jxp_map_validation/main_compatibility_contract.json`
- `japan_expanded_v2_map/tools/jxp_map_validation/validate_main_compatibility.py`
- `japan_expanded_v2_map/tools/validate_all.ps1`
