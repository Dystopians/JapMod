# 日轮诸道：日本扩展风味包 热修复报告

更新时间：2026-07-09
当前版本：0.5.1

## 问题

使用大友测试时，玩家能在任务提示中看到“整饬本领”已经完成或被引用，但任务树界面仍主要显示原版日本任务，无法在树上找到该任务。

## 根因

原版 EU4 v1.37.5 的任务界面文件 `interface/countrymissionsview.gui` 中设置了：

```txt
max_slots_horizontal = 5
```

此前 0.5 为了避免覆盖原版日本任务，将大量自定义任务放在 `slot = 6` 及更高槽位，尤其大名任务位于 `slot = 16/17`。这些任务可以被脚本解析、可以进入依赖关系和完成状态，但在游戏任务界面中存在不可见风险。

## 修复

所有自定义任务组已经回流到 `slot = 1` 至 `slot = 5` 的可见范围内，并通过更高的 `position` 放在原版任务下方，避免覆盖原版任务。

重点调整：

- 大名本领任务：`slot = 1`，`position = 9-13`。
- 大名港町/南蛮接触任务：`slot = 2`，`position = 9-11`。
- 统一后共享任务：`slot = 1/2`，`position = 9-14`。
- 路线主干任务：`slot = 3/4/5`，`position = 9` 起。
- 宗教分支任务：`slot = 4`，`position = 25-29`。
- 国内制度与边疆外交任务：`slot = 1/2`，`position = 45-50`。

## 受影响文件

- `missions/jxp_japan_missions.txt`
- `missions/jxp_03_overseas_missions.txt`
- `missions/jxp_04_daimyo_missions.txt`
- `missions/jxp_09_religious_route_missions.txt`
- `missions/jxp_10_popular_maritime_missions.txt`
- `missions/jxp_11_branching_missions.txt`
- `descriptor.mod`
- `../japan_expanded_v2.mod`

## 校验

- `rg` 检查：`missions` 目录中已无 `slot > 5`。
- EU4 Mod 校验脚本：通过。
- 本次未改动本地化文本，因此不需要重新生成 localisation。

## 游戏内测试建议

以大友开局，打开任务界面后应在原版日本任务下方看到：

- 第 1 列下方：“整饬本领”“修筑城下”“束合一门”“奉书上洛”“问鼎京都”。
- 第 2 列下方：“港町商书”“铁炮传闻”“译读异国书”。

如果仍未显示，需要在启动器中确认启用的是 0.5.1 版本，并重新开始新档测试，因为任务树布局通常不会可靠刷新到旧存档。
