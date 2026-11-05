#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
import math
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

class ArmController:
    def __init__(self):
        rospy.init_node('arm_controller')
        
        # Arm joint name
        self.arm_joint_name = "arm1"
        
        # Publish joint command
        self.arm_pub = rospy.Publisher('/underwater_robot/arm1_joint_position_controller/command', Float64, queue_size=10)
        
        # Control parameters
        self.target_angle = 0.0  # Target angle (radians)
        self.rate = rospy.Rate(10)  # 10Hz
        
        # Subscribe to joint states
        rospy.Subscriber('/joint_states', JointState, self.joint_state_callback)
        
        # Service or topic to control arm
        rospy.Subscriber('/arm_control/command', Float64, self.arm_command_callback)
        
        rospy.loginfo("Arm controller started for joint: %s", self.arm_joint_name)
        
    def joint_state_callback(self, msg):
        # Monitor joint state
        if self.arm_joint_name in msg.name:
            idx = msg.name.index(self.arm_joint_name)
            current_angle = msg.position[idx]
            # rospy.loginfo("Current arm angle: %.2f rad", current_angle)
    
    def arm_command_callback(self, msg):
        # Receive arm control command
        self.target_angle = msg.data
        rospy.loginfo("Received arm command: %.2f rad", self.target_angle)
    
    def set_arm_angle(self, angle):
        # Set arm angle
        self.target_angle = angle
        command_msg = Float64()
        command_msg.data = self.target_angle
        self.arm_pub.publish(command_msg)
        rospy.loginfo("Setting arm to: %.2f rad", angle)
    
    def run_demo(self):
        # Run demo: periodic arm movement
        count = 0
        while not rospy.is_shutdown():
            # Sine wave movement -1.57 to +1.57 radians (-90 to +90 degrees)
            angle = 1.57 * math.sin(count * 0.1)
            self.set_arm_angle(angle)
            
            count += 1
            self.rate.sleep()

if __name__ == '__main__':
    try:
        controller = ArmController()
        
        # Wait for system startup
        rospy.sleep(2.0)
        
        # Run demo or wait for commands
        controller.run_demo()
        # Or comment the above line and wait for external commands:
        # rospy.spin()
        
    except rospy.ROSInterruptException:
        pass
