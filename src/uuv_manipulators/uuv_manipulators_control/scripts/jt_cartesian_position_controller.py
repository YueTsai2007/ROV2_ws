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

import argparse
import rospy
import sys
import os
import numpy as np
from copy import deepcopy
import PyKDL
from uuv_manipulators_control import CartesianPositionController


class JCartesianController(CartesianPositionController):
    """
    Jacobian transpose controller
    """

    LABEL = 'Jacobian transpose cartesian controller'
    def __init__(self):
        """
        Class constructor
        """
        
        CartesianPositionController.__init__(self)
        self._reference_pos = dict()
        for joint in self._arm_interface.joint_names:
            self._reference_pos[joint] = deepcopy(self._arm_interface.home[joint])
        # Retrieve the controller parameters from the parameter server
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

        # Initialization flag, to wait the end-effector get to the home
        # position
        self._is_init = False

        self._run()
    
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
        # Leave if ROS is not running or command is not valid
        if rospy.is_shutdown() or self._last_goal is None:
            return
        # Calculate the goal pose
        goal = self._get_goal()
        pos = self._arm_interface.joint_angles

        # End-effector's pose
        ee_pose = self._arm_interface.get_ee_pose_as_frame()
        # End-effector's velocity
        ee_vel = self._arm_interface.get_ee_vel_as_kdl_twist()
        # Calculate pose error
        error = PyKDL.diff(goal, ee_pose)
        # End-effector wrench to achieve target
        velocity = np.matrix(np.zeros(6)).T
        for i in range(len(velocity)):
            velocity[i] = -(self._Kp[i] * error[i] + self._Kd[i] * ee_vel[i])
        n = 0    
        # Compute jacobian transpose
        J = self._arm_interface.jacobian()
        JT = self._arm_interface.jacobian_transpose()
        I = np.eye(6)
        la = 0.1
        # Calculate the velocity for the joints
        position = JT * np.linalg.pinv(J*JT+la**2*I) * velocity
        
        for joint in self._arm_interface.joint_names:
            self._reference_pos[joint] += position[n]/50.0              
                        # Check for the joint limits
            self._reference_pos[joint] = self._check_joint_limits(self._reference_pos[joint], joint)
            position[n] = self._reference_pos[joint]
            n += 1
        n = 0
        # Store current pose target
        self._last_goal = goal

        self.publish_goal()
        self.publish_joint_positions(position)

if __name__ == '__main__':
    # Start the node
    node_name = os.path.splitext(os.path.basename(__file__))[0]
    rospy.init_node(node_name)
    rospy.loginfo('Starting [%s] node' % node_name)

    jt_controller = JCartesianController()

    rospy.spin()
    rospy.loginfo('Shutting down [%s] node' % node_name)
