#!/usr/bin/python3
import rospy
import os
import numpy as np
from copy import deepcopy
import PyKDL
from uuv_manipulators_control import CartesianController

class JCartesianController(CartesianController):
    """
    Jacobian transpose controller
    """

    LABEL = 'Jacobian transpose cartesian controller'

    def __init__(self):
        """
        Class constructor
        """
        # 初始化父类
        CartesianController.__init__(self)

        # 定义 Kp 和 Kd
        self._Kp = [10000.0, 10000.0, 10000.0, 1500.0, 1500.0, 1500.0]
        self._Kd = [3.0, 3.0, 3.0, 1.0, 1.0, 1.0]
        rospy.loginfo('Kp=%s', str(self._Kp))
        rospy.loginfo('Kd=%s', str(self._Kd))

        # 定义目标坐标 (x, y, z, roll, pitch, yaw)
        self._target_position = [1,1,-46, 0,0, 0]#水下环境请用这条
        #self._target_position = [1,1,2, 0,0, 0]#陆地环境用这条
        rospy.loginfo('Target Position: %s', str(self._target_position))

        self._reference_pos = dict()
        for joint in self._arm_interface.joint_names:
            self._reference_pos[joint] = deepcopy(self._arm_interface.home[joint])

        self._run()  # 启动控制循环

    def _get_goal(self):
        """
        Generate the goal frame based on the target position (x, y, z, roll, pitch, yaw)
        """
        target_frame = PyKDL.Frame()
        target_frame.p = PyKDL.Vector(self._target_position[0], 
                                      self._target_position[1], 
                                      self._target_position[2])
        target_frame.M = PyKDL.Rotation.RPY(self._target_position[3],
                                            self._target_position[4],
                                            self._target_position[5])
        rospy.loginfo("Target frame (position): %s", str(self._target_position))
        return target_frame

    def _update(self):
        """
        Update control logic
        """
        rospy.loginfo("Entered Jac_update loop")
        if rospy.is_shutdown() or self._last_goal is None:
            rospy.loginfo("Jac problems, last_goal not set")
            return

        goal = self._get_goal()
        rospy.loginfo("Goal position: %s", str(goal))

        # 获取末端执行器的当前位姿和速度
        ee_pose = self._arm_interface.get_ee_pose_as_frame()
        ee_vel = self._arm_interface.get_ee_vel_as_kdl_twist()

        # 计算位姿误差
        error = PyKDL.diff(goal, ee_pose)

        # 计算速度
        velocity = np.matrix(np.zeros(6)).T
        self._initial_velocity = [1, 1, 0.5, 0.5, 0.5, 0.5]
        for i in range(len(velocity)):
            velocity[i] = -(self._Kp[i] * error[i] + self._Kd[i] * ee_vel[i]) + self._initial_velocity[i]

        # 计算雅克比矩阵及其转置
        J = self._arm_interface.jacobian()
        JT = self._arm_interface.jacobian_transpose()
        rospy.loginfo("Jacobian: %s", str(J))
        rospy.loginfo("Jacobian Transpose: %s", str(JT))

        I = np.eye(6)
        la = 0.1

        # 计算关节力矩
        tau = JT * np.linalg.pinv(J * JT + la**2 * I) * velocity
        rospy.loginfo("Calculated joint efforts: %s", str(tau))

        # 发布力矩
        self.publish_joint_efforts(tau)

        # 发布目标位置
        self.publish_goal()

if __name__ == '__main__':
    node_name = os.path.splitext(os.path.basename(__file__))[0]
    rospy.init_node(node_name)
    rospy.loginfo('Starting [%s] node' % node_name)

    jt_controller = JCartesianController()

    rospy.spin()
    rospy.loginfo('Shutting down [%s] node' % node_name)

