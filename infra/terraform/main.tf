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

# ----------------------------------------------------
# NETWORKING (VPC & SUBNETS)
# ----------------------------------------------------
data "aws_availability_zones" "available" {}

resource "aws_vpc" "driftguard_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "driftguard-vpc"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.driftguard_vpc.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name = "driftguard-public-${count.index}"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.driftguard_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = {
    Name = "driftguard-private-${count.index}"
  }
}

# ----------------------------------------------------
# AMAZON ECR REGISTRY
# ----------------------------------------------------
resource "aws_ecr_repository" "api" {
  name                 = "driftguard-api"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "dashboard" {
  name                 = "driftguard-dashboard"
  image_tag_mutability = "MUTABLE"
}

# ----------------------------------------------------
# AMAZON S3 ARTIFACT STORE
# ----------------------------------------------------
resource "aws_s3_bucket" "artifacts" {
  bucket        = "driftguard-mlflow-artifacts-${var.environment}"
  force_destroy = true
}

# ----------------------------------------------------
# AMAZON RDS POSTGRESQL (Metadata Registry)
# ----------------------------------------------------
resource "aws_db_subnet_group" "db" {
  name       = "driftguard-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "metadata_store" {
  identifier             = "driftguard-metadata-db"
  allocated_storage      = 20
  max_allocated_storage  = 100
  db_name                = "driftguard"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.micro"
  username               = "driftguard"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db.name
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.db.id]
}

# ----------------------------------------------------
# AMAZON ELASTICACHE REDIS (Online Store)
# ----------------------------------------------------
resource "aws_elasticache_subnet_group" "redis" {
  name       = "driftguard-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "feature_store" {
  cluster_id           = "driftguard-redis-store"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
}

# ----------------------------------------------------
# AMAZON EKS KUBERNETES CLUSTER
# ----------------------------------------------------
resource "aws_iam_role" "eks" {
  name = "driftguard-eks-cluster-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks.name
}

resource "aws_eks_cluster" "k8s_fleet" {
  name     = "driftguard-eks-cluster"
  role_arn = aws_iam_role.eks.arn
  vpc_config {
    subnet_ids = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
  }
  depends_on = [aws_iam_role_policy_attachment.eks_cluster]
}

# ----------------------------------------------------
# SECURITY GROUPS
# ----------------------------------------------------
resource "aws_security_group" "db" {
  name   = "driftguard-db-sg"
  vpc_id = aws_vpc.driftguard_vpc.id
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.driftguard_vpc.cidr_block]
  }
}

resource "aws_security_group" "redis" {
  name   = "driftguard-redis-sg"
  vpc_id = aws_vpc.driftguard_vpc.id
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.driftguard_vpc.cidr_block]
  }
}
