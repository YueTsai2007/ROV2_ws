cmake_minimum_required(VERSION 2.8.3)

project(underwater_robot)

find_package(catkin REQUIRED)

catkin_package()

find_package(roslaunch)

foreach(dir config launch meshes urdf)
	install(DIRECTORY ${dir}/
		DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/${dir})
endforeach(dir)

# Install executable wrappers for both devel and install spaces (ROS Noetic).
catkin_install_python(PROGRAMS
  scripts/arm_control_node.py
  scripts/publish_default_joint_states.py
  scripts/set_clean_urdf.py
  scripts/spawn_fixed.py
  scripts/generate_tam.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
