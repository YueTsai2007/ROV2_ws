#!/usr/bin/env python
# Copyright (c) 2016 The UUV Simulator Authors.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import rospy
import argparse
import sys
import numpy as np
from copy import deepcopy
from uuv_manipulator_interfaces import ArmInterface
from PID import PIDRegulator
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64
from uuv_manipulators_control import CartesianController
import PyKDL

class JointPositionController(CartesianController):
    def __init__(self):
        # Initializing arm interface
        CartesianController.__init__(self)
        
        Kd_tag = '~Kd'
        Kp_tag = '~Kp'
        if not rospy.has_param(Kd_tag):
            rospy.ROSException('Kd gain vector not available for tag=%s' % Kd_tag)
        if not rospy.has_param(Kp_tag):
            rospy.ROSException('Kp gain vector not available for tag=%s' % Kp_tag)

        self._Kd = rospy.get_param(Kd_tag)
        self._Kp = rospy.get_param(Kp_tag)

        rospy.loginfo('Kp=%s', str(self._Kp))
        rospy.loginfo('Kd=%s', str(self._Kd))
        self._is_init = False

        

        # PID controllers
        self._controllers = dict()
        # Current reference for each joint
        self._reference_pos = dict()
        # Output command topics
        self._command_topics = dict()
        
        
        # Axes gain values
        self._axes_gain = dict()


        # Last joystick update timestamp
        self._last_update = rospy.get_time()
        
       

        # Reading the controller configuration
        controller_config = rospy.get_param('~controller_config')
        for joint in self._arm_interface.joint_names:
            for tag in controller_config:
                if tag in joint:
                    try:
                        # Read the controller parameters
                        self._controllers[joint] = PIDRegulator(controller_config[tag]['controller']['p'],
                                                                controller_config[tag]['controller']['i'],
                                                                controller_config[tag]['controller']['d'],
                                                                1000)
                        self._command_topics[joint] = rospy.Publisher(
                            controller_config[tag]['topic'],
                            Float64,
                            queue_size=1)
                        self._axes_gain[joint] = controller_config[tag]['axis_gain']

                        # Setting the starting reference to the home position
                        # in the robot parameters file
                        self._reference_pos[joint] = deepcopy(self._arm_interface.home[joint])
                        
                    except:
                        raise rospy.ROSException('Error while trying to setup controller for joint <%s>' % joint)
                    

        
        rate = rospy.Rate(50)
        self._another_run()
        



    def _another_run(self):
        rate = rospy.Rate(self._publish_rate)
        while not rospy.is_shutdown():
            self._update()
            pos = self._arm_interface.joint_angles
            for joint in pos:
                #u = self._controllers[joint].regulate(self._reference_pos[joint] - pos[joint], rospy.get_time())
                u = self._controllers[joint].regulate(self._reference_pos[joint], rospy.get_time())
                self._command_topics[joint].publish(Float64(u))
            rate.sleep()
    def _check_joint_limits(self, value, joint):
        """Check the joint position and maintain it within joint limits"""
        output = value
        if self._arm_interface.joint_limits[joint] is not None:
            if output < self._arm_interface.joint_limits[joint]['lower']:
                output = self._arm_interface.joint_limits[joint]['lower']
            if output > self._arm_interface.joint_limits[joint]['upper']:
                output = self._arm_interface.joint_limits[joint]['upper']
        return output

    def _update(self):
        try:
            # If deadman button is not pressed, do nothing
            # Leave if ROS is not running or command is not valid
            if rospy.is_shutdown() or self._last_goal is None:
                return
            # Calculate the goal pose
            goal = self._get_goal()

            # End-effector's pose
            ee_pose = self._arm_interface.get_ee_pose_as_frame()
            # End-effector's velocity
            ee_vel = self._arm_interface.get_ee_vel_as_kdl_twist()
            # Calculate pose error
            error = PyKDL.diff(goal, ee_pose)
            # End-effector wrench to achieve target
            cartesianvelocity = np.matrix(np.zeros(6)).T
            for i in range(len(cartesianvelocity)):
                cartesianvelocity[i] = -(self._Kp[i] * error[i] + self._Kd[i] * ee_vel[i])

            # Compute jacobian transpose
            J = self._arm_interface.jacobian()
            JT = self._arm_interface.jacobian_transpose()
            I = np.eye(6)
            la = 0.1
            # Calculate the torques for the joints
            velocity = JT * cartesianvelocity
            #velocity = JT * np.linalg.pinv(J*JT+la**2*I) * cartesianvelocity
            # Store current pose target
            self._last_goal = goal

            self.publish_goal()
            n = 0
            for i, joint in enumerate(self._arm_interface.joint_names):
                #self._reference_pos[joint] += velocity[i]
                self._reference_pos[joint] += self._axes_gain[joint]*velocity[i]
                # Check for the joint limits
                self._reference_pos[joint] = self._check_joint_limits(self._reference_pos[joint], joint)
                
            self._last_update = rospy.get_time()
            n = 0
        except Exception as e:
            print('Error during update, message=', e)
            
            

if __name__ == '__main__':
    # Start the node
    node_name = os.path.splitext(os.path.basename(__file__))[0]
    rospy.init_node(node_name)
    rospy.loginfo('Starting [%s] node' % node_name)

    controller = JointPositionController()

    rospy.spin()
    rospy.loginfo('Shuting down [%s] node' % node_name)
