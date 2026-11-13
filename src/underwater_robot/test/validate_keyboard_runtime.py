#!/usr/bin/env python3
"""Exercise the real keyboard process through a PTY while physics is paused."""
import json
import os
from pathlib import Path
import pty
import subprocess
import sys
import time
import rospy
from gazebo_msgs.srv import GetPhysicsProperties
from geometry_msgs.msg import Twist


def _check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    rospy.init_node('keyboard_runtime_audit',anonymous=True)
    _check(rospy.ServiceProxy('/gazebo/get_physics_properties',GetPhysicsProperties)().pause,
           'Physics must be paused for keyboard runtime audit')
    samples=[]
    sub=rospy.Subscriber('/underwater_robot/cmd_vel',Twist,lambda m:samples.append((time.monotonic(),m.linear.x,m.angular.z)))
    master,slave=pty.openpty()
    child=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/demo_keyboard.py'),
        '__ns:=/underwater_robot','__name:=demo_keyboard_audit'],stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
    try:
        time.sleep(1.2)
        start=time.monotonic(); os.write(master,b'w'); time.sleep(.15)
        _check(any(t>=start and abs(x-.1)<1e-9 for t,x,z in samples),'W key did not publish forward velocity')
        time.sleep(.4)
        _check(samples and abs(samples[-1][1])<1e-9,'Keyboard release did not clear velocity')
        start=time.monotonic(); os.write(master,b'q'); time.sleep(.15)
        _check(any(t>=start and abs(z-.15)<1e-9 for t,x,z in samples),'Q key did not publish yaw')
        os.write(master,b' '); time.sleep(.2)
        _check(abs(samples[-1][1])+abs(samples[-1][2])<1e-9,'Space key did not clear velocity')
        print(json.dumps({'keyboard_pty':'PASS','forward_mps':.1,'yaw_rate_radps':.15,'idle_and_space_zero':True,'samples':len(samples)},indent=2))
    finally:
        child.terminate()
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
        os.close(master); os.close(slave)


if __name__=='__main__': main()
