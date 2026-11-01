# crane_plus_gazebo/crane_plus_with_table.launch.py をベースに、
# 投げる課題用のワールド/モデルに差し替え、MoveIt・RVizを外したもの

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch.actions import TimerAction
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.actions import SetParameter


def generate_launch_description():
    # PATHを追加で通さないとSTLファイルが読み込まれない
    env = {'IGN_GAZEBO_SYSTEM_PLUGIN_PATH': os.environ['LD_LIBRARY_PATH'],
           'IGN_GAZEBO_RESOURCE_PATH': os.path.dirname(
               get_package_share_directory('crane_plus_description'))}
    pkg = get_package_share_directory('crane_plus_throw')
    world_file = os.path.join(pkg, 'worlds', 'throw_world.sdf')
    gui_config = os.path.join(
        get_package_share_directory('crane_plus_gazebo'), 'gui', 'gui.config')
    # -r オプションで起動時にシミュレーションをスタートしないと、コントローラが起動しない
    ign_gazebo = ExecuteProcess(
            cmd=['ign gazebo -r', world_file, '--gui-config', gui_config],
            output='screen',
            additional_env=env,
            shell=True
        )

    description = Command([
        'xacro ', os.path.join(pkg, 'urdf', 'crane_plus_throw.urdf.xacro'),
        ' use_gazebo:=true use_ignition:=true',
        ' gz_control_config_package:=crane_plus_control',
        ' gz_control_config_file_path:=config/crane_plus_controllers.yaml',
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': description}])

    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        output='log',
        arguments=['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', 'world', 'base_link'])

    # ワールド読込中にcreateすると、OKが返っても要求が捨てられることがあるため、
    # crane_plusがワールドに現れるまでcreateを繰り返す
    gazebo_spawn_entity = ExecuteProcess(
        cmd=['until ign model --list 2>/dev/null | grep -q crane_plus; do '
             'ros2 run ros_gz_sim create -topic /robot_description -name crane_plus -z 1.015; '
             'sleep 5; done'],
        shell=True,
        output='screen',
    )

    spawners = [
        ExecuteProcess(
            cmd=[f'ros2 run controller_manager spawner {name}'],
            shell=True,
            output='screen')
        for name in ['joint_state_broadcaster',
                     'crane_plus_arm_controller',
                     'crane_plus_gripper_controller']
    ]

    # clockに加え、ボールの固定/解放トピックをROS 2からGazeboへ中継する
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
                   '/throw/attach@std_msgs/msg/Empty]ignition.msgs.Empty',
                   '/throw/detach@std_msgs/msg/Empty]ignition.msgs.Empty',
                   '/model/ball/detachable_joint/state@std_msgs/msg/String[ignition.msgs.StringMsg',
                   '/overhead_camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                   # 正解データ(ボールの真の位置)。データ収集と評価だけに使い、AIの入力には使わない
                   '/model/ball/odometry@nav_msgs/msg/Odometry[ignition.msgs.Odometry'],
        output='screen'
    )

    return LaunchDescription([
        SetParameter(name='use_sim_time', value=True),
        ign_gazebo,
        robot_state_publisher,
        static_tf,
        TimerAction(period=5.0, actions=[gazebo_spawn_entity]),
        *spawners,
        bridge,
    ])
