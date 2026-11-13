#!/bin/bash

echo "=== 修复NED坐标系问题（正确版本）==="

echo "1. 发布NED到ROS的世界坐标系变换..."
# 格式: x y z yaw pitch roll frame_id child_frame_id
rosrun tf2_ros static_transform_publisher 0 0 0 1.5707963267948966 0 3.141592653589793 world_ned world &

echo "2. 发布机器人基础链接变换..."
rosrun tf2_ros static_transform_publisher 0 0 0 1.5707963267948966 0 3.141592653589793 underwater_robot/base_link_ned underwater_robot/base_link &

echo "3. 发布所有其他链接的变换..."
for link in Link1 Link2 Link3 Link4 Link5 Link6 Link7 Link8 Link9 Link10; do
  rosrun tf2_ros static_transform_publisher 0 0 0 1.5707963267948966 0 3.141592653589793 underwater_robot/${link}_ned underwater_robot/$link &
  echo "发布变换: underwater_robot/${link}_ned → underwater_robot/$link"
done

echo "4. 等待TF发布..."
sleep 3

echo "5. 检查TF树..."
rosrun tf tf_monitor

echo "6. 检查特定变换..."
echo "--- world_ned to world ---"
rosrun tf tf_echo world_ned world

echo "--- world_ned to base_link ---"
rosrun tf tf_echo world_ned base_link

echo "=== 修复完成 ==="
echo "在RViz中设置 Fixed Frame = world"
