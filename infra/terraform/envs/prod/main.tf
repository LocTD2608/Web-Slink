terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "../../modules/networking"
  vpc_cidr = "10.0.0.0/16"
}

module "database" {
  source = "../../modules/database"
  vpc_id = module.networking.vpc_id
  db_subnet_ids = module.networking.database_subnet_ids
}

module "compute" {
  source = "../../modules/compute"
  vpc_id = module.networking.vpc_id
  app_subnet_ids = module.networking.private_subnet_ids
  db_endpoint = module.database.db_endpoint
}
