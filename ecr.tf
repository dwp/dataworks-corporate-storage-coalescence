resource "aws_ecr_repository" "dataworks-corporate-storage-coalescence" {
  name = "dataworks-corporate-storage-coalescence"
  tags = merge(
    local.common_tags,
    { DockerHub : "dwpdigital/dataworks-corporate-storage-coalescence" }
  )
}

resource "aws_ecr_repository_policy" "dataworks-corporate-storage-coalescence" {
  repository = aws_ecr_repository.dataworks-corporate-storage-coalescence.name
  policy     = data.terraform_remote_state.management.outputs.ecr_iam_policy_document
}

output "ecr_url" {
  value = aws_ecr_repository.dataworks-corporate-storage-coalescence.repository_url
}
