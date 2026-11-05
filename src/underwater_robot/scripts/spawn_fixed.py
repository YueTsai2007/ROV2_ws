#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import subprocess

# Set encoding
reload(sys)
sys.setdefaultencoding('utf-8')

def main():
    # URDFFile path
    urdf_file = os.path.join(os.path.dirname(__file__), '../urdf/test_simple.urdf')
    
    # ReadURDFFile
    with open(urdf_file, 'r') as f:
        urdf_content = f.read()
    
    # Call spawn_model via subprocess, pass directlyXMLContent
    cmd = [
        'rosrun', 'gazebo_ros', 'spawn_model',
        '-string', urdf_content,
        '-urdf',
        '-model', 'python_robot',
        '-x', '0', '-y', '0', '-z', '1'
    ]
    
    print("Execute command:", ' '.join(cmd))
    result = subprocess.call(cmd)
    
    if result == 0:
        print("Robot spawned successfully!")
    else:
        print("Robot spawn failed, exit code:", result)

if __name__ == '__main__':
    main()
