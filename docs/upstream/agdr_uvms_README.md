# `agdr_uvms`


> Link to the `uuv_simulator` repository [here](https://github.com/uuvsimulator/uuv_simulator)

> Link to the [documentation page of **Unmanned Underwater Vehicle Simulator**](https://uuvsimulator.github.io/packages/uuv_simulator/intro/) 

Agdr_uvms is a modified version of [**Unmanned Underwater Vehicle Simulator**](https://github.com/uuvsimulator/uuv_simulator). Now it is maintained in Dexterous Robotics Lab in Shenzhen Technology University. We made it compatible with ROS Noetic.

The **agdr_uvms** is a set of packages that include plugins and ROS applications that allow simulation of underwater vehicles in [Gazebo](http://gazebosim.org/). 


# Installation
>## Installing ROS and Catkin

For ROS-kinetic, lunar, melodic versions are not available for modification, please go to the original package address  
> Link to the `uuv_simulator` repository [here](https://github.com/uuvsimulator/uuv_simulator)。  

For ros-noetic version, please follow the steps below.    

Once you have ROS installed, make sure you have the most up to date packages:
```
rosdep update
sudo apt update
sudo apt dist-upgrade
```


 **If** your `rosdep update` meet the problems like `unable to process source [https://raw.githubusercontent.com...]`,try the way below:    

   1.Get into hosts
```
sudo apt install vim
sudo vim /etc/hosts
```
2.Add this to the hosts ,then try`rosdep update`again.
```
 151.101.76.133    raw.githubusercontent.com
```


After `apt dist-upgrade` Install [catkin](http://wiki.ros.org/catkin) the ROS build system and [wstool](https://wiki.ros.org/wstool)
```
sudo apt install ros-noetic-catkin python3-catkin-tools python3-wstool
```
>## Download uuv_simulator

Once the `ros-npetic-desktop-full` package for the desired distribution is installed, the uuv_simulator can be installed as

```
git clone https://github.com/TUSZ-AGDR/agdr_uvms.git
```


For instructions on how to install the package from source, check this [instructions page](https://uuvsimulator.github.io/installation/)  

  >## Build your Catkin Workspace  
 First we need to rename the folder, renaming the `agdr` folder to src so that it can be recognised as the `src` folder of the catkin workspace and create the root directory of the catkin workspace.  
  ```
  mv agdr_uvms src
  mkdir -p ~/catkin_ws/src
  mv src ~/catkin_ws/
  ```
Install the dependencies required by your workspace but not yet installed:
```
cd ~/catkin_ws/src

rosdep install -y --from-paths . --ignore-src --rosdistro noetic --skip-keys=python-matplotlib
```
And fill in the missing packages.
```
cd ..

sudo apt-get update

sudo apt-get install python3-pip ros-noetic-rviz ros-noetic-control ros-noetic-ros-controllers ros-noetic-velocity-controllers ros-noetic-view-controller-msgs ros-noetic-ros-control-boilerplate-dbgsym ros-noetic-ros-controllers-cartesian

sudo pip install pymap3d==1.5.2

sudo pip3 install scipy casadi
```
The next command will configure your catkin workspace:
```
catkin build
```
Source the catkin workspace:
```
source ~/catkin_ws/devel/setup.bash
```
Optional: add the previous command to your `.bashrc`:
```
echo 'source ~/catkin_ws/devel/setup.bash' >> ~/.bashrc
```
  >## Roslaunch

Executing the following command, we can see in gazebo that `herkules_ship_wreck`
```
roslaunch uuv_gazebo_worlds herkules_ship_wreck.launch
```
![gazebo](./photos/1.jpg)

By executing the following command, we can view the status of uuv in both gazebo and rviz
```
roslaunch rexrov2_gazebo start_demo_pid_controller.launch
```
![gazebo](./photos/2.jpg)

To generate a spiral path with two turns, run the following command
```
roslaunch uuv_control_utils start_helical_trajectory.launch uuv_name:=rexrov2 n_turns:=2
```
![gazebo](./photos/3.jpg)

  >## Start Joystick Control
Firstly, make sure the joystick is connected, confirm your joy_id,Then start each of these files.

1.Load the gazebo environment
```
roslaunch uuv_gazebo_worlds subsea_bop_panel.launch
```
2.Load uvms
```
roslaunch uuv_descriptions upload_rexrov_oberon_arms.launch mode:=default x:=0 y:=0 z:=-40 namespace:=rexrov
```
3.Joystick remote control robot arm or ROV separately

**Notice**: Holding down the RB of the Joystick to control UUVM is to control only the ROV movement, holding down the LB of the Joystick is to control UUVM is to control only the robot arm movement.

```
roslaunch oberon7_control uuv_oberon7_separate_teleop.launch uuv_name:=rexrov model_name:=rexrov joy_id:=0
```
Or joystick remote control robot arm and ROV move simultaneously (Hold on LB to control is)

**Notice**: Holding down the RB of the Joystick to control UUVM is to control the cooperative movement of the robot arm and ROV, holding down the LB and RB of the Joystick to control UUVM is to control only the ROV movement, holding down the home and RB of the Joystick is to control UUVM is to control only the robot arm movement.

```
roslaunch oberon7_control uuv_oberon7_cooperate_teleop.launch uuv_name:=rexrov model_name:=rexrov joy_id:=0
```
# Features

> **Gazebo/ROS plugins**

- Implementation of Fossen's equations of motion for underwater vehicles
- Thruster modules with implementations for thruster's angular velocity to output thrust force based on [`Yoerger el al., 1990`](http://dx.doi.org/10.1109/48.107145) and [`Bessa et al., 2006`](http://www.abcm.org.br/symposium-series/SSM_Vol2/Section_IX_Submarine_Robotics/SSM2_IX_01.pdf)
- Lift and drag plugin for simulation of fins
- Simulation of 3D current velocity models (constant or based on first-order Gauss-Markov processes)
- Sensor plugins

> **Controllers**

- For AUVs
    - [`casadi`](https://web.casadi.org/)-based effort allocation algorithm 
    - Geometric tracking PD controller
- For ROVs
    - Thruster manager with computation of the thruster allocation matrix based on the thruster frames available in `/tf`
    - Model-based feedback linearization controller ([`Fossen, 2011`](https://www.wiley.com/en-us/Handbook+of+Marine+Craft+Hydrodynamics+and+Motion+Control-p-9781119991496))
    - Nonlinear PID controller ([`Fossen, 2011`](https://www.wiley.com/en-us/Handbook+of+Marine+Craft+Hydrodynamics+and+Motion+Control-p-9781119991496))
    - Non-model-based sliding mode controller ([`García-Valdovinos el al., 2014`](https://journals.sagepub.com/doi/full/10.5772/56810) and [`Salgado-Jiménez et al., 2011`](http://cdn.intechopen.com/pdfs/15221.pdf))
    - PD controller with restoration forces compensation 
    - 6-DOF PID controller
    - Singularity-free tracking controller ([`Fjellstad and Fossen, 1994`](https://ieeexplore.ieee.org/abstract/document/411068))
- Teleoperation nodes for AUVs and ROVs

> **Gazebo world models**

- Ocean wave shaders for wave animation
- Scenarios from the SWARMs project demonstration locations (e.g. Mangalia, Romania and Trondheim, Norway)
- Subsea BOP panel for manipulation tasks

> **Vehicle models**

- Work-class ROV `rexrov` based on the model presetend in [`Berg, 2012`](https://brage.bibsys.no/xmlui/handle/11250/238170?locale-attribute=no)
- [`eca_a9`](https://github.com/uuvsimulator/eca_a9)
- [`lauv_gazebo`](https://github.com/uuvsimulator/lauv_gazebo)
- [`desistek_saga`](https://github.com/uuvsimulator/desistek_saga)
- [`rexrov2`](https://github.com/uuvsimulator/rexrov2)

# License

Agdr_uvms is open-sourced under the Apache-2.0 license. See the
[LICENSE](https://github.com/TUSZ-AGDR/agdr_uvms/blob/main/LICENSE.txt) file for details.

For a list of other open source components included in UUV Simulator, see the
file [3rd-party-licenses.txt](https://github.com/TUSZ-AGDR/agdr_uvms/blob/main/3rd-party-licenses.txt).

