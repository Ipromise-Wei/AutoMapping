# 软件、源码与部署版本

记录日期：2026-10-13。来源为部署主机的 ROS 包清单、Git 提交、已安装 Debian 包与 SDK 头文件。本文件用于重建环境和追溯差异，不表示任意升级组合已经验证。

## 1. 项目自身版本

| 组件 | 版本 | 位置 |
| --- | --- | --- |
| 机器人集成项目 | V2.0 / ROS 包 `2.0.0` | `src/songwei_bringup/package.xml` |
| 独立自动探索适配 | `0.1.0` | `addons/auto_mapping/src/songwei_auto_mapping/package.xml` |

Git 提交号记录本仓库精确内容；包版本用于 ROS 软件包识别，两者用途不同。后续修改应以实际 Git 提交为准。

## 2. 随仓库提供的第三方源码

| 组件 | 上游 | 固定提交 | 包版本/说明 |
| --- | --- | --- | --- |
| Ranger ROS 2 | [agilexrobotics/ranger_ros2](https://github.com/agilexrobotics/ranger_ros2/tree/b6ea21a275ca5e7168130cc6470e61474681d679) | `b6ea21a275ca5e7168130cc6470e61474681d679` | humble 分支快照；ranger_base / ranger_msgs `0.0.1`，ranger_bringup `0.0.0` |
| UGV SDK | [agilexrobotics/ugv_sdk](https://github.com/agilexrobotics/ugv_sdk/tree/f2704eacdc90357078cd93ec60aae08bb4baab35) | `f2704eacdc90357078cd93ec60aae08bb4baab35` | `0.1.6` |
| GoogleTest（UGV 测试依赖） | [google/googletest](https://github.com/google/googletest/tree/b796f7d44681514f58a683a3a71ff17c94edb0c1) | `b796f7d44681514f58a683a3a71ff17c94edb0c1` | 随 UGV 源码提供内容快照 |
| Livox ROS Driver 2 | [Livox-SDK/livox_ros_driver2](https://github.com/Livox-SDK/livox_ros_driver2/tree/21445540f0d100dc86a7e6df312dd70bbdb4afdf) | `21445540f0d100dc86a7e6df312dd70bbdb4afdf` | 驱动头文件 `1.2.8`；ROS package.xml `1.0.0` |
| Nav2 RPP Controller | [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2/tree/a097086719c88f781aa59788eca29ac6ca5e56db/nav2_regulated_pure_pursuit_controller) | `a097086719c88f781aa59788eca29ac6ca5e56db` | `1.1.20`，带下述本地补丁 |
| Frontier Exploration | [mertgulerx/frontier_exploration_ros2](https://github.com/mertgulerx/frontier_exploration_ros2/tree/0d611801cfe152dbd5000cf0b1936783b8977bde) | `0d611801cfe152dbd5000cf0b1936783b8977bde` | `1.6.1`，上游源码未修改 |

本仓库采用源码内容快照，顶层没有 Git submodule 依赖。上游源码目录内原有的 `.gitignore`、`.gitmodules` 等说明文件保留；上游 Git 数据库不上传。

### 本地适配与改动

- `songwei_bringup` 提供实际底盘的启动、话题重映射、点云预处理、地图和导航配置。
- Livox 的 ROS 2 `package.xml` 与 `launch` 目录由 `scripts/build.sh` 从上游 ROS 2 文件生成，不跟踪生成副本。
- RPP 控制器在判断终点转向时使用变换后路径的末端位置，避免前视点在曲线轨迹上造成错误的终点距离判断。保留碰撞检查和角速度限制。详见 [SONGWEI_PATCH.txt](../src/nav2_regulated_pure_pursuit_controller/SONGWEI_PATCH.txt)。
- 自动探索适配放在 `songwei_auto_mapping` 与模块脚本中，不修改上游 Frontier Exploration 算法文件。
- 自动模块局部代价地图使用 `map` 坐标系、规划启发式缓存关闭、Nav2 行为树响应等待配置为 `500 ms`；仅影响该模块自己的配置。

各组件按其源码目录中的许可证分发；本项目保留上游版权头与许可证文件。Nav2 RPP 目录补入与固定提交一致的 Nav2 `LICENSE` 文本。不能用项目版本号替代或覆盖第三方许可证。

## 3. 系统依赖与已部署版本

| 项目 | 已安装版本 |
| --- | --- |
| Ubuntu | `22.04.5 LTS` |
| 架构 | `x86_64` |
| ROS 发行版 | `humble` |
| Git | `2.34.1` |
| CMake | `3.22.1` |
| ros-humble-navigation2 | `1.1.20-1jammy.20260219.051851` |
| ros-humble-nav2-bringup | `1.1.20-1jammy.20260219.053625` |
| ros-humble-slam-toolbox | `2.6.10-1jammy.20260219.051236` |
| ros-humble-rviz2 | `11.2.25-1jammy.20251228.130645` |
| ros-humble-pointcloud-to-laserscan | `2.0.1-3jammy.20260310.174149` |

APT 软件仓库会更新，README 中普通 `apt install` 会安装当时可用版本，并非完整锁定所有传递依赖。版本变化后应重新检查功能兼容性；本次仅记录已部署环境。

### Livox SDK2（系统依赖，不内置）

- 上游：[Livox-SDK/Livox-SDK2](https://github.com/Livox-SDK/Livox-SDK2/tree/6a940156dd7151c3ab6a52442d86bc83613bd11b)。
- 主机源码目录：`/home/hzauaiot/Livox-SDK2`。
- 主机源码提交：`6a940156dd7151c3ab6a52442d86bc83613bd11b`。
- 已安装 `/usr/local/include/livox_lidar_def.h` 版本宏：`1.4.3`。
- 动态库：`/usr/local/lib/liblivox_lidar_sdk_shared.so`。
- 主机 SDK 工作目录的示例 `mid360_config.json` 有现场网络配置改动；项目运行使用自己的 `src/songwei_bringup/config/MID360_config.json`。

源码提交与安装头文件分别核对；本记录不宣称对当前已安装 SDK 二进制做过可重现构建校验。

## 4. 本次快照保留的地图

| 地图名称 | 随仓库提供的文件 | 用途说明 |
| --- | --- | --- |
| `room_401` | YAML / PGM / posegraph / data | 已有场地地图，导航默认名称 |
| `room_401_2` | YAML / PGM / posegraph / data | 另一次场地地图记录 |
| `auto_room_01` | YAML / PGM / posegraph / data | 自动探索生成的地图记录 |
| `validation_initial` | YAML / PGM / posegraph / data | 历史验证记录；保留原有阈值 |

地图随首次提交归档，后续新保存地图由用户决定是否再提交。自动探索地图不保证场地完全覆盖。

## 5. 更新与运行原则

1. 停止对应模式后再编译或切换版本，避免运行进程与磁盘配置不同步。
2. 基础工作区使用 `scripts/build.sh`；自动模块使用自己的 `addons/auto_mapping/scripts/build.sh`。
3. 不在同一终端叠加旧版项目环境；重新打开终端可避免 overlay 混用。
4. 精确回溯使用本仓库 Git 提交，升级第三方组件时同步更新本版本记录和验证结果。
5. 本次上传只整理文档与版本管理，不修改实车运行参数，不重新启动实车程序。
