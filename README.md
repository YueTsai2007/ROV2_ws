# ROV2_ws — 水下航行器仿真工作空间

基于 ROS + Gazebo 的 ROV（遥控水下航行器）仿真与控制系统研发平台。

- **自定义机器人**：`underwater_robot` — 6 推进器、10 连杆的 ROV
- **上游框架**：AGDR_UVMS（基于 [UUV Simulator](https://github.com/uuvsimulator/uuv_simulator)，兼容 ROS Noetic）
- **仿真环境**：Gazebo 水下物理仿真（Fossen 动力学、水流扰动、传感器、机械臂）

---

## 目录结构

```
ROV2_ws/
├── README.md                 # 项目说明
├── .catkin_workspace          # catkin 工作空间标记
├── scripts/                   # 辅助脚本
│   ├── debug_simulation.sh    #   仿真环境调试
│   └── fixed_ned_tf.sh        #   NED 坐标系 TF 修复
├── docs/                      # 文档与参考资料
│   ├── shuoming.txt           #   详细使用说明（控制命令、轨迹规划、扰动、机械臂）
│   ├── velocity.txt           #   速度命令 / 推进器测试备忘
│   ├── frames.gv / frames.pdf #   TF 树可视化
│   ├── underwater_robot.csv   #   机器人数据
│   └── upstream/              #   上游项目原始文档（AGDR_UVMS）
└── src/                       # ROS 包（所有包平级）
    ├── underwater_robot/      # ★ 自定义 ROV 包
    ├── rexrov2/               # RexROV 2 航行器
    ├── joy_teleop/            # 摇杆遥控
    ├── uuv_simulator/         # UUV 模拟器核心（13 个子包）
    ├── uuv_manipulators/      # 水下机械臂（Oberon4/7）
    ├── kdl_parser/            # KDL 运动学解析器 (C++)
    ├── kdl_parser_py/         # KDL Python 绑定
    ├── uuv_simulation_wrapper/# 仿真封装器
    ├── uuv_with_hands_descriptions/
    ├── rexrov_dual_oberon_description/
    ├── oberon4_with_hand_description/
    ├── oberon7_with_hand_description/
    └── teleop_tools_msgs/     # 遥控消息定义
```

---

## 依赖环境

| 组件 | 版本要求 |
|------|---------|
| **ROS** | Noetic（推荐） / Melodic |
| **Gazebo** | 9+ |
| **Python** | 3.6+ |
| **OS** | Ubuntu 20.04（WSL2 可用） |
| **编译工具** | catkin, C++14 编译器 |

### 关键 ROS 依赖

```bash
sudo apt install ros-noetic-joy \
  ros-noetic-robot-state-publisher \
  ros-noetic-joint-state-publisher-gui \
  ros-noetic-rviz \
  ros-noetic-gazebo-ros-pkgs \
  ros-noetic-gazebo-ros-control \
  ros-noetic-ros-control \
  ros-noetic-ros-controllers \
  ros-noetic-tf2-ros \
  ros-noetic-xacro \
  python3-catkin-tools
```

---

## Docker 环境

Docker 镜像包含 Ubuntu 20.04、ROS Noetic、Gazebo、项目依赖和已编译的工作空间。首次构建需要联网下载依赖，可能需要较长时间和较多磁盘空间。

```bash
git clone -b docker https://github.com/YueTsai2007/ROV2_ws.git
cd ROV2_ws
docker build -t rov2:noetic .
docker run --rm -it --network host rov2:noetic
# 容器内已加载 ROS 和工作空间环境
roslaunch underwater_robot headless_underwater.launch
```

需要 Gazebo 或 RViz 图形界面时，Linux 主机须运行 X11（WSL2 需配置 WSLg 或 X server）。例如在支持 X11 的 Linux 主机上：

```bash
xhost +local:root
docker run --rm -it --network host \
  -e DISPLAY -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  rov2:noetic
# 完成后在主机撤销授权
xhost -local:root
```

容器内运行 `roslaunch underwater_robot simple_gazebo_test.launch` 启动图形仿真。若需要 GPU 加速，还需按主机显卡配置 Docker 的 GPU 支持。镜像构建时复制源码；修改源码后需重新执行 `docker build`。ROS Noetic 和 Ubuntu 20.04 已停止标准维护，依赖下载与安全更新受上游支持情况影响。

---

## 构建

```bash
# 进入工作空间
cd ~/ROV2_ws

# 安装 rosdep 依赖（首次构建前）
rosdep install --from-paths src --ignore-src -r -y

# 编译（catkin_make 或 catkin build）
catkin_make
# 或
catkin build

# 加载环境
source devel/setup.bash
```

---

## 快速开始

### 1. 简单测试（自定义 ROV）

```bash
# 基础 Gazebo 测试
roslaunch underwater_robot simple_gazebo_test.launch

# 带 PID 控制器的完整仿真
roslaunch underwater_robot start_uuv_pid_controller.launch

# RViz 可视化
roslaunch underwater_robot display.launch
```

### 2. UUV 仿真（RexROV 2）

```bash
# 启动海洋环境 + 控制器
roslaunch rexrov2_gazebo start_demo_pid_controller.launch

# 螺旋轨迹测试
roslaunch uuv_control_utils start_helical_trajectory.launch \
  uuv_name:=rexrov2 n_turns:=2 radius:=8
```

### 3. 带机械臂的 UVMS 系统

```bash
# 启动海底操作场景
roslaunch uuv_gazebo_worlds subsea_bop_panel.launch

# 加载带双机械臂的机器人
roslaunch uuv_descriptions upload_rexrov_oberon_arms.launch \
  mode:=default x:=0 y:=0 z:=-40 namespace:=rexrov

# 机械臂协同控制
roslaunch oberon7_control uuv_oberon7_cooperate_teleop.launch \
  uuv_name:=rexrov model_name:=rexrov joy_id:=0
```

更多命令参考 **[docs/shuoming.txt](docs/shuoming.txt)**（包含轨迹规划、环境扰动、推进器故障模拟、机械臂控制等完整示例）。

---

## 自定义 ROV 说明

### 配置

| 文件 | 说明 |
|------|------|
| `config/thruster_manager.yaml` | 6 推进器配置（位置、方向、最大推力 200N） |
| `config/TAM.yaml` | 推力分配矩阵（6×6） |
| `config/joints.yaml` | 关节状态控制器 |

### URDF 模型

| 文件 | 用途 |
|------|------|
| `urdf/underwater_robot.urdf` | ★ 核心 URDF 基础模型 |
| `urdf/underwater_robot_complete.xacro` | 完整版（含执行器） |
| `urdf/underwater_robot_uuv2.xacro` | UUV 框架兼容版（当前使用） |
| `urdf/underwater_robot_simple_geometry.urdf` | 简化几何版（快速测试） |
| `urdf/underwater_robot_clean.urdf` | 清洁版（无头仿真用） |
| `urdf/underwater_robot_simple_hydro.xacro` | 简化流体动力学版 |
| `urdf/archive/` | 历史/未使用版本 |

### 启动文件

| 文件 | 用途 |
|------|------|
| `launch/simple_gazebo_test.launch` | 最简 Gazebo 测试 |
| `launch/start_uuv_pid_controller.launch` | 完整 PID 控制 + UUV |
| `launch/final_underwater_sim.launch` | 最终水下仿真 |
| `launch/headless_underwater.launch` | 无头模式（仅 gzserver） |
| `launch/arm_control.launch` | 机械臂独立控制 |
| `launch/underwater_ned_compatible.launch` | NED 坐标系兼容 |

---

## 上游项目

本项目集成了 [AGDR_UVMS](https://github.com/TUSZ-AGDR/agdr_uvms)，是 [UUV Simulator](https://github.com/uuvsimulator/uuv_simulator) 的 ROS Noetic 兼容分支。

- 上游许可证：[docs/upstream/LICENSE.txt](docs/upstream/LICENSE.txt)
- 原始 README：[docs/upstream/agdr_uvms_README.md](docs/upstream/agdr_uvms_README.md)

---

## 许可证

- `underwater_robot/` — BSD（自定义开发）
- 上游包（UUV Simulator 等） — 参见各包的 `package.xml` 及 `docs/upstream/LICENSE.txt`
