Ranger Mini V3 手动建图与保存地图导航 — songwei_V2.0

目标主机：hzauaiot@192.168.123.41
工作目录：/home/hzauaiot/songwei_V2.0
环境：Ubuntu 22.04 / ROS 2 Humble / ROS_DOMAIN_ID=30

使用顺序：已有地图可直接启动导航；新场地先手动建图、保存、停止建图，再启动新地图导航。
建图和导航都自动打开各自的 RViz2 窗口，二者不能同时运行。
以下地图路径均指底盘主机上的文件。

手动建图脚本启动：官方底盘驱动、MID-360 驱动、逐点运动补偿与车身回波过滤、点云转 LaserScan、
SLAM Toolbox、用于显示的 robot_state_publisher、RViz2。

1. 手动建图
在目标主机的终端运行：
  cd /home/hzauaiot/songwei_V2.0
  ./scripts/start_mapping.sh
通过底盘遥控器驾驶，RViz2 的 Fixed Frame=map，显示 /map 和 /scan。
启动脚本会检查已有驱动和导航进程，避免重复占用 CAN 和雷达。
每次 start_mapping.sh 都从空白地图开始，之前保存的地图文件会保留。

2. 可选键盘驾驶
另开终端（SSH 使用 ssh -t）：
  /home/hzauaiot/songwei_V2.0/scripts/keyboard.sh
i 前进，, 后退，j/l 左右旋转，J/L 左右横移，k/空格停止。
平移 0.15 m/s，旋转 0.25 rad/s；0.3 秒无按键输入自动发布零速度。
遥控器驾驶使用遥控模式；键盘驾驶需切换到底盘允许 CAN 控制的模式。

3. 保存地图
  /home/hzauaiot/songwei_V2.0/scripts/save_map.sh room_01
保存 maps/room_01.yaml、.pgm、.posegraph、.data，不覆盖同名地图。
地图采集完成后，保持建图终端运行，在另一个终端执行保存。
确认四个文件均保存成功后，再停止建图：
  /home/hzauaiot/songwei_V2.0/scripts/stop_mapping.sh
然后使用刚保存的地图导航：
  /home/hzauaiot/songwei_V2.0/scripts/start_navigation.sh room_01
保存时先检查建图服务，全部文件生成成功后再移入 maps；已有任何同名地图文件都会拒绝覆盖。

4. 关闭
前台启动时 Ctrl+C，也可在另一终端执行：
  /home/hzauaiot/songwei_V2.0/scripts/stop_mapping.sh
键盘控制终端也应 Ctrl+C。

5. 编译
在只加载 /opt/ros/humble 的终端中：
  cd /home/hzauaiot/songwei_V2.0
  ./scripts/build.sh
无需加载旧 songwei 工作区。

6. 当前配置（沿用旧工程，安装外参仍需实际核对）
CAN：can0，500000 bit/s。
雷达：MID-360，192.168.1.175；主机接收 IP 192.168.1.5。
base_link -> livox_frame：x=0.35、y=0.0、z=0.10 m，旋转均为 0。
配置：src/songwei_bringup/config/robot.yaml、MID360_config.json。
robot.yaml 的高度过滤按旧配置设置，并非本次实测；雷达安装位置变动后需调整。
地图分辨率 0.05 m。有效扫描范围 0.30–12.0 m，后方遮挡区域沿用旧工程屏蔽。
当前采用底盘轮式里程计与二维扫描匹配；运动建图请低速驾驶。
MID-360 的每个点按采集时间与轮式里程计插值，统一变换到该帧末尾的 base_link，
再投影为 /scan。车身范围内及低置信度回波在投影前剔除。
处理后的点云为 /songwei/cloud_deskewed，RViz2 点云显示使用此话题。
缺少完整里程计时间区间时丢弃该帧，不进行无依据的运动外推。

7. 控制 API
官方 ROS 2 驱动接收 geometry_msgs/msg/Twist，线速度 m/s，角速度 rad/s。
此工作区将其输入 /cmd_vel 重映射为 /songwei/cmd_vel。
输出 /odom、/system_state、/motion_state、/actuator_state、/battery_state。
部署和验证仅接收传感器数据，未主动向实际底盘发送非零速度。

8. 官方来源及编译版本
官网开发者中心：https://research.agilex.ai/
Ranger ROS2：https://github.com/agilexrobotics/ranger_ros2 （humble 分支）
  b6ea21a275ca5e7168130cc6470e61474681d679
UGV SDK：https://github.com/agilexrobotics/ugv_sdk （main 分支）
  f2704eacdc90357078cd93ec60aae08bb4baab35
Livox：https://github.com/Livox-SDK/livox_ros_driver2
  21445540f0d100dc86a7e6df312dd70bbdb4afdf

启动日志显示在启动终端；ROS 原始日志位于 ~/.ros/log/。
验证：logs/validation.json（隔离域31）、logs/hardware_validation.json（实际部署域30）。
隔离验证用 scripts/test_live_inputs.py，只转发雷达和里程计，不接触硬件控制；
生产启动不使用它。scripts/check_mapping.py 可检查地图、扫描和 TF。
运动修正验证：logs/deskew_geometry_test.json、logs/deskew_replay_comparison.json。
同一段遥控行驶记录回放中，最大位置修正步长从 0.442 m 降至 0.149 m，
最大角度修正步长从 4.80 度降至 1.60 度；这是该段记录的验证结果，仍需实车复测。

9. 保存地图上的 2D Goal Pose 自动导航
先关闭手动建图及独立的 map_server，再在目标主机执行：
  cd /home/hzauaiot/songwei_V2.0
  ./scripts/start_navigation.sh room_401
不传参数时默认使用 maps/room_401.yaml。也可以直接读取本地主机上其他目录的地图：
  ./scripts/start_navigation.sh /home/hzauaiot/my_maps/room.yaml
或使用相对于当前终端目录的路径：
  ./scripts/start_navigation.sh ./maps/room_401.yaml
路径中有空格时用引号包住完整路径。
必须有 YAML 和其 image 字段指向的图片（通常为 PGM/PNG）；无需 posegraph/data 来执行导航。
相对 image 路径按 YAML 所在目录解析，不能只拷贝 YAML 而遗漏图片。
当前导航轨迹库使用 0.05 m/像素地图、origin 的 yaw 为 0；本工程手动建图默认满足此要求。
启动前会检查 YAML、图片、分辨率、原点和阈值，不符合时给出明确错误并停止启动。
此脚本独立启动硬件、已保存地图、AMCL 定位、Nav2 和导航 RViz2。
导航时由 AMCL 发布 map -> odom，不运行在线 SLAM。

RViz2 操作顺序：
  (1) Fixed Frame 保持 map。
  (2) 点击 2D Pose Estimate，在地图上车的真实位置按下鼠标，拖出真实朝向。
      等雷达扫描与地图墙面基本重合，Navigation 2 面板显示导航已激活。
      每次导航启动后均需此步骤；设置前 AMCL 提示 Please set the initial pose，
      并出现等待 map 坐标变换的日志，这是等待初始化的位置提示。
  (3) 遥控器切换到允许 CAN 控制的模式。
  (4) 点击 2D Goal Pose，在已知可通行区域指定目标，拖动箭头指定终点朝向。
      车辆随后规划、行驶并在目标容差内停车。新目标会替换正在执行的目标。
  (5) Navigation 2 面板的 Cancel 用于取消当前目标。

关闭：启动终端 Ctrl+C，或另一个终端执行 ./scripts/stop_navigation.sh。
该关闭脚本先取消目标并发布零速度，再关闭自身启动的节点。
速度上限为 0.15 m/s、0.30 rad/s，导航不使用横移。
使用 Smac State Lattice（0.5 m 转弯半径、可原地旋转的差速轨迹库）
和 Regulated Pure Pursuit 跟随，覆盖 Ranger 的旋转及双阿克曼模式。
配置：src/songwei_bringup/config/navigation.yaml。
车体占据范围按 0.72 x 0.50 m 设置，并增加每侧 0.05 m padding。
现有雷达投影保留后方遮挡区域，导航只生成前进路径；恢复流程采用清图和等待。

导航校验：logs/navigation_validation.json。
在隔离的 ROS_DOMAIN_ID=31 中，以 room_401 地图和虚拟 Ranger 运动模型验证
2D Goal Pose 话题、AMCL、规划、限速、到达停车、目标朝向、取消停车和障碍目标拒绝。
这些测试未连接真实 CAN；实车效果需按上述流程定位后测试。

流程复查：已修正复用传感器启动文件时 rviz=false 泄漏至导航启动文件的问题。
logs/launch_scope_validation.json 验证两个模式默认各启动一个 RViz，导航模式不启动 SLAM。
logs/map_input_validation.json 验证本地地图名称、相对路径、含空格绝对路径和错误文件检查。
logs/workflow_mapping_validation.json 记录旧雷达数据回放重新建图并保存四个文件的结果。
logs/imported_navigation_validation.json 与 logs/rebuilt_navigation_validation.json 分别记录
本地导入地图、新生成地图的 AMCL 定位、规划、目标导航、终点朝向、取消停车和障碍目标拒绝。

终点转向修正：工作区编译了与系统版本一致的官方
nav2_regulated_pure_pursuit_controller 1.1.20，提交 a097086719c88f781aa59788eca29ac6ca5e56db。
只将到达目标位置的判断从前视点改为路径终点，避免近距离改变朝向时跟随弯曲路径离开目标。
继续使用原有角速度限制和足迹碰撞检查。源码和变更说明位于
src/nav2_regulated_pure_pursuit_controller/，scripts/build.sh 会一并编译。
测试中 RViz2 在收到关闭信号时出现过 exit code -11；窗口打开、地图显示和工具均正常，
退出后无导航或硬件子进程残留。日志中此退出异常发生在测试结束后的关闭阶段。

地图读取阈值：room_401.yaml 的 free_thresh 已从 0.25 修正为 0.196，
使 PGM 的灰色未知区域保持未知，而不是加载成可通行区域。
原 YAML 保存在 logs/navigation_backup/room_401.before_navigation.yaml；
PGM 图像、posegraph 和 data 均保留。save_map.sh 对后续地图使用同样阈值。

Nav2 Humble 官方 API：
https://api.nav2.org/nav2-humble/html/md_nav2_bt_navigator_README.html
https://api.nav2.org/nav2-humble/html/md_nav2_smac_planner_README.html
https://api.nav2.org/nav2-humble/html/md_nav2_regulated_pure_pursuit_controller_README.html
