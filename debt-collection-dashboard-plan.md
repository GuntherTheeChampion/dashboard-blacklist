# Debt Collection Dashboard — Implementation Plan

## Top-Level Overview

Build a single-file Streamlit application (`app.py`) that acts as a lightweight,
lightning-fast internal search engine over ~112,000 rows of customer data sourced
from a published Google Sheets CSV export. The app enforces Role-Based Access
Control (RBAC) with two roles — **Manager** and **Visitor** — each seeing a
purpose-built dashboard. All data is loaded once at startup via `@st.cache_data`
and never reloaded on user interaction.

**Confirmed columns in the source sheet (headers are in row 1, data starts at row 2 — standard layout):**

| Col | Column name | Description | Notes | Copy policy |
|-----|-------------|-------------|-------|-------------|
| A | `account_number` | Unique account ID | Integer | Visitor: protected |
| B | `msisdn` | Phone number — the key field collectors dial | Indonesian format e.g. `628119979910` | Visitor: **copyable** via `st.code()` |
| C | `Val` | Formula column | Contains `FALSE`, `#REF!` — treat as raw string | Visitor: protected |
| D | `Cust Name` | Customer full name — primary search field | Has trailing dots e.g. `SELVINA TRI SAPTARI PUTRI .` — strip on load | Visitor: protected |
| E | `Address` | Street address | Long free-text | Visitor: protected |
| F | `City` | City | e.g. `GARUT`, `BANDUNG` | Visitor: protected |
| G | `total_bucket_per_msisdn` | Total outstanding bucket per MSISDN | Numeric-looking | Visitor: protected |

**CORRECTED CSV LOADING NOTE:**
Headers are in **row 1** and data starts in **row 2** — this is a standard CSV layout.
`pd.read_csv(url)` with default `header=0` is correct. No `skiprows` needed.
Additional cleaning required on load:
- Strip trailing/leading whitespace and dots from `Cust Name` (e.g. `"PUTRI ."` → `"PUTRI"`).
- `Val` column contains formula error strings (`FALSE`, `#REF!`) — keep as string, no numeric coercion.
- No unnamed columns — all 7 columns A–G have names in row 1.

**CSV source URL:**
`https://docs.google.com/spreadsheets/d/1R23JcPXdpPO8k_3ERpDoyzT4smFgmvJU/export?format=csv`

**Original Google Sheet URL (for Sumber Data link):**
`https://docs.google.com/spreadsheets/d/1R23JcPXdpPO8k_3ERpDoyzT4smFgmvJU/edit`

**Scope:** Phase 1 MVP — read-only Google Sheets CSV, no Google Sheets API write-back yet.

---

## Sub-Task 1 — Project Bootstrap & Data Layer

**Intent:**  
Set up the single `app.py` file and implement the cached data-loading function. This
is the performance backbone of the entire application. Using `@st.cache_data` ensures
the 112k-row DataFrame is read from the network exactly once per server session; all
subsequent user interactions are purely in-memory Pandas operations — no re-downloads.

**Expected Outcomes:**
- `app.py` exists with proper imports and a `SHEET_CSV_URL` constant.
- `load_data()` function decorated with `@st.cache_data` reads the CSV, coerces all
  relevant columns to strings (preventing NaN type mismatches during search), and
  returns a clean DataFrame.
- A `requirements.txt` is created listing `streamlit`, `pandas`, and `requests`.

**Todo List:**
1. Create `app.py` with standard imports (`streamlit`, `pandas`).
2. Define `SHEET_CSV_URL` and `SHEET_EDIT_URL` constants.
3. Implement `@st.cache_data` `load_data()` that calls
   `pd.read_csv(SHEET_CSV_URL)` (default `header=0`), then:
   - Strips leading/trailing whitespace from all column names.
   - Fills NA with empty strings.
   - Casts all columns to `str`.
   - Strips whitespace + trailing dots from `Cust Name`:
     `df['Cust Name'] = df['Cust Name'].str.strip().str.strip('.')`.strip()`.
   - Strips whitespace from all other string cell values.
4. Create `requirements.txt` with `streamlit`, `pandas`, `requests`.

**Relevant Context:**
- Default `header=0` is correct — row 1 of the sheet is the header row.
- `Cust Name` has trailing dots/spaces from the source data that must be stripped
  so that search and duplicate detection work correctly.
- `Val` column contains formula strings (`FALSE`, `#REF!`) — leaving as `str` is safe.
- All columns cast to `str` ensures `.str.contains()` never raises TypeError on
  numeric-looking columns like `total_bucket_per_msisdn`.

**Status:** [ ] pending

---

## Sub-Task 2 — Authentication & Session State (RBAC)

**Intent:**  
Implement a login wall using `st.session_state` so that unauthenticated users see only
a login form. Once authenticated, the role (`manager` or `visitor`) is stored in
session state and drives which dashboard is rendered. A sidebar shows the current role
and a Logout button that clears session state.

**Expected Outcomes:**
- Unauthenticated users see only a centered login form (username + password).
- Correct credentials set `st.session_state.logged_in = True` and
  `st.session_state.role = "manager" | "visitor"`.
- Wrong credentials show `st.error()`.
- Sidebar always shows the logged-in user's role and a Logout button.
- Logout clears `logged_in` and `role` from session state and reruns.

**Credentials:**
| Role    | Password     |
|---------|-------------|
| manager | manager123  |
| visitor | visitor123  |

**Todo List:**
1. Define a `CREDENTIALS` dict mapping password → role.
2. Write a `show_login()` function that renders the login form.
3. Write a `show_sidebar()` function that renders role badge + Logout button.
4. In `main()`, gate on `st.session_state.get("logged_in", False)` and branch to
   the appropriate dashboard.

**Relevant Context:**
- Use `st.rerun()` after login/logout to trigger a clean re-render.
- No persistent auth tokens needed; session state is per-browser-tab.

**Status:** [ ] pending

---

## Sub-Task 3 — Visitor Dashboard (Search + Copy-Restricted Display)

**Intent:**  
Give Visitors a fast MSISDN/name search experience. Results must be sorted by
relevance (exact matches first, then partial matches). The `MSISDN` field must be
rendered with `st.code()` for easy copying. All *other* displayed fields must be
rendered inside an HTML block with `user-select: none; pointer-events: none;` CSS
injected via `st.markdown(..., unsafe_allow_html=True)` so they cannot be highlighted,
copied, or screenshot-selected.

**Expected Outcomes:**
- Text input for search query — searches across **`Cust Name`** (primary) and also
  `msisdn`, `City`, `account_number` (secondary), case-insensitive.
- Results are displayed in ranked order: exact `Cust Name` match = top, partial = below.
- Number of results shown is capped at **50** to keep the page responsive.
- Each result card shows:
  - `msisdn` → rendered via `st.code()` (copyable, one-click).
  - All other fields (`account_number`, `Val`, `Cust Name`, `Address`, `City`,
    `total_bucket_per_msisdn`) → rendered inside
    `<div style="user-select:none; pointer-events:none;">` (not copyable).
- Empty search state shows a friendly prompt, not an empty table.

**Todo List:**
1. Write `search_and_rank(df, query)` shared function:
   - Score 2: `Cust Name` exactly equals query (case-insensitive).
   - Score 1: query is a substring of `Cust Name`, `msisdn`, `City`, or
     `account_number` (case-insensitive).
   - Score 0: no match — row excluded.
   - Returns DataFrame sorted descending by score, then `Cust Name` alphabetically.
2. Write `render_visitor_card(row)` that builds one result card:
   - `st.code(row['msisdn'])` for the copyable phone number.
   - All other fields in a single `st.markdown()` HTML block with
     `user-select:none; pointer-events:none;` on the container div.
3. Cap display at 50 rows; show `st.info()` banner if matches exceed 50.
4. Wire into `show_visitor_dashboard()`.

**Relevant Context:**
- `st.markdown(..., unsafe_allow_html=True)` is needed to inject the CSS.
- `pointer-events: none` prevents clicks; `user-select: none` prevents text selection.
- The 50-row card cap is a performance decision — rendering 112k HTML divs would
  lock the browser.

**Status:** [ ] pending

---

## Sub-Task 4 — Manager Dashboard (Search, Edit, Duplicate Detection, Source Link)

**Intent:**  
Give Managers a power-user view with editable rows, duplicate/similarity detection,
and a direct link back to the source Google Sheet. The goal is to help the Manager
spot duplicate entries and make corrections efficiently.

**Expected Outcomes:**
- Search bar (case-insensitive, uses `search_and_rank()` same as Visitor) with
  relevance sorting.
- Results shown in `st.data_editor()` — all columns editable, Manager can fix data.
- A **duplicate detection panel** below the editor: rows where `msisdn` appears
  more than once in the *result set* are flagged with `st.warning()` + a separate
  filtered table showing only the duplicates side-by-side.
- A "💾 Save Changes" button → `st.success()` placeholder for Phase 2 write-back.
- A **summary metrics row** above the editor: total matches, unique MSISDNs,
  duplicate count — using `st.metric()`.
- A "📄 Sumber Data" button in the sidebar that opens the original Google Sheet.
- Result cap of **200 rows** for Manager (no HTML card rendering overhead).

**Todo List:**
1. Write `show_manager_dashboard()` with search input calling `search_and_rank()`.
2. Show `st.metric()` summary: total results, unique `msisdn` count, duplicate count.
3. Display `st.data_editor(result_df, key="manager_editor", num_rows="dynamic")`.
4. Duplicate detection: `result_df[result_df.duplicated('msisdn', keep=False)]`;
   if non-empty, show `st.warning()` + `st.dataframe()` of duplicate rows.
5. "💾 Save Changes" button with `st.success()` placeholder message.
6. Sidebar: "📄 Sumber Data" as `st.link_button()` pointing to `SHEET_EDIT_URL`.

**Relevant Context:**
- `st.data_editor` requires a stable `key=` to avoid widget identity collisions.
- `st.link_button()` opens URLs in a new tab natively — no HTML needed.
- `search_and_rank()` is defined once and shared by both dashboards.
- Duplicate detection runs on the search *result set*, not all 112k rows.

**Status:** [ ] pending

---

## Sub-Task 5 — Styling, UX Polish & Final Wiring

**Intent:**  
Apply a clean, professional theme appropriate for an internal tool, wire all components
into a coherent `main()` entry point, and inject global CSS to suppress the Streamlit
menu/footer for a cleaner internal-tool feel.

**Expected Outcomes:**
- Global CSS hides the Streamlit hamburger menu and "Made with Streamlit" footer.
- Login page is centered and visually distinct.
- Role badge in sidebar uses colored `st.badge()` or colored markdown.
- App title and favicon set via `st.set_page_config()`.
- All sub-tasks wired into a single `main()` function at the bottom of `app.py`.

**Todo List:**
1. Add `st.set_page_config(page_title="Debt Collection Dashboard", page_icon="💰",
   layout="wide")` at the very top.
2. Inject global CSS to hide Streamlit chrome.
3. Style the login form with `st.columns` centering trick.
4. Wire `main()`: check session state → `show_login()` or
   `show_sidebar()` + dashboard branch.

**Relevant Context:**
- `st.set_page_config()` must be the first Streamlit call in the script.
- CSS injection via `st.markdown('<style>...</style>', unsafe_allow_html=True)`.

**Status:** [ ] pending
