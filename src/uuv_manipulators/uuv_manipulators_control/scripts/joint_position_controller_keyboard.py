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
import sys
import tty
import termios
from copy import deepcopy
from uuv_manipulator_interfaces import ArmInterface
from PID import PIDRegulator
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64
from std_msgs.msg import String


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd, termios.TCSAFLUSH)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
    return ch
class JointPositionController:
    def __init__(self):
        # Initializing arm interface
        self._arm_interface = ArmInterface()

        # PID controllers
        self._controllers = dict()
        # Current reference for each joint
        self._reference_pos = dict()
        # Output command topics
        self._command_topics = dict()
        # Axes mapping
        self._axes = dict()
        # Axes gain values
        self._axes_gain = dict()





        self._last_key_update = rospy.get_time()

        self.key_callback()

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
                        self._axes[joint] = controller_config[tag]['joint_input_axis']
                        self._axes_gain[joint] = controller_config[tag]['axis_gain']

                        # Setting the starting reference to the home position
                        # in the robot parameters file
                        self._reference_pos[joint] = deepcopy(self._arm_interface.home[joint])
                    except:
                        raise rospy.ROSException('Error while trying to setup controller for joint <%s>' % joint)

        rate = rospy.Rate(50)

        while not rospy.is_shutdown():
            pos = self._arm_interface.joint_angles
            for joint in pos:
                u = self._controllers[joint].regulate(self._reference_pos[joint] - pos[joint], rospy.get_time())
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

    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd, termios.TCSAFLUSH)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
        return ch


    def key_callback(self):
        try:
            self._reference_pos = deepcopy(self._arm_interface.home)
            self._last_key_update = rospy.get_time()
            key = self.getch()
            key_mapping = {'a': [1], 's': [2], 'd': [3], 'f': [4], 'g': [5], 'h': [6], 'z': [-1], 'x': [-2], 'c': [-3],
                           'v': [-4], 'b': [-5], 'n': [-6]}
            sign = 1
            n = 0
            if key == 'a':
                n = 1
            elif key == 's':
                n = 2
            elif key == 'd':
                n = 3
            elif key == 'f':
                n = 4
            elif key == 'g':
                n = 5
            elif key == 'h':
                n = 6
            elif key == 'z':
                n = 6
                sign = -1
            elif key == 'x':
                n = 2
                sign = -1
            elif key == 'c':
                n = 3
                sign = -1
            elif key == 'v':
                n = 4
                sign = -1
            elif key == 'b':
                n = 5
                sign = -1
            elif key == 'n':
                n = 6
                sign = -1
            # If deadman button is not pressed, do nothing
            for joint in self._arm_interface.joint_names:
                n -= 1
                if n==0:
                    self._reference_pos[joint] += self._axes_gain[joint] * sign / n
                    self._reference_pos[joint] = self._check_joint_limits(self._reference_pos[joint], joint)
            n = 0
            self._last_key_update = rospy.get_time()
        except:
            print('Error during keyboard parsing, message=')



if __name__ == '__main__':
    # Start the node
    node_name = "oberon_keyboard"
    rospy.init_node(node_name)
    rospy.loginfo('Starting [%s] node' % node_name)

    controller = JointPositionController()

    rospy.spin()
    rospy.loginfo('Shuting down [%s] node' % node_name)
