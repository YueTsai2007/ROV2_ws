#!/usr/bin/env python3
"""Republish the last robot dynamic transforms to late listeners while paused."""
import copy
import threading
import time

import rospy
from gazebo_msgs.srv import GetPhysicsProperties
from tf2_msgs.msg import TFMessage


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
    publisher = None
    while not rospy.is_shutdown():
        try:
            is_paused = physics().pause
            with lock:
                paused[0] = is_paused
                transforms = copy.deepcopy(list(cache.values()))
            if is_paused and transforms:
                if publisher is None:
                    publisher = rospy.Publisher('/tf', TFMessage, queue_size=1, latch=True)
                    now = rospy.Time.now()
                    for transform in transforms:
                        transform.header.stamp = now
                    publisher.publish(TFMessage(transforms=transforms))
            elif not is_paused and publisher is not None:
                publisher.unregister()
                publisher = None
        except (rospy.ServiceException, rospy.ROSException) as exc:
            if publisher is not None:
                publisher.unregister()
                publisher = None
            rospy.logwarn_throttle(10, 'Cannot check Gazebo pause state: %s', exc)
        time.sleep(0.25)


if __name__ == '__main__':
    main()
