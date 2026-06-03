output "eks_cluster_name" {
  value = aws_eks_cluster.k8s_fleet.name
}

output "eks_cluster_endpoint" {
  value = aws_eks_cluster.k8s_fleet.endpoint
}

output "s3_bucket_artifacts_name" {
  value = aws_s3_bucket.artifacts.id
}

output "rds_db_endpoint" {
  value = aws_db_instance.metadata_store.endpoint
}

output "redis_cache_node_address" {
  value = aws_elasticache_cluster.feature_store.cache_nodes[0].address
}

output "ecr_api_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_dashboard_url" {
  value = aws_ecr_repository.dashboard.repository_url
}
