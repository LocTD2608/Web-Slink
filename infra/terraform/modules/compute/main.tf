# Compute Module (EC2 / ECS / ASG for FastAPI Application Nodes)
variable "vpc_id" {}
variable "app_subnet_ids" { type = list(string) }
variable "db_endpoint" {}

output "app_cluster_id" { value = "app-cluster-prod" }
output "app_load_balancer_dns" { value = "lb-course-reg-prod.aws.internal" }
