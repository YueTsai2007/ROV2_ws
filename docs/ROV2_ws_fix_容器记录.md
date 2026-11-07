# ROV2 fix 分支容器记录

## 2026-11-06：创建与检查

- GitHub 分支：`fix/underwater-robot-round1`，提交 `5d4da4cd8a03aa948525d944d33c00c8b5256b02`。
- 项目位置：`D:\Users\Lenovo\Documents\ChatGPT\rov_ws\ROV2_ws_fix`，挂载到容器 `/ws`。
- 容器：`rov2-fix`，基于已存在的 `rov2:noetic`；未构建新镜像。显卡设备和 WSLg 的 X11 socket 已映射。
- 容器 OpenGL 实测：`D3D12 (NVIDIA GeForce RTX 5060 Laptop GPU)`，绘制调用错误码 `0x0`。
- 已确认 ROS Noetic、RViz、tf_conversions、joy、gazebo_ros_control 以及 numpy、scipy、casadi、pymap3d 存在。
- 分支自带 Python 回归测试：7 项通过。
- 初次使用 `catkin build` 在 Windows 挂载目录编译：21/48 个包成功、无包失败，但耗时约 11 分钟并出现时钟偏差警告；已主动中止，其构建产物保留在 `/ws`。
- 为避免挂载目录 I/O 和时间戳影响，将 `/ws/src` 复制至容器内 `/opt/rov2-fix-local/src`，接下来在该副本编译；原检出不变，副本和编译产物依赖容器保留。
- 容器内使用 `catkin_make -j2` 完整编译成功，工作空间为 `/opt/rov2-fix-local`；没有构建新 Docker 镜像。
- `bringup.launch gui:=false paused:=true` 启动成功，Gazebo 中存在 `ocean_box` 和 `underwater_robot`；`pose_gt` 有 Gazebo 发布者、TF 节点订阅者，0–5 六路推进器均有 Gazebo 订阅者。仿真保持暂停，PID 默认未启动。
- 启动 `gzclient` 和 `rviz -d /opt/rov2-fix-local/src/underwater_robot/config/standard_ros.rviz`；两个进程运行并加载 `/usr/lib/wsl/lib/libd3d12.so` 和 `libd3d12core.so`，初步日志无材质或网格错误。OpenGL 独立测试确认 NVIDIA GPU；图形画面未进行人工视觉验收。
- 分支 `display.launch` 引用不存在的 `urdf.rviz`，未修改源码；当前测试直接使用已有 `config/standard_ros.rviz`。
- 分支文档注明模型质量与排水体积、推进矩阵秩 5、机械臂零限位和 PID 动态控制仍需进一步校准验证；不要将暂停接口测试当作闭环验证。
- `/ws` 是 Windows 检出的挂载，当前正在运行的工作空间是容器内的 `/opt/rov2-fix-local` 副本；修改 `/ws` 不会自动同步到副本。容器删除后内部副本和构建产物会丢失。

## 2026-11-06：RViz 模型引用修复

- 当前 bringup 将完整 xacro 生成的描述放在 `/underwater_robot/robot_description`；ROS 1 RViz 使用 `Robot Description` 属性，原配置的 `Description Topic` 不适用。
- 原 `display.launch` 指向不存在的 `urdf.rviz`，其全局描述参数与当前 bringup 不一致。
- 本轮先修改容器源码副本中的 `config/standard_ros.rviz` 和 `launch/display.launch`，并验证；原 Git 检出及其他源码不改动。
- 容器候选配置将 ROS 1 的 `Robot Description` 指向 `/underwater_robot/robot_description`，并设置 `TF Prefix: underwater_robot`；独立 `display.launch` 使用同一命名空间、实际存在的 RViz 配置和静态世界坐标。该独立启动应在停止 bringup 后使用，避免重复节点和参数覆盖。待验证。
- 实际 RViz 测试显示 URDF 已解析成功，但当前暂停场景的动态 TF 未更新，连杆仍提示缺少坐标变换，不能视为完整显示验证通过。
- 已启动隔离的独立 display 测试；后续检查命令因执行权限自动审核额度限制未执行。隔离测试设有 75 秒超时。两处修复仍仅在 `/opt/rov2-fix-local` 容器副本中，尚未同步到 `/ws` 原检出。
- 继续验证：独立 display 的 world→underwater_robot/Link1 TF 可查询，RViz 的 RobotModel 状态为 OK；但新启动窗口中显示项未默认启用，画面仍不显示模型。将为 Grid 与 RobotModel 显式设置 `Enabled: true` 后再次验证。
- 已在同一容器内的 `config/standard_ros.rviz` 中显式启用 Grid 和 RobotModel；未改动其他源码，也没有同步到 `/ws` 或重建镜像。
- 使用独立 ROS master（端口 11343）再次启动 `display.launch`：描述参数、节点与坐标变换均存在，`world → underwater_robot/Link1` 测得平移约 `[0.288, 0.180, -0.110]`。实际 RViz 画面已能看到网格，但本次未能观察到机器人，因此不能认定视觉显示修复完成。
- 独立 display 使用原始 URDF（11 个 link、11 个 visual）；仿真 bringup 使用 xacro（17 个 link、11 个 visual），独立测试不能代替仿真模型的视觉验证。仿真暂停时动态 TF 不更新，需单独处理后再验证实际仿真画面。
- 测试日志出现 ROS 时钟回跳及根 link 惯量的 KDL 提示；其成因及对画面的影响尚未确定。测试进程设有 300 秒超时，不删除任何文件。

## 2026-11-06：继续检查 TF 与视觉显示

- 复查时 Gazebo 已处于运行状态（`pause: False`），仿真模型 world→base_link 约为 `[-10.979, -2.277, -99.750]` 米，已经远离世界原点；来源于本次实时 TF 查询。这可能影响以世界原点为焦点的仿真 RViz 视野，但不能解释此前独立 URDF 测试的空画面。
- 运行状态下新启动的 TF 监听器可以查询 world→underwater_robot/base_link。临时暂停约 5 秒后新订阅 `/tf` 没收到消息，提示模拟时钟未继续发布；测试结束后已恢复原运行状态，并通过服务确认 `pause: False`。这支持暂停后新启动监听器拿不到动态 TF 的判断，不代表所有静态 TF 失效。
- 测试观察文件保留在容器 `/tmp/rov2-paused-tf-observe.txt`（0 字节）。未修改项目源代码。独立 RViz 测试按原设定超时结束，机器人网格仍未完成视觉验收；根因尚未确定。
- 后续只读检查确认：`ground_truth_to_tf_underwater_robot` 从 `pose_gt` 发布动态 TF，`robot_state_publisher` 从 `joint_states` 发布关节 TF，二者均订阅仿真时钟。暂停后直接增加 world→base_link 静态变换会与恢复运行后的动态变换冲突；暂停时的完整关节 TF 也需要处理。尚未修改启动文件或增加脚本，修复方案仍需验证。

## 2026-11-06：暂停 TF 缓存试验

- 按授权在容器副本新增 `scripts/pause_tf_cache.py`，并在 `launch/underwater_uuv.launch` 增加默认启用的 `paused_tf_cache` 节点及开关参数 `cache_paused_tf`。原始 `/ws` 检出、Docker 镜像及其他源码未修改。工作目录保留本次脚本、launch 副本和探针用于复查。
- 节点运行时缓存机器人动态 TF；检测到暂停后发布一次带 latch 的缓存，恢复时注销发布者。初版持续重发同一时间戳导致 TF_REPEATED_DATA，已调整为只发布一次。
- 在正在运行的仿真中启动试验节点，等待缓存后暂停，使用墙钟探针作为新监听器查询 `world → underwater_robot/Link1` 成功；随后恢复原运行状态，服务确认 `pause: False`。脚本语法检查通过，`roslaunch --nodes` 能解析新节点。
- 局限：仿真一开始就暂停且尚未收到动态 TF 时，缓存为空，不能凭空生成机器人位姿和关节状态；尚未验证重启后的完整 launch，也未完成 RViz 实际画面验收。当前运行中的 bringup 未重启，新增节点不会自动加载；测试节点按超时退出。
- 已在当前 bringup 中单独启动常驻 `paused_tf_cache`，再次短暂停止仿真后，新监听器查询 `world → underwater_robot/Link1` 成功，测试后恢复运行。若从启动即暂停的空缓存开始，可先短暂运行仿真使缓存获得 TF，再暂停；这会推进物理仿真且可能改变机器人位置，非零步长方案。
- 只读检查：独立 URDF 的 base_link.STL 有效，约 0.724×0.380×0.400 米，并非网格缺失或尺寸明显异常；独立 RViz 画面空白的根因仍未确定。

## 2026-11-06：启动图形窗口与控制链检查

- 复用运行中的 bringup，启动 `gzclient` 与 RViz；仅在容器 `/tmp/rov2-follow-robot.rviz` 创建视角跟随配置，目标为 `underwater_robot/base_link`，没有修改项目源码。两个进程及窗口存在，但窗口被其他应用遮挡，未完成视觉验收。
- 当前 Gazebo 正在运行；查询到机器人在大约 `[-10.84, -2.06, -99.75]` 米。未重置模型或暂停仿真。
- 六路推进器输入话题有 Gazebo 订阅者；项目键盘工具发布 `/underwater_robot/cmd_vel`，当前控制链没有该话题的订阅者。键盘至推进器的控制未验证，控制参数也未经校准。未发送推进器指令。

## 2026-11-06：重新排查 RViz 网格显示

- 使用容器临时配置 `/tmp/rov2-diagnostic.rviz`，固定坐标设为机器人本体：网格可见，RobotModel 状态为 OK，模型仍不可见。RViz 属性显示所有连杆启用、全局和 Link1 的 Alpha 为 1；17 个连杆 TF 均可查询，11 个 STL 文件均能完整读取且尺寸正常。
- 在 ROS 临时参数 `/rviz_diagnostic_description` 中，仅对照测试将 visual 几何换成盒体，其他连杆、TF 和材质保持，画面能显示盒体。恢复网格后未见机器人；二进制 STL 小写扩展名、临时 ASCII STL、临时 OBJ 和双面 OBJ 在本次画面中均未观察到模型。容器 Assimp 对原始 STL 与临时 OBJ 的直接导入均成功；这些结果定位到 RViz 网格显示链路，但尚不足以确定根因。
- RViz 日志显示 D3D12 NVIDIA 渲染器，不能由此认定网格渲染正常。对照结果保存在容器 `/tmp/rov2_meshdiag` 与临时配置文件中，未修改项目源码，未下载软件。诊断窗口已通过 RViz 服务切回真实机器人配置，窗口本身有测试超时。

## 2026-11-06：定位 RViz 的 GPU 网格显示问题

- 容器内 RViz 官方 `loadMeshFromResource` 探针成功加载原始 STL，得到一个 submesh、128220 个顶点/索引和正常包围盒。实际机器人 Ogre Entity 可见、缩放为 1、材质 alpha 为 1。不能把空画面归因于网格文件缺失、尺寸、透明度或未创建实体。
- 相同最小 OBJ 模型在默认 `GALLIUM_DRIVER=d3d12` 的 NVIDIA RViz 窗口不可见，在明确设置 `GALLIUM_DRIVER=llvmpipe` 和 `LIBGL_ALWAYS_SOFTWARE=1` 的软件渲染窗口可见；软件窗口进程映射 `swrast_dri.so` 且无 `libd3d12`。加载真实机器人后，画面显示真实机器人网格。已核实这只是 CPU 软件渲染，不代表 NVIDIA RViz 加速正常。
- 临时测试 `MESA_GL_VERSION_OVERRIDE=3.1COMPAT` 和 `2.1` 时最小网格仍不可见；禁用 `GL_ARB_vertex_buffer_object` 的测试窗口崩溃，未修改系统或默认容器配置。微软 WSLg 问题 https://github.com/microsoft/wslg/issues/554 报告过类似的 GPU 下网格不显示、软件渲染可见现象，但本机底层驱动缺陷的具体机制尚未确定。
- 为便于查看，单独启动了 `GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1` 的 RViz，使用临时配置 `/tmp/rov2-software-view.rviz`：固定坐标为机器人 base_link、视距 3，并添加视角工具。已通过实际画面确认真实机器人模型可见。此窗口可能占用较多 CPU；Gazebo 的既有进程未更改渲染配置。没有重建镜像、下载软件或修改项目源码。
- 两个独立的临时 Ogre 探针进一步复现：同一 RViz 加载器、同一 base_link 网格，NVIDIA D3D12 绘制结果为背景，llvmpipe 能绘制；其中一个探针统计到软件路径 10175 个非黑像素、D3D12 为 0。已尝试多种 OpenGL 版本兼容值、关闭线程和 shader cache，未找到有效 GPU 开关；个别临时探针退出时崩溃，未改变主仿真。
- 当前容器 `libgl1-mesa-dri` 和 `libglx-mesa0` 为 21.2.6，Ogre 为 1.9；NVIDIA 驱动显示 621.01。宿主 Ubuntu 24.04 的 Mesa 较新，但宿主与容器 glibc 版本不同，不能直接替换库并假定兼容。GPU 根本修复还需单独测试兼容的运行库或环境；本轮未进行安装、下载或重建。
