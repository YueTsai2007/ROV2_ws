#!/usr/bin/env python3
"""Regression checks for sampling a path before its first control update."""
import logging
import unittest
from unittest.mock import Mock

from uuv_trajectory_generator.wp_trajectory_generator import WPTrajectoryGenerator


class WaypointSamplingTest(unittest.TestCase):
    def setUp(self):
        self.generator = WPTrajectoryGenerator.__new__(WPTrajectoryGenerator)
        self.generator._logger = logging.getLogger('waypoint_sampling_test')
        self.generator._interp_method = 'test'
        self.interpolator = Mock()
        self.generator._path_generators = {'test': self.interpolator}

    def test_initializes_before_first_sample(self):
        self.generator._has_started = False
        self.interpolator.init_interpolator.return_value = True
        self.interpolator.get_samples.return_value = ['path']
        self.assertEqual(self.generator.get_samples(0.1), ['path'])
        self.interpolator.init_interpolator.assert_called_once_with()
        self.interpolator.get_samples.assert_called_once_with(0.0, 0.1)

    def test_reports_failed_initialization(self):
        self.generator._has_started = False
        self.interpolator.init_interpolator.return_value = False
        self.assertIsNone(self.generator.get_samples())
        self.interpolator.get_samples.assert_not_called()

    def test_does_not_reinitialize_running_interpolator(self):
        self.generator._has_started = True
        self.generator.get_samples()
        self.interpolator.init_interpolator.assert_not_called()


if __name__ == '__main__':
    unittest.main()
