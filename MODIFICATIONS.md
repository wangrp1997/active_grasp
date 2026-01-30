# active_grasp 修改记录

本文档记录对 `src/active_grasp/` 的修改，用于 ROS2 真机集成。

---

## 2026-01-29: 添加规划模式（Planning Mode）

### 目标
将 active_grasp 改为"规划模式"，只发布 NBV 算出的视角位姿，不直接控制机械臂。

### 修改文件
- `src/active_grasp/src/active_grasp/controller.py`

### 具体修改
1. **添加 `planning_mode` 参数**（`load_parameters()`）
   - 默认 `False`，保持原有行为
   - 通过 ROS 参数 `~planning_mode` 控制

2. **初始化视角位姿发布器**（`init_robot_connection()`）
   - 仅在 `planning_mode=True` 时初始化
   - 话题：`~viewpoint_pose`（`geometry_msgs/PoseStamped`）

3. **发布 NBV 视角位姿**（`search_grasp()`）
   - 每次 `policy.update()` 后，如果 `x_d` 不为空，发布视角位姿

4. **跳过执行**（`execute_grasp()`）
   - 规划模式下直接返回 `"published"`，不执行抓取

### 使用方式
在 launch 文件或参数文件中设置：
```xml
<param name="planning_mode" value="true" />
```

或通过 rosparam 设置：
```bash
rosparam set /grasp_controller/planning_mode true
```

### 测试步骤
1. **允许 Docker 访问 X11（宿主机执行一次）**
   ```bash
   xhost +local:docker
   ```

2. **启动容器（挂载源码 + GUI 显示）**
   ```bash
   cd /home/nros/Documents/apm/active_grasp_ws
   docker run -it --rm --name active_grasp \
     -v $(pwd)/src/active_grasp:/root/active_grasp_ws/src/active_grasp \
     -v $(pwd)/src/robot_helpers:/root/active_grasp_ws/src/robot_helpers \
     -v $(pwd)/src/vgn:/root/active_grasp_ws/src/vgn \
     -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
     active_grasp_noetic
   ```

3. **重新编译并启动环境（终端1，容器内）**
   ```bash
   source /opt/ros/noetic/setup.bash
   catkin build active_grasp
   source devel/setup.bash
   roslaunch active_grasp env.launch sim:=true
   # RViz 会自动启动
   ```

4. **设置参数并运行（终端2，新开）**
   ```bash
   docker exec -it active_grasp bash
   source /opt/ros/noetic/setup.bash
   source /root/active_grasp_ws/devel/setup.bash
   rosparam set /grasp_controller/planning_mode true
   python3 /root/active_grasp_ws/src/active_grasp/scripts/run.py nbv --runs 1
   ```

5. **检查话题（终端3，新开）**
   ```bash
   docker exec -it active_grasp bash
   source /opt/ros/noetic/setup.bash
   rostopic list | grep viewpoint
   rostopic echo /grasp_controller/viewpoint_pose
   ```

### 测试结果
- ✅ 视角位姿话题正常发布：`/grasp_controller/viewpoint_pose`
- ✅ 消息类型：`geometry_msgs/PoseStamped`
- ✅ frame_id：`panda_link0`
- ✅ NBV 计算的不同视角位姿都能正常发布

### ROS1–ROS2 桥接测试（ros1_bridge）

1. **启动带 NBV 的 ROS1 容器（建议用 host 网络，宿主机终端1）**
   ```bash
   cd /home/nros/Documents/apm/active_grasp_ws
   xhost +local:docker
   docker run -it --rm --name active_grasp \
     --network host \
     -v $(pwd)/src/active_grasp:/root/active_grasp_ws/src/active_grasp \
     -v $(pwd)/src/robot_helpers:/root/active_grasp_ws/src/robot_helpers \
     -v $(pwd)/src/vgn:/root/active_grasp_ws/src/vgn \
     -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
     active_grasp_noetic
   ```

2. **容器内启动环境（终端1，容器内）**
   ```bash
   source /opt/ros/noetic/setup.bash
   catkin build active_grasp
   source devel/setup.bash
   roslaunch active_grasp env.launch sim:=true
   # RViz 会自动启动
   ```

3. **容器内运行 NBV + 视角发布（终端2，新开容器 shell）**
   ```bash
   docker exec -it active_grasp bash
   source /opt/ros/noetic/setup.bash
   source /root/active_grasp_ws/devel/setup.bash
   rosparam set /grasp_controller/planning_mode true
   python3 /root/active_grasp_ws/src/active_grasp/scripts/run.py nbv --runs 1
   ```

4. **宿主机启动 ros1_bridge（终端3，宿主机）**
   ```bash
   # 激活 ROS2 环境 + 启动 bridge（机器上已配置好 alias）
   start_ros_bridge
   # 实际等价于：
   #   source ~/.local/ros2_rc
   #   source ~/Documents/Woosh/ros_bridge/ros-humble-ros1-bridge/install/local_setup.zsh
   #   ros2 run ros1_bridge dynamic_bridge --bridge-all-topics
   ```

5. **ROS2 侧检查桥接结果（终端4，宿主机）**
   ```bash
   # 激活 ROS2 环境（如有 rws/rr 等别名，按本机习惯执行）
   rws   # 或 source ~/.local/ros2_rc

   ros2 topic list | grep viewpoint
   ros2 topic echo /grasp_controller/viewpoint_pose
   ```

6. **预期：ROS2 侧能看到与 ROS1 中相同的 `/grasp_controller/viewpoint_pose` 消息**

---

## 2026-01-30: ROS2 可视化节点测试

### 目标
测试 ROS2 可视化节点，在 RViz2 中显示视角位姿（相机视锥）。

### 修改文件
- `ros2_ws/src/active_grasp_ros2_bridge/active_grasp_ros2_bridge/viewpoint_visualizer.py`（新建）
- `ros2_ws/src/active_grasp_ros2_bridge/setup.py`（添加节点入口）
- `ros2_ws/src/active_grasp_ros2_bridge/package.xml`（添加依赖）

### 功能说明
- 订阅 ROS1 桥接过来的 `/grasp_controller/viewpoint_pose`（`geometry_msgs/msg/PoseStamped`）
- 订阅相机信息 `/woosh/camera/woosh_left_hand_rgbd/depth/camera_info`（获取内参）
- 将 frame_id 从 `panda_link0` 改为 `woosh_base_link`（测试阶段，不做坐标变换）
- 发布相机视锥 Marker 到 `/active_grasp/viewpoint_markers`（`visualization_msgs/msg/Marker`）

### 测试步骤

1. **编译 ROS2 包（宿主机）**
   ```bash
   cd /home/nros/Documents/apm/active_grasp_ws/ros2_ws
   rws  # 或 source ~/.local/ros2_rc
   colcon build --packages-select active_grasp_ros2_bridge
   source install/setup.bash
   ```

2. **确保 ROS1 容器和 ros1_bridge 已启动**
   - ROS1 容器运行中，已设置 `planning_mode=true` 并运行 `run.py nbv`
   - `ros1_bridge` 已启动（`start_ros_bridge`）

3. **检查话题（宿主机，ROS2 环境）**
   ```bash
   rws
   ros2 topic list | grep viewpoint
   ros2 topic list | grep camera
   ```

4. **启动可视化节点（宿主机，ROS2 环境）**
   ```bash
   rws
   source install/setup.bash
   ros2 run active_grasp_ros2_bridge viewpoint_visualizer
   ```

5. **在 RViz2 中查看**
   - 如果已有 RViz2 运行（如 `woosh_bringup moveit_servo.launch.py`），直接添加 Marker 显示
   - 或单独启动 RViz2：
     ```bash
     rws
     rviz2
     ```
   - 在 RViz2 中：
     - Fixed Frame 设置为 `woosh_base_link`
     - 添加 Marker 显示，话题选择 `/active_grasp/viewpoint_markers`
     - 应该能看到蓝色相机视锥

### 预期结果
- ✅ 节点正常启动，无报错
- ✅ 能接收到视角位姿和相机信息
- ✅ RViz2 中能看到相机视锥显示

### 测试结果（2026-01-30）
- ✅ 成功复现原项目的轨迹可视化效果
- ✅ 发布实际到达的视角位姿（当前相机位姿 `pose`），而非目标视角 `x_d`
- ✅ 在 RViz2 中正确显示：
  - 轨迹点（蓝色球体，SPHERE_LIST）
  - 连接线（蓝色线条，LINE_STRIP）
  - 视锥（每4个视角一个，蓝色相机视锥）
- ✅ 添加重复位姿过滤逻辑，提高发布稳定性（阈值：位置和姿态差异 < 1e-6）

### 关键修改点
1. **controller.py**: 发布实际相机位姿 `pose` 而非目标视角 `x_d`
2. **viewpoint_visualizer.py**: 
   - 实现与原项目一致的 `path()` 方法（球体列表 + 线条 + 视锥）
   - 添加重复位姿过滤，提高稳定性
   - 使用 MarkerArray 发布所有 markers

---
