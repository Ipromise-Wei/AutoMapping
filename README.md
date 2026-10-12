# AutoMapping — Ranger Mini V3 建图与导航

基于 **松灵 Ranger Mini V3、Livox MID-360、ROS 2 Humble、SLAM Toolbox 和 Nav2** 的实车项目。原部署目录为 `/home/hzauaiot/songwei_V2.0`。

项目版本：**V2.0**（`songwei_bringup` 包版本 `2.0.0`）；可选自动建图适配包版本：**0.1.0**。本次仓库快照日期：**2026-10-13**。详细依赖版本见 [版本记录](docs/VERSIONS.md)。

本仓库保存完整项目源码、运行配置、使用文档和已保存地图。第三方驱动源码随仓库提供；编译产物、运行日志、进程锁及录制数据不入库。自动探索算法来自 [mertgulerx/frontier_exploration_ros2](https://github.com/mertgulerx/frontier_exploration_ros2)，本仓库是面向实际底盘的集成项目。

## 目录

- [1. 功能与模式选择](#1-功能与模式选择)
- [2. 环境、版本与硬件参数](#2-环境版本与硬件参数)
- [3. 克隆、依赖安装与编译](#3-克隆依赖安装与编译)
- [4. 每次运行前的准备](#4-每次运行前的准备)
- [5. 手动建图 → 保存 → 导航](#5-手动建图--保存--导航)
- [6. 直接加载本地地图导航](#6-直接加载本地地图导航)
- [7. 无地图自动探索建图](#7-无地图自动探索建图)
- [8. 地图文件与配置位置](#8-地图文件与配置位置)
- [9. 常见输出与故障处理](#9-常见输出与故障处理)
- [10. 停止、禁用和删除自动建图模块](#10-停止禁用和删除自动建图模块)
- [11. 数据链路、验证与当前限制](#11-数据链路验证与当前限制)
- [12. 项目结构与版本管理](#12-项目结构与版本管理)

## 1. 功能与模式选择

| 运行模式 | 启动入口 | 谁决定车辆运动 | 是否需要已有地图 |
| --- | --- | --- | --- |
| 手动建图 | `./scripts/start_mapping.sh` | 人工遥控；可选独立键盘控制 | 否，每次从空白地图开始 |
| 保存地图导航 | `./scripts/start_navigation.sh 地图名` | 在 RViz2 点击 **2D Goal Pose**，Nav2 执行 | 是，YAML + 对应图片 |
| 独立自动探索建图 | `./addons/auto_mapping/scripts/start.sh` | 探索器自动选目标，Nav2 执行，SLAM 同时建图 | 否，每次从空白地图开始 |

**同一时间只运行一种模式。** 三种模式共用底盘和雷达，启动脚本通过硬件锁与进程检查避免重复占用。

原有手动建图与保存地图导航分阶段使用。新增自动探索模块可以同时运行 SLAM 和 Nav2，独立放在 `addons/auto_mapping` 中；删除该模块不影响原有两种模式。不要向正在自动探索的导航动作另外发送手动目标。

详细分步说明：

- [原有手动建图与保存地图导航指南](RUN_GUIDE.md)
- [独立自动建图模块说明](addons/auto_mapping/README.md)
- [软件与上游版本记录](docs/VERSIONS.md)
- [版本变更说明](CHANGELOG.md)

## 2. 环境、版本与硬件参数

### 2.1 已部署环境

| 项目 | 本次部署使用的版本/配置 |
| --- | --- |
| 操作系统 | Ubuntu **22.04.5 LTS**，x86_64 |
| ROS | **ROS 2 Humble** |
| Nav2 | **1.1.20** |
| SLAM Toolbox | **2.6.10** |
| RViz2 | **11.2.25** |
| pointcloud_to_laserscan | **2.0.1** |
| Livox SDK2 | 安装头文件版本 **1.4.3**；源码提交见版本记录 |
| livox_ros_driver2 | 驱动头文件版本 **1.2.8**；ROS 包清单版本 **1.0.0** |
| frontier_exploration_ros2 | **1.6.1**，固定提交源码 |
| 主机 | `hzauaiot@192.168.123.41` |
| 工作目录 | `/home/hzauaiot/songwei_V2.0` |
| 默认 ROS 域 | `ROS_DOMAIN_ID=30` |

这些是本次主机的实测安装版本，不表示其他 ROS 发行版或所有硬件组合已经验证。精确提交号、Debian 包版本和本地补丁详见 [docs/VERSIONS.md](docs/VERSIONS.md)。

### 2.2 底盘与传感器

| 参数 | 当前值 |
| --- | --- |
| 底盘 | 松灵 Ranger Mini V3 |
| CAN | `can0`，`500000 bit/s` |
| 雷达 | Livox MID-360 |
| 雷达 IP | `192.168.1.175` |
| 雷达接收网卡 | 已部署主机为 `enp3s0`，接收地址 `192.168.1.5` |
| 地图分辨率 | `0.05 m/像素` |
| 导航车身 footprint | `0.72 × 0.50 m`，每侧 padding `0.05 m` |
| 导航速度上限 | 线速度 `0.15 m/s`；角速度 `0.30 rad/s` |
| 有效扫描 | 前方约 `270°`，量程 `0.30–12.0 m`；后方约 `90°` 屏蔽 |
| 安装外参 | `base_link → livox_frame`：平移 `[0.35, 0.0, 0.10] m`，RPY `[0, 0, 0]` |

外参沿用现有项目，需要与实际安装核对。用户测量的雷达离地约 `43 cm` 是相对地面的高度，不能直接替代相对 `base_link` 的 z 外参。

自动导航和自动探索当前均采用前进路径，不会自动倒车脱困。底盘能遥控倒车不代表导航已具备后退避障能力。

## 3. 克隆、依赖安装与编译

**已经在原主机部署完成时，正常启动无需重复安装或编译，直接跳到第 4 节。** 以下用于新电脑或新目录恢复项目，不要覆盖正在使用的同名目录。

### 3.1 获取项目

```bash
cd "$HOME"
git clone https://github.com/Ipromise-Wei/AutoMapping.git songwei_V2.0
cd songwei_V2.0
```

仓库已包含 Ranger、UGV SDK、Livox ROS 驱动和自动探索源码，无需再次向 `src` 克隆这些包，也不需要执行顶层 `git submodule update`。地图的 `.data`、`.posegraph` 也保留在仓库，因此首次下载比纯源码项目更大。

### 3.2 安装 ROS 与工具

先按 [ROS 2 Humble 官方 Ubuntu 安装文档](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html) 安装 ROS 2 Humble Desktop，并确保存在 `/opt/ros/humble/setup.bash`。下列命令以 ROS 软件源已配置为前提：

```bash
sudo apt update
sudo apt install -y \
  git build-essential cmake pkg-config \
  python3-colcon-common-extensions python3-rosdep \
  python3-numpy python3-yaml \
  libpcl-dev libapr1-dev can-utils \
  ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-slam-toolbox ros-humble-pointcloud-to-laserscan \
  ros-humble-rviz2 ros-humble-robot-state-publisher \
  ros-humble-teleop-twist-keyboard
```

只在尚未初始化 rosdep 的主机执行一次：

```bash
sudo rosdep init
```

然后更新索引：

```bash
rosdep update
```

### 3.3 安装 Livox SDK2

Livox SDK2 是 ROS 驱动之外的系统依赖，**不随本仓库打包**。已部署主机的 `/usr/local/lib` 已有 SDK 库；新主机需要安装。

下面固定到部署主机使用的源码提交，构建步骤依据 [Livox SDK2 官方说明](https://github.com/Livox-SDK/Livox-SDK2/blob/6a940156dd7151c3ab6a52442d86bc83613bd11b/README.md)：

```bash
mkdir -p "$HOME/deps"
cd "$HOME/deps"
git clone https://github.com/Livox-SDK/Livox-SDK2.git
git -C Livox-SDK2 checkout 6a940156dd7151c3ab6a52442d86bc83613bd11b
cmake -S Livox-SDK2 -B Livox-SDK2/build -DCMAKE_BUILD_TYPE=Release
cmake --build Livox-SDK2/build -j2
sudo cmake --install Livox-SDK2/build
sudo ldconfig
```

若 `Livox-SDK2` 目录已经存在，应先确认其版本和本地改动，再决定是否复用；不要直接覆盖已有 SDK 工作目录。

### 3.4 安装项目依赖并编译基础工作区

使用新终端，避免加载旧项目或其他 Nav2 overlay：

```bash
cd "$HOME/songwei_V2.0"
source /opt/ros/humble/setup.bash

# Livox 上游同时包含 ROS1/ROS2 清单，先选择 ROS2 清单供 rosdep 读取。
cp src/livox_ros_driver2/package_ROS2.xml src/livox_ros_driver2/package.xml
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y

# 原有脚本使用 logs 保存锁和 PID；仓库的占位文件已保留此目录。
mkdir -p logs maps
./scripts/build.sh
```

基础编译包含本项目修正后的 `nav2_regulated_pure_pursuit_controller`；脚本已配置允许覆盖同名系统包。不要仅编译 `songwei_bringup` 而遗漏这个控制器。

### 3.5 可选：编译自动探索模块

只使用原有手动建图、保存地图导航时，可以跳过本节。先完成基础工作区编译，再执行：

```bash
cd "$HOME/songwei_V2.0"
source /opt/ros/humble/setup.bash
source install/local_setup.bash
rosdep install --from-paths \
  addons/auto_mapping/src/frontier_exploration_ros2 \
  addons/auto_mapping/src/songwei_auto_mapping \
  --ignore-src --rosdistro humble -r -y
./addons/auto_mapping/scripts/build.sh
```

模块自行使用 `addons/auto_mapping/build`、`install`、`log`，通过 `COLCON_IGNORE` 与根工作区隔离。修改源码或配置后，停止对应运行模式再编译；本仓库的发布整理不要求重启现有部署。

## 4. 每次运行前的准备

以下运行命令以原部署主机路径为例。若克隆到其他位置，将 `cd` 路径替换为实际目录；启动脚本会根据自身位置找到工作区。

```bash
# 从另一台电脑连接时使用；在底盘本机终端无需 SSH。
ssh hzauaiot@192.168.123.41
```

在底盘主机的各个操作终端中：

```bash
cd /home/hzauaiot/songwei_V2.0
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
```

1. 底盘、雷达上电，CAN 和雷达网线连接正常。
2. 雷达接收网卡配置为与雷达匹配的网段；在原主机为 `enp3s0 / 192.168.1.5`。换主机后需要同步核对 `MID360_config.json` 的接收地址。
3. 停止上一次运行模式，关闭独立键盘控制终端。关闭窗口不一定代表进程已退出。
4. 遥控建图使用遥控模式；自动导航/自动探索使用允许 CAN 控制的模式。遥控器的具体开关位置以实际设备为准。

检查 CAN：

```bash
ip -details link show can0
```

应看到接口启用且 bitrate 为 `500000`。若未配置，在底盘驱动停止的情况下执行一次：

```bash
./scripts/setup_can.sh can0
```

启动脚本会加载 ROS 环境并自动打开相应 RViz2，不需要额外启动底盘、雷达或 RViz2。SSH 启动且未设置 `DISPLAY` 时，RViz2 默认出现在**底盘主机桌面**，可通过其显示器或远程桌面操作。

## 5. 手动建图 → 保存 → 导航

适用于没有场地地图、需要重新手动建图的情况。以下 `room_new_01` 是示例新名称；若已有同名文件，请换名。

### 5.1 终端一：启动手动建图

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/start_mapping.sh
```

保持终端一运行，在自动打开的 RViz2 中确认 `Fixed Frame=map`。用遥控器低速驾驶车辆采集场地，转弯时放慢速度，尽量形成重复观测。

此阶段由 SLAM 建图，不需要 `2D Pose Estimate`。原手动建图入口没有同时启动 Nav2，点击导航目标不会自动驾驶。

可选键盘控制需要另开终端，并让底盘处于允许 CAN 控制的模式：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/keyboard.sh
```

`i` 前进、`,` 后退、`j/l` 旋转、`J/L` 横移，`k` 或空格停止。该入口是人工控制，与自动导航的前进限制是两个不同功能。

### 5.2 终端二：保存地图

让车辆停稳，**保持建图终端运行**：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/save_map.sh room_new_01
ls -lh maps/room_new_01.*
```

应生成四个文件：`.yaml`、`.pgm`、`.posegraph`、`.data`。地图名只使用字母、数字、下划线、短横线，不带扩展名。脚本拒绝覆盖同名地图；保存失败时先处理错误，不要提前关闭建图。

### 5.3 终端二：停止建图，加载新地图导航

确认保存成功后：

```bash
./scripts/stop_mapping.sh
```

等待退出，并关闭使用过的键盘控制终端，再运行：

```bash
./scripts/start_navigation.sh room_new_01
```

随后按第 6.2 节在 RViz2 设置实际位置和导航目标。即使车辆保存地图后没有移动，切换到 AMCL 导航也需要设置初始位置。

## 6. 直接加载本地地图导航

### 6.1 启动

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/start_navigation.sh room_401
```

脚本启动底盘、雷达、地图服务器、AMCL、Nav2 和导航 RViz2。无需在 RViz2 中手动“导入”地图；地图路径传给启动脚本即可。

支持以下路径写法，每次只执行其中一条：

```bash
./scripts/start_navigation.sh ./maps/room_401.yaml
./scripts/start_navigation.sh /home/hzauaiot/my_maps/room.yaml
```

带空格的路径使用引号。省略参数时默认加载 `room_401`，建议每次明确写地图名，防止用错场地。

### 6.2 RViz2 操作顺序

1. 确认显示了正确地图，`Fixed Frame=map`。
2. 点击 **2D Pose Estimate**，在车辆实际位置按下鼠标，拖动箭头指定车头朝向后松开。
3. 等待 AMCL 更新，检查扫描点与墙面、固定障碍是否基本重合。初始估计不能保证一次点击就完全对齐；明显错位时重新设置。
4. 遥控器切换到允许 CAN 控制的模式。
5. 点击 **2D Goal Pose**，在已知空闲区域设置目标位置，拖动箭头指定到达朝向。
6. 观察规划路径和车辆运动；使用 Navigation 2 面板的 **Cancel** 可取消当前目标。

当前位置容差为 `0.20 m`，角度容差为 `0.15 rad`（约 8.6°）。目标点需要为整个车身和转向留出空间；地图中的白色像素并不保证所有车身朝向都能通过。

### 6.3 关闭导航

另一个终端执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./scripts/stop_navigation.sh
```

也可在启动终端按 `Ctrl+C` 并等待退出。

## 7. 无地图自动探索建图

该模式使用独立模块：实时 SLAM 生成地图，探索器寻找已知/未知边界，Nav2 控制车辆前往目标。无需已有地图，也无需手动点击 `2D Goal Pose`。

### 7.1 启动

先关闭手动建图或保存地图导航。将底盘设置为允许 CAN 控制的模式，然后执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/start.sh
```

地图、扫描、里程计、TF 和 Nav2 就绪后，**车辆会自行开始探索**。本模式使用 SLAM 定位，不运行 AMCL，因此不需要 `2D Pose Estimate`。

首次检查也可以使用暂停启动方式，代替上面的普通启动命令：

```bash
./addons/auto_mapping/scripts/start.sh --paused
```

此时节点、地图和 RViz2 正常启动，探索器暂不发送目标。确认地图与扫描后，在另一个终端执行：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/resume.sh
```

### 7.2 暂停与继续

```bash
# 暂停探索，取消当前目标并确认停车，SLAM 与 RViz2 保持运行。
./addons/auto_mapping/scripts/pause.sh

# 需要继续时单独执行。
./addons/auto_mapping/scripts/resume.sh
```

暂停后地图不会清空；继续时探索器会重新选择目标。需要人工遥控脱困时，先暂停并确认停车，再切换遥控模式。

### 7.3 保存自动建图结果

在启动终端保持运行的情况下，另一个终端执行；`auto_room_02` 应替换成尚未使用的名字：

```bash
cd /home/hzauaiot/songwei_V2.0
./addons/auto_mapping/scripts/save_map.sh auto_room_02
ls -lh maps/auto_room_02.*
```

保存脚本先暂停探索、确认静止，再调用原项目保存逻辑。成功生成四个地图文件后保持暂停；如需继续探索，再执行 `resume.sh`。关闭程序不会自动保存地图。

### 7.4 停止自动建图并使用结果导航

```bash
./addons/auto_mapping/scripts/stop.sh
```

等待退出后：

```bash
./scripts/start_navigation.sh auto_room_02
```

此时切换为保存地图导航，按照第 6.2 节设置 **2D Pose Estimate → 2D Goal Pose**。

## 8. 地图文件与配置位置

### 8.1 地图文件

| 文件 | 用途 |
| --- | --- |
| `地图名.yaml` | 图片路径、分辨率、原点、占据阈值 |
| `地图名.pgm` | 二维占据栅格图像 |
| `地图名.posegraph` / `地图名.data` | SLAM Toolbox 序列化建图数据 |

保存地图导航只需要 YAML 和其 `image` 指向的图片。图片相对路径以 YAML 所在目录为基准。当前导航要求 `resolution=0.05` 且 `origin` 的 yaw 为 `0`，脚本会检查地图格式。

本次仓库包含 `room_401`、`room_401_2`、`auto_room_01` 和 `validation_initial`。前三者对应已有场地记录；`validation_initial` 是历史验证地图。地图名称不代表地图已完成实车验收，使用前应核对场地与定位。新保存逻辑使用 `free_thresh=0.196`、`occupied_thresh=0.65`；历史 `validation_initial` 保留其原始阈值，勿直接当作生产场地地图。

已有 `.posegraph/.data` 虽已归档，当前启动脚本仍从空白地图开始，尚未提供一键加载序列化图继续建图的入口。

### 8.2 配置入口

| 文件 | 作用 |
| --- | --- |
| `src/songwei_bringup/config/robot.yaml` | CAN、雷达外参、点云过滤、扫描范围 |
| `src/songwei_bringup/config/MID360_config.json` | 雷达地址及接收网络配置 |
| `src/songwei_bringup/config/slam_toolbox.yaml` | 手动/自动建图共用的 SLAM 配置 |
| `src/songwei_bringup/config/navigation.yaml` | 原有保存地图导航参数 |
| `addons/auto_mapping/src/songwei_auto_mapping/config/navigation.yaml` | 自动建图模块专用 Nav2 参数 |
| `addons/auto_mapping/src/songwei_auto_mapping/config/exploration.yaml` | 探索目标选择、失败抑制、完成判定等 |

改配置应先停止相应模式，重新编译相应工作区，再重新启动；不要假设修改文件会实时更新正在运行的节点。原始安装外参若发生变化，手动与自动建图都会受影响。

## 9. 常见输出与故障处理

| 提示/现象 | 含义与处理 |
| --- | --- |
| `already running` / “仍在运行” | 有现存实例或硬件被占用；使用对应停止脚本，等待退出后重启。不要仅删除锁文件。 |
| `Please set the initial pose` | 保存地图导航的 AMCL 等待初始位置，在 RViz2 设置 **2D Pose Estimate**。 |
| `map ... does not exist` / 等待 `base_link → map` | 保存地图导航刚启动时通常伴随未初始化 AMCL；设置初始位置后仍出现，应检查 TF、扫描和节点状态。自动 SLAM 模式应检查 SLAM 与输入数据，不能靠 AMCL 初始化解决。 |
| `detected collision ahead` | 控制器预测当前运动会碰撞，检查实际障碍、定位、车体 footprint 和转向空间。 |
| `Controller patience exceeded` / `Goal failed` | 持续没有有效控制或路径，当前目标失败；当前配置不会自动倒车脱困。 |
| `no valid path found` | 当前地图、障碍、车体尺寸和运动约束下找不到通往目标的路径。白色区域仍可能被狭窄通道分隔。 |
| `Distance remaining: 0.000` | DEBUG 导航反馈；不能单凭零值认定目标已到达或建图完成。尚未形成有效路径时也可能出现零值，需结合规划结果和目标状态。 |
| `frontier_counts: raw=4, decision=4` | 本轮检测到 4 个边界候选；它们不一定能被 Nav2 成功到达。数字随地图改变。 |
| `All currently detected frontiers are temporarily suppressed` | 当前候选连续失败，被暂时跳过；此版本抑制超时为 `90 s`，之后可能再次尝试，不能直接视为建图完成。 |
| `STATUS_ABORTED` | 导航动作失败；应查看同一时间的规划器/控制器日志。 |
| 接近边界时目标被取消 | 探索器有 `0.5 m` 的接近完成逻辑，在条件满足时取消旧目标并选下一个；结合 `active frontier considered complete...` 日志判读。 |
| 保存提示同名地图存在 | 换一个新地图名，后续导航使用同一个名字。 |
| 保存提示找不到 SLAM 服务 | 保持建图运行，检查保存终端与启动终端的 `ROS_DOMAIN_ID` 是否相同。 |
| SSH 启动后看不到 RViz2 | 默认窗口显示在底盘主机桌面，使用该主机显示器或远程桌面查看。 |
| 编译缺少 `liblivox_lidar_sdk_shared.so` | 按第 3.3 节安装 Livox SDK2，检查 `/usr/local/lib` 和 `/usr/local/include`。 |

自动探索为显示上游的目标与候选标记启用了 DEBUG，日志会较多。正常运行日志在启动终端和 `~/.ros/log/`。需要只读排查时，在另一个终端加载对应环境：

```bash
cd /home/hzauaiot/songwei_V2.0
source scripts/env.sh
ros2 node list
ros2 topic list
ros2 run tf2_ros tf2_echo map base_link
```

查看自动探索自定义接口时使用 `source addons/auto_mapping/scripts/env.sh`。只读命令不会取消当前任务。

## 10. 停止、禁用和删除自动建图模块

| 正在运行的模式 | 停止命令 |
| --- | --- |
| 手动建图 | `./scripts/stop_mapping.sh` |
| 保存地图导航 | `./scripts/stop_navigation.sh` |
| 自动探索建图 | `./addons/auto_mapping/scripts/stop.sh` |

关闭 RViz2 窗口不能代替停止整套程序。需要保留的实时地图应先保存，再执行停止。

不启动自动建图入口，该模块就不会运行；本项目没有为它添加开机自启。

可恢复地禁用（先停止模块）：

```bash
cd /home/hzauaiot/songwei_V2.0
mv addons/auto_mapping addons/auto_mapping.disabled
```

恢复原目录名即可恢复。永久删除时先确认模块已停止，再删除其专属目录：

```bash
cd /home/hzauaiot/songwei_V2.0
rm -r -- addons/auto_mapping
```

原有 `src`、`scripts`、`maps` 保留，原有手动建图与保存地图导航无需因此重编译。若当前终端曾加载过自动建图 overlay，换一个新终端再使用原项目。Git 仓库中删除模块会显示为文件删除，这是正常版本管理状态。

## 11. 数据链路、验证与当前限制

### 11.1 数据链路

```text
MID-360 → 点云运动补偿/车体过滤 → LaserScan /scan
Ranger  → /odom + odom→base_link

手动建图：        SLAM Toolbox → /map + map→odom → RViz2
保存地图导航：    map_server + AMCL → Nav2 → velocity_smoother → Ranger
自动探索建图：    SLAM Toolbox → frontier_exploration_ros2 → Nav2 → Ranger
```

主要话题：`/livox/lidar`、`/songwei/cloud_deskewed`、`/scan`、`/odom`、`/map`、`/plan`、`/songwei/nav_cmd_vel`、`/songwei/cmd_vel`。探索器通过 `/navigate_to_pose` 动作使用 Nav2。

自动模块复用原 SLAM/传感器启动文件，使用自己的导航参数、行为树、探索参数和 RViz2 配置。自动模式下没有 AMCL 或静态地图服务器参与定位。

### 11.2 已有验证与限制

- 上游自动探索测试曾运行 **141 项，通过**。
- 使用独立 ROS 域、虚拟扫描和 Ranger 运动模型验证过真实 SLAM、Nav2、自动目标、地图增长、暂停/继续、保存和退出流程。
- 加入自动模块时，原项目 **558 个文件校验一致**；原基础工作区仍发现原有 **7 个包**，上游自动探索 **69 个受版本管理文件未修改**。这些数字对应当时集成验证，不包括本次新增的仓库说明文件。
- 当前实车观察到剩余 4 个候选边界反复规划失败、暂时抑制后重试。软件链路测试通过不能证明当前房间已经完全覆盖或所有目标都可达。
- 后方扫描屏蔽、前进路径约束、狭窄转向空间，以及地图/外参误差都可能影响实际可达性。`2D Pose Estimate` 提供初始估计，无法消除所有标定或地图误差。

原部署的测试报告位于根目录或自动模块的 `logs` 中，属于本机诊断记录，**没有随 Git 上传**；新克隆仓库不会自动拥有这些报告。自动模块的集成测试源码位于 `addons/auto_mapping/tests`，测试自身要求隔离 ROS 域，不能当成实车启动入口。

## 12. 项目结构与版本管理

```text
songwei_V2.0/
├── README.md                         # 本说明
├── CHANGELOG.md                      # 当前版本变更
├── docs/VERSIONS.md                  # 软件/硬件/源码版本
├── RUN_GUIDE.md                      # 原有两种模式详细运行指南
├── scripts/                          # 原有编译、建图、导航、保存、停止入口
├── src/
│   ├── songwei_bringup/               # 机器人集成、配置与点云预处理
│   ├── ranger_ros2/                   # Ranger 官方驱动
│   ├── ugv_sdk/                       # 松灵 SDK 源码
│   ├── livox_ros_driver2/             # Livox ROS 驱动
│   └── nav2_regulated_pure_pursuit_controller/  # 与系统同版的局部修正
├── maps/                             # 已保存地图及 SLAM 数据
├── addons/auto_mapping/               # 可独立删除的自动探索模块
│   ├── COLCON_IGNORE
│   ├── README.md
│   ├── UPSTREAM.txt
│   ├── scripts/
│   ├── src/
│   │   ├── frontier_exploration_ros2/
│   │   └── songwei_auto_mapping/
│   └── tests/
└── logs/                             # 运行时生成，不上传日志内容
```

基础与自动模块的 `build/`、`install/`、`log/` 均由编译生成。Git 忽略这些内容，下载后必须在相应环境编译。

查看当前检出版本：

```bash
git log -1 --oneline
git status --short
```

第三方代码保留原许可证及版权声明；上游地址、固定提交和本地改动说明见 [版本记录](docs/VERSIONS.md)。自动探索包的 **1.6.1**、集成适配包的 **0.1.0** 和机器人项目的 **V2.0** 是不同层次的版本。
