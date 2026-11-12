#!/usr/bin/env python3
"""Regression checks for real control methods; no ROS master or actuators."""
import ast
import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch
import numpy as np
import rospy
from geometry_msgs.msg import Twist, WrenchStamped
from uuv_trajectory_generator import TrajectoryPoint
from uuv_control_interfaces.dp_controller_local_planner import DPControllerLocalPlanner

ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT.parent/'uuv_simulator/uuv_control'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def method(path,name,namespace):
    tree=ast.parse(path.read_text())
    node=next(n for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body
              if isinstance(n,ast.FunctionDef) and n.name==name)
    unit=ast.Module(body=[node],type_ignores=[]); ast.fix_missing_locations(unit)
    exec(compile(unit,str(path),'exec'),namespace)
    return namespace[name]


class ControlTests(unittest.TestCase):
    def planner(self):
        p=DPControllerLocalPlanner.__new__(DPControllerLocalPlanner)
        p._logger=logging.getLogger('test')
        p._vehicle_pose=TrajectoryPoint(); p._vehicle_pose.pos=np.array([0.,0.,-3.])
        p._vehicle_pose.rotq=np.array([2**-.5,0,0,2**-.5])
        p._is_automatic=False; p._last_teleop_update=None
        p._last_teleop_reference_time=None; p._teleop_timeout=.5
        p._teleop_vel_ref=None; p._max_forward_speed=.2
        p.init_odom_event=threading.Event(); p.init_odom_event.set()
        return p

    def test_teleop_rotates_once_and_has_matching_velocity(self):
        p=self.planner(); cmd=Twist(); cmd.linear.y=.1
        with patch('rospy.get_time',return_value=1.): p._update_teleop(cmd)
        with patch('rospy.get_time',return_value=1.05): ref=p._calc_teleop_reference()
        np.testing.assert_allclose(ref.pos-p._vehicle_pose.pos,[0,0,.005],atol=1e-12)
        np.testing.assert_allclose(ref.vel[:3],[0,0,.1],atol=1e-12)

    def test_zero_and_stale_commands_stop_reference_velocity(self):
        p=self.planner(); cmd=Twist(); cmd.linear.x=.1
        with patch('rospy.get_time',return_value=1.): p._update_teleop(cmd)
        with patch('rospy.get_time',return_value=2.): ref=p._calc_teleop_reference()
        np.testing.assert_array_equal(ref.vel,np.zeros(6))
        with patch('rospy.get_time',return_value=2.1): p._update_teleop(Twist())
        np.testing.assert_array_equal(p._this_ref_pnt.vel,np.zeros(6))
        self.assertFalse(p._is_teleop_active)

    def test_nonfinite_teleop_is_rejected(self):
        p=self.planner(); cmd=Twist(); cmd.linear.x=float('nan')
        with patch('rospy.get_time',return_value=1.),patch('rospy.logwarn_throttle'):
            p._update_teleop(cmd)
        self.assertFalse(p._is_teleop_active)

    def test_configured_saturation_is_used_by_real_initializer_and_output(self):
        path=CONTROL/'uuv_trajectory_control/src/uuv_control_interfaces/dp_controller_base.py'
        tree=ast.parse(path.read_text()); cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        # Exercise the actual constructor prefix through parameter validation,
        # before it allocates any ROS publishers/services.
        cut=next(i for i,n in enumerate(init.body) if isinstance(n,ast.Assign) and
                 any(isinstance(t,ast.Attribute) and t.attr=='use_auv_control_allocator' for t in n.targets))
        init.body=init.body[:cut]
        fake=SimpleNamespace(get_param=lambda n,d=None:100 if n=='~saturation' else d,
             has_param=lambda n:False,get_namespace=lambda:'/underwater_robot/',ROSException=ValueError)
        ns={'np':np,'rospy':fake,'get_logger':lambda:logging.getLogger('test'),
            'LocalPlanner':lambda **k:None}
        unit=ast.Module(body=[init],type_ignores=[]); ast.fix_missing_locations(unit)
        exec(compile(unit,str(path),'exec'),ns)
        instance=SimpleNamespace(); ns['__init__'](instance)
        self.assertEqual(instance._control_saturation,100)
        captured=[]
        instance.odom_is_init=True; instance.thrusters_only=True
        instance._vehicle_model=SimpleNamespace(body_frame_id='base_link')
        instance._thrust_pub=SimpleNamespace(publish=captured.append)
        ns={'np':np,'rospy':rospy,'WrenchStamped':WrenchStamped}
        publish=method(path,'publish_control_wrench',ns)
        with patch('rospy.Time.now',return_value=rospy.Time(1)):
            publish(instance,np.array([1000.,0,0,0,0,0]))
        self.assertEqual(captured[-1].wrench.force.x,100)

    def test_allocator_timeout_uses_wall_clock_and_clears_all_outputs(self):
        path=CONTROL/'uuv_thruster_manager/scripts/thruster_allocator.py'
        ns={'time':SimpleNamespace(monotonic=lambda:10.6)}
        stop=method(path,'stop_thrusters',ns); check=method(path,'check_timeout',ns)
        captured=[]
        node=SimpleNamespace(_command_lock=threading.RLock(),thrust=np.ones(6),
            config={'timeout':.5},_last_command_wall=10.,_watchdog_stopped=False)
        node.command_thrusters=lambda:captured.append(node.thrust.copy())
        node.stop_thrusters=lambda:stop(node)
        check(node)
        np.testing.assert_array_equal(captured[-1],np.zeros(6))
        self.assertTrue(node._watchdog_stopped)

    def test_guard_limits_rejects_invalid_and_expires_independently(self):
        guard=load('demo_guard',ROOT/'scripts/demo_command_guard.py')
        state=guard.CommandBuffer(10,.5)
        state.accept(0,100,1); state.accept(1,float('nan'),1)
        self.assertEqual(state.values(1.1)[:2],[10,0])
        self.assertEqual(state.values(1.6),[0]*6)

    def test_demo_geometry_mass_and_generated_files(self):
        import yaml,xml.etree.ElementTree as ET
        gen=load('demo_model_generator',ROOT/'scripts/generate_demo_model.py')
        xml,config,tam=gen.build()
        self.assertEqual((ROOT/'urdf/underwater_robot_demo.xacro').read_text(),xml)
        root=ET.fromstring(xml)
        self.assertEqual(len(root.findall("./link[@name='base_link']/visual")),11)
        mass=sum(float(n.get('value')) for n in root.findall('./link/inertial/mass'))
        self.assertAlmostEqual(mass,25.06)
        b=np.array(tam['tam'])
        self.assertEqual(np.linalg.matrix_rank(b,tol=1e-8),5)
        self.assertEqual(np.linalg.matrix_rank(b[[0,1,2,5]],tol=1e-8),4)
        np.testing.assert_allclose(b,yaml.safe_load((ROOT/'config/demo_TAM.yaml').read_text())['tam'])
        self.assertEqual(config['thruster_manager']['max_thrust'],8)
        # CAD vertical axes become the standard body +Z direction.
        np.testing.assert_allclose(b[:3,2:4],[[0,0],[0,0],[1,1]],atol=1e-12)


if __name__=='__main__': unittest.main()
