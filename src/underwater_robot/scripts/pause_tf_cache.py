#!/usr/bin/env python3
"""Republish the last robot dynamic transforms to late listeners while paused."""
import copy
import threading
import time
import xml.etree.ElementTree as ET

import rospy
from gazebo_msgs.srv import GetLinkState, GetPhysicsProperties
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage


def initial_snapshot(namespace, get_link):
    """Read actual paused link poses without advancing the simulation clock."""
    description = '/' + namespace + '/robot_description'
    if not rospy.has_param(description):
        return []
    robot = ET.fromstring(rospy.get_param(description))
    pairs = [('world', 'base_link')]
    for joint in robot.findall('joint'):
        if joint.get('type') != 'fixed':
            pairs.append((joint.find('parent').get('link'), joint.find('child').get('link')))
    transforms = []
    for parent, child in pairs:
        reference = 'world' if parent == 'world' else namespace + '::' + parent
        result = get_link(namespace + '::' + child, reference)
        if not result.success:
            return []
        pose = result.link_state.pose
        transform = TransformStamped()
        transform.header.frame_id = parent if parent == 'world' else namespace + '/' + parent
        transform.child_frame_id = namespace + '/' + child
        transform.transform.translation.x = pose.position.x
        transform.transform.translation.y = pose.position.y
        transform.transform.translation.z = pose.position.z
        transform.transform.rotation = pose.orientation
        transforms.append(transform)
    return transforms


def main():
    rospy.init_node('paused_tf_cache')
    namespace = rospy.get_param('~namespace', 'underwater_robot').strip('/')
    prefix = namespace + '/'
    cache = {}
    lock = threading.Lock()
    paused = [False]

    def receive(message):
        with lock:
            if paused[0]:
                return
            for transform in message.transforms:
                if transform.child_frame_id.lstrip('/').startswith(prefix):
                    cache[transform.child_frame_id] = copy.deepcopy(transform)

    rospy.Subscriber('/tf', TFMessage, receive, queue_size=100)
    physics = rospy.ServiceProxy('/gazebo/get_physics_properties', GetPhysicsProperties)
    get_link = rospy.ServiceProxy('/gazebo/get_link_state', GetLinkState)
    publisher = rospy.Publisher('/tf', TFMessage, queue_size=1, latch=True)
    published_for_pause = False
    first_publish = True
    while not rospy.is_shutdown():
        try:
            is_paused = physics().pause
            with lock:
                paused[0] = is_paused
                transforms = copy.deepcopy(list(cache.values()))
            if is_paused and not transforms and not published_for_pause:
                transforms = initial_snapshot(namespace, get_link)
            if is_paused and transforms:
                if not published_for_pause:
                    if first_publish:
                        deadline = time.monotonic() + 0.2
                        while not rospy.is_shutdown() and publisher.get_num_connections() == 0 and time.monotonic() < deadline:
                            time.sleep(0.05)
                        first_publish = False
                    now = rospy.Time.now()
                    if now.to_nsec() > 0:
                        for transform in transforms:
                            transform.header.stamp = now
                    publisher.publish(TFMessage(transforms=transforms))
                    published_for_pause = True
            elif not is_paused:
                published_for_pause = False
        except (rospy.ServiceException, rospy.ROSException) as exc:
            published_for_pause = False
            rospy.logwarn_throttle(10, 'Cannot check Gazebo pause state: %s', exc)
        time.sleep(0.25)


if __name__ == '__main__':
    main()
