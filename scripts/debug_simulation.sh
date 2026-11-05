#!/bin/bash

# Auto-detect workspace root (parent of scripts/ directory)
WS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WS_ROOT"
source devel/setup.bash

echo "=== 环境检查 ==="
echo "ROS_PACKAGE_PATH: $ROS_PACKAGE_PATH"
echo "GAZEBO_MODEL_PATH: $GAZEBO_MODEL_PATH"

echo "=== 检查URDF ==="
check_urdf src/underwater_robot/urdf/underwater_robot_simple_geometry.urdf

echo "=== 检查网格文件 ==="
roscd underwater_robot/meshes
find . -name "*.STL" | wc -l

echo "=== 启动简单Gazebo测试 ==="
echo "如果Gazebo启动成功，你应该能看到一个黄色盒子"
echo "按Ctrl+C停止测试"

timeout 30s roslaunch underwater_robot simple_gazebo_test.launch

if [ $? -eq 124 ]; then
    echo "Gazebo测试超时，但可能已成功启动"
else
    echo "Gazebo测试完成"
fi
