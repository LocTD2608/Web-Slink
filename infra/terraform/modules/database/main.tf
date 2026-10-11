# Database Module (Amazon RDS PostgreSQL Multi-AZ & ElastiCache Redis Cluster)
variable "vpc_id" {}
variable "db_subnet_ids" { type = list(string) }

output "db_endpoint" { value = "postgres-prod.c123.rds.amazonaws.com:5432" }
output "redis_endpoint" { value = "redis-cluster.c123.cache.amazonaws.com:6379" }
