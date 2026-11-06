#!/usr/bin/env python3
"""Regression tests for command routing and spawn failures without a ROS master."""
import importlib.util
from pathlib import Path
import sys
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeScriptsTest(unittest.TestCase):
    def setUp(self):
        self.ros = Mock()
        self.modules = patch.dict(sys.modules, {
            'rospy': self.ros,
            'sensor_msgs': Mock(),
            'sensor_msgs.msg': SimpleNamespace(JointState=Mock()),
            'std_msgs': Mock(),
            'std_msgs.msg': SimpleNamespace(Float64=SimpleNamespace),
            'rospkg': SimpleNamespace(RosPack=lambda: SimpleNamespace(get_path=lambda _: str(ROOT))),
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_default_start_waits_for_commands(self):
        self.ros.get_param.side_effect = lambda name, default: default
        self.ros.ROSInterruptException = type('ROSInterruptException', (Exception,), {})
        runpy.run_path(str(ROOT / 'scripts/arm_control_node.py'), run_name='__main__')
        self.ros.spin.assert_called_once_with()
        self.ros.Publisher.return_value.publish.assert_not_called()

    def test_external_command_reaches_controller(self):
        controller = load_script('arm_control_node').ArmController()
        controller.arm_command_callback(SimpleNamespace(data=0.25))
        self.assertEqual(controller.arm_pub.publish.call_args.args[0].data, 0.25)
        self.assertEqual(controller.target_angle, 0.25)
        self.assertEqual(self.ros.Subscriber.call_args_list[0].args[0],
                         '/underwater_robot/joint_states')

    def test_invalid_command_does_not_publish_or_change_target(self):
        controller = load_script('arm_control_node').ArmController()
        for value in [float('nan'), float('inf'), -float('inf')]:
            controller.arm_command_callback(SimpleNamespace(data=value))
        controller.arm_pub.publish.assert_not_called()
        self.assertEqual(controller.target_angle, 0.0)

    def test_joint_state_without_positions_is_valid(self):
        controller = load_script('arm_control_node').ArmController()
        controller.joint_state_callback(SimpleNamespace(name=['arm1'], position=[]))

    def test_spawn_uses_package_resources_and_returns_failure(self):
        module = load_script('spawn_fixed')
        with patch.object(module.subprocess, 'call', return_value=7) as spawn:
            self.assertEqual(module.main(), 7)
        argv = spawn.call_args.args[0]
        self.assertEqual(argv[:4], ['rosrun', 'gazebo_ros', 'spawn_model', '-string'])
        self.assertIn('<robot', argv[4])
        self.assertIn('-urdf', argv)


if __name__ == '__main__':
    unittest.main()
