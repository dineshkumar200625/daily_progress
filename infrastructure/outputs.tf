output "vpc_id" {
  value = aws_vpc.project_vpc.id
}

output "public_subnets" {
  value = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
}

output "private_subnets" {
  value = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
}

output "eks_cluster_name" {
  value = aws_eks_cluster.project_cluster.name
}

output "eks_cluster_endpoint" {
  value = aws_eks_cluster.project_cluster.endpoint
}

output "eks_cluster_role_arn" {
  value = aws_iam_role.eks_cluster_role.arn
}

output "node_group_role_arn" {
  value = aws_iam_role.eks_node_role.arn
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.eks_oidc.arn
}

output "nat_gateway_ip" {
  value = aws_eip.nat_eip.public_ip
}
