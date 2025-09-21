"""
SEC Filing Downloader
Downloads 10-K filings from SEC EDGAR database
"""

import os
import requests
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import json
from pathlib import Path


class SECDownloader:
    """Downloads SEC 10-K filings for specified companies and years"""

    # Company CIK codes from assignment
    COMPANY_CIKS = {
        "GOOGL": "1652044",
        "MSFT": "789019",
        "NVDA": "1045810"
    }

    BASE_URL = "https://www.sec.gov"
    EDGAR_URL = f"{BASE_URL}/Archives/edgar/data"
    HEADERS = {
        "User-Agent": "Financial-QA-System research@example.com",
        "Accept-Encoding": "gzip, deflate"
    }

    def __init__(self, download_dir: str = "data/filings"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def get_company_filings(self, cik: str, form_type: str = "10-K") -> List[Dict]:
        """Get list of filings for a company using SEC EDGAR submissions API"""
        # Use SEC's official data API
        cik_padded = cik.zfill(10)  # Pad CIK to 10 digits with leading zeros
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

        try:
            print(f"Fetching submissions for CIK {cik_padded}...")
            response = requests.get(submissions_url, headers=self.HEADERS)
            response.raise_for_status()
            time.sleep(0.1)  # Be respectful to SEC servers - max 10 requests/second

            data = response.json()
            filing_list = []

            # Extract filings from the submissions data
            if "filings" in data and "recent" in data["filings"]:
                recent_filings = data["filings"]["recent"]

                # Get arrays of filing data
                forms = recent_filings.get("form", [])
                accession_numbers = recent_filings.get("accessionNumber", [])
                filing_dates = recent_filings.get("filingDate", [])
                report_dates = recent_filings.get("reportDate", [])
                primary_documents = recent_filings.get("primaryDocument", [])
                primary_doc_descriptions = recent_filings.get("primaryDocDescription", [])

                # Find 10-K filings
                for i, form in enumerate(forms):
                    if form == form_type and i < len(accession_numbers):
                        filing_date = filing_dates[i] if i < len(filing_dates) else ""
                        report_date = report_dates[i] if i < len(report_dates) else filing_date
                        primary_doc = primary_documents[i] if i < len(primary_documents) else ""
                        description = primary_doc_descriptions[i] if i < len(primary_doc_descriptions) else f"{form_type} filing"

                        # Extract year from filing or report date
                        year = filing_date[:4] if filing_date else report_date[:4] if report_date else ""

                        # Only include filings from 2022-2024
                        if year in ["2022", "2023", "2024"]:
                            filing_list.append({
                                "accessionNumber": accession_numbers[i],
                                "filingDate": filing_date,
                                "reportDate": report_date,
                                "primaryDocument": primary_doc,
                                "primaryDocDescription": description,
                                "targetYear": year
                            })

            print(f"Found {len(filing_list)} {form_type} filings for years 2022-2024")
            return filing_list

        except Exception as e:
            print(f"Error fetching filings for CIK {cik}: {e}")
            return []

    def filter_filings_by_year(self, filings: List[Dict], years: List[str]) -> List[Dict]:
        """Filter filings by target years"""
        filtered = []
        for filing in filings:
            filing_year = filing["filingDate"][:4]
            # For 10-K, usually filed in early year for previous year's data
            # Check both filing year and report year
            report_year = filing["reportDate"][:4] if filing["reportDate"] else filing_year

            if filing_year in years or report_year in years:
                filing["targetYear"] = report_year
                filtered.append(filing)

        return filtered[:len(years)]  # Limit to requested years

    def download_filing(self, cik: str, accession_number: str, filename: str,
                       company: str, year: str) -> Optional[str]:
        """Download a single filing"""
        # Clean accession number for URL
        acc_no_clean = accession_number.replace("-", "")

        # Construct download URL
        filing_url = f"{self.EDGAR_URL}/{cik}/{acc_no_clean}/{filename}"

        # Create company directory
        company_dir = self.download_dir / company
        company_dir.mkdir(exist_ok=True)

        # Local filename
        local_filename = f"{company}_{year}_{filename}"
        local_path = company_dir / local_filename

        # Skip if already exists
        if local_path.exists():
            print(f"File already exists: {local_path}")
            return str(local_path)

        try:
            print(f"Downloading {filing_url}")
            response = requests.get(filing_url, headers=self.HEADERS)
            response.raise_for_status()

            # Save file
            with open(local_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded: {local_path}")
            time.sleep(0.1)  # Be respectful

            return str(local_path)

        except Exception as e:
            print(f"Error downloading {filing_url}: {e}")
            return None

    def download_company_filings(self, company: str, years: List[str]) -> List[str]:
        """Download all filings for a company and years"""
        if company not in self.COMPANY_CIKS:
            raise ValueError(f"Unknown company: {company}")

        cik = self.COMPANY_CIKS[company]
        print(f"Downloading {company} filings for years {years}")

        # Get company filings
        filings = self.get_company_filings(cik)
        if not filings:
            print(f"No filings found for {company}")
            return []

        # Filter by years
        target_filings = self.filter_filings_by_year(filings, years)
        print(f"Found {len(target_filings)} filings for {company}")

        downloaded_files = []
        for filing in target_filings:
            filepath = self.download_filing(
                cik,
                filing["accessionNumber"],
                filing["primaryDocument"],
                company,
                filing["targetYear"]
            )
            if filepath:
                downloaded_files.append(filepath)

        return downloaded_files

    def download_all_filings(self, companies: List[str], years: List[str]) -> Dict[str, List[str]]:
        """Download filings for all companies and years"""
        results = {}

        for company in companies:
            try:
                files = self.download_company_filings(company, years)
                results[company] = files
                print(f"Downloaded {len(files)} files for {company}")
            except Exception as e:
                print(f"Error downloading {company}: {e}")
                results[company] = []

        return results


if __name__ == "__main__":
    # Test download
    downloader = SECDownloader()
    companies = ["GOOGL", "MSFT", "NVDA"]
    years = ["2022", "2023", "2024"]

    results = downloader.download_all_filings(companies, years)
    print(f"Download results: {results}")