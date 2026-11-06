#!/usr/bin/env python3
"""Static consistency checks, independent of ROS and Gazebo."""
from pathlib import Path
import importlib.util
import unittest
import xml.etree.ElementTree as ET
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('generate_tam', ROOT / 'scripts/generate_tam.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

class GeometryTest(unittest.TestCase):
    def test_thruster_geometry_and_tam(self):
        cfg = yaml.safe_load((ROOT / 'config/thruster_manager.yaml').read_text())
        b = gen.matrix(cfg)
        stored = np.array(yaml.safe_load((ROOT / 'config/TAM.yaml').read_text())['tam'])
        np.testing.assert_allclose(stored, b, atol=1e-12)
        self.assertEqual(np.linalg.matrix_rank(b, tol=1e-8), 5)
        self.assertLess(np.linalg.norm(np.linalg.pinv(b), 2), 10)
        cad = ET.parse(ROOT / 'urdf/underwater_robot.urdf').getroot()
        root = ET.parse(ROOT / 'urdf/underwater_robot_uuv2.xacro').getroot()
        plugins = {int(p.findtext('thrusterID')): p for p in root.findall('./gazebo/plugin') if p.find('thrusterID') is not None}
        self.assertEqual(set(plugins), set(range(6)))
        for i in range(6):
            item = cfg['thrusters']['thruster_%d' % i]
            cad_joint = cad.find("joint[@name='%s']" % item['joint'])
            cad_origin = np.fromstring(cad_joint.find('origin').get('xyz'), sep=' ')
            cad_axis = np.fromstring(cad_joint.find('axis').get('xyz'), sep=' ')
            np.testing.assert_allclose(item['origin'], cad_origin)
            np.testing.assert_allclose(item['direction'], cad_axis / np.linalg.norm(cad_axis))
            expected = np.r_[item['direction'], np.cross(item['origin'], item['direction'])]
            np.testing.assert_allclose(b[:, i], expected, atol=1e-12)
            joint = root.find("joint[@name='thruster_%d_joint']" % i)
            origin = np.fromstring(joint.find('origin').get('xyz'), sep=' ')
            axis = np.fromstring(joint.find('axis').get('xyz'), sep=' ')
            np.testing.assert_allclose(origin, cfg['thrusters']['thruster_%d' % i]['origin'])
            np.testing.assert_allclose(axis, cfg['thrusters']['thruster_%d' % i]['direction'])
            self.assertEqual(plugins[i].findtext('jointName'), 'thruster_%d_joint' % i)
            self.assertEqual(plugins[i].findtext('linkName'), 'thruster_%d_link' % i)
            self.assertEqual(float(plugins[i].findtext('./conversion/rotorConstant')), cfg['thruster_manager']['conversion_fcn_params']['gain'])

    def test_launch_xml(self):
        for name in ['bringup.launch', 'underwater_uuv.launch', 'start_uuv_pid_controller.launch']:
            self.assertEqual(ET.parse(ROOT / 'launch' / name).getroot().tag, 'launch')

if __name__ == '__main__':
    unittest.main()
