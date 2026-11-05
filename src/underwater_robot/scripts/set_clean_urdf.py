#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import rospy
import rospkg

def set_clean_urdf():
    rospy.init_node('set_clean_urdf')

    # Use rospkg Locate URDF File（不依赖硬编码路径）
    rospack = rospkg.RosPack()
    pkg_path = rospack.get_path('underwater_robot')
    urdf_path = os.path.join(pkg_path, 'urdf', 'underwater_robot.urdf')
    with open(urdf_path, 'r') as f:
        urdf_content = f.read()
    
    # CleanupWindowsNewline
    clean_urdf = urdf_content.replace('\r', '')
    
    # SetParameters
    rospy.set_param('/underwater_robot/robot_description', clean_urdf)
    print("Clean URDF parameter set successfully")
    
    # Verify
    test_urdf = rospy.get_param('/underwater_robot/robot_description')
    print("URDF length:", len(test_urdf))
    print("First 100 chars:", test_urdf[:100])

if __name__ == '__main__':
    try:
        set_clean_urdf()
    except Exception as e:
        print("Failed to set clean URDF:", str(e))
