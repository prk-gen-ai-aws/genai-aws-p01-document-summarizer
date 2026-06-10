"""
Project 1 — AI Document Summarizer
Lambda Handler — orchestrates S3 read + Bedrock summarization
"""

import json
import os
import boto3
import PyPDF2
import io

# ── AWS clients ──
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION_NAME', 'us-east-1'))
bedrock_client = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION_NAME', 'us-east-1'))

# ── Environment variables ──
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

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

    # Handle PDF files
    if key.lower().endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'
        return text.strip()

    # Handle text files
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


def invoke_bedrock(prompt: str) -> str:
    """Call Amazon Bedrock Claude 3 Sonnet and return the summary."""
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
        modelId=BEDROCK_MODEL_ID,
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
        summary = invoke_bedrock(prompt)

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
                's3_key': s3_key
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
