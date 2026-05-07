terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # FIX 1: Declaring the TLS provider explicitly
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# FIX 1 (cont.): The TLS provider block
provider "tls" {}

data "aws_availability_zones" "available" {
  state = "available"
}

#############################
# 1. NETWORK (VPC & Subnets)
#############################

resource "aws_vpc" "project_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "smart-sre-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.project_vpc.id
  tags   = { Name = "project-igw" }
}

resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.project_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags = {
    Name                                        = "public-1"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/project-eks-cluster" = "shared"
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.project_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true
  tags = {
    Name                                        = "public-2"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/project-eks-cluster" = "shared"
  }
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.project_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name                                        = "private-1"
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/project-eks-cluster" = "shared"
  }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.project_vpc.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name                                        = "private-2"
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/project-eks-cluster" = "shared"
  }
}

#############################
# 2. NAT GATEWAY & ROUTING
#############################

resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

resource "aws_nat_gateway" "nat_gateway" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet_1.id
  depends_on    = [aws_internet_gateway.igw]
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.project_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.project_vpc.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gateway.id
  }
}

resource "aws_route_table_association" "pub1" { subnet_id = aws_subnet.public_subnet_1.id; route_table_id = aws_route_table.public_rt.id }
resource "aws_route_table_association" "pub2" { subnet_id = aws_subnet.public_subnet_2.id; route_table_id = aws_route_table.public_rt.id }
resource "aws_route_table_association" "priv1" { subnet_id = aws_subnet.private_subnet_1.id; route_table_id = aws_route_table.private_rt.id }
resource "aws_route_table_association" "priv2" { subnet_id = aws_subnet.private_subnet_2.id; route_table_id = aws_route_table.private_rt.id }

#############################
# 3. EKS CLUSTER
#############################

resource "aws_iam_role" "eks_cluster_role" {
  name = "eksClusterRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "eks.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# FIX 3: Added the VPC Resource Controller policy
resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
}

resource "aws_eks_cluster" "project_cluster" {
  name     = "project-eks-cluster"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller
  ]
}

#############################
# 4. NODE GROUP
#############################

resource "aws_iam_role" "eks_node_role" {
  name = "eksNodeRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "node_worker" { role = aws_iam_role.eks_node_role.name; policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy" }
resource "aws_iam_role_policy_attachment" "node_cni" { role = aws_iam_role.eks_node_role.name; policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy" }
resource "aws_iam_role_policy_attachment" "node_ecr" { role = aws_iam_role.eks_node_role.name; policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" }

# FIX 2: Moved scaling/healing permissions here (Node Level) 
resource "aws_iam_role_policy_attachment" "node_autoscaling" { role = aws_iam_role.eks_node_role.name; policy_arn = "arn:aws:iam::aws:policy/AutoScalingFullAccess" }
resource "aws_iam_role_policy_attachment" "node_logs" { role = aws_iam_role.eks_node_role.name; policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess" }

resource "aws_eks_node_group" "worker_nodes" {
  cluster_name    = aws_eks_cluster.project_cluster.name
  node_group_name = "worker-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
  instance_types  = ["t3.medium"]

  scaling_config {
    desired_size = 2
    max_size     = 4
    min_size     = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr
  ]
}

#############################
# 5. OIDC PROVIDER
#############################

data "tls_certificate" "eks_oidc" {
  url = aws_eks_cluster.project_cluster.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks_oidc" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.project_cluster.identity[0].oidc[0].issuer
}