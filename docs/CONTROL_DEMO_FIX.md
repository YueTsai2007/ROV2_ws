# 控制链修复与演示验证

日期：2026-11-07。修复范围经用户确认；所有动力学参数为演示估算，不能代替实机数据。

## 改动边界和行为

- 修复轨迹控制核心：`dp_controller_base.py` 的配置限幅变量和非有限输出处理；`dp_controller_local_planner.py` 的双重旋转、零速度参考和输入超时；`thruster_allocator.py` 的墙钟超时、无效力指令处理和退出归零。
- `rov_pid_controller.launch` 增加分配器超时参数传递，保留原默认值以兼容现有模型；新演示入口显式设为 0.5 秒。
- 新增独立 `underwater_robot_demo.xacro`，由 `generate_demo_model.py` 生成。用原始 CAD 零位姿的 11 个网格组成机身视觉，机械臂和原始旋转关节在此演示中固定；原始 URDF、STL 和物理模型未修改。
- 统一基座控制坐标：X 向前、Y 向左、Z 向上。原始 CAD 视觉与推进器几何通过同一个 Rx(+90°) 和中心平移转换；演示生成时 roll=0，不叠加旧 CAD 模型的生成旋转。
- 演示主机身质量 25 kg，六个辅助推进器连杆各 0.01 kg，中性浮力，浮心位于重心上方 0.04 m；矩形包络惯量、简化机身碰撞体、阻尼和最大推力均为估算。参数来源在 `config/demo_parameters.yaml`，生成的矩阵和模型可重复生成。
- 新增 `demo_command_guard.py`：独立节点按墙钟检查原始命令新鲜度，在 0.5 秒后输出零；把分配器与 Gazebo 之间的命令分开，限制为每路最多 8 N 对应的命令幅值。进程收到正常退出信号时也归零；强制终止所有监督节点不是经过验证的安全停止方式。
- 新增 `demo_keyboard.py`：W/S 前后，A/D 左右，R/F 上下，Q/E 航向；速度默认 0.1 m/s、航向角速度 0.15 rad/s，键盘无输入 0.2 秒后发零，空格停止，Ctrl-C 退出。
- 新增 `demo.launch`、`demo_pid.launch`、`demo_keyboard.launch`；默认暂停、控制器不自动运行，控制器可以独立启动和停止。原始入口保留供对照。
- 补齐新增脚本的 CMake 安装列表及运行依赖；此前已在容器验证的正放初始化/显示配置也同步进本地修改。

## 验证记录

- 在原 Noetic 容器中运行 `python3 -m unittest discover -s test -v`：14 项通过，包括原有 7 项检查和 7 项控制链回归检查。新检查覆盖坐标旋转及速度一致性、遥控零值/失联、非有限输入、实际初始化限幅、墙钟归零、守护命令限幅与超时、演示几何及矩阵一致性。
- `xacro` 展开成功，`demo.launch gui:=false start_controller:=true` 节点列表解析成功。
- Windows 本地 Python 未安装 PyYAML，未下载依赖；模型生成和测试使用已有容器环境。生成脚本适配了 Noetic 的 Python 3.8。
- 输出隔离运行验证通过：`cmd_vel → PID → 推力分配 → guard` 完整连通，六路真实推进器输入无发布者，实际推力均为 0、位移为 0。随后停止分配器，验证 guard 对超大输入限幅、NaN 输入归零及失联后归零。
- 实际低推力运行验证通过：5 秒静置位移为 0，初始 roll/pitch 为 0；分别输入 0.05 m/s 或 0.05 rad/s 的 2 秒指令，前进位移约 0.02142 m、左移约 0.02067 m、上升约 0.01731 m、航向变化约 0.02568 rad，方向均正确。实际最大推进器推力约 0.4194 N、控制合力/力矩分量峰值约 1.034（力与力矩单位分别为 N、N·m）；未触及 8 N 单路上限。
- 实际运行测试结束后已暂停，六路 guard 命令均为 0。上述短时测试没有验证速度跟踪精度或扰动抑制，不能把输入速度等同于实际速度。
- 真实键盘程序通过 Linux PTY 验证：W 发出 0.1 m/s 前进参考、Q 发出 0.15 rad/s 航向角速度参考，空格和无输入后归零。该项在物理仿真暂停时执行，不产生运动。
- 现有容器工作空间中 `catkin_make --pkg underwater_robot -j2` 通过，新增脚本的 catkin devel 包装器生成成功；没有构建 Docker 镜像或下载依赖。
- 可重复验证脚本为 `test/validate_demo_runtime.py --mode isolated|motion` 与 `test/validate_keyboard_runtime.py`。脚本输出 JSON，以上记录摘自 2026-11-07 的实测输出。2026-11-12 整理提交时 Docker 引擎未运行，原始 JSON 留在容器内，未随此次提交归档。

## 已知限制

矩阵总体秩仍为 5；X/Y/Z/航向目标子空间秩为 4，但任意六自由度独立控制不成立。演示模型冻结机械臂关节；尚不提供机械臂动力学或实机参数验证。RViz 在本机仍需 `GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1` 绕过既有 D3D12 网格绘制问题，这不是 GPU 加速修复。
