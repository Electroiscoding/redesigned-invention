resource "aws_elasticache_cluster" "paraearth_redis" {
  cluster_id           = "paraearth-redis-cluster"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
}