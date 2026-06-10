# ============================================================
# Remote Backend Configuration — Project 1
# Uses shared S3 bucket and DynamoDB lock table
# Created in terraform-backend repo
# ============================================================

terraform {
  backend "s3" {
    bucket         = "prk-terraform-state-759802535955"
    key            = "p01-document-summarizer/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "prk-terraform-state-lock"
    encrypt        = true
  }
}
