# Sample Documents

These sample documents are provided so you can immediately test the
AI Document Summarizer with each supported document type — no need
to find or create your own files.

## Available Samples

| File | Document Type to Select |
|---|---|
| `insurance-claim-sample.txt` | Insurance Claim |
| `loan-document-sample.txt` | Loan Document |
| `legal-contract-sample.txt` | Legal Contract |
| `research-report-sample.txt` | Research Report |
| `general-document-sample.txt` | General Document |

All samples above are **fictional** — created for testing purposes only.
No real names, companies, or data are used.

## Testing SEC Filings (10-K / 10-Q)

For the **SEC Filing (10-K / 10-Q)** document type, download any real
filing directly from SEC EDGAR (public domain, free):

1. Go to [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany)
2. Search for any public company (e.g. AAPL, MSFT, AMZN)
3. Download the latest 10-K or 10-Q PDF
4. Upload it to the app and select "SEC Filing (10-K / 10-Q)"

> Note: For performance, the app processes the first 15 pages of any PDF —
> this covers the most relevant sections (overview, market cap, risk factors)
> for most filings.

## How to Use

1. Run the app: `streamlit run app/main.py`
2. Select the matching document type from the dropdown
3. Upload the corresponding sample file
4. Click **Generate Summary**
