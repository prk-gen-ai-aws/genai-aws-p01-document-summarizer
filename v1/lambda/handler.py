"""
Project 1 — AI Document Summarizer
Lambda Handler — orchestrates S3 read + Bedrock summarization
Model ID read from SSM Parameter Store — single source of truth
"""

import json
import os
import boto3
import PyPDF2
import io

# ── AWS clients ──
region = os.environ.get('AWS_REGION_NAME', 'us-east-1')
s3_client = boto3.client('s3', region_name=region)
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
ssm_client = boto3.client('ssm', region_name=region)

# ── Environment variables ──
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
SSM_MODEL_PARAM = os.environ.get('SSM_MODEL_PARAM', '/prk/genai/p01/bedrock-model-id')

def get_model_id() -> str:
    """Read model ID from SSM Parameter Store — single source of truth."""
    response = ssm_client.get_parameter(Name=SSM_MODEL_PARAM)
    return response['Parameter']['Value']

# ── Summary length prompts ──
SUMMARY_PROMPTS = {
    'short': 'Provide a concise summary in 3-5 sentences.',
    'medium': 'Provide a comprehensive summary in 2-3 paragraphs covering the main points.',
    'detailed': 'Provide a detailed summary covering all key sections, main findings, and important details.'
}

# ── Document type prompts ──
DOCUMENT_TYPE_PROMPTS = {
    'sec_10k': 'This is an SEC 10-K annual report. Focus on: revenue and financial performance, key risk factors, business overview, and management outlook.',
    'sec_10q': 'This is an SEC 10-Q quarterly report. Focus on: quarterly financial results, changes from prior quarter, updated risk factors, and management commentary.',
    'insurance_claim': 'This is an insurance claim document. Focus on: incident description, claimed damages, coverage details, and any supporting evidence mentioned.',
    'loan_document': 'This is a loan processing document. Focus on: loan amount, terms and conditions, borrower details, and key financial metrics.',
    'legal_contract': 'This is a legal contract. Focus on: parties involved, key obligations, terms and conditions, and important clauses.',
    'research_report': 'This is a research report. Focus on: key findings, methodology, conclusions, and recommendations.',
    'general': 'This is a general document.'
}


def extract_text_from_s3(bucket: str, key: str) -> str:
    """Read file from S3 and extract text content."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read()

    if key.lower().endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'
        return text.strip()

    return content.decode('utf-8').strip()


def build_prompt(text: str, doc_type: str, summary_length: str) -> str:
    """Build a structured prompt for Bedrock."""
    doc_context = DOCUMENT_TYPE_PROMPTS.get(doc_type, DOCUMENT_TYPE_PROMPTS['general'])
    length_instruction = SUMMARY_PROMPTS.get(summary_length, SUMMARY_PROMPTS['medium'])

    return f"""You are an expert document analyst. {doc_context}

Please analyze the following document and provide a summary.
{length_instruction}

Document content:
{text[:8000]}

Summary:"""


def invoke_bedrock(prompt: str, model_id: str) -> str:
    """Call Amazon Bedrock and return the summary."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })

    response = bedrock_client.invoke_model(
        modelId=model_id,
        body=body,
        contentType='application/json',
        accept='application/json'
    )

    response_body = json.loads(response['body'].read())
    return response_body['content'][0]['text']


def lambda_handler(event, context):
    """Main Lambda entry point."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        s3_key = body.get('s3_key')
        doc_type = body.get('doc_type', 'general')
        summary_length = body.get('summary_length', 'medium')

        if not s3_key:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 's3_key is required'})
            }

        # Get model ID from SSM — single source of truth
        model_id = get_model_id()

        # Extract text from S3
        text = extract_text_from_s3(S3_BUCKET_NAME, s3_key)

        if not text:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Could not extract text from document'})
            }

        # Build prompt and call Bedrock
        prompt = build_prompt(text, doc_type, summary_length)
        summary = invoke_bedrock(prompt, model_id)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'summary': summary,
                'doc_type': doc_type,
                'summary_length': summary_length,
                's3_key': s3_key,
                'model_id': model_id
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
