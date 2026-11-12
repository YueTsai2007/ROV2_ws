#!/usr/bin/env python3
"""Independent wall-clock watchdog between allocator output and Gazebo."""
import math
import threading
import time


class CommandBuffer:
    def __init__(self, limit, timeout):
        if not math.isfinite(limit) or limit <= 0 or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Command limit and timeout must be finite and positive')
        self.limit, self.timeout = limit, timeout
        self.commands = [0.0] * 6
        self.times = [None] * 6
        self.lock = threading.Lock()

    def accept(self, index, command, now):
        with self.lock:
            self.commands[index] = max(-self.limit, min(self.limit, command)) if math.isfinite(command) else 0.0
            self.times[index] = now

    def values(self, now):
        with self.lock:
            return [c if t is not None and 0 <= now-t <= self.timeout else 0.0
                    for c,t in zip(self.commands,self.times)]


def main():
    import rospy
    from uuv_gazebo_ros_plugins_msgs.msg import FloatStamped
    rospy.init_node('demo_command_guard')
    max_thrust = float(rospy.get_param('~max_thrust',8.0))
    gain = float(rospy.get_param('~conversion_gain',0.001))
    if max_thrust <= 0 or gain <= 0: raise ValueError('Invalid thrust conversion')
    buffer = CommandBuffer(math.sqrt(max_thrust/gain),float(rospy.get_param('~timeout',0.5)))
    output = rospy.get_param('~output_prefix','thrusters').rstrip('/')
    publishers = [rospy.Publisher(output+'/%d/input'%i,FloatStamped,queue_size=1) for i in range(6)]
    def receive(message,index): buffer.accept(index,message.data,time.monotonic())
    subscriptions = [rospy.Subscriber('thruster_commands/%d/input'%i,FloatStamped,receive,callback_args=i,queue_size=1) for i in range(6)]
    def send(values):
        for pub,value in zip(publishers,values):
            msg=FloatStamped(); msg.header.stamp=rospy.Time.now(); msg.data=value; pub.publish(msg)
    def stop(): send([0.0]*6)
    rospy.on_shutdown(stop)
    rospy.loginfo('Demo command guard ready; wall timeout=%ss, command limit=%s',buffer.timeout,buffer.limit)
    try:
        while not rospy.is_shutdown():
            send(buffer.values(time.monotonic()))
            time.sleep(0.05)
    finally: stop()


if __name__ == '__main__': main()
