# 控制链修复与演示验证

日期：2026-11-07。修复范围经用户确认；所有动力学参数为演示估算，不能代替实机数据。

## 改动边界和行为

- 更新 README 的项目状态与原始模型启动说明，反映 15 项回归、轨迹与双臂测试，并保留原始模型动力学、实物摇杆和 NVIDIA RViz 的待验收状态。

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

## RexROV 2 两圈螺旋轨迹验收（2026-11-12）

### 全工作空间干净构建

本机图形驱动核查：`rov2-fix` 中 Mesa D3D12 驱动来自 `libgl1-mesa-dri` 21.2.6，容器环境设置了 `GALLIUM_DRIVER=d3d12` 和 NVIDIA 适配器。Ubuntu 24.04 已安装 Mesa 25.2.8。两个版本存在差异，但尚未证明升级驱动可解决 RViz 网格绘制问题；本轮没有替换库或下载软件。

进一步检查 Ubuntu 的 `libdril_dri.so`，其版本需求包含 `GLIBC_2.34`，容器的 glibc 版本为 2.31。因此直接将该主机驱动库提供给容器不能满足依赖；尚未验证兼容运行环境中的新版 Mesa 对 RViz 的实际效果。

检查容器已有 Zink 路径，Vulkan ICD 目录为空，只有 Vulkan loader。仅设置 `MESA_LOADER_DRIVER_OVERRIDE=zink` 时离屏探针仍报告 D3D12 NVIDIA，未实际切换；强制 `GALLIUM_DRIVER=zink` 时 GLXContext 创建失败，退出码 1，并提示 core dumped。离屏探针生成了 `/tmp/rviz-offscreen-zink-check-20261112.png`，本轮保留。当前环境没有验证成功的 Zink 硬件路径。

再次核对本机，Windows `nvidia-smi` 显示 GeForce RTX 5060 Laptop GPU、驱动 621.01；容器可见 `/dev/dxg` 和 WSL 的 `libcuda.so.1`，并设置 D3D12 的 NVIDIA 适配器。设备可见性本身不能证明 RViz 网格绘制成功；容器没有已配置的 Vulkan ICD。后续需要兼容容器运行库的替代图形组件或兼容环境，再用画面与渲染器信息实测。

仅查询本地 apt 索引，Focal 的 `libgl1-mesa-dri` 候选版本仍是已安装的 21.2.6；`mesa-vulkan-drivers` 21.2.6 未安装，包大小约 5.8 MB，依赖 glibc ≥2.29。它可用于补齐 Vulkan ICD 的对照实验，现阶段没有证据证明可提供 NVIDIA 硬件 Vulkan 或修复 RViz。没有下载或安装。

构建后核对本地与容器文件：`pause_tf_cache.py`、`demo.launch` 的 SHA-256 一致；`underwater_robot_control.launch` 字节哈希不同，但统一换行后内容一致。该核对只覆盖这三个文件，不能证明两个源码树全部一致。

进一步按 Git 工作区状态枚举 25 个已修改或新增的 `src/` 文件，逐一与容器构建使用的对应文件比较文本，统一换行并忽略末尾换行后全部一致。该检查覆盖当前列出的改动文件，未检查未修改文件及容器额外文件。

在现有 `rov2-fix` 容器中，仅加载 `/opt/ros/noetic/setup.bash`，对容器内源目录 `/opt/rov2-fix-local/src` 执行 `catkin_make -C /tmp/rov2-clean-build.8rHUUo --source /opt/rov2-fix-local/src -j3`。新目录没有旧的构建或 devel 缓存，全量构建到 100%，退出码 0。加载新生成的 `devel/setup.bash` 后，运行 `python3 -m unittest discover -s test -v`，15 项通过。此次复用容器内已安装依赖，构建日志与产物保留在上述目录；从空镜像安装依赖的流程未在本轮验证。

### 海底双臂协同场景

第一次切换场景遇到默认 Gazebo 端口已占用。复测为海底场景单独设置 ROS 11411 和 Gazebo 11412，成功生成 `herkules_seabed`、`bop_panel` 与 `rexrov`。反馈包含 Oberon 4 和 Oberon 7 关节。README 的协同入口启动了 Oberon 7 的六轴及两路夹爪控制器，需要另启 `oberon4_control joint_control.launch uuv_name:=rexrov` 才能操作第二只机械臂，已将该步骤补入 README。

模拟摇杆轴值 0.20 时，两个速度输入均为零，符合默认死区 0.50。轴 4 改为 0.55、按住使能键索引 5 后，载体与 Oberon 7 的 X 速度参考均为 0.165 m/s，两秒内载体位移 0.285 m，Oberon 7 肘部变化 0.181 rad。加载 Oberon 4 控制后，同时发送轴 0 为 0.82、轴 4 为 0.55 的两秒输入，载体位移 0.303 m、Oberon 4 方位角变化 0.260 rad、Oberon 7 肘部变化 0.225 rad。随后短时发送开夹爪按钮，Oberon 7 左指变化 0.863 rad。结束发送零输入并暂停。容器无 `/dev/input/js0`，实物摇杆、接触抓取与海底面板操作尚待验收。

### 推进器故障与传感器抽测

在暂停场景退出 PID 和分配器，确认没有其他推进器指令发布者。仅向 0 号推进器发送固定输入 30，其余七路为零。输出效率依次为 100%、50%、0%、100%，实测稳态推力中值分别为 23.892、11.946、0、23.892 N。四阶段比值与恢复通过，结束恢复原效率、发送零指令并暂停。该测试覆盖单路效率故障注入，闭环容错与多路故障仍待验收。

在同一运行中收到 IMU 614 帧、DVL 86 帧、磁力计 6124 帧、压力 123 帧和三路摄像头各 219 帧。IMU 四元数范数约 1，DVL 有四束量程；三路 `rgb8` 图像均为 768×492，数据长度与 CameraInfo 一致。尚未比对 DVL 真值、相机画面质量和噪声模型。

发现 ROS 单位错误。磁力计插件直接发布内部 µT 数值到要求 T 的 `MagneticField`，实测向量约 `[3.37, 32.55, -56.16]`。压力插件直接发布内部 kPa 数值到要求 Pa 的 `FluidPressure`，实测约 320.91。修复应只在 ROS 发布边界换算数值与方差，保持原有 Xacro 参数和 Gazebo 内部约定。两处插件源码修改尚待确认边界。

用户确认源码修改范围后，磁力计 ROS 输出乘以 1e-6、协方差乘以 1e-12，压力 ROS 输出乘以 1e3、方差乘以 1e6。Gazebo 内部值未改，编译和实时输出复测结果如下。

两处源码已复制到 `rov2-fix`，执行 `catkin_make --pkg uuv_sensor_ros_plugins -j3` 成功，磁力计和压力插件均重新链接。

在独立 ROS 11471 / Gazebo 11472 重启 RexROV 2 场景，实测磁场为 `[-3.2468e-5, -1.69e-10, -5.6310e-5]` T，协方差对角为 `[1e-12, 1e-12, 1.96e-12]` T²；压力为 338049.98 Pa，方差为 9000000 Pa²。数值量级及方差换算符合当前配置，测试后暂停并关闭独立场景。不同运行的深度和朝向有变化，不能将两次测量逐值比较。

再次核查噪声实现发现，压力噪声的实际标准差为 `noise_sigma * noise_amplitude`，此前 ROS 方差换算遗漏了幅值因子。现将 ROS 方差改为 `(noise_sigma * noise_amplitude * 1000)^2`，需重新编译并以非单位幅值复测；此前方差实测不能验证此因子。

压力插件重新编译成功。在独立 ROS 11681 / Gazebo 11682 的最小模型中设置 sigma=2、amplitude=0.5，模型生成服务返回成功，但 gzserver 随后报 `undefined symbol: sensor_msgs::msgs::Pressure::Pressure()` 并退出，未收到压力消息。插件中该 protobuf 构造函数为未解析符号；先前 RexROV 场景能够运行，可能存在插件加载顺序依赖，尚需确认。非单位幅值验证未通过，不能据此宣称运行验收完成。

`nm` 确认缺失构造函数由现有 `libuuv_sensor_gazebo_msgs.so` 定义，压力插件的动态依赖列表没有该库。`CMakeLists.txt` 为压力插件声明了构建依赖，却没有链接该库。使用 `LD_PRELOAD` 预加载现有库，在独立 ROS 11691 / Gazebo 11692 重复同一测试，收到压力 110400.92 Pa、方差 1000000 Pa²，与 `(2 × 0.5 × 1000)^2` 一致。测试结束暂停。预加载验证了方差与缺失库的关系，正式链接修复仍需修改该包 CMakeLists.txt。

经用户确认，修改该包 `CMakeLists.txt`。检查发现 DVL、IMU、磁力计、RPT 与压力五个插件均有同一消息库未解析符号且动态依赖缺失，现为五个目标显式链接 `uuv_sensor_gazebo_msgs`，待重新编译与独立加载验证。

`catkin_make --pkg uuv_sensor_ros_plugins -j3` 成功，`readelf` 确认五个插件均包含消息库动态依赖。在不设置 `LD_PRELOAD` 的独立 ROS 11701 / Gazebo 11702 场景生成压力探针，sigma=2、amplitude=0.5 时输出 111693.96 Pa，方差 1000000 Pa²，符合预期且 gzserver 未发生缺符号退出。结束后暂停并停止测试。其余四个插件已验证动态链接，尚未逐个独立加载复测。

重新链接后在独立 ROS 11711 / Gazebo 11712 启动 RexROV 2，分别收到压力、磁力计、IMU、DVL 消息，时间戳约为 1.60–1.66 秒；日志未发现缺失符号错误。测试结束暂停并停止 Gazebo 和控制节点。此项为联合场景发布检查，RPT 尚未独立加载验证。

在未预加载消息库的独立 ROS 11721 / Gazebo 11722 场景单独生成 RPT 探针，Python `wait_for_message` 已收到 `PositionWithCovarianceStamped`，Gazebo 日志未见缺失符号。测试打印脚本误用 `position` 字段而报 `AttributeError`，后续命令未加载工作空间环境导致 `rostopic echo` 找不到自定义消息类。因此本次确认独立加载和消息到达，数值正确性未验收；测试结束已暂停并停止 Gazebo。

更换独立 ROS 11731 / Gazebo 11732 后，按正确字段 `pos.pos` 读取无噪声探针。RPT 与 Gazebo 的 X、Y 均为 1、2 m；RPT Z 为 0.96825 m（时间 11.891 s），Gazebo Z 为 0.94952 m（时间 11.912 s）。探针处于自由落体，两项非同时采样，Z 差值不能作为误差验收；水平位置检查通过。测试后暂停并停止 Gazebo。

在独立 ROS 11741 / Gazebo 11742 使用静止、无噪声 RPT 探针，RPT 与 Gazebo 的三维位置均为 `(1, 2, 3)` m，协方差矩阵全零，三轴误差小于 1e-6 m。验证静态零噪声数值通过，动态时序及噪声统计仍未验证。测试后暂停并停止 Gazebo。

检查 `RPTROSPlugin.cc` 发现其位置噪声使用 `GetGaussianNoise(noiseAmp)`，实际标准差为 `noiseSigma * noiseAmp`，但 ROS 与 Gazebo 消息的协方差均只使用 `noiseSigma²`。当幅值不为 1 时，报告的协方差与生成噪声不一致。此插件源码尚未获得修改范围确认。

同一模式也出现在 `DVLROSPlugin.cc` 与 `PoseGTROSPlugin.cc`：生成噪声使用 `noiseAmp`，但消息方差使用 `noiseSigma²`。这两处需要按各自输出量和坐标转换检查后修复并实测；当前尚未修改其源码。

经用户确认，RPT 和 DVL 的 ROS/Gazebo 协方差均改为 `(noiseSigma * noiseAmp)^2`。位姿插件仅对线速度与角速度加噪，ENU/NED 里程计的速度协方差改为该实际方差，位姿协方差设为零以匹配未加噪的位姿。修改待编译及非单位幅值实测。

Docker 恢复后，原编译日志止于 85%，容器已退出，未有完成记录。重新以 `-j1` 编译传感器包成功。编译报告 RPT `OnUpdate` 非 void 函数缺少成功返回值，已补充 `return true`，该后续修改需重新编译与运行验证。

补充返回值后再次执行单线程传感器包编译，构建到 100%、退出码 0。非单位幅值下的运行验证仍待完成。

按 README 以 `gui:=false` 启动 RexROV 2，再执行 `start_helical_trajectory.launch uuv_name:=rexrov2 n_turns:=2 radius:=8`。记录 `/rexrov2/pose_gt`、控制参考及 `/rexrov2/trajectory_tracking_on`。跟踪标志从真切换为假，采得 2996 组位姿与最近参考，覆盖 149.75 秒仿真时间。实际角度累计 2.028 圈，参考为 2.026 圈，参考半径在 8 m 附近的样本对应实际平均半径 8.001 m。实际深度约 24.99–30.11 m。位置 RMSE 为 0.187 m，峰值误差 1.357 m，结束后三秒采样的实际位置与参考相差约 0.027 m。误差基于最近到达的参考消息，未做时间插值。采集结束已暂停仿真。该试验覆盖 README 的默认两圈配置。

后续审查修复了连续零速度覆盖定点目标的问题。定点目标在遥控从有输入变为零输入时捕获一次，后续零速度消息保留该目标。新增回归用例模拟停键后位姿漂移，Noetic 容器内 15 项测试通过。水流测试结果见下文。

`headless_underwater.launch` 已改为复用演示入口并关闭 GUI。Gazebo 实际生成了位于 `[0, 0, -3]` 的正放模型，启动状态为暂停，未启动 `gzclient`。

水流验收第一次调用世界水流服务成功，但 0.20 m/s 水流下实测位移为零，因此该次结果不能用于证明抗扰。检查水动力插件发现它仅在模型声明 `flow_velocity_topic` 时订阅世界水流。已在演示模型生成器与生成的 Xacro 中补上 `hydrodynamics/current_velocity`，重新生成模型后的复测结果如下。

重新启动模型后的水流复测通过。持续发布零速度，施加 X 向 0.20 m/s 水流约 5 秒，实测偏离目标 0.4481 m，参考位置漂移为 0。撤除水流约 12 秒后，位置误差降为 0.0111 m，满足本轮设定的 0.03 m 及受扰误差 40% 两项恢复阈值。测试结束后恢复零水流并暂停仿真。该结果覆盖单方向短时水流与撤流恢复；持续水流测试见下文。

旧 `underwater_robot_control.launch` 原来引用缺失的级联分配配置，现复用已启动演示模型的 PID 配置。摇杆改为可选入口 `joy_on:=true`，默认启用按钮索引 4，速度参考限制为 0.1 m/s，航向参考为 0.15 rad/s。默认和摇杆两种配置均通过 `roslaunch --nodes`，实物摇杆仍需设备接入后验收。README 已更正旧无头入口和历史 `.urdf` 文件的说明。容器复测 15 项回归通过。

矩阵总体秩仍为 5；X/Y/Z/航向目标子空间秩为 4，但任意六自由度独立控制不成立。演示模型冻结机械臂关节；尚不提供机械臂动力学或实机参数验证。RViz 在本机仍需 `GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1` 绕过既有 D3D12 网格绘制问题，这不是 GPU 加速修复。

### 演示模型持续水流

临时增益对照：新启动演示 PID，通过 `set_pid_params` 将 X 轴 Ki 设为 3，其余轴 Ki 保持 0。沿 X 施加 0.20 m/s 水流 24 秒，最大正向偏移 0.3955 m，末值 −0.0670 m。撤流后反向超调 0.4383 m，12 秒时仍偏 −0.1254 m。六路实测峰值 3.5652 N，低于每路 8 N 上限。试验显示积分改善受扰时的偏差，但此增益的撤流恢复表现不宜作为默认配置。保留原默认参数。采样结束后 Bash 将管道末尾 CR 当成命令并返回非零，退出清理仍执行了撤流、暂停和停止 PID。

另在同一隔离场景复测持续水流。起点为 `(0, 0, -3)` m，启动演示 PID 后施加 X 向 0.20 m/s 水流约 24 秒，最后三次位置误差为 0.6267、0.6350、0.6381 m。撤流后约 8.7 秒，误差降至 0.0466 m。该次运行量化了当前演示控制器在持续水流下的残余偏差，尚未实现持续水流下的精确定点。采样全部输出后，PowerShell 管道的脚本结束标记被 Python 误读，返回非零；清理仍执行，将水流恢复为零并暂停物理。

`demo_pid.launch` 当前六轴 Ki 均为 0，控制器只能以持续位置误差抵消恒定水流。`dp_pid_controller_base.py` 每步累积误差，输出饱和时没有冻结或回算积分；在线设置增益也不会清空已累计的误差。若进行非零 Ki 对照试验，应使用新启动的控制器，并同时记录六路推力、饱和及撤流后的超调。本轮仅确认控制律与配置，默认增益未改。

### 演示模型冷启动暂停 TF

`demo.launch` 启用 `pause_tf_cache.py`。当仿真从暂停状态启动且还没有动态 TF 时，节点从 Gazebo 查询基座世界位姿及非固定关节的相对位姿，通过锁存的 `/tf` 提供初始变换。恢复仿真后退出该发布路径，由运行中的 TF 发布者更新。

在独立 ROS 11421 和 Gazebo 11422 上实测，仿真时钟为零时，`tf2` 成功查询世界到基座（Z = −3 m）和六个推进器的变换。恢复后读到非零时间戳，再次暂停后新建监听器仍能读到上述变换。重新暂停时观察到 `base_link_ned` 重复时间戳警告。已有监听器跨暂停切换尚待验收。

原始模型在独立 ROS 11431 和 Gazebo 11432 上复测。监听器按墙钟等待两秒后，仿真时钟仍为 0，世界到基座的平移为 `(0, 0, -5)` m。读取 URDF 中全部 13 个非固定关节的子坐标系，逐个查询到世界的变换，全部成功。全程未解除暂停或发送运动命令。

### 原 README 的旧启动入口

在独立 ROS 11461 / Gazebo 11462 实跑 `underwater_ned_compatible.launch`。模型生成进程正常退出，Gazebo 模型查询返回成功。关节控制验收失败：查询到的 `controller_manager` 服务数量为 0，spawner 明确报告找不到接口；旧 `--shutdown-timeout` 参数也已失效。旧入口直接加载的 `underwater_robot.urdf` 未声明 `gazebo_ros_control` 或关节传动，单改 spawner 超时无法恢复关节控制。本轮查询后暂停并正常关闭隔离测试。Gazebo 与 RViz 进程注册成功，未检查窗口画面或坐标转换精度。

在独立原始模型（ROS 11431）中启动 `arm_control.launch`，保持时钟为 0。测试订阅器收到由 `/arm_control/command` 转发到 `/underwater_robot/arm1_joint_position_controller/command` 的 0.125 rad 指令，转发通过。源码检查发现原始 `arm1` 的上下限、力矩与速度均为零，包内也未定义匹配该输出话题的位置控制器；旧 NED 入口仅尝试启动关节状态控制器。本轮未解除暂停，未验收关节运动。需要明确演示关节限位及原始 URDF 的可修改范围后，才能补齐执行链。

经用户确认，原始 URDF 中为 `arm1` 设置估算范围 ±1 rad、最大力矩 5 N·m、速度 0.5 rad/s，添加 effort 传动与 Gazebo ROS 控制插件。旧 NED 入口配置命名空间内的关节状态控制器与位置控制器，初始 PID 为 P=5、I=0、D=0.5。以上均为仿真估算，控制器加载和关节实际运动待复测。

独立 ROS 11611 / Gazebo 11612 力矩核查中，先后发送 +1、−1 rad，采集 698 组关节反馈与最近控制器状态。控制器状态的命令峰值为 8.566 N·m，`/underwater_robot/joint_states` 中 arm1 的 effort 绝对值峰值为 0.156 N·m，控制器命令峰值附近 effort 反馈为 0。两种消息采样不同步，且该反馈尚未证实能代表施加到 Gazebo 关节的力矩，不能据此断定 5 N·m 限幅是否生效。已安装的 `gazebo_ros_control` 接口头文件包含 effort 饱和接口，但仅凭接口声明不能证明该测试路径已正确注册和执行限幅。结束时暂停并关闭本次独立节点；需要进一步观测限幅后命令或实际关节力矩。

随后在独立 ROS 11631 / Gazebo 11632 进行动力学对照。临时测试模型使用固定基座、垂直转轴、1 kg·m² 转动惯量、零阻尼和相同的 `gazebo_ros_control` effort 接口与 5 N·m URDF 限值。直接发送 2、10、−10 N·m 命令，分别由 100 帧关节速度计算角加速度，结果为 2.000、5.000、−5.000 rad/s²。该结果证明当前插件对这个探测模型的正反方向命令执行 5 N·m 饱和，尚未直接测到原始 arm1 的实际施力。首次探测模型因无惯量基座被合并而加载失败，修正后完成测试；结束已暂停并停止独立 Gazebo。

曾将该 URDF 的行尾统一为 LF，但导致整份原 CRLF 文件出现无关差异。现恢复 CRLF，只保留一处原有行尾空格清理和机械臂实质改动；使用 `core.whitespace=cr-at-eol` 检查通过，URDF 差异为新增 21 行、删除 5 行。

安装的 `joint_limits_interface` 头文件中，`EffortJointSaturationHandle` 会按 `max_effort` 裁剪命令，超出位置或速度边界时进一步限制方向；`DefaultRobotHWSim` 头文件声明了该饱和接口。头文件本身不能证明本次运行中限幅句柄已注册并执行，实际施力峰值仍待验证。

容器中用 `urdf_parser_py` 解析当前原始模型，`arm1` 的 effort、lower、upper、velocity 分别为 5.0、−1.0、1.0、0.5，且能识别 `arm1_transmission`。解析器提示不认识 actuator 内的 `hardwareInterface` 标签；此前 Gazebo 已成功加载 effort 控制器。该检查仅确认 URDF 解析，并不证明限幅执行。

最新 TF 代码同步到容器后重新运行 `underwater_robot` 的 15 项 Python 回归，全部通过。该测试不覆盖真实推进器运动或机械臂力矩限幅。

最新 TF 修复后，在独立 ROS 11651 / Gazebo 11652 运行 `validate_demo_runtime.py --mode motion`，结果 PASS。静置 5 秒位移为零，前、左、上位移分别为 0.02176、0.02214、0.02377 m，航向变化 0.02367 rad，方向均正确；六路实际推力峰值最大 0.4206 N。测试末六路命令为零，确认物理暂停后关闭相关节点。该项是短时低推力回归，不代表实机标定或完整六自由度控制。

独立 ROS 11671 / Gazebo 11672 将守护节点输出重定向至 `control_audit/thrusters` 后运行 `validate_demo_runtime.py --mode isolated`，结果 PASS。模型位移和六路实际推力均为零，异常数值、限幅及超时归零检查通过，结束时六路输出均为零；确认暂停后关闭相关节点。

独立 ROS 11511 / Gazebo 11512 场景中，关节状态控制器和 `arm1_joint_position_controller` 均为 running，后者声明了 arm1 的 effort 接口。向位置控制器发送 0.2 rad，约 3 秒后反馈 0.20452 rad、误差 −0.00452 rad。测试后物理已暂停，关节限位、反向运动、通过 `arm_control.launch` 的端到端运动和接触任务仍待验收。

在独立 ROS 11551 / Gazebo 11552 同时启动旧 NED 场景及 `arm_control.launch`，向 `/arm_control/command` 连续发送每项 7 秒的指令。输入 0.2、−0.2、1.3、−1.3 rad 时，控制器目标依次为 0.2、−0.2、1.0、−1.0 rad，末次实际角度分别为 0.20454、−0.19539、0.99995、−0.99709 rad。角度实测极值为 1.00025 和 −0.99793 rad；控制器状态报告的负向越限阶段命令峰值为 8.61 N·m，高于 URDF 所设 5 N·m，需要进一步核实 Gazebo 最终施加的 effort 限制。试验发送零指令后暂停并关闭独立节点；抓取、真实硬件参数和长时间稳定性未验证。

先前在 11531/11532 的测试与并行浮力测试误用了同一端口，结果不作为验收依据。负向限位重试期间控制器列表为空，最终以独立 11551/11552 的完整复测为准。

暂停启动的控制器还存在 TF 等待风险。`vehicle.py` 和 `dp_controller_local_planner.py` 在订阅里程计前，查询 `world` 到 `world_ned` 并设置 10 秒 ROS 时间超时；分配器的 `thruster_manager.py` 也使用带超时的 TF 查询。容器内 Noetic 的 `tf2_ros.Buffer` 用 `rospy.Time.now()` 和 `rospy.sleep()` 实现此等待。仿真时钟为零时，若首次查询早于 TF 回调，等待可能停在第一次睡眠。该机制与前次暂停启动未就绪的表现一致，仍需修复后复跑验证。

三个初始化查询现改为无 ROS 时间等待的查询，使用单调墙钟分别限制 10、10、1 秒，超时后沿用各自原有异常处理。暂停启动和正常运行均需复测。

修复同步至容器后，在原始模型的独立 ROS 11431、物理暂停状态启动旧 PID，等待 15 秒。PID 已订阅 `/underwater_robot/pose_gt`，分配器已发布 `/underwater_robot/thrusters/0/input`，Gazebo 已订阅该输入。测试结束控制器退出，另行确认场景仍暂停。正常运行和动态闭环仍待验证；本次 shell 因末尾换行字符返回非零，以上节点及话题状态已独立观察。

在已暂停的原始模型（ROS 11431）上实跑 `start_uuv_pid_controller.launch`，PID 与分配器节点均注册。启动后约 5 秒，`pose_gt` 已有 Gazebo 发布者，PID 尚未注册订阅，推进器输入首次查询也未就绪；停止本次控制器后重新枚举，Gazebo 的六路输入及推力反馈话题均已出现。结果仅确认进程与模型接口存在，控制器就绪和闭环未通过本次检查。测试保持暂停，未发送运动指令。

下沉原因已定位到 `underwater_robot_complete.urdf`：浮力体积、阻尼和浮心直接写在插件根下，缺少 `UnderwaterObjectPlugin.cc` 用来注册水动力对象的 `<link name="base_link">`，所以旧模型的体积配置没有作用。按该文件的 21.961 kg 和 1028 kg/m³ 计算，中性浮力估算排水体积为 0.02136 m³，历史设置的 0.05 m³ 即使生效也会造成上浮。修复应补齐插件配置并用仿真静置测试验证，原始模型文件的修改边界尚待确认。

经确认后已为 `base_link` 添加水动力配置，排水体积按现有质量和水密度估算为 0.021363 m³，浮心暂取现有重心，阻尼取演示估算值。静置表现尚待实测，参数需实机数据校准。

独立 ROS 11481 / Gazebo 11482 实测约 5.038 秒，Z 为 −4.9582 m，Z 向速度为 0.000146 m/s，下沉得到抑制。但姿态四元数约 `(0.7058, 0.0272, 0.0144, 0.7077)`，发生约 90° 横滚，未通过正放静置验收。测试后暂停并关闭，需继续分析姿态和碰撞影响。

场景文件检查显示海床碰撞面位于 Z = −100 m，模型生成点为 −5 m，海床不能解释生成后立即横滚。水动力代码把浮力作用在配置的相对浮心，模型当前浮心与重心重合，因而没有主动恢复横滚的静浮力力矩。横滚的初始触发仍需测量，不能仅凭这一点断言其原因。

进一步核查 Gazebo `AddForceAtRelativePosition` 的位置以质心为原点，之前错误填入 URDF 的重心坐标，造成约 0.215 m 侧向力臂。现修正为相对质心上方 0.04 m 的估算值，待复测。同步修正 TF 超时回退的 ENU/NED 旋转，使其与项目静态发布器一致，并修正推进器管理器根命名空间错误截去坐标系首字符的问题。三项改动均待运行验收。

独立 ROS 11501 / Gazebo 11502 复测完整模型，仿真时间 3.53 秒时位置仍为 `(0, 0, -5)` m、姿态为单位四元数、线速度和角速度均为零。测试后暂停并关闭。该结果覆盖无扰动静置，受扰姿态恢复尚待测。

独立 ROS 11531 / Gazebo 11532 将模型姿态设置为横滚 0.2 rad 后恢复仿真，随后测得横滚依次为 0.00890、0.000316、0.0000126、0.00000044 rad，深度保持约 −5 m。采样结束已暂停。该测试覆盖单次初始姿态扰动，浮心和阻尼仍为演示估算。

事后发现机械臂测试同时使用了 11531/11532，存在节点重名替换。本次恢复数据因此只能作为初步观察，需在独占端口重测。

更换独占 ROS 11561 / Gazebo 11562 重测，设置横滚 0.2 rad 后，每隔约三秒实测 0.00892、0.000316、0.0000111、0.000000389 rad，最终 Z = −5.00015 m。采样结束暂停物理。独占复测确认该演示配置对单次横滚扰动有恢复作用。

对实际 `Vehicle` 和 `DPControllerLocalPlanner` 初始化注入 TF 缺失，回退矩阵均与项目静态变换一致；对 `ThrusterManager` 注入根命名空间，查询目标为 `base_link`、源为 `base_link_ned`。这些是隔离测试，动态控制尚需复验。

在独立 ROS 11451 / Gazebo 11452 上运行 `final_underwater_sim.launch`。模型生成进程正常退出，`/gazebo/get_model_state final_underwater_robot world` 返回 `success: True`。仿真时钟 0.460 秒时，模型从初始 Z = −5 m 下沉到 −5.124 m，Z 向速度为 −1.548 m/s，姿态四元数仍为单位旋转。日志报告 KDL 根连杆惯量警告。该入口的模型生成通过，浮力和平衡未通过静置要求。查询后暂停并通过 SIGINT 停止独立测试。

在独立 ROS 11441 / Gazebo 11442 上运行 `simple_gazebo_test.launch gui:=false`。模型生成进程正常退出，`/gazebo/get_model_state underwater_robot world` 返回 `success: True`，仿真时钟已推进到 1.118 秒。该入口从 Z = 1 m 投放简化模型，查询时 Z = 0.268 m；验收覆盖无界面生成和物理推进。测试结束后通过 SIGINT 正常关闭该测试的节点。

在 `rov2-fix` 的 Noetic 环境中，对 `simple_gazebo_test`、`start_uuv_pid_controller`、`final_underwater_sim`、`arm_control` 和 `underwater_ned_compatible` 分别运行 `roslaunch --nodes` 与 `roslaunch --dump-params`，五组节点列表和参数均解析成功。`arm_control_node.py` 在容器内存在且可执行。`start_uuv_pid_controller` 默认只启动推进器分配器和 PID 节点，完整运行需另有模型、位姿与推进器接口。各入口的运行检查和剩余问题见本节上方。

## 全工作区静态代码排查与批量修复（2026-11-13）

日期：2026-11-13。本轮对工作区（重点 `src/underwater_robot`）进行全量静态排查后，按模块边界执行定点修复；按 `ROUND1_STATUS.md` 约定保留 `underwater_robot.urdf`、`underwater_robot_uuv2.xacro` 与 `TAM.yaml` 的原始 CAD 质量/坐标系基线以待实机数据，未删除任何历史或归档文件。

### 改动边界和行为

- **Launch 与配置修复（`src/underwater_robot`）**：
  - `launch/spawn_underwater.launch`：移除闭合标签 `</launch>s` 末尾多余的 `s`；将 `robot_description` 移至全局 `<param>`，并将 `spawn_model` 的 `-stdin` 改为 `-param robot_description`。
  - `launch/simple_underwater.launch`：将 `robot_description` 移至全局 `<param>`，并将 `spawn_model` 的 `-stdin` 改为 `-param robot_description`，确保 `robot_state_publisher` 与 `spawn_model` 均可读取。
  - `launch/test_encoded.launch`：将不存在的 `urdf/test_simple.xacro`（`xacro` 命令）修正为 `cat '$(find underwater_robot)/urdf/test_simple.urdf'`。
  - `launch/underwater_with_gui.launch`：将不存在的 `config/underwater.rviz` 修正为 `config/standard_ros.rviz`。
  - `launch/clean_underwater.launch`：将误指为 `<launch>` 文件的 `urdf/underwater_robot_clean.urdf` 改为 `urdf/underwater_robot.urdf`。
  - `config/joint_names_underwater_robot.yaml`：移除首元素空字符串 `''` 与末尾多余逗号。

- **运行时脚本、构建与测试修复（`src/underwater_robot`）**：
  - `scripts/demo_keyboard.py`：新增 `_drain_escape_sequence()` 与 `\x1b` 检测，过滤方向键等 ANSI 转义序列以免误触发 `a`/`d` 横向推力；新增 `safe_stop()` 捕获 `rospy.ROSException` 并采用嵌套 `try/finally`，确保退出时始终恢复 `termios.tcsetattr`。
  - `scripts/demo_command_guard.py`：将 `time.monotonic()` 默认采样移入 `CommandBuffer.lock` 保护区内（`accept()` 与 `values()`），消除跨线程时钟竞态导致的有效指令误归零；`stop()` 中捕获 `rospy.ROSException`。
  - `scripts/pause_tf_cache.py`：复用持久化 latched `/tf` 发布器，首次发布前最多等待 0.2 s 订阅者连接，并在 `/clock` 暂停（`to_nsec() == 0`）时保护原始时间戳不被 `Time(0)` 覆盖。
  - `scripts/arm_control_node.py`：移除未使用变量 `current_angle`；将启动阶段阻塞仿真时间的 `rospy.sleep(2.0)` 移入 `if rospy.get_param('~demo', False):` 分支，避免 `paused:=true` 时阻塞 `rospy.spin()`。
  - `scripts/publish_default_joint_states.py`、`set_clean_urdf.py`、`spawn_fixed.py`：补全 `# -*- coding: utf-8 -*-` 编码声明、显式使用 `encoding='utf-8'` 打开文件；`set_clean_urdf.py` 在异常分支返回退出码 `1`。
  - `CMakeLists.txt` 与 `package.xml`：补充 `if(CATKIN_ENABLE_TESTING)` / `catkin_add_nosetests(test)` 测试注册及 `<exec_depend>tf2_msgs</exec_depend>` 直接运行依赖。
  - `test/test_runtime_scripts.py`：新增 `test_demo_keyboard_filters_ansi_escape_and_restores_terminal` 与 `test_demo_command_guard_monotonic_ordering_and_safe_stop` 两项回归用例。
  - `test/validate_demo_runtime.py`：新增 `_check()` 显式抛出 `RuntimeError` 替代裸 `assert`。

- **URDF / Xacro 宏与水动力插件 Schema 修复（`src/underwater_robot/urdf/`）**：
  - `urdf/underwater_robot_actuators.xacro`：引入 `common.urdf.xacro` 与 `uuv_gazebo_ros_plugins/urdf/thruster_snippets.xacro`，将未定义的 `thruster_macro` 替换为 `thruster_module_first_order_basic_fcn_macro`（推进器 `0`–`3`）。
  - `urdf/underwater_robot_complete.xacro`：引入 `thruster_snippets.xacro`；将 `libuuv_underwater_object_ros_plugin.so` 水动力参数包裹进 `<link name="base_link">`，`added_mass`、`linear_damping` 与 `linear_damping_forward_speed` 改为空格分隔向量字符串。
  - `urdf/underwater_robot_simple_hydro.xacro`：将 `libuuv_underwater_object_ros_plugin.so` 水动力参数包裹进 `<link name="base_link">`。

- **工作区跨包与关联源码修复**：
  - `scripts/fixed_ned_tf.sh`：移除 `killall static_transform_publisher` 与 `tf2_ros static_transform_publisher` 无效的第 9 个周期参数 `100`，将 NED-ENU 旋转改为与项目一致的 `1.5707963267948966 0 3.141592653589793`，并为子坐标系补全 `underwater_robot/` 命名空间前缀。
  - `src/uuv_manipulators/uuv_manipulators_kinematics/src/uuv_manipulator_interfaces/arm.py:167`：将 Python 2 `xrange(self.n_links)` 改为 `range(self.n_links)`。
  - `src/uuv_manipulators/uuv_manipulators_control/CMakeLists.txt`：在 `catkin_install_python` 中补装 `scripts/yt_cartesian_position_controllers.py` 与 `scripts/key_publisher.py`。
  - `src/uuv_manipulators/oberon7/oberon7_control/launch/yt_cartesian_position_controller.launch:19`：将硬编码 `ns="/rexrov/oberon7"` 参数化为 `ns="$(arg uuv_name)/$(arg arm_name)"`。
  - `src/uuv_simulator/uuv_control/uuv_thruster_manager/scripts/thruster_allocator.py:180-181`：当 `msg.header.frame_id` 为空字符串时映射为 `None`，避免 `accept_wrench` 误拒并触发 `stop_thrusters()`。
  - `src/uuv_simulator/uuv_sensor_plugins/uuv_sensor_ros_plugins/src/MagnetometerROSPlugin.cc:82-88,147-148`：为 `magnetic_field_covariance[0/4/8]` 补乘 `this->noiseAmp * this->noiseAmp`，并将发布时间戳从 `ros::Time::now()` 改为 `_info.simTime`。
  - `yaml.load` 安全替换：将 `src/uuv_simulator/uuv_control/uuv_trajectory_control/src/uuv_waypoints/waypoint_set.py:239`、`src/uuv_simulation_wrapper/scripts/run_batch`（9 处）、`simulation_runner.py:341` 及 `test/test_run_task.py:66` 统一改为 `yaml.safe_load()`。
  - `src/uuv_simulation_wrapper/CMakeLists.txt`：在 `catkin_install_python` 中补装 `scripts/run_batch` 与 `scripts/clean_port_locks`。

### 验证记录与待确认项

- ROS 11895 / Gazebo 11896 的静止磁力计探针设 `noise_xy=2`、`noise_z=4`、`noise_amplitude=0.25`。ROS 协方差对角实测 `[2.5e-13, 2.5e-13, 1e-12]` T²，非对角值全零，消息时间戳为仿真启动后 0.221 秒。全部断言通过，场景正常退出。

- ROS 11885 / Gazebo 11886 启用原生 DVL 消息，沿用机器人 TF，运行时设置 `noise_sigma=2`、`noise_amplitude=0.25`。临时订阅器 `/tmp/rov2-native-dvl-probe` 通过项目 protobuf 直接读取 `rexrov2/dvl`，确认速度协方差对角值均为 0.25，其余元素为零。复测退出码 0。

- 使用现有 Gazebo 11 头文件和 `libuuv_sensor_gazebo_msgs.so` 编译临时 RPT 订阅探针（`/tmp/rov2-native-rpt-probe`）。首次编译缺少 Gazebo 消息头目录，补上后成功。ROS 11875 / Gazebo 11876 中订阅 `probe/rpt`，确认原生 protobuf 九个协方差元素的对角值均为 0.25，其余为 0。测试退出码 0。该检查覆盖原生 RPT，DVL 原生消息仍待测。

- 原生 RPT 在 ROS 11873 / Gazebo 11874 复测，等待收到 ROS 消息后，`gz topic -l` 列出 `probe/rpt`（无前导斜杠）。`gz topic -i` 未返回类型或发布者，`gz topic -e` 未解出消息。确认原生话题注册，原生协方差仍需用链接项目 protobuf 的订阅器验收。

- Gazebo 原生 RPT 首次探针在 ROS 11871 / Gazebo 11872 启用 `enable_gazebo_messages`，模型生成服务成功。立即执行 `gz topic -l` 时未找到预期名称，脚本退出，未验证原生消息。需等待发布注册并核查 Gazebo 实际话题名及自定义 protobuf 解码方式。

- ROS 11861 / Gazebo 11862 使用静止探针、`publish_ned_odom=true` 和 `base`→`base_ned` 静态变换。`noise_sigma=2`、`noise_amplitude=0.25` 时，`odom_ned` 速度协方差六个对角值均为 0.25，位姿协方差全零，进程正常退出。此探针的父坐标系是默认 `world`，只验证 NED 子坐标系输出的协方差，不涵盖 `world_ned` 下的位姿变换。

- DVL 在 ROS 11851 / Gazebo 11852 加入机器人 TF 发布节点后复测成功。`noise_sigma=2`、`noise_amplitude=0.25` 时，ROS 速度协方差三个对角值均为 0.25，其余元素为零。断言通过；启动进程收到 SIGINT 后未在 12 秒内退出，关闭需单独处理。

- DVL 非单位幅值首次试验在 ROS 11841 / Gazebo 11842 中展开 RexROV 2 URDF，运行时仅覆盖 DVL 的 `noise_sigma=2` 和 `noise_amplitude=0.25`，生成模型成功，但 15 秒内未收到 `/rexrov2/dvl`，关闭等待也超时。此次直接生成未启动标准入口的 TF 发布链，需核查波束 TF 并复测。未修改源码。

- ROS 11831 / Gazebo 11832 静止探针以 `noise_sigma=2`、`noise_amplitude=0.25` 实测。RPT 三轴与 ENU 里程计六个速度协方差对角值均为 0.25，里程计位姿协方差为零，全部断言通过。PowerShell 管道的 heredoc 结束标记被 Python 误读，导致断言完成后脚本退出码为 1。DVL 非单位幅值、NED 与 Gazebo 原生消息仍待独立检查。

- 最新构建在 ROS 11821 / Gazebo 11822 的 RexROV 2 无界面场景中发布了磁力计、DVL 和里程计消息，分别读取到 0.022、1.168 和 2.252 秒的仿真时间戳。三种消息的协方差均为零；本次只验证默认配置发布，非单位噪声幅值仍需专项复测。

- ROS 11801 / Gazebo 11802 短时运行剩余三个旧入口。`test_encoded` 与 `clean_underwater` 的模型生成进程均正常退出。`underwater_with_gui` 发布了海床及边界模型，但测试退出超时，未确认 Gazebo/RViz 窗口或显示，需单独复测。

- 在 Noetic 容器中复查 `spawn_underwater`、`simple_underwater`、`test_encoded`、`underwater_with_gui`、`clean_underwater`，五个入口均通过 `roslaunch --nodes` 和 `--dump-params`。在独立 ROS 11781 / Gazebo 11782 依次实跑前两个无界面入口，均收到 `Successfully spawned entity`，测试以 SIGINT 结束。后三个入口本次仅检查启动配置。

- Catkin 原先按目录注册测试，容器内 Nose 跳过可执行的测试文件，实际运行 0 项。`src/underwater_robot/CMakeLists.txt` 改为显式注册三个测试文件后，默认环境下 `catkin_make run_tests_underwater_robot -j1` 分别运行 7、8、2 项，全部通过。汇总中的 34 项包含诊断阶段留下的旧目录注册报告，本次实际运行 17 项。

- Docker Linux 引擎恢复后，重启现有 `rov2-fix` 容器并同步工作区内已修改和新增的 `src/` 文件。执行全工作区增量 `catkin_make -j1` 到 100%，退出码 0。加载新构建环境后运行 `python3 -m unittest discover -s src/underwater_robot/test -v`，17 项全部通过。Catkin 测试注册和运行场景仍待单独验收。

- **容器验收环境（2026-11-13）**：Docker Desktop 后端日志记录 `sailor-ingest.sock` 重命名为 `.stale` 时系统拒绝访问，Linux 引擎启动失败。再次执行 `docker ps -a --filter name=rov2-fix`，仍无法连接 Linux 引擎命名管道。全量构建和运行复测需待引擎恢复。

- **本机 Windows 静态与单元测试验证**：
  - `python -m unittest discover -s src/underwater_robot/test -v`：`test_runtime_scripts.RuntimeScriptsTest` **7/7 通过**（含新增的 `demo_keyboard.py` 与 `demo_command_guard.py` 回归用例）；`test_control_chain` 与 `test_geometry` 因 Windows 本机未安装 `rospy` 与 `PyYAML` 而报 `ModuleNotFoundError`。
  - XML 解析检查（`xml.etree.ElementTree.parse` 覆盖 `src/underwater_robot/launch/*.launch`、`urdf/*.urdf`、`urdf/*.xacro`）：**34 个文件全部解析通过**（退出码 0）。
  - Python 字节码编译检查（`py_compile.compile` 覆盖 `src/underwater_robot/scripts/*.py` 与 `test/*.py` 及跨包修改脚本）：全部编译通过（退出码 0）。
- **待在 ROS Noetic / Gazebo 容器中复测项**：
  - 全量 `catkin_make -j2 -l2` 与 `catkin_make run_tests`（验证 `MagnetometerROSPlugin.cc` 重新编译、`test_control_chain.py`、`test_geometry.py` 及新增 `catkin_add_nosetests` 注册）；
  - `underwater_robot_uuv2.xacro` / `TAM.yaml` 在 `bringup.launch` 中的 CAD (+Y 向上) 与 ROS (+Z 向上) 坐标系对齐及真实 CAD 质量/体积标定，仍待用户提供实机参数后推进；
  - 废弃/残留文件（`urdf/archive/*`、`urdf/underwater_robot_clean.urdf`、`scripts/preprocess_urdf.py`、`thruster_force.txt`、`src/rexrov2/rexrov2_control/launch/udo systemctl status apparmor`）以及 `rexrov_dual_oberon_description` 中缺失的 `oberon7_lite` 引用、`uuv_simulation_wrapper/test/example_start_ocean_world.launch` 中缺失的 `ocean_waves.launch` 引用，本轮未作删除，留待用户确认处理。

## 坐标变换、GUI 启动、NVIDIA 渲染与控制验收（2026-11-13）

### 1. 容器同步与 `world_ned` 里程计变换验证
- 在 `rov2-fix` 容器内将 `/ws/src/` 同步至 `/opt/rov2-fix-local/src/`（保持 `/ws/build` 不污染），执行 `catkin_make -j2 -l2` 构建至 100%（退出码 0）。
- 在独立 ROS 11801 实跑 `uuv_assistants/publish_world_ned_frame.launch`，用已知 ENU/NED 位姿与速度验证 `Vehicle(inertial_frame_id='world_ned')` 与 `DPControllerLocalPlanner`：
  - `transform_ned_to_enu` 矩阵与 `[[0, 1, 0], [1, 0, 0], [0, 0, -1]]` 误差 `< 1e-15`；
  - `_transform_position([1.0, 2.0, -3.0], 'world_ned', 'world')` 输出 `[2.0, 1.0, 3.0]` 并可逆还原；
  - `Vehicle.update_odometry` 在 `yaw=+90°`（`lin_vel=[1.0, 0.5, 0.2]`、`ang_vel=[0.1, -0.2, 0.3]`）及非零 `RPY=(0.3, -0.2, 1.1)` 下，速度变换误差及 `R_B_to_I @ vehicle.vel[:3] == lin_vel` 一致性误差均 `< 1e-9`；静态 TF 四元数与 `quaternion_from_euler(pi, 0, pi/2)` 误差 `< 1e-9`。

### 2. `underwater_with_gui.launch` 修复与实跑、NVIDIA 渲染核查
- 修复 [underwater_with_gui.launch](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/launch/underwater_with_gui.launch)：新增 `software_gl` 参数（默认 `true` 控制 `LIBGL_ALWAYS_SOFTWARE=1`），将 `robot_description`、`joint_state_publisher` 与 `robot_state_publisher`（`tf_prefix=underwater_robot`）纳入 `ns="underwater_robot"`，将 `spawn_urdf` 改为 `-param /underwater_robot/robot_description`，并补充 `world -> underwater_robot/base_link` 静态 TF（`0 0 -5 0 0 0`）以匹配 `standard_ros.rviz`。
- 在 `rov2-fix`（`DISPLAY=:0`、ROS 11811 / Gazebo 11812）实跑 `underwater_with_gui.launch`（`software_gl:=true` 与 `software_gl:=false` 均测试）：`gzserver`、`gzclient`、`rviz`、`joint_state_publisher`、`robot_state_publisher` 与 `spawn_urdf` 均正常启动且模型生成进程正常退出。
- **NVIDIA 渲染核查（未下载任何新包）**：容器内存在 `/dev/dxg`（无 `/dev/dri`），在 `GALLIUM_DRIVER=d3d12`、`MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` 且取消 `LIBGL_ALWAYS_SOFTWARE` 下运行 `rviz` 并开启 `LIBGL_DEBUG=verbose`，实测 `libGL` 仍回退加载 `swrast_dri.so`（`MESA-LOADER: dlopen(/usr/lib/x86_64-linux-gnu/dri/swrast_dri.so)`）。容器内候选待确认图形组件为 Ubuntu Focal `mesa-vulkan-drivers`（`21.2.6-0ubuntu0.1~20.04.2`，约 5.8 MB）及 `mesa-utils`，本轮未下载，留待确认后再安装测试。

### 3. 机械臂 `arm1` 力矩限值核查与持续水流 PID 整定
- **机械臂 `arm1` 实测（独立 ROS 11831 / Gazebo 11832，`underwater_ned_compatible.launch`）**：
  - 向 `/underwater_robot/arm1_joint_position_controller/command` 发送 `0.2`、`1.3`、`-1.3`、`0.0` rad 阶跃，位置被 `[-1.0, 1.0]` 限位截断（`0.99911` / `-0.99724` rad）。
  - 在 `1.0 -> -1.3 rad` 阶跃瞬态采样中，控制器命令峰值达 `-8.7495 N·m`（超 `5.0 N·m`），`/underwater_robot/joint_states` 中 `effort` 字段始终为 `0.0000`，且关节角速度瞬态达到 `-2.4652 rad/s`（超出 URDF `velocity="0.5"` 约 5 倍）。由于 `Link10` 转动惯量极小（`izz=0.004060257 kg·m²`）且 50 Hz 采样间隔为 20 ms，无法直接从 `joint_states.effort` 证实 Gazebo 内部已对 `arm1` 施加 `5.0 N·m` 饱和限制。
- **持续水流抗饱和与 `Ki` 整定（独立 ROS 11821 / Gazebo 11822）**：
  - 修改 [dp_pid_controller_base.py](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/uuv_simulator/uuv_control/uuv_trajectory_control/src/uuv_control_interfaces/dp_pid_controller_base.py)：在 `update_pid()` 中增加条件积分抗饱和（当 `raw_out` 超出 `±saturation` 且与积分增量同向时冻结积分，并将 `self._int[i]` 限幅在 `[-sat/ki, sat/ki]`），同步更新 `set_pid_params_callback()`，并在 [test_control_chain.py](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/test/test_control_chain.py) 新增 `test_pid_anti_windup_freezes_and_clamps_integrator`。
  - 在 `demo.launch` + `demo_pid.launch` 下施加 `0.20 m/s` X 向持续水流 24 s 并撤流恢复 15 s：
    - `Kp=[40,40,40,4,4,6]`、`Kd=[25,25,30,3,3,4]`、`Ki=[10,10,10,0,0,0.5]` 时，稳态位置误差 **`0.0016 m`**，水流中最大偏差 `0.1837 m`，撤流反向超调 `0.1884 m`，恢复终值误差 **`0.0038 m`**，六路单推力峰值 **`3.3421 N`**（低于 8 N 上限）。已将该组参数更新至 [demo_pid.launch](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/launch/demo_pid.launch)。
- **最终回归验证**：同步全部最新改动后，在 `rov2-fix` 运行 `python3 -m unittest discover -s /opt/rov2-fix-local/src/underwater_robot/test -v`，**18/18 项测试全部通过**（`0.040s`）。

### 4. NVIDIA 渲染补充核查（安装 `mesa-vulkan-drivers` 与 `mesa-utils` 后）
- 经用户确认，在 `rov2-fix` 安装 `mesa-vulkan-drivers=21.2.6-0ubuntu0.1~20.04.2` 与 `mesa-utils=8.4.0-1build1`。
- **`GALLIUM_DRIVER=d3d12` + `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA`（`software_gl:=false`）**：
  - `glxinfo -B` 确认 `direct rendering: Yes`、`Accelerated: yes`、`Device: D3D12 (NVIDIA GeForce RTX 5060 Laptop GPU)`、显存 `15952MB`、`OpenGL core profile 3.3` / `OpenGL 3.1 Mesa 21.2.6`。
  - 实跑 `roslaunch underwater_robot underwater_with_gui.launch software_gl:=false`（`DISPLAY=:0`），RViz 日志明确输出 `OpenGL device: D3D12 (NVIDIA GeForce RTX 5060 Laptop GPU)`、`OpenGl version: 3.1 (GLSL 1.4)`，未出现 OGRE 或 `.STL` 网格加载错误。
  - 注：容器内通过 Qt `grabWindow(0)` 抓取 X11 根窗口返回全黑（WSLg Wayland 合成器禁止 X11 根窗口回读），因此 `.STL` 网格在 `D3D12` 加速下的实际肉眼画面仍需您在 Windows 桌面窗口直接目视确认。
- **`GALLIUM_DRIVER=zink`**：`glxinfo -B` 报 `failed to create dri screen` / `BadValue`，因 Focal 源 `mesa-vulkan-drivers` 21.2.6 不包含 D3D12 Vulkan ICD（`dzn`），`zink` 路径在当前镜像不可用。

### 5. 剩余工程问题补充修复与复测（2026-11-13）
- **Launch / URDF / 脚本 / 传感器补充修复**：
  - [underwater_ned_compatible.launch](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/launch/underwater_ned_compatible.launch)：将 `robot_description`、控制器参数与 `robot_state_publisher`（`tf_prefix=underwater_robot`）移入 `ns="underwater_robot"`，将 `spawn_urdf` 改为 `-param /underwater_robot/robot_description`，并补充 `world -> underwater_robot/base_link` 静态 TF 以匹配 `standard_ros.rviz`。
  - [underwater_robot_actuators.xacro](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/urdf/underwater_robot_actuators.xacro) 与 [underwater_robot_complete.xacro](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/urdf/underwater_robot_complete.xacro)：新增 `underwater_robot_thruster_macro`（`parent_link:=base_link`），修复原先指向不存在 `${namespace}/base_link` 的父连杆前缀失配。
  - [package.xml](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/package.xml)：替换 `TODO` 作者与维护者占位符；[demo_command_guard.py](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/scripts/demo_command_guard.py) 新增 `normalize_output_prefix()` 防止空或 `'/'` 前缀生成非法话题名。
  - [test_geometry.py](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/test/test_geometry.py)：`test_launch_xml` 扩展为遍历校验 `launch/` 全部 24 个 `.launch` 文件；[validate_keyboard_runtime.py](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/test/validate_keyboard_runtime.py) 替换裸 `assert` 为显式 `RuntimeError`；[test_runtime_scripts.py](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/underwater_robot/test/test_runtime_scripts.py) 新增 `test_demo_command_guard_normalizes_output_prefix`。
  - [IMUROSPlugin.cc](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/uuv_simulator/uuv_sensor_plugins/uuv_sensor_ros_plugins/src/IMUROSPlugin.cc)：为 `gyroVar`、`accelVar` 与 `orientationVar` 补乘 `noiseAmp * noiseAmp`；[run_batch](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/uuv_simulation_wrapper/scripts/run_batch) 第 341 行改为原始字符串 `r'(\d+)'` 消除 `SyntaxWarning`；[model.xacro](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/src/uuv_simulator/uuv_gazebo_plugins/uuv_gazebo_ros_plugins/test/models/thrusters/model.xacro) 修正 `mesh/prop.dae` 为 `meshes/prop.dae`；[debug_simulation.sh](file:///d:/Users/Lenovo/Documents/ChatGPT/rov_ws/ROV2_ws_fix/scripts/debug_simulation.sh) 改用 `cd "$(rospack find underwater_robot)/meshes"`。
- **容器编译与回归复测**：
  - 将 `/ws/src/` 同步至 `/opt/rov2-fix-local/src/`，执行 `catkin_make -C /opt/rov2-fix-local --pkg uuv_sensor_ros_plugins -j2`，`libuuv_gazebo_ros_imu_plugin.so` 等传感器插件编译链接 100% 通过。
  - 运行 `python3 -m unittest discover -s /opt/rov2-fix-local/src/underwater_robot/test -v`：**19/19 项测试全部通过**（`0.048s`）。
