# ============================================================
# Project 1 — AI Document Summarizer
# Main Infrastructure
# Resources: S3, IAM Role, Lambda, API Gateway
# ============================================================

provider "aws" {
  region = var.aws_region
}

# ── Local values ──
locals {
  prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = "prk"
    ManagedBy   = "Terraform"
  }
}

# ============================================================
# S3 Bucket — document storage
# ============================================================
resource "aws_s3_bucket" "documents" {
  bucket = "${local.prefix}-documents-${var.aws_account_id}"

  tags = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================================
# IAM Role — Lambda execution role (least privilege)
# ============================================================
resource "aws_iam_role" "lambda_execution" {
  name = "${local.prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Basic Lambda execution policy (CloudWatch logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy — S3 read + Bedrock invoke (least privilege)
resource "aws_iam_role_policy" "lambda_custom" {
  name = "${local.prefix}-lambda-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadDocuments"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Sid    = "BedrockInvokeModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}"
      }
    ]
  })
}

# ============================================================
# Lambda Function — document summarizer
# ============================================================
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/handler.py"
  output_path = "${path.module}/../../lambda/handler.zip"
}

resource "aws_lambda_function" "summarizer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${local.prefix}-summarizer"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      S3_BUCKET_NAME   = aws_s3_bucket.documents.id
      BEDROCK_MODEL_ID = var.bedrock_model_id
      AWS_REGION_NAME  = var.aws_region
    }
  }

  tags = local.common_tags
}

# ============================================================
# API Gateway — REST API
# ============================================================
resource "aws_api_gateway_rest_api" "summarizer" {
  name        = "${local.prefix}-api"
  description = "Document Summarizer API"

  tags = local.common_tags
}

resource "aws_api_gateway_resource" "summarize" {
  rest_api_id = aws_api_gateway_rest_api.summarizer.id
  parent_id   = aws_api_gateway_rest_api.summarizer.root_resource_id
  path_part   = "summarize"
}

resource "aws_api_gateway_method" "summarize_post" {
  rest_api_id   = aws_api_gateway_rest_api.summarizer.id
  resource_id   = aws_api_gateway_resource.summarize.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.summarizer.id
  resource_id             = aws_api_gateway_resource.summarize.id
  http_method             = aws_api_gateway_method.summarize_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.summarizer.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.summarizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.summarizer.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "summarizer" {
  depends_on  = [aws_api_gateway_integration.lambda]
  rest_api_id = aws_api_gateway_rest_api.summarizer.id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "summarizer" {
  deployment_id = aws_api_gateway_deployment.summarizer.id
  rest_api_id   = aws_api_gateway_rest_api.summarizer.id
  stage_name    = var.environment

  tags = local.common_tags
}

# ── Replace the deployment resource at the bottom ──
