import gspread
from google.oauth2.service_account import Credentials
from app.config import GOOGLE_SHEET_ID


class SheetManager:
    """
    Manages Google Sheets writes for:
    1. Main Article Sheet
    2. Dedicated Gap Analysis Sheet

    GUARANTEES:
    - No accidental data wipes
    - Deterministic row updates
    - Stable UI reflection
    - Gap Analysis sheet integrity
    """

    # ==================================================
    # SCHEMAS
    # ==================================================
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

    # ==================================================
    # INIT
    # ==================================================
    def __init__(self, creds_path: str = "service_account.json"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=scopes
        )

        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID)

        self.article_sheet = self.spreadsheet.sheet1
        self.gap_sheet = self._get_or_create_sheet("Gap Analysis")

        self._ensure_headers(self.article_sheet, self.ARTICLE_HEADERS)
        self._ensure_headers(self.gap_sheet, self.GAP_HEADERS)

        self._article_row_cache = self._build_article_row_cache()
        self._url_row_cache = self._build_url_row_cache()

    # ==================================================
    # INTERNAL HELPERS
    # ==================================================
    def _get_or_create_sheet(self, title: str):
        try:
            return self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(
                title=title,
                rows=500,
                cols=20
            )

    def _ensure_headers(self, sheet, headers: list):
        """
        Ensures header row exists and matches schema.
        NEVER clears valid data rows.
        """
        existing = sheet.row_values(1)
        if not existing:
            sheet.append_row(headers, value_input_option="RAW")

    def _build_article_row_cache(self) -> dict:
        cache = {}
        records = self.article_sheet.get_all_records()
        for idx, row in enumerate(records):
            aid = row.get("Article ID")
            if aid:
                cache[aid] = idx + 2
        return cache

    def _build_url_row_cache(self) -> dict:
        cache = {}
        records = self.article_sheet.get_all_records()
        for idx, row in enumerate(records):
            url = row.get("URL")
            if url:
                cache[url] = idx + 2
        return cache

    # ==================================================
    # ARTICLE UPSERT (MAIN SHEET)
    # ==================================================
    def upsert(self, data: dict):
        article_id = data.get("article_id")
        url = data.get("url")

        if not article_id or not url:
            return

        row = [
            article_id,
            data.get("article_title"),
            data.get("category"),
            data.get("section"),
            url,
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

        # Update by Article ID
        if article_id in self._article_row_cache:
            r = self._article_row_cache[article_id]
            self.article_sheet.update(f"A{r}:O{r}", [row], value_input_option="RAW")
            return

        # Update by URL (fallback)
        if url in self._url_row_cache:
            r = self._url_row_cache[url]
            self.article_sheet.update(f"A{r}:O{r}", [row], value_input_option="RAW")
            self._article_row_cache[article_id] = r
            return

        # Insert new row
        self.article_sheet.append_row(row, value_input_option="RAW")
        r = len(self.article_sheet.get_all_values())
        self._article_row_cache[article_id] = r
        self._url_row_cache[url] = r

    # ==================================================
    # GAP ANALYSIS UPSERT (DEDICATED SHEET)
    # ==================================================
    def upsert_gap_analysis(self, gaps: list):
        """
        Writes ONLY to Gap Analysis sheet.
        Keeps header intact.
        Fully refreshes data rows.
        """

        if not gaps:
            print("⚠️ No gaps to write")
            return

        # Ensure header integrity
        header = self.gap_sheet.row_values(1)
        if header != self.GAP_HEADERS:
            self.gap_sheet.clear()
            self.gap_sheet.append_row(self.GAP_HEADERS, value_input_option="RAW")

        # Remove existing data rows (keep header)
        existing_rows = len(self.gap_sheet.get_all_values())
        if existing_rows > 1:
            self.gap_sheet.delete_rows(2, existing_rows)

        rows = [
            [
                g.get("gap_id"),
                g.get("category"),
                g.get("gap_description"),
                g.get("priority"),
                g.get("suggested_article_title"),
                g.get("rationale")
            ]
            for g in gaps
        ]

        self.gap_sheet.append_rows(rows, value_input_option="RAW")
        print(f"✅ Gap Analysis updated ({len(rows)} rows)")