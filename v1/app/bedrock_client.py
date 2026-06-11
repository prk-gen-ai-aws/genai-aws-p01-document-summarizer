"""
Project 1 — AI Document Summarizer
AWS Integration Layer — S3 upload + API Gateway call
"""

import boto3
import requests
import os
import uuid
import json
from dotenv import load_dotenv

load_dotenv()

# ── Config ──
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL')


def upload_to_s3(file_bytes: bytes, filename: str) -> str:
    """Upload file to S3 and return the S3 key."""
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    s3_key = f"uploads/{uuid.uuid4()}/{filename}"
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=file_bytes
    )
    return s3_key


def call_summarize_api(s3_key: str, doc_type: str, summary_length: str) -> dict:
    """Call API Gateway to summarize the document."""
    import json
    payload = {
        "s3_key": s3_key,
        "doc_type": doc_type,
        "summary_length": summary_length
    }
    response = requests.post(
        API_GATEWAY_URL,
        json=payload,
        timeout=60
    )
    result = response.json()
    # API Gateway wraps Lambda response — unwrap body if needed
    if isinstance(result, dict) and 'body' in result:
        body = result['body']
        if isinstance(body, str):
            body = json.loads(body)
        return body
    return result


def fetch_sec_filing(ticker: str, filing_type: str) -> tuple:
    """
    Fetch SEC filing text from EDGAR for a given ticker.
    Returns (text_content, filename)
    """
    import urllib.request

    headers = {'User-Agent': 'PRK Portfolio Project prk@example.com'}
    filename = f"{ticker}_{filing_type}.txt"

    try:
        # Search EDGAR for company CIK
        search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms={filing_type}&hits.hits._source=period_of_report,entity_name,file_date,period_of_report"
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            return f"No {filing_type} filing found for ticker {ticker} on SEC EDGAR.", filename

        # Get the latest filing details
        latest = hits[0].get('_source', {})
        entity_name = latest.get('entity_name', ticker)
        period = latest.get('period_of_report', 'Unknown period')

        placeholder = f"""SEC {filing_type} Filing — {entity_name} ({ticker})
Period: {period}

This is a placeholder for the actual SEC EDGAR filing content.
In production this would fetch the full filing text from EDGAR.
Entity: {entity_name}
Ticker: {ticker}
Filing Type: {filing_type}
Period of Report: {period}
"""
        return placeholder, filename

    except Exception as e:
        placeholder = f"SEC {filing_type} filing for {ticker}. Could not fetch from EDGAR: {str(e)}"
        return placeholder, filename
