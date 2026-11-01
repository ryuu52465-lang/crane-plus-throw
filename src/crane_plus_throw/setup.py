import os
from glob import glob
from setuptools import setup

package_name = 'crane_plus_throw'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pai-student',
    maintainer_email='noreply@example.com',
    description='CRANE+ V2 grasp and throw',
    license='Apache License 2.0',
    entry_points={
        'console_scripts': [
            'throw_node = crane_plus_throw.throw_node:main',
            'collect_data = crane_plus_throw.collect_data:main',
            'train_model = crane_plus_throw.train_model:main',
            'ai_throw_node = crane_plus_throw.ai_throw_node:main',
        ],
    },
)
