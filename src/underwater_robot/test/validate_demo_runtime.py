#!/usr/bin/env python3
"""Explicit integration audit for the dedicated demo; publishes bounded inputs.

Run with --mode isolated only when guard_output:=control_audit/thrusters.
Run with --mode motion only on the demo model with the normal command guard.
All modes require a running clock, finish with zero velocity and paused physics.
"""
import argparse
import json
import math
import threading
import time
import numpy as np
import rospy
import rosgraph
import rosnode
from geometry_msgs.msg import Twist, WrenchStamped
from gazebo_msgs.srv import GetModelState
from std_srvs.srv import Empty
from uuv_gazebo_ros_plugins_msgs.msg import FloatStamped


def _check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--mode',choices=['isolated','motion'],required=True)
    args=parser.parse_args()
    rospy.init_node('demo_runtime_audit',anonymous=True)
    ns='/underwater_robot/'
    _check('name="underwater_robot_demo"' in rospy.get_param(ns+'robot_description'), 'Only run on dedicated demo')
    _check(rospy.get_param(ns+'thruster_manager/max_thrust') <= 8.0, 'max_thrust exceeds demo limit 8.0')
    limit=math.sqrt(8.0/.001)
    latest=[None]*6; peaks=[0.]*6; counts=[0]*6
    thrust_peaks=[0.]*6; wrench_peak=[0.]
    lock=threading.Lock()
    prefix='control_audit/thrusters' if args.mode=='isolated' else 'thrusters'
    def command(msg,index):
        with lock:
            _check(math.isfinite(msg.data), 'Non-finite thruster command')
            latest[index]=msg.data; peaks[index]=max(peaks[index],abs(msg.data)); counts[index]+=1
    def thrust(msg,index):
        with lock: thrust_peaks[index]=max(thrust_peaks[index],abs(msg.data))
    def wrench(msg):
        values=[msg.wrench.force.x,msg.wrench.force.y,msg.wrench.force.z,msg.wrench.torque.x,msg.wrench.torque.y,msg.wrench.torque.z]
        with lock: wrench_peak[0]=max(wrench_peak[0],max(abs(x) for x in values))
    subscriptions=[rospy.Subscriber(ns+prefix+'/%d/input'%i,FloatStamped,command,callback_args=i) for i in range(6)]
    subscriptions += [rospy.Subscriber(ns+'thrusters/%d/thrust'%i,FloatStamped,thrust,callback_args=i) for i in range(6)]
    subscriptions.append(rospy.Subscriber(ns+'thruster_manager/input_stamped',WrenchStamped,wrench))
    pub=rospy.Publisher(ns+'cmd_vel',Twist,queue_size=1)
    model=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
    pause=rospy.ServiceProxy('/gazebo/pause_physics',Empty)
    def state():
        s=model('underwater_robot','world'); _check(s.success, 'GetModelState failed')
        p=s.pose.position; q=s.pose.orientation
        roll=math.atan2(2*(q.w*q.x+q.y*q.z),1-2*(q.x*q.x+q.y*q.y))
        pitch=math.asin(max(-1.,min(1.,2*(q.w*q.y-q.z*q.x))))
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        return np.array([p.x,p.y,p.z,roll,pitch,yaw])
    def drive(axis,value,duration):
        end=time.monotonic()+duration
        while time.monotonic()<end:
            message=Twist()
            if axis is not None:
                if axis<3: setattr(message.linear,['x','y','z'][axis],value)
                else: message.angular.z=value
            pub.publish(message); time.sleep(.05)
    report={'mode':args.mode}
    try:
        drive(None,0,1.0)
        _check(all(c>0 for c in counts),'Missing guarded output')
        if args.mode=='isolated':
            pubs,_,_=rosgraph.Master(rospy.get_name()).getSystemState()
            _check(not any(t.startswith(ns+'thrusters/') and t.endswith('/input') and p for t,p in pubs),
                   'Unexpected publisher on thrusters/*/input in isolated mode')
            before=state(); drive(0,.05,1.5); drive(None,0,.5)
            after=state(); report['isolated_pose_drift']=float(np.linalg.norm(after[:3]-before[:3]))
            _check(report['isolated_pose_drift']<.05, 'Isolated pose drift exceeded 0.05m')
            _check(max(peaks)>0.01 and wrench_peak[0]>0.01,'Control path produced no output')
            rosnode.kill_nodes([ns+'thruster_allocator'])
            time.sleep(.8)
            raw=rospy.Publisher(ns+'thruster_commands/0/input',FloatStamped,queue_size=1)
            time.sleep(.3)
            msg=FloatStamped(); msg.data=1e6
            raw.publish(msg); time.sleep(.15)
            _check(abs(latest[0]-limit)<.01,'Guard limit not enforced')
            msg.data=float('nan'); raw.publish(msg); time.sleep(.15)
            _check(abs(latest[0])<1e-9,'Guard did not reject NaN')
            msg.data=10.; raw.publish(msg); time.sleep(.15)
            _check(abs(latest[0]-10)<.01, 'Guard did not pass valid command 10.0')
            time.sleep(.8)
            _check(all(abs(x)<1e-9 for x in latest),'Guard did not stop stale allocator output')
            report['guard_limit_nan_timeout']='PASS'
        else:
            start=state(); drive(None,0,5.); end=state()
            report['hover_drift_5s_m']=float(np.linalg.norm(end[:3]-start[:3]))
            report['hover_roll_pitch_rad']=end[3:5].tolist()
            _check(report['hover_drift_5s_m']<.1 and max(abs(end[3:5]))<.15, 'Hover drift or tilt exceeded')
            results={}
            for name,axis in [('forward',0),('left',1),('up',2),('yaw',3)]:
                before=state(); drive(axis,.05,2.); drive(None,0,.3); after=state()
                delta=after-before
                if axis==3: response=math.atan2(math.sin(delta[5]),math.cos(delta[5]))
                else:
                    yaw=before[5]; body_to_world=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
                    response=float((body_to_world.T @ delta[:3])[axis])
                results[name]={'response':response,'delta_xyz_rpy':delta.tolist()}
                _check(response>1e-4,'Wrong or missing response for '+name)
                _check(max(abs(after[3:5]))<.2,'Unexpected roll/pitch')
                drive(None,0,.5)
            report['motion']=results
            _check(max(thrust_peaks)<=8.05,'Thrust limit exceeded')
        _check(max(peaks)<=limit+.01 and wrench_peak[0]<=30.0001, 'Command peak or wrench peak exceeded')
        report.update({'guard_command_peaks':peaks,'actual_thrust_peaks_N':thrust_peaks,'wrench_peak':wrench_peak[0],'output_samples':counts,'result':'PASS'})
    finally:
        drive(None,0,.3); pause(); time.sleep(.8)
        report['paused_final_guard_commands']=list(latest)
        print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
