import gspread
from google.oauth2.service_account import Credentials
from app.config import GOOGLE_SHEET_ID


class SheetManager:
    """
    Manages all Google Sheets operations.

    Responsibilities:
    - Connect to Google Sheets
    - Idempotent upsert for articles
    - Write aggregated gap analysis

    Design goals:
    - Fast (minimal API calls)
    - Safe (never breaks pipeline)
    - Deterministic (same input → same row)
    """

    # --------------------------------------------------
    # SCHEMA DEFINITIONS
    # --------------------------------------------------
    ARTICLE_HEADERS = [
        "Article ID",
        "Article Title",
        "Category",
        "Section",
        "URL",
        "Content Type",
        "Approx Word Count",
        "Has Screenshots",
        "Topics Covered",
        "Gaps Identified",
        "Target User Role",
        "Onboarding Stage",
        "Gap Severity",
        "Automation Opportunity",
        "Category Risk Level"
    ]

    GAP_HEADERS = [
        "Gap ID",
        "Category",
        "Gap Description",
        "Priority",
        "Suggested Article Title",
        "Rationale"
    ]

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(self, creds_path: str = "service_account.json"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = Credentials.from_service_account_file(
            creds_path,
            scopes=scopes
        )

        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID)

        # Worksheets
        self.article_sheet = self.spreadsheet.sheet1
        self.gap_sheet = self._get_or_create_sheet("Gap Analysis")

        # Ensure headers exist
        self._ensure_headers(self.article_sheet, self.ARTICLE_HEADERS)
        self._ensure_headers(self.gap_sheet, self.GAP_HEADERS)

        # Cache article row index (huge speed-up)
        self._article_row_cache = self._build_article_row_cache()

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------
    def _get_or_create_sheet(self, title: str):
        try:
            return self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(
                title=title,
                rows=200,
                cols=20
            )

    def _ensure_headers(self, sheet, headers: list):
        existing = sheet.row_values(1)
        if existing != headers:
            sheet.clear()
            sheet.append_row(headers, value_input_option="RAW")

    def _build_article_row_cache(self) -> dict:
        """
        Builds:
        {
            article_id -> row_number
        }
        """
        cache = {}
        rows = self.article_sheet.get_all_records()

        for idx, row in enumerate(rows):
            article_id = row.get("Article ID")
            if article_id:
                cache[article_id] = idx + 2  # header is row 1

        return cache

    # --------------------------------------------------
    # ARTICLE UPSERT
    # --------------------------------------------------
    def upsert(self, data: dict):
        """
        Inserts or updates a single article row.
        """
        article_id = data.get("article_id")
        if not article_id:
            return

        row = [
            article_id,
            data.get("article_title"),
            data.get("category"),
            data.get("section"),
            data.get("url"),
            data.get("content_type"),
            data.get("approx_word_count"),
            "Yes" if data.get("has_screenshots") else "No",
            ", ".join(data.get("topics_covered", [])),
            ", ".join(data.get("gaps_identified", [])),
            data.get("target_user_role"),
            data.get("onboarding_stage"),
            data.get("gap_severity"),
            data.get("automation_opportunity"),
            data.get("category_risk_level")
        ]

        # Update existing
        if article_id in self._article_row_cache:
            row_num = self._article_row_cache[article_id]
            self.article_sheet.update(
                f"A{row_num}:O{row_num}",
                [row],
                value_input_option="RAW"
            )
        else:
            self.article_sheet.append_row(row, value_input_option="RAW")
            self._article_row_cache[article_id] = (
                len(self._article_row_cache) + 2
            )

    # --------------------------------------------------
    # GAP ANALYSIS UPSERT
    # --------------------------------------------------
    def upsert_gap_analysis(self, gaps: list):
        """
        Overwrites Gap Analysis sheet with latest results.
        """
        if not gaps:
            return

        self.gap_sheet.clear()
        self.gap_sheet.append_row(self.GAP_HEADERS, value_input_option="RAW")

        rows = []
        for gap in gaps:
            rows.append([
                gap.get("gap_id"),
                gap.get("category"),
                gap.get("gap_description"),
                gap.get("priority"),
                gap.get("suggested_article_title"),
                gap.get("rationale")
            ])

        # Batch insert (faster, quota-safe)
        self.gap_sheet.append_rows(rows, value_input_option="RAW")