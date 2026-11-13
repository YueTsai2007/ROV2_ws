#!/usr/bin/env python
# Copyright (c) 2016-2019 The UUV Simulator Authors.
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
from __future__ import print_function
import numpy
import time
import threading
import rospy
import tf
import tf.transformations as trans
from os.path import isdir, join
from copy import deepcopy
import yaml
import tf2_ros
from uuv_thrusters import ThrusterManager
from geometry_msgs.msg import Wrench, WrenchStamped
from uuv_thruster_manager.srv import *


class ThrusterAllocatorNode(ThrusterManager):
    """The thruster allocator node allows a client node 
    to command the thrusters.
    """

    def __init__(self):
        """Class constructor."""
        ThrusterManager.__init__(self)

        self.last_update = rospy.Time.now()
        self._last_command_wall = time.monotonic()
        self._command_lock = threading.RLock()
        self._watchdog_stopped = False
        rospy.on_shutdown(self.stop_thrusters)

        # Subscriber to the wrench to be applied on the UUV
        self.input_sub = rospy.Subscriber('thruster_manager/input',
                                          Wrench, self.input_callback)

        # To deliver the wrench input with an option to use another body frame
        # (options: base_link and base_link_ned), use the wrench stamped
        # message
        self.input_stamped_sub = rospy.Subscriber(
            'thruster_manager/input_stamped', WrenchStamped,
            self.input_stamped_callback)
        self.thruster_info_service = rospy.Service(
            'thruster_manager/get_thrusters_info', ThrusterManagerInfo,
            self.get_thruster_info)
        self.curve_calc_service = rospy.Service(
            'thruster_manager/get_thruster_curve', GetThrusterCurve,
            self.get_thruster_curve)
        self.set_thruster_manager_config_service = rospy.Service(
            'thruster_manager/set_config', SetThrusterManagerConfig,
            self.set_config)
        self.get_thruster_manager_config_service = rospy.Service(
            'thruster_manager/get_config', GetThrusterManagerConfig,
            self.get_config)

        while not rospy.is_shutdown():
            self.check_timeout()
            # Actuator timeout must also expire when /clock is paused.
            time.sleep(1.0 / max(1, self.config['update_rate']))

    def stop_thrusters(self):
        with self._command_lock:
            if self.thrust is not None:
                self.thrust.fill(0)
                self.command_thrusters()
            self._watchdog_stopped = True

    def check_timeout(self):
        with self._command_lock:
            if (self.config['timeout'] > 0 and not self._watchdog_stopped and
                    time.monotonic() - self._last_command_wall > self.config['timeout']):
                self.stop_thrusters()

    def accept_wrench(self, force, torque, frame_id=None):
        with self._command_lock:
            if not self.ready:
                return
            if (not numpy.isfinite(numpy.r_[force, torque]).all() or
                    frame_id not in (None, self.config['base_link'], self.config['base_link'] + '_ned') or
                    (frame_id == self.config['base_link'] + '_ned' and self.base_link_ned_to_enu is None)):
                self.stop_thrusters()
                rospy.logwarn_throttle(1, 'Rejected invalid thruster wrench or frame')
                return
            self.publish_thrust_forces(force, torque, frame_id)
            self.last_update = rospy.Time.now()
            self._last_command_wall = time.monotonic()
            self._watchdog_stopped = False

    def get_thruster_info(self, request):
        """Return service callback with thruster information."""
        return ThrusterManagerInfoResponse(
            self.n_thrusters,
            self.configuration_matrix.flatten().tolist(),
            self.namespace + self.config['base_link'])

    def get_thruster_curve(self, request):
        """Return service callback for computation of thruster curve."""
        if self.n_thrusters == 0:
            return GetThrusterCurveResponse([], [])
        # TODO Get thruster index, for the case the vehicle has different
        # models
        input_values, thrust_values = self.thrusters[0].get_curve(
            request.min, request.max, request.n_points)
        return GetThrusterCurveResponse(input_values, thrust_values)

    def set_config(self, request):
        old_config = deepcopy(self.config)
        self.ready = False
        self.config['base_link'] = request.base_link
        self.config['thruster_frame_base'] = request.thruster_frame_base
        self.config['thruster_topic_prefix'] = request.thruster_topic_prefix
        self.config['thruster_topic_suffix'] = request.thruster_topic_suffix
        self.config['timeout'] = request.timeout
        print('New configuration:\n')
        for key in self.config:
            print(key, '=', self.config[key])
        if not self.update_tam(recalculate=True):
            print('Configuration parameters are invalid, going back to old configuration...')
            self.config = old_config
            self.update_tam(recalculate=True)
        return SetThrusterManagerConfigResponse(True)

    def get_config(self, request):
        return GetThrusterManagerConfigResponse(
            self.namespace,
            self.config['base_link'],
            self.config['thruster_frame_base'],
            self.config['thruster_topic_prefix'],
            self.config['thruster_topic_suffix'],
            self.config['timeout'],
            self.config['max_thrust'],
            self.n_thrusters,
            self.configuration_matrix.flatten().tolist())

    def input_callback(self, msg):
        """
        Callback to the subscriber that receiver the wrench to be applied on
        UUV's BODY frame.
        @param msg Wrench message
        """
        if not self.ready:
            return

        force = numpy.array((msg.force.x, msg.force.y, msg.force.z))
        torque = numpy.array((msg.torque.x, msg.torque.y, msg.torque.z))

        # This mode assumes that the wrench is given wrt thruster manager
        # configured base_link reference
        self.accept_wrench(force, torque)

    def input_stamped_callback(self, msg):
        """
        Callback to the subscriber that receiver the stamped wrench to be
        applied on UUV's BODY frame.
        @param msg Stamped wrench message
        """
        if not self.ready:
            return

        force = numpy.array(
            (msg.wrench.force.x, msg.wrench.force.y, msg.wrench.force.z))
        torque = numpy.array(
            (msg.wrench.torque.x, msg.wrench.torque.y, msg.wrench.torque.z))

        # Send the frame ID for the requested wrench
        frame_id = msg.header.frame_id.split('/')[-1] if msg.header.frame_id else None
        self.accept_wrench(force, torque, frame_id)


if __name__ == '__main__':
    rospy.init_node('thruster_allocator')

    try:
        node = ThrusterAllocatorNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        print('ThrusterAllocatorNode::Exception')
    print('Leaving ThrusterAllocatorNode')
