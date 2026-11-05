#!/usr/bin/env python
# -*- coding: utf-8 -*
import rospy
from sensor_msgs.msg import JointState
from std_msgs.msg import Header

def publish_joint_states():
    rospy.init_node('default_joint_states_publisher')
    pub = rospy.Publisher('/underwater_robot/joint_states', JointState, queue_size=10)
    rate = rospy.Rate(10)  # 10Hz
    
    joint_state = JointState()
    joint_state.header = Header()
    joint_state.header.stamp = rospy.Time.now()
    
    # Based on yourURDFSet all joint names
    joint_state.name = [
        'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 
        'camera', 'arm1'
    ]
    
    # Set all joint positions to0
    joint_state.position = [0.0] * len(joint_state.name)
    joint_state.velocity = [0.0] * len(joint_state.name)
    joint_state.effort = [0.0] * len(joint_state.name)
    
    while not rospy.is_shutdown():
        joint_state.header.stamp = rospy.Time.now()
        pub.publish(joint_state)
        rate.sleep()

if __name__ == '__main__':
    try:
        publish_joint_states()
    except rospy.ROSInterruptException:
        pass
