# ============================================================
# Project 1 — AI Document Summarizer
# Input Variables
# ============================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID — used in resource names for uniqueness"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project identifier — used in all resource names"
  type        = string
  default     = "p01-doc-summarizer"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID for summarization"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}
