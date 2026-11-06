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

## 本轮改进与验证状态

- 修复机械臂外部命令未转发、默认演示覆盖命令，以及缺失关节位置和非有限命令的处理；演示模式可用 `roslaunch underwater_robot arm_control.launch demo:=true` 显式启用。
- 修复模型生成脚本的 Python 3 兼容性、资源路径和失败退出码；补充节点安装配置、消息依赖与机械臂控制器的 `tf_conversions` 运行依赖。
- 修正传感器基础初始化和磁力计更新函数缺少成功返回值的问题；修正海底场景暂停参数，并为基础仿真和 RexROV 演示增加 `gui:=false` 无界面选项。
- 更新分阶段启动说明，忽略构建产物，并加入命令转发、异常输入、模型生成失败等回归测试。

在 ROS Noetic / Gazebo 11 Docker 中，完整 catkin 构建和 7 项回归测试通过；暂停状态下，自定义机器人模型、位姿及六个推进器接口通过检查。RexROV 模型、PID 和推进器分配器已启动，双机械臂模型已生成。螺旋轨迹采样初始化和重复 TF 时间戳问题已修复；容器实测轨迹生成及发布成功，短时重测未出现重复 TF。机械臂依赖安装后协同控制进程已启动，但暂停仿真下控制器等待 TF，完整协同运动和动态控制仍待验证；测试环境没有摇杆和图形界面。详细记录见 [第二轮状态](src/underwater_robot/ROUND2_STATUS.md) 和下方快速开始说明。

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
  ros-noetic-tf-conversions \
  ros-noetic-xacro \
  python3-catkin-tools
```

---

## 准备环境和构建

以下步骤以 **Ubuntu 20.04、ROS Noetic、Gazebo 11** 为例。每个终端都需要加载 ROS 和工作空间环境。三种仿真场景分别启动；切换场景前先停止上一个场景，以免重复启动 Gazebo 和 ROS master。

### 进入已有 Docker 容器

如果 ROS 和 Gazebo 已安装在 Docker 容器中，在**宿主机终端**查看并进入容器：

```bash
docker ps -a
# 将 <容器名> 替换为实际名称；容器已运行时可跳过 docker start
docker start <容器名>
docker exec -it <容器名> bash
```

以下示例假设仓库在容器内的 `/ws`。请先用 `ls /ws/src` 确认；路径不同时，将命令中的 `/ws` 换成实际路径。容器需要挂载工作空间并安装本项目依赖；仅使用基础 ROS 镜像并不保证已经安装 Gazebo 和全部依赖。本次验证使用的容器名为 `rov2-onboarding`，该名称并非所有环境通用。

**本机 Ubuntu** 可跳过 Docker 步骤，将下文 `/ws` 替换为本机仓库路径，例如 `~/ROV2_ws`。如果尚未获取代码：

```bash
git clone -b fix/underwater-robot-round1 https://github.com/YueTsai2007/ROV2_ws.git ~/ROV2_ws
```

### 安装依赖并编译

在容器内或本机工作空间执行。首次使用 `rosdep` 时，请先按 ROS 官方安装说明完成初始化和更新。

```bash
source /opt/ros/noetic/setup.bash
cd /ws
rosdep install --from-paths src --ignore-src -r -y
catkin_make -j2
source /ws/devel/setup.bash
```

如果依赖已经安装，可跳过 `rosdep install`。编译完成后验证包可以找到：

```bash
rospack find underwater_robot
rospack find rexrov2_gazebo
```

**每次新开终端**，都要重新进入同一个容器并加载环境：

```bash
# 宿主机：使用相同容器名再打开一个 shell
docker exec -it <容器名> bash

# 容器内：每个新终端都执行
source /opt/ros/noetic/setup.bash
source /ws/devel/setup.bash
cd /ws
```

本机 Ubuntu 用户只需在每个新终端执行上述两条 `source` 和 `cd`，并替换工作空间路径。

---

## 仿真启动步骤

### 1. 自定义 ROV：基础 Gazebo 测试

此示例使用简化几何模型，适合确认 Gazebo 和机器人模型能加载；它不是带推进器和 PID 的完整水下场景。

**终端 1**：

```bash
# 无图形环境；有可用桌面时去掉 gui:=false
roslaunch underwater_robot simple_gazebo_test.launch gui:=false
```

等待日志出现 `Successfully spawned entity`。保持终端 1 运行，在已加载环境的**终端 2**检查：

```bash
rosnode list
rosservice call /gazebo/get_model_properties "model_name: 'underwater_robot'"
```

返回 `success: True` 表示模型已加载。按终端 1 中的 `Ctrl+C` 停止场景，待进程退出后再运行下一种场景。

### 2. 自定义 ROV：水下场景与控制器

**终端 1：启动场景和机器人。** 默认暂停，且不会启动 PID。无图形环境使用下面的命令；有图形桌面时可改为 `gui:=true`。

```bash
roslaunch underwater_robot bringup.launch gui:=false paused:=true
```

等待模型生成成功，然后在**终端 2**检查模型和接口：

```bash
rosservice call /gazebo/get_model_properties "model_name: 'underwater_robot'"
rostopic list | grep '^/underwater_robot/'
rostopic info /underwater_robot/pose_gt
rostopic info /underwater_robot/thrusters/0/input
rostopic info /underwater_robot/joint_states
```

模型查询应返回 `success: True`；话题信息可用于检查发布者和订阅者。仿真暂停时，传感器消息和 `/clock` 可能不更新，`rostopic echo` 可能一直等待，这不代表话题不存在。

**物理模型验证后**，可在终端 2 恢复或再次暂停仿真：

```bash
rosservice call /gazebo/unpause_physics '{}'
rosservice call /gazebo/pause_physics '{}'
```

恢复后可用 `rostopic echo -n 1 /underwater_robot/pose_gt` 查看一条位姿消息。在另一个已加载环境的终端启动 PID 和推进器分配器：

```bash
roslaunch underwater_robot start_uuv_pid_controller.launch
```

控制器依赖位姿和 TF；暂停状态下可能等待仿真时间或 TF。也可以启动时传 `start_controller:=true`，但这不保证模型、TF 与控制器按就绪顺序启动。**当前自定义模型质量与排水体积不匹配，推进矩阵秩为 5，机械臂限位为零；PID 动态表现未验证。** 动态运行前需校准模型，详见 [第一轮集成状态](src/underwater_robot/ROUND1_STATUS.md)。

可选的 RViz 模型查看命令如下，需要图形桌面：

```bash
roslaunch underwater_robot display.launch
```

`display.launch` 是独立的机器人描述可视化流程；它不是 Gazebo 控制仿真的启动命令。本项目的 GUI/RViz 未在无显示的测试容器中验证。结束时在启动控制器和场景的终端分别按 `Ctrl+C`。

### 3. RexROV 2：水下场景和螺旋轨迹

先停止上一场景。**终端 1**启动海洋环境、RexROV 2、推进器分配器和 PID：

```bash
# 无图形环境；有桌面时可使用 gui:=true
roslaunch rexrov2_gazebo start_demo_pid_controller.launch gui:=false
```

等待模型生成、`ThrusterManager: ready` 和 `PID controller ready!` 等日志。新开并配置好环境的**终端 2**检查：

```bash
rosnode list | grep rexrov2
rostopic list | grep '^/rexrov2/'
rostopic echo -n 1 /rexrov2/pose_gt
```

确认控制器就绪后，在终端 2 发送螺旋轨迹：

```bash
roslaunch uuv_control_utils start_helical_trajectory.launch \
  uuv_name:=rexrov2 n_turns:=2 radius:=8
```

命令退出后，检查终端 1 的轨迹生成日志；也可查看轨迹话题：

```bash
rostopic info /rexrov2/dp_controller/trajectory
rostopic echo -n 1 /rexrov2/dp_controller/trajectory/header
```

轨迹生成与发布已做短时验证；完整轨迹跟踪尚未验收。终端 1 按 `Ctrl+C` 结束整个场景。

### 4. 双机械臂 UVMS：场景、模型和协同控制

先停止上一场景，并在每个新终端加载环境。协同遥控需要安装 `tf_conversions` 并连接摇杆；容器使用摇杆时还需在**创建容器时**将设备映射进去，例如 Docker 的 `--device=/dev/input/js0:/dev/input/js0`。请根据实际设备调整编号。

**终端 1：启动海底场景。**

```bash
roslaunch uuv_gazebo_worlds subsea_bop_panel.launch gui:=false
```

等待 Gazebo 启动并提供 `/gazebo/spawn_urdf_model` 服务。在**终端 2**确认服务并生成模型：

```bash
rosservice list | grep /gazebo/spawn_urdf_model
roslaunch uuv_descriptions upload_rexrov_oberon_arms.launch \
  x:=0 y:=0 z:=-40 namespace:=rexrov
```

等待 `Successfully spawned entity`，保持终端 1 和终端 2 运行。**终端 3：启动协同控制。**

```bash
roslaunch oberon7_control uuv_oberon7_cooperate_teleop.launch \
  uuv_name:=rexrov model_name:=rexrov joy_id:=0
```

在另一个终端检查 `rosnode list | grep /rexrov` 和 `rostopic list | grep /rexrov`。如果提示无法打开 `/dev/input/js0`，请检查摇杆是否存在以及容器设备映射。模型和控制进程已做启动检查，完整摇杆操纵和机械臂运动尚未验证；暂停仿真时控制器可能等待 TF。结束时在终端 3、2、1 依次按 `Ctrl+C`。

更多轨迹、扰动和推进器命令可参考 [docs/shuoming.txt](docs/shuoming.txt)；其中历史命令未逐项验证，启动参数以本 README 和对应 launch 文件为准。

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
| `launch/start_uuv_pid_controller.launch` | PID 控制器及推进器分配器（需先启动场景和机器人） |
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
