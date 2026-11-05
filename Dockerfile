FROM osrf/ros:noetic-desktop-full

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/rov2_ws

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-catkin-tools python3-pip python3-rosdep \
    python3-matplotlib python3-scipy \
    ros-noetic-joy ros-noetic-joint-state-publisher-gui \
    ros-noetic-ros-control ros-noetic-ros-controllers \
    ros-noetic-gazebo-ros-control ros-noetic-view-controller-msgs \
    && rm -rf /var/lib/apt/lists/*

COPY src/ src/
RUN rosdep update --include-eol-distros \
    && apt-get update \
    && rosdep install --from-paths src --ignore-src --rosdistro noetic \
       --skip-keys=python-matplotlib -r -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir pymap3d==1.5.2 'casadi<3.7'

RUN source /opt/ros/noetic/setup.bash && catkin_make -j2
COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
