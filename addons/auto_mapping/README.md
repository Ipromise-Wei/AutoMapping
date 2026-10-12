# 独立自动建图模块使用说明

模块目录：`/home/hzauaiot/songwei_V2.0/addons/auto_mapping`  
适用底盘：Ranger Mini V3；ROS 2 Humble  
更新日期：2026-10-13

## 1. 这个模块做什么

从空白地图启动 SLAM Toolbox，同时运行 Nav2 和 `frontier_exploration_ros2`。探索器根据实时地图的已知/未知边界自动选择目标，Nav2 控制车辆前往目标，SLAM 持续更新地图。

原有手动建图、已有地图导航的脚本、配置和运行入口保持不变。此模块有独立源码、配置、编译目录、安装目录、日志和 RViz2 配置。原项目的 `RUN_GUIDE.md` 继续用于原来的两种运行方式。

三个模式共用底盘和雷达，**同一时间只启动一个模式**。新模块与原有脚本使用同一把硬件锁，避免重复启动。

## 2. 快速启动自动建图

以下命令都在底盘主机的终端执行。如果使用另一台电脑，先连接：

```bash
ssh hzauaiot@192.168.123.41
```

### 2.1 关闭原来的运行模式

如果已有地图导航正在运行：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/stop_navigation.sh
```

如果手动建图正在运行，先保存需要保留的地图，再执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/stop_mapping.sh
```

如果所有相关程序都已停止，直接进入下一步。独立键盘控制终端也应关闭。

### 2.2 启动新模块

将底盘、雷达上电，遥控器切换到允许 **CAN 控制**的模式。车辆起点应有足够的行驶和转向空间。

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/start.sh
```

保持这个终端运行。启动脚本会自动打开专用 RViz2，并启动传感器、SLAM、Nav2 和探索器。等待地图、扫描、里程计、TF 及 Nav2 全部就绪后，**车辆会自行开始探索**。

- 不需要已有地图文件。
- 不需要 `2D Pose Estimate`，当前位置由本次 SLAM 会话建立。
- 不需要点击 `2D Goal Pose`，探索目标由程序生成。
- 每次重新执行启动脚本都从空白地图开始；已保存文件不会被覆盖。
- 默认 ROS 域为 `30`。若终端以前用于隔离测试，先执行 `export ROS_DOMAIN_ID=30`，控制、保存终端也应使用同一域。
- 通过 SSH 启动且未设置 `DISPLAY` 时，RViz2 默认显示在底盘主机桌面；通过该主机的显示器或远程桌面操作。

### 2.3 首次试用：先看地图，再开始运动

如果希望先启动所有节点、观察扫描和实时地图，再手动开始自动探索，可以使用暂停启动方式：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/start.sh --paused
```

此时 SLAM 和 Nav2 运行，探索器暂不发送目标。准备好后，在另一个终端执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/resume.sh
```

不要同时执行普通启动和暂停启动，两者是同一个模块的两种启动选项。

## 3. 查看探索过程

专用 RViz2 使用 `map` 坐标系，显示：

| 显示项 | 含义 |
| --- | --- |
| Live SLAM Map | 当前实时生成的地图 |
| Laser Scan | 激光扫描投影 |
| Ranger Mini V3 / Footprint | 车辆模型及导航使用的车体占据范围 |
| Planned Path | Nav2 规划路径 |
| Exploration Frontiers | 探索器选出的候选边界点 |
| Automatic Goal | 当前自动选择的目标位置和朝向 |

窗口不提供初始定位和手动导航目标按钮，防止与自动探索目标混用。暂停、继续和关闭使用下述独立脚本。

上游只在 DEBUG 日志级别发布探索标记和目标话题，本模块已为探索器启用该级别，因此探索日志较详细；其他节点仍使用默认日志级别。

## 4. 暂停与继续

在另一个终端暂停探索：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/pause.sh
```

脚本要求探索器停止下发目标并取消当前目标，确认速度输出为零且里程计显示车辆静止后，提示“探索已暂停”。SLAM、雷达和 RViz2 继续运行，地图仍保留。

继续探索：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/resume.sh
```

继续时会重新选择探索目标。上游的停止/启动控制会重置本次探索选择状态，但不会清除 SLAM 已生成的地图。

不要通过关闭 RViz2 窗口来停车；窗口关闭不会自动关闭探索器或底盘。遥控器若仍在人工驾驶，应先让车停稳。

## 5. 保存自动生成的地图

地图达到需要的覆盖范围后，保持启动终端运行，在另一个终端执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/save_map.sh auto_room_01
```

保存脚本会先暂停探索并确认停车，再调用原项目的地图保存脚本。成功后生成：

```text
/home/hzauaiot/songwei_V2.0/maps/auto_room_01.yaml
/home/hzauaiot/songwei_V2.0/maps/auto_room_01.pgm
/home/hzauaiot/songwei_V2.0/maps/auto_room_01.posegraph
/home/hzauaiot/songwei_V2.0/maps/auto_room_01.data
```

- 名称只使用英文字母、数字、下划线、短横线，不带扩展名。
- 不覆盖同名地图；提示已有文件时换一个名字。
- 保存成功后探索保持暂停，继续探索需执行 `resume.sh`。
- 若暂停或静止确认失败，脚本不继续保存；先检查启动日志、里程计和遥控器状态。
- 控制服务若偶发回复超时，会有限重试；只有明确收到暂停完成回复并确认静止后才保存。
- **先保存成功，再关闭模块。** 关闭程序不会自动保存地图。

探索器找不到可用边界时会停止探索，并在 `/auto_mapping/exploration_complete` 发布完成事件。此状态表示当前没有可用目标，不保证所有房间或角落都已覆盖；确认地图后仍需执行保存命令。

## 6. 关闭模块，并使用新地图导航

在另一个终端关闭自动建图：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/stop.sh
```

该脚本先尝试暂停、停车，再关闭本模块记录的启动进程及其子进程。也可在启动终端按 `Ctrl+C` 退出；需要保留的地图必须事先保存。

等待自动建图退出后，使用原来的导航入口加载新地图：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/start_navigation.sh auto_room_01
```

此时已经切回原有保存地图导航模式：在导航 RViz2 使用 **2D Pose Estimate** 设置实际位置和朝向，对齐后再用 **2D Goal Pose** 指定目标。

如果要切回原来的遥控手动建图，关闭自动建图后直接运行：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/start_mapping.sh
```

## 7. 不使用、禁用或删除这个模块

不执行 `addons/auto_mapping/scripts/start.sh`，模块就不会运行。原有启动脚本不会自动加载或启动它，也没有增加开机自启。

如需可恢复地禁用，先用 `stop.sh` 关闭自动建图，再执行：

```bash
cd /home/hzauaiot/songwei_V2.0
mv addons/auto_mapping addons/auto_mapping.disabled
```

恢复时改回原名：

```bash
cd /home/hzauaiot/songwei_V2.0
mv addons/auto_mapping.disabled addons/auto_mapping
```

如果确认要永久移除，先关闭模块，然后只删除这个目录：

```bash
cd /home/hzauaiot/songwei_V2.0
rm -r -- addons/auto_mapping
```

模块内的源码、编译产物及测试日志会一起删除。已保存到原项目 `maps` 目录中的地图仍然保留。删除后不需要重编译原项目，原来的手动建图和地图导航入口仍可使用。若在终端手动加载过模块环境，删除后换一个新终端再使用原项目。

## 8. 独立编译与配置

模块已编译部署，正常运行无需重复编译。需要修改本模块后重新编译时，先停止自动建图，再执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/build.sh
```

本模块使用自己的 `build`、`install`、`log` 目录。顶层 `COLCON_IGNORE` 使原项目的编译不会递归发现这些可选包；独立编译脚本明确指定自己的 `src`。

主要文件（均相对于模块目录）：

| 文件 | 用途 |
| --- | --- |
| `src/songwei_auto_mapping/launch/auto_mapping.launch.py` | 自动建图组合启动；调用原有传感器/SLAM 启动文件，不修改其实现 |
| `src/songwei_auto_mapping/config/navigation.yaml` | 本模块独立 Nav2 参数 |
| `src/songwei_auto_mapping/config/exploration.yaml` | 边界选择、探索控制和传感器视场参数 |
| `src/songwei_auto_mapping/rviz/auto_mapping.rviz` | 自动建图专用显示配置 |
| `src/frontier_exploration_ros2` | 固定版本的上游源码及许可证 |
| `UPSTREAM.txt` | 上游地址和精确提交版本 |
| `logs` | 编译、测试和原文件校验记录；正常运行日志显示在启动终端 |

适配设置：

- SLAM 负责发布实时 `/map` 和 `map → odom`；不启动 AMCL 或保存地图服务器。
- 沿用原模块传感器安装参数、点云处理、270° 扫描配置。
- 车体尺寸、碰撞检测、速度上限沿用已部署设置：`0.15 m/s`、`0.30 rad/s`。
- 探索器使用 `base_link` 和 `/navigate_to_pose`，传感器视场按 270° 设置。
- 上游直接按地图坐标查询两个代价地图，因此仅在本模块中将局部代价地图坐标系设为 `map`。
- 本模块关闭随地图变化不合适的规划启发式缓存，保留禁止穿越未知区域的设置。
- 本模块的 Nav2 行为树等待动作响应/取消结果的超时设为 `500 ms`，用于探索目标切换；原导航配置不变。
- 保留上游 DP 目标排序；启用失败目标暂时抑制与到达后等待，关闭自动返回起点，以及依据可见信息增益提前更换目标的选项。
- 沿用上游默认的边界目标接近完成距离 `0.5 m`：当目标未被判为阻塞、车辆进入该范围后，探索器取消当前导航目标并选择下一边界，减少近目标绕行。此时 Nav2 显示目标取消属于正常切换；原有保存地图导航的到达精度不变。
- **当前仍不支持自动倒车。** 后方扫描屏蔽和原有前进导航约束没有改动，狭窄位置可能需要人工介入；暂停探索后再切换遥控模式操作。

## 9. 验证与适用范围

隔离验证使用 `ROS_DOMAIN_ID=31`、`ROS_LOCALHOST_ONLY=1`，关闭实际底盘和雷达驱动，用模拟扫描和 Ranger 运动模型运行真实 SLAM、Nav2 和探索器。测试报告位于：

- `logs/integration_report.json`：无地图启动、自动目标、路径、地图增长、暂停、继续、保存及关闭。
- `logs/isolation_report.json`：原文件校验、原有两种启动流程及模块隔离检查。
- `logs/upstream_tests.log`：上游测试。

这些测试验证软件链路，不代表已经完成当前房间的实车自动探索验收。实际覆盖率受地图质量、定位、起点空间、障碍分布和雷达可见区域影响。

部署验证结果：上游 141 项测试通过；原项目 558 个文件校验一致，原项目编译仍只发现原有 7 个包；上游 69 个受版本管理的文件与固定提交一致。集成测试验证了默认自动启动、边界目标接近完成后自动切换、地图增长、暂停停车、继续探索、保存四个地图文件、原导航地图格式检查和退出无残留。隔离测试没有启动实际 CAN 或雷达驱动，也没有自动启动实车探索。

上游来源：[mertgulerx/frontier_exploration_ros2](https://github.com/mertgulerx/frontier_exploration_ros2)。本模块采用提交 `0d611801cfe152dbd5000cf0b1936783b8977bde`，包清单版本为 `1.6.1`，上游源码未修改，保留 Apache-2.0 许可证。
