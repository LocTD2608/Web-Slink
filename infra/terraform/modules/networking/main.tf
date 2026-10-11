# Networking Module (VPC, Public/Private Subnets, Security Groups)
variable "vpc_cidr" { default = "10.0.0.0/16" }

output "vpc_id" { value = "vpc-academic-prod-01" }
output "public_subnet_ids" { value = ["subnet-pub-1a", "subnet-pub-1b"] }
output "private_subnet_ids" { value = ["subnet-app-1a", "subnet-app-1b"] }
output "database_subnet_ids" { value = ["subnet-db-1a", "subnet-db-1b"] }
