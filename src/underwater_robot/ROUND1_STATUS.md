# Underwater robot round 1: integration in progress

This is an unvalidated simulation integration, not a calibrated vehicle model.
The branch must not be considered to have passed the PID acceptance test.

## Changes

* The model keeps the SolidWorks URDF intact and adds six provisional 0.01 kg
  thruster links at the CAD joint positions. Logical IDs 0..5 correspond to
  J1, J2, J5, J6, J7, J8. The Gazebo ROS joint-state plugin reports both CAD and
  auxiliary joints. CAD rotor motion is not coupled to auxiliary rotors.
* Gazebo and the allocator use gain 0.001. TAM columns use the same positions
  and axes as the auxiliary joints, referred to the base link origin. The
  generator truncates singular values below 1e-8 to prevent the upstream
  pseudoinverse from amplifying CAD rounding. Effective rank is 5, not 6.
* `bringup.launch` defaults to paused simulation and does not start the PID.
  `start_controller:=true` is only a convenience; roslaunch includes do not
  provide readiness ordering. For validation start components separately.

## Critical limitations

The CAD links total roughly 232.79 kg but the inherited displaced volume is
0.021 m^3. The forces do not balance. Do not run uncontrolled dynamic tests
until CAD mass, centers of mass, inertias, displaced volume and buoyancy center
have been independently checked and updated. Auxiliary masses and damping are
placeholders; zero added mass is an interface baseline, not a physical model.
The simulator applies force to auxiliary link centers of mass. Validate actual
Gazebo force axes, moments, collision behavior and rotor reaction effects.
The provisional P/D gains are not tuned; with rank 5, arbitrary 6D commands
cannot be followed. PoseGT publishes world-frame velocities in this upstream
implementation: verify the controller's expected twist frame before PID tests.

## Reproduce static checks

```sh
python3 src/underwater_robot/scripts/generate_tam.py
python3 src/underwater_robot/test/test_geometry.py
rosrun xacro xacro src/underwater_robot/urdf/underwater_robot_uuv2.xacro namespace:=underwater_robot > /tmp/rov.urdf
check_urdf /tmp/rov.urdf
```

## Staged runtime tests on Ubuntu 20.04 and ROS Noetic

Build the workspace with its dependencies and source `devel/setup.bash`.
After correcting the physical model, start the world and model paused with
`roslaunch underwater_robot bringup.launch gui:=true`. Check the Gazebo log for
all plugins, unpause, and verify `/underwater_robot/pose_gt`, `/joint_states`
under the vehicle namespace, and world-to-base and joint transforms.

With the PID and allocator stopped, command each input topic independently in
both directions and observe force and torque. Stop each command and explicitly
send zero before testing the next one. Verify the six ROS input subscribers and
joint-state feedback. Next start the allocator alone using the upstream
`thruster_manager.launch` with this package's config and TAM; test small wrench
commands and compare each thrust with the stored TAM. Finally start the PID
launch, verify the velocity frame and reference, begin with small feasible
setpoints, and check convergence, saturation and stability. Never run a manual
publisher simultaneously with the allocator. No stage has been verified here.
