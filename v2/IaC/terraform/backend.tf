terraform {
  backend "s3" {
    bucket       = "prk-terraform-state-ACCOUNT-ID"
    key          = "p01-v2-document-summarizer/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
