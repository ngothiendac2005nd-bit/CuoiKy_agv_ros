include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "base_link", 
  published_frame = "map",      
  odom_frame = "odom",
  
  -- Sửa ở đây: Nếu chạy Gazebo thường đã có odom, nên để false để tránh xung đột
  provide_odom_frame = false,   
  
  publish_frame_projected_to_2d = false,
  use_pose_extrapolator = true,
  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 0,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 1,
  
  -- Tăng thời gian chờ để tránh lỗi "map does not exist" lúc khởi động
  lookup_transform_timeout_sec = 1.0, 
  
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 5e-3,
  trajectory_publish_period_sec = 30e-3,
  rangefinder_sampling_ratio = 1.0,
  odometry_sampling_ratio = 1.0,
  fixed_frame_pose_sampling_ratio = 1.0,
  imu_sampling_ratio = 1.0, 
  landmarks_sampling_ratio = 1.0,
}

MAP_BUILDER.use_trajectory_builder_3d = true
MAP_BUILDER.num_background_threads = 8

TRAJECTORY_BUILDER_3D.min_range = 0.2
TRAJECTORY_BUILDER_3D.max_range = 30.0 -- Tăng tầm quét để map rộng hơn
TRAJECTORY_BUILDER_3D.num_accumulated_range_data = 1
TRAJECTORY_BUILDER_3D.voxel_filter_size = 0.15 -- Tăng nhẹ để mượt hơn

TRAJECTORY_BUILDER_3D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_3D.real_time_correlative_scan_matcher.linear_search_window = 0.2
TRAJECTORY_BUILDER_3D.real_time_correlative_scan_matcher.angular_search_window = math.rad(3.0)

POSE_GRAPH.optimize_every_n_nodes = 10 -- Tối ưu dày hơn để giữ map ổn định
POSE_GRAPH.constraint_builder.min_score = 0.55
POSE_GRAPH.constraint_builder.sampling_ratio = 0.03
POSE_GRAPH.optimization_problem.huber_scale = 5e2

return options
