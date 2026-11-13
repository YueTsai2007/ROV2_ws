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

    def test_demo_keyboard_filters_ansi_escape_and_restores_terminal(self):
        class FakeTwist:
            def __init__(self):
                self.linear = SimpleNamespace(x=0.0, y=0.0, z=0.0)
                self.angular = SimpleNamespace(x=0.0, y=0.0, z=0.0)

        chars = iter(['\x1b', '[', 'D', '\x03'])
        fake_stdin = SimpleNamespace(
            isatty=lambda: True,
            fileno=lambda: 0,
            read=lambda n=1: next(chars),
        )
        fake_termios = Mock(TCSADRAIN=1)
        fake_termios.tcgetattr.return_value = ['saved_settings']
        fake_tty = Mock()
        published = []
        self.ros.ROSException = type('ROSException', (Exception,), {})
        self.ros.is_shutdown.return_value = False
        self.ros.get_param.side_effect = lambda name, default: default

        def publish_and_fail_on_stop(msg):
            published.append((msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.z))
            raise self.ros.ROSException('publisher closed')

        self.ros.Publisher.return_value.publish.side_effect = publish_and_fail_on_stop
        with patch.dict(sys.modules, {
            'termios': fake_termios,
            'tty': fake_tty,
            'geometry_msgs': Mock(),
            'geometry_msgs.msg': SimpleNamespace(Twist=FakeTwist),
        }):
            kb = load_script('demo_keyboard')
            with patch.object(kb.sys, 'stdin', fake_stdin), \
                 patch.object(kb.select, 'select', return_value=([fake_stdin], [], [])):
                kb.main()

        self.assertTrue(all(v == (0.0, 0.0, 0.0, 0.0) for v in published))
        fake_termios.tcsetattr.assert_called_once_with(fake_stdin, fake_termios.TCSADRAIN, ['saved_settings'])

    def test_demo_command_guard_monotonic_ordering_and_safe_stop(self):
        guard = load_script('demo_command_guard')
        buf = guard.CommandBuffer(10.0, 0.5)
        with patch.object(guard.time, 'monotonic', side_effect=[10.0, 10.1]):
            buf.accept(0, 5.0)
            self.assertEqual(buf.values()[0], 5.0)
        buf.accept(1, 3.0, now=10.5)
        self.assertEqual(buf.values(now=10.2)[1], 0.0)
        self.assertEqual(buf.values(now=10.6)[:2], [0.0, 3.0])

        self.ros.ROSException = type('ROSException', (Exception,), {})
        self.ros.is_shutdown.return_value = True
        self.ros.get_param.side_effect = lambda name, default: default
        self.ros.Publisher.return_value.publish.side_effect = self.ros.ROSException('closed')
        with patch.dict(sys.modules, {
            'uuv_gazebo_ros_plugins_msgs': Mock(),
            'uuv_gazebo_ros_plugins_msgs.msg': SimpleNamespace(
                FloatStamped=lambda: SimpleNamespace(header=SimpleNamespace(stamp=None), data=0.0)
            ),
        }):
            guard.main()

    def test_demo_command_guard_normalizes_output_prefix(self):
        guard = load_script('demo_command_guard')
        self.assertEqual(guard.normalize_output_prefix(''), 'thrusters')
        self.assertEqual(guard.normalize_output_prefix('/'), 'thrusters')
        self.assertEqual(guard.normalize_output_prefix('thrusters/'), 'thrusters')
        self.assertEqual(guard.normalize_output_prefix('/ns/thrusters/'), '/ns/thrusters')

        self.ros.ROSException = type('ROSException', (Exception,), {})
        self.ros.is_shutdown.return_value = True
        self.ros.get_param.side_effect = lambda name, default: '/' if name == '~output_prefix' else default
        with patch.dict(sys.modules, {
            'uuv_gazebo_ros_plugins_msgs': Mock(),
            'uuv_gazebo_ros_plugins_msgs.msg': SimpleNamespace(
                FloatStamped=lambda: SimpleNamespace(header=SimpleNamespace(stamp=None), data=0.0)
            ),
        }):
            guard.main()
        topics = [call.args[0] for call in self.ros.Publisher.call_args_list]
        self.assertEqual(topics, [f'thrusters/{i}/input' for i in range(6)])


if __name__ == '__main__':
    unittest.main()
