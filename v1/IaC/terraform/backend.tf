# ============================================================
# Remote Backend Configuration — Project 1
# Uses shared S3 bucket for state + native S3 lock file
# Run terraform init with -backend-config for account-specific values
# See backend.tfvars.example for configuration
# ============================================================

terraform {
  backend "s3" {
    bucket       = "prk-terraform-state-ACCOUNT-ID"
    key          = "p01-document-summarizer/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
