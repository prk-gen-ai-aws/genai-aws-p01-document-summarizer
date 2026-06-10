# ============================================================
# Remote Backend Configuration — Project 1
# Uses shared S3 bucket for state + native S3 lock file
# ============================================================

terraform {
  backend "s3" {
    bucket     = "prk-terraform-state-759802535955"
    key        = "p01-document-summarizer/terraform.tfstate"
    region     = "us-east-1"
    encrypt    = true
    use_lockfile = true
  }
}
