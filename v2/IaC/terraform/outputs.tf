# ============================================================
# Project 1 — AI Document Summarizer
# Outputs — values displayed after terraform apply
# Add these to your .env file after deployment
# ============================================================

output "api_gateway_url" {
  description = "API Gateway endpoint URL — add to .env as API_GATEWAY_URL"
  value       = aws_api_gateway_stage.summarizer.invoke_url != "" ? "${aws_api_gateway_stage.summarizer.invoke_url}/summarize" : "not yet deployed"
}

output "s3_bucket_name" {
  description = "S3 bucket name — add to .env as S3_BUCKET_NAME"
  value       = aws_s3_bucket.documents.id
}

output "lambda_function_name" {
  description = "Lambda function name — useful for testing and logs"
  value       = aws_lambda_function.summarizer.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.summarizer.arn
}
