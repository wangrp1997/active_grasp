#!/usr/bin/env python3
"""
ROS1 TF 桥接节点：订阅话题，发布到 ROS1 TF 树
"""

import rospy
from geometry_msgs.msg import TransformStamped
import tf2_ros


class TFBridgeROS1:
    """订阅 TransformStamped 话题，发布到 ROS1 TF 树"""
    
    def __init__(self):
        # 参数
        self.source_frame = rospy.get_param("~source_frame", "woosh_base_link")
        self.target_frame = rospy.get_param("~target_frame", "woosh_left_hand_rgbd_depth_optical_frame")
        self.input_topic = rospy.get_param("~input_topic", "/tf_bridge/transform")
        
        # TF 广播器
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()
        
        # 订阅话题
        rospy.Subscriber(self.input_topic, TransformStamped, self.transform_callback)
        
        rospy.loginfo(
            f"TF 桥接节点已启动: 订阅 {self.input_topic}, "
            f"发布 TF {self.source_frame} -> {self.target_frame}"
        )
    
    def transform_callback(self, msg):
        """处理接收到的 TF 变换"""
        # 确保 frame_id 正确
        msg.header.frame_id = self.source_frame
        msg.child_frame_id = self.target_frame
        
        # 更新时间戳为当前时间，避免重复时间戳警告
        msg.header.stamp = rospy.Time.now()
        
        # 发布到 TF 树
        self.tf_broadcaster.sendTransform(msg)
        rospy.logdebug(f"发布 TF: {self.source_frame} -> {self.target_frame}, stamp={msg.header.stamp}")
    
    def run(self):
        rospy.spin()


def main():
    rospy.init_node("tf_bridge_ros1")
    node = TFBridgeROS1()
    node.run()


if __name__ == "__main__":
    main()
