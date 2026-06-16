# AI Document Summarizer
Serverless document intelligence pipeline on AWS powered by Amazon Bedrock.

A Streamlit web app that summarizes any document using AI. Upload a PDF or TXT file, select the document type, and get a concise AI-generated summary in under 10 seconds.

Supported document types: SEC Filings (10-K / 10-Q), Insurance Claims, Loan Documents, Legal Contracts, Research Reports, General Documents.

Real-world use case: analysts, legal teams, and finance professionals dealing with large volumes of documents can get instant AI-powered summaries — saving hours of manual reading.

[View on GitHub](https://github.com/prk-gen-ai-aws/genai-aws-p01-document-summarizer)

---

## How It Works

1. User uploads a PDF or TXT file (up to 10MB) via the Streamlit UI
2. File is stored securely in Amazon S3 (private, AES256 encrypted)
3. AWS Lambda reads the file, extracts text (first 15 pages for PDFs), and builds a document-type-aware prompt
4. Amazon Bedrock (Claude Haiku 4.5) generates a concise summary
5. Summary is returned to the UI via API Gateway

The AI model ID is stored in AWS SSM Parameter Store - upgrade the model by changing one parameter, no code changes needed.

Note: The Streamlit app runs locally on your machine. Only the backend (Lambda, API Gateway, S3, SSM) runs in AWS.

---

## Architecture

Architecture diagram: v2/docs/architecture-v2.svg

Components:
- Streamlit (local) sends POST request to API Gateway
- API Gateway triggers Lambda
- Lambda reads document from S3, fetches model ID from SSM, then calls Bedrock
- Bedrock (Claude Haiku 4.5) returns summary
- Summary travels back through Lambda and API Gateway to Streamlit

---

## Project Structure

    genai-aws-p01-document-summarizer/
    v2/                          <- current version
      app/                       <- Streamlit UI (runs locally)
        main.py                  <- app entry point
        bedrock_client.py        <- AWS integration layer
      lambda/                    <- Lambda function code
        handler.py               <- orchestrator
      IaC/
        terraform/               <- Terraform IaC
        cloudformation/          <- CloudFormation IaC
      sample-documents/          <- ready-to-use test files
      docs/                      <- architecture diagrams
    v1/                          <- reference only (see VERSIONS.md)
    VERSIONS.md                  <- version history

    .streamlit/                  <- project root level
      config.toml                <- sets 10MB upload limit

---

## Tech Stack

- Frontend: Streamlit (Python) - runs locally on your machine
- API: Amazon API Gateway (REST)
- Compute: AWS Lambda (Python 3.12)
- AI: Amazon Bedrock - Claude Haiku 4.5
- Storage: Amazon S3 (private, AES256 encrypted)
- Config: AWS SSM Parameter Store
- IaC: Terraform + CloudFormation (both provided)
- Language: Python 3.12

---

## Terraform vs CloudFormation

Both options deploy identical application infrastructure. Choose based on your preference.

Terraform:
- State management: You manage state (S3 remote state + lock file)
- S3 bucket naming: Uses random_id suffix - always safe to destroy and recreate
- Portability: Works across cloud providers
- Best for: Multi-cloud teams or when you want explicit state control

CloudFormation:
- State management: AWS manages state internally - no backend setup needed
- S3 bucket naming: Uses AccountSuffix + DeploymentVersion parameters - increment on recreate
- Portability: AWS only
- Best for: AWS-native teams or when you want simpler state management

Key difference on destroy and recreate:
- Terraform: destroy and reapply always works - random_id generates a new unique suffix automatically
- CloudFormation: after destroy, increment DeploymentVersion parameter (v1 -> v2) before redeploying

---

## Prerequisites

- AWS account with CLI configured (aws configure)
- Python 3.12+
- Terraform installed (for Terraform deployment only)
- The repo includes .env.example at the root — copy it to .env after deployment and fill in your values
- First-time Bedrock activation (one-time per AWS account):
  Go to AWS Console -> Amazon Bedrock -> Playgrounds -> Chat
  Select Claude Haiku 4.5 -> send any message
  This activates your account for Anthropic models

---

## Fork and Deploy - Complete Guide

If you are forking this repo and deploying to your own AWS account, follow these steps in order.

### Before you start

Step 1 - Create and activate a Python virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate

Step 2 - Build the Lambda deployment package:

    pip install PyPDF2 -t v2/lambda/package/
    cp v2/lambda/handler.py v2/lambda/package/
    cd v2/lambda/package
    zip -r ../handler.zip .
    cd ../../..

This builds the Lambda zip file needed for both Terraform and CloudFormation deployments.

---

### Option A: Deploy with Terraform

Step 1 - Set up the shared Terraform backend first (one-time):

Fork and deploy this repo first: https://github.com/prk-gen-ai-aws/terraform-backend
This creates the S3 bucket used to store Terraform state. Follow the README in that repo.

Step 2 - Fill in your values:

    cd v2/IaC/terraform
    cp terraform.tfvars.example terraform.tfvars

Edit terraform.tfvars and fill in:
- aws_region: your AWS region (e.g. us-east-1)
- aws_account_id: your 12-digit AWS account ID
- project_name: keep as-is or customize
- environment: dev
- bedrock_model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
  (verify this is active in your account: aws bedrock list-inference-profiles --region us-east-1)

    cp backend.tfvars.example backend.tfvars

Edit backend.tfvars and fill in:
- bucket: name of the S3 bucket created by your terraform-backend deployment

Step 3 - Deploy infrastructure:

    terraform init -backend-config=backend.tfvars
    terraform plan
    terraform apply

Step 4 - Deploy Lambda code:

    cd ../../..

    # Get your Lambda function name from Terraform output first:
    terraform -chdir=v2/IaC/terraform output lambda_function_name

    # Then deploy using the name returned above:
    aws lambda update-function-code --function-name <lambda_function_name> --zip-file fileb://v2/lambda/handler.zip

Step 5 - Configure environment:

    cp .env.example .env

Edit .env and fill in:
- AWS_REGION: your region
- S3_BUCKET_NAME: from terraform output s3_bucket_name
- API_GATEWAY_URL: from terraform output api_gateway_url

---

### Option B: Deploy with CloudFormation (simpler - no backend setup needed)

Step 1 - Deploy stack:

    aws cloudformation deploy \
      --template-file v2/IaC/cloudformation/template.yaml \
      --stack-name p01-doc-sum-dev \
      --parameter-overrides \
        AccountSuffix=<last-4-digits-of-your-account-id> \
        DeploymentVersion=v1 \
      --capabilities CAPABILITY_NAMED_IAM \
      --region us-east-1

Step 2 - Get outputs:

    aws cloudformation describe-stacks --stack-name p01-doc-sum-dev --query Stacks[0].Outputs

Step 3 - Deploy Lambda code:

    # Get LambdaFunctionName from Step 2 outputs, then deploy:
    aws lambda update-function-code --function-name <LambdaFunctionName from Step 2> --zip-file fileb://v2/lambda/handler.zip

Step 4 - Configure environment:

    cp .env.example .env

Edit .env and fill in:
- AWS_REGION: your region
- S3_BUCKET_NAME: from stack outputs (S3BucketName)
- API_GATEWAY_URL: from stack outputs (ApiGatewayUrl)

---

### Run the App (same for both options)

    source .venv/bin/activate
    pip install -r v2/app/requirements.txt
    streamlit run v2/app/main.py

Note: Upload limit is set to 10MB via .streamlit/config.toml at project root.

---

## Sample Documents

Ready-to-use test files are in v2/sample-documents/

- insurance-claim-sample.txt  -> Insurance Claim
- loan-document-sample.txt    -> Loan Document
- legal-contract-sample.txt   -> Legal Contract
- research-report-sample.txt  -> Research Report
- general-document-sample.txt -> General Document

For SEC Filing testing, download any 10-K or 10-Q from SEC EDGAR:
https://www.sec.gov/cgi-bin/browse-edgar

Note: Large PDFs (100+ pages) are processed using the first 15 pages for performance.
The most important sections of most business documents appear in the first 15 pages.

---

## Cost Estimate

All components are serverless - you pay only for what you use.

- Amazon Bedrock (Claude Haiku 4.5): approx USD 0.001 per summary
- AWS Lambda: Free tier covers development usage
- API Gateway: Free tier covers development usage
- Amazon S3: less than USD 0.01 per month for test files
- SSM Parameter Store: Free (standard tier)
- Total (development): less than USD 1.00 per month

---

## Things to Consider at Scale

Security:
- Add VPC endpoints to keep Bedrock traffic off the public internet
- Enable Bedrock Guardrails for content safety on sensitive documents
- Use S3 presigned URLs instead of direct PutObject for tighter access control

Scalability:
- Set Lambda reserved concurrency to prevent runaway costs
- Request Bedrock throughput quota increases for high-volume document processing
- Consider S3 multipart upload for documents larger than 10MB

High Availability:
- Deploy across multiple AWS regions for disaster recovery
- Add Lambda retry logic with exponential backoff
- Use SQS dead-letter queues for failed invocations

Cost Optimization:
- Implement prompt caching for repeated document types
- Set CloudWatch billing alarms for unexpected spend
- Consider async processing (SQS + Lambda) to decouple uploads from summarization

Performance:
- Current approach processes first 15 PDF pages
- For full-document processing at scale, consider a chunking strategy with multiple Lambda invocations

---

## AWS Documentation References

- Amazon Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html
- AWS Lambda execution roles: https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html
- Amazon API Gateway: https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- Amazon S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- AWS SSM Parameter Store: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html
- Terraform AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

---

## Version History

See VERSIONS.md for details on v1 vs v2 differences.

---

> Part of an ongoing series exploring Gen AI on AWS - applying real-world architecture patterns from serverless foundations to multi-agent agentic systems.
>
> Browse all projects: https://github.com/prk-gen-ai-aws
