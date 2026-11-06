# Round 1 repair: work in progress

This branch is an incomplete integration baseline. It has not passed ROS/Gazebo
testing and must not be treated as a working PID control loop.

Implemented: the underwater-object link configuration, a PoseGT plugin definition,
the invalid PID launch substitution and RViz path, and zero integral gains.

Blocking work before bringup:
- Verify CAD link masses, inertias and displaced volume; 0.021 m^3 is the old,
  unvalidated value. Damping and zero added mass are only interface placeholders.
- Replace the six thruster plugins and align their force application points,
  thrust axes, IDs, gain, URDF geometry, TAM and real joint state publication.
- Remove duplicate model/state publishers from the control launch after the
  replacement state publisher is implemented. Rebuild and test the TAM, including
  rank and reference point, and add a gated bringup.
- On Ubuntu 20.04 / ROS Noetic, build and verify model expansion, plugin loading,
  odometry frames and velocities, each thruster in isolation, allocation, and
  controller convergence. No ROS or Gazebo runtime was available for this commit.

Do not start the existing PID launch together with the model launch: it still
contains duplicate state/model publishers. The original six thruster plugins and
TAM are also known to be inconsistent. This branch preserves them for the next
change rather than claiming that the control chain is functional.
