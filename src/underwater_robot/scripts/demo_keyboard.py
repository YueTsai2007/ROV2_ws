#!/usr/bin/env python3
"""Small momentary teleop commands. Requires an interactive terminal."""
import select
import sys
import termios
import time
import tty


def main():
    import rospy
    from geometry_msgs.msg import Twist
    rospy.init_node('demo_keyboard')
    if not sys.stdin.isatty(): raise RuntimeError('Use docker exec -it and an interactive terminal')
    pub=rospy.Publisher('cmd_vel',Twist,queue_size=1)
    speed=float(rospy.get_param('~speed',0.1)); yaw_rate=float(rospy.get_param('~yaw_rate',0.15))
    keys={'w':(0,1),'s':(0,-1),'a':(1,1),'d':(1,-1),'r':(2,1),'f':(2,-1),'q':(3,1),'e':(3,-1)}
    print('Demo: W/S forward/back, A/D left/right, R/F up/down, Q/E yaw. Space stops; Ctrl-C exits.')
    settings=termios.tcgetattr(sys.stdin); last=0.0; key=''
    rospy.on_shutdown(lambda:pub.publish(Twist()))
    try:
        tty.setcbreak(sys.stdin.fileno())
        while not rospy.is_shutdown():
            ready,_,_=select.select([sys.stdin],[],[],0.05)
            if ready:
                key=sys.stdin.read(1).lower(); last=time.monotonic()
                if key=='\x03': break
            command=Twist()
            if time.monotonic()-last < 0.2 and key in keys:
                axis,sign=keys[key]
                if axis==0: command.linear.x=sign*speed
                if axis==1: command.linear.y=sign*speed
                if axis==2: command.linear.z=sign*speed
                if axis==3: command.angular.z=sign*yaw_rate
            pub.publish(command)
    finally:
        pub.publish(Twist()); termios.tcsetattr(sys.stdin,termios.TCSADRAIN,settings)


if __name__ == '__main__': main()
