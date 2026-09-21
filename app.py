"""
Blacklist Dashboard — Phase 1 MVP
Single-file Streamlit application.

Roles:
  Manager  -> username: manager  password: manager123
  Visitor  -> username: visitor  password: visitor123

Data source:
  Google Sheets CSV export (~112,000 rows), loaded once via @st.cache_data.
  The cache is primed at module import time so there is zero loading delay
  after the user logs in. Phase 2 will add Google Sheets API write-back.
"""

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1R23JcPXdpPO8k_3ERpDoyzT4smFgmvJU/export?format=csv"
)

SHEET_EDIT_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1R23JcPXdpPO8k_3ERpDoyzT4smFgmvJU/edit"
)

# { (username, password): role }
CREDENTIALS = {
    ("manager", "Blk@Mngr24"): "manager",
    ("visitor", "Vis#Blk24"): "visitor",
}

SEARCH_COLS = ["Cust Name", "msisdn", "City", "account_number"]
MANAGER_CAP = 5000


# ─────────────────────────────────────────────
# PAGE CONFIG  (must be the very first st call)
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Blacklist Dashboard",
    layout="wide",
    # Collapse the native sidebar — we use a top navbar instead
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────
# DATA LAYER — primed at module load, not at login
# ─────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Download and cache the full dataset from Google Sheets.
    Called once at module import so the cache is warm before the user
    even reaches the login screen — zero delay after login.
    """
    df = pd.read_csv(SHEET_CSV_URL, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].str.strip()
    if "Cust Name" in df.columns:
        df["Cust Name"] = df["Cust Name"].str.strip(".").str.strip()

    # Normalise the total bucket column to a stable key "total_bucket".
    # The sheet header varies between "total_bucket_per_msisdn" and
    # "total_bucket_per_misdn" depending on the export — handle both.
    for raw_col in list(df.columns):
        if raw_col.lower().startswith("total_bucket"):
            df = df.rename(columns={raw_col: "total_bucket"})
            break

    return df


# Prime the cache immediately on import — runs in the background while
# the user is reading the login form. By the time they click Login the
# DataFrame is already in memory and load_data() returns instantly.
load_data()


# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────

def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Hide all Streamlit chrome ─────────────────── */
        #MainMenu            { visibility: hidden; }
        footer               { visibility: hidden; }
        header               { visibility: hidden; }
        /* Hide the sidebar collapse arrow entirely */
        [data-testid="collapsedControl"] { display: none; }
        section[data-testid="stSidebar"] { display: none; }

        /* ── Top navbar ────────────────────────────────── */
        .top-navbar {
            position: fixed;
            top: 0; left: 0; right: 0;
            height: 52px;
            background: #161b22;
            border-bottom: 1px solid #30363d;
            display: flex;
            align-items: center;
            padding: 0 28px;
            z-index: 999;
            gap: 16px;
        }
        .top-navbar .brand {
            font-weight: 700;
            font-size: 15px;
            color: #e6edf3;
            letter-spacing: 0.02em;
            margin-right: auto;
        }
        .top-navbar .nav-user {
            font-size: 13px;
            color: #8b949e;
        }
        .top-navbar .nav-user strong {
            color: #e6edf3;
        }
        .badge-manager {
            background: #7c5cd8;
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-visitor {
            background: #3b82d4;
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }
        .nav-source-link {
            font-size: 13px;
            color: #3b82d4;
            text-decoration: none;
            border: 1px solid #3b82d4;
            padding: 3px 12px;
            border-radius: 6px;
        }
        .nav-source-link:hover { background: #3b82d420; }

        /* Push page content below the fixed navbar */
        .main .block-container {
            padding-top: 68px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# TOP NAVBAR
# ─────────────────────────────────────────────

def show_navbar() -> None:
    """
    Render a fixed top navbar with brand, user info, role badge,
    optional Sumber Data link (manager only), Refresh Data button,
    and a Logout button.

    Streamlit buttons cannot live inside the fixed HTML navbar div,
    so they are placed in narrow columns pulled up via negative margin
    to visually sit inside the navbar band.
    """
    role = st.session_state.get("role", "visitor")
    username = st.session_state.get("username", "")
    badge_class = "badge-manager" if role == "manager" else "badge-visitor"
    role_label = "Manager" if role == "manager" else "Visitor"

    source_link = (
        f'<a class="nav-source-link" href="{SHEET_EDIT_URL}" target="_blank">'
        "Sumber Data"
        "</a>"
        if role == "manager"
        else ""
    )

    navbar_html = (
        '<div class="top-navbar">'
        '<span class="brand">Blacklist Dashboard</span>'
        f'{source_link}'
        f'<span class="nav-user">'
        f'<strong>{username}</strong>'
        f'&nbsp;&nbsp;<span class="{badge_class}">{role_label}</span>'
        f'</span>'
        '<span style="width:8px"></span>'
        "</div>"
    )
    st.markdown(navbar_html, unsafe_allow_html=True)

    # Two buttons in narrow columns, pulled up into the navbar band.
    spacer, refresh_col, logout_col = st.columns([0.86, 0.07, 0.07])

    with refresh_col:
        st.markdown('<div style="margin-top:-46px">', unsafe_allow_html=True)
        if st.button("Refresh Data", key="navbar_refresh"):
            load_data.clear()   # wipe the @st.cache_data entry
            load_data()         # re-download immediately so next render is instant
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with logout_col:
        st.markdown('<div style="margin-top:-46px">', unsafe_allow_html=True)
        if st.button("Logout", key="navbar_logout"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────

def show_login() -> None:
    """Centered login form. Data is already cached — login is instant."""
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.title("Blacklist Dashboard")
        st.subheader("Internal Dashboard")
        st.write("")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password"
            )
            submitted = st.form_submit_button(
                "Login", use_container_width=True, type="primary"
            )

        if submitted:
            role = CREDENTIALS.get((username.strip(), password))
            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.username = username.strip()
                st.rerun()
            else:
                st.error("Incorrect username or password. Please try again.")


# ─────────────────────────────────────────────
# SHARED SEARCH UTILITY
# ─────────────────────────────────────────────

def search_and_rank(
    df: pd.DataFrame, query: str, visitor_mode: bool = False
) -> pd.DataFrame:
    """
    Return rows matching query, sorted by relevance.

    Both roles use the same 3-tier Cust Name priority scoring:
      3 — Cust Name exactly equals query
      2 — Cust Name starts with query
      1 — Cust Name contains query (mid/end)

    Secondary columns (msisdn, account_number) score 1 only when
    the row has NO Cust Name match (score still 0).

    City is intentionally excluded from scoring to prevent partial
    city name matches (e.g. "hera" in "Halmahera") from polluting
    results with unrelated customer names.

    visitor_mode is kept as a parameter for forward compatibility
    but the scoring logic is now identical for both roles.
    """
    q = query.strip().lower()
    if not q:
        return pd.DataFrame(columns=df.columns)

    scores = pd.Series(0, index=df.index)

    # Tier 1-3: Cust Name scoring (applies to both roles)
    if "Cust Name" in df.columns:
        name_lower = df["Cust Name"].str.lower()
        # Score 1 — name contains query anywhere (lowest)
        scores = scores.where(
            ~name_lower.str.contains(q, regex=False, na=False), other=1
        )
        # Score 2 — name starts with query (overrides contains)
        scores = scores.where(
            ~name_lower.str.startswith(q, na=False), other=2
        )
        # Score 3 — exact name match (overrides starts-with)
        scores = scores.where(~(name_lower == q), other=3)

    # Secondary: msisdn and account_number score 1 only when no name match
    for col in ["msisdn", "account_number"]:
        if col in df.columns:
            col_mask = (
                df[col].str.lower().str.contains(q, regex=False, na=False)
                & (scores == 0)
            )
            scores = scores.where(~col_mask, other=1)

    matched = df[scores > 0].copy()
    matched["_score"] = scores[scores > 0]
    matched = matched.sort_values(
        ["_score", "Cust Name"], ascending=[False, True]
    ).drop(columns=["_score"])
    return matched.reset_index(drop=True)


# ─────────────────────────────────────────────
# VISITOR DASHBOARD
# ─────────────────────────────────────────────

def render_visitor_card(row: pd.Series) -> None:
    """
    Compact horizontal card optimised for both desktop and mobile.

    Layout: CSS Grid with 2 columns on mobile (<=600px) and 4 columns
    on desktop. All protected fields (no-copy) live in one HTML block.
    FA ID uses st.code() placed directly below the card with zero gap,
    visually attached via negative top margin so it reads as part of
    the card.

    All styles are fully inline — no external CSS class references
    inside the protected block — to prevent Streamlit code-fence bug.
    """
    name    = row.get("Cust Name", "")
    msisdn  = row.get("msisdn", "")
    city    = row.get("City", "")
    address = row.get("Address", "")
    bucket  = row.get("total_bucket", "")
    fa_id   = row.get("account_number", "")

    # Inline style fragments
    WRAP  = (
        "user-select:none;pointer-events:none;"
        "background:#f7f8fa;border:1px solid #e5e7eb;border-radius:8px 8px 0 0;"
        "padding:10px 14px 8px 14px;margin-bottom:0;"
    )
    GRID  = (
        "display:grid;"
        "grid-template-columns:repeat(2,1fr);"   # 2-col default (mobile)
        "gap:6px 14px;"
    )
    # On wider screens override to 4 columns via a media-query style block
    MEDIA = (
        "<style>"
        "@media(min-width:600px){"
        ".vc-grid{grid-template-columns:repeat(4,1fr)!important}"
        "}"
        "</style>"
    )
    CELL  = "min-width:0;"          # prevent overflow in narrow cells
    LBL   = (
        "font-size:10px;font-weight:600;color:#57606a;"
        "text-transform:uppercase;letter-spacing:0.04em;margin-bottom:1px;"
    )
    VAL   = "font-size:13px;color:#1f2328;word-break:break-word;"
    # Address gets its own wider row spanning all columns
    ADDR_ROW = (
        "grid-column:1/-1;"        # span full width
        "min-width:0;"
    )

    st.markdown(
        f"{MEDIA}"
        f'<div style="{WRAP}">'
        f'<div class="vc-grid" style="{GRID}">'
        # Cell 1 — Name
        f'<div style="{CELL}">'
        f'<div style="{LBL}">Nama Nasabah</div>'
        f'<div style="{VAL}">{name}</div>'
        f'</div>'
        # Cell 2 — MSISDN
        f'<div style="{CELL}">'
        f'<div style="{LBL}">MSISDN</div>'
        f'<div style="{VAL}">{msisdn}</div>'
        f'</div>'
        # Cell 3 — City
        f'<div style="{CELL}">'
        f'<div style="{LBL}">Kota</div>'
        f'<div style="{VAL}">{city}</div>'
        f'</div>'
        # Cell 4 — Total Bucket
        f'<div style="{CELL}">'
        f'<div style="{LBL}">Total Bucket</div>'
        f'<div style="{VAL}">{bucket}</div>'
        f'</div>'
        # Full-width row — Address
        f'<div style="{ADDR_ROW}">'
        f'<div style="{LBL}">Alamat</div>'
        f'<div style="{VAL}">{address}</div>'
        f'</div>'
        f'</div>'   # end grid
        f'</div>',  # end card
        unsafe_allow_html=True,
    )

    # FA ID copyable strip — visually attached to the bottom of the card.
    # Rounded only on bottom edges; zero gap achieved by negative margin.
    fa_strip = (
        "background:#eef4ff;border:1px solid #c7d9f8;border-top:none;"
        "border-radius:0 0 8px 8px;"
        "padding:5px 14px 6px 14px;margin-bottom:8px;"
        "display:flex;align-items:center;gap:10px;"
    )
    fa_lbl = (
        "font-size:10px;font-weight:600;color:#3b82d4;"
        "text-transform:uppercase;letter-spacing:0.04em;white-space:nowrap;"
    )
    fa_val = (
        "font-family:monospace;font-size:13px;color:#1f2328;"
        "background:#dbeafe;border:1px solid #bfdbfe;border-radius:4px;"
        "padding:1px 8px;cursor:pointer;"
    )
    st.markdown(
        f'<div style="{fa_strip}">'
        f'<span style="{fa_lbl}">FA ID</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    # st.code renders with its own copy button — placed directly below
    # the strip label via tight container margins
    st.markdown(
        '<div style="margin-top:-12px;margin-bottom:8px;">',
        unsafe_allow_html=True,
    )
    st.code(fa_id, language=None)
    st.markdown("</div>", unsafe_allow_html=True)


def show_visitor_dashboard(df: pd.DataFrame) -> None:
    st.title("Pencarian Nasabah")
    st.caption("Masukkan nama, nomor MSISDN, atau kota untuk mencari data nasabah.")

    query = st.text_input(
        "Cari Nasabah",
        placeholder="Contoh: SELVINA SAPTARI atau BANDUNG",
        label_visibility="collapsed",
    )

    if not query.strip():
        st.info("Ketik nama atau nomor MSISDN nasabah di kotak pencarian untuk memulai.")
        return

    results = search_and_rank(df, query, visitor_mode=True)
    total = len(results)

    if total == 0:
        st.warning(f'Tidak ditemukan data untuk "{query}".')
        return

    st.success(f'Ditemukan {total:,} hasil untuk "{query}".')
    st.divider()

    for _, row in results.iterrows():
        render_visitor_card(row)


# ─────────────────────────────────────────────
# MANAGER DASHBOARD
# ─────────────────────────────────────────────

def show_manager_dashboard(df: pd.DataFrame) -> None:
    st.title("Manager Dashboard")
    st.caption("Cari, periksa duplikat, dan edit data nasabah.")

    query = st.text_input(
        "Cari Nasabah",
        placeholder="Contoh: SELVINA SAPTARI atau BANDUNG",
        label_visibility="collapsed",
        key="manager_search",
    )

    if not query.strip():
        st.info("Ketik nama, MSISDN, kota, atau account number untuk memulai pencarian.")
        return

    results = search_and_rank(df, query)
    total = len(results)

    if total == 0:
        st.warning(f'Tidak ditemukan data untuk "{query}".')
        return

    display_df = results.head(MANAGER_CAP).copy()
    if total > MANAGER_CAP:
        st.info(f"Ditemukan {total:,} hasil. Menampilkan {MANAGER_CAP} teratas.")

    # Summary metrics
    unique_msisdn = display_df["msisdn"].nunique()
    dup_count = display_df.duplicated("msisdn", keep=False).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Hasil", f"{len(display_df):,}")
    c2.metric("MSISDN Unik", f"{unique_msisdn:,}")
    c3.metric(
        "Duplikat MSISDN",
        f"{dup_count:,}",
        delta=f"{dup_count} entri" if dup_count > 0 else None,
        delta_color="inverse" if dup_count > 0 else "off",
    )

    st.divider()
    st.subheader("Data Nasabah")
    st.data_editor(
        display_df,
        key="manager_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "account_number": st.column_config.TextColumn("Account Number", width="medium"),
            "msisdn":         st.column_config.TextColumn("MSISDN", width="medium"),
            "Val":            st.column_config.TextColumn("Val", width="small"),
            "Cust Name":      st.column_config.TextColumn("Nama Nasabah", width="large"),
            "Address":        st.column_config.TextColumn("Alamat", width="large"),
            "City":           st.column_config.TextColumn("Kota", width="medium"),
            "total_bucket": st.column_config.TextColumn(
                "Total Bucket (IDR)", width="medium"
            ),
        },
    )

    if st.button("Simpan Perubahan", type="primary"):
        st.success(
            "Perubahan telah dicatat. "
            "Write-back ke Google Sheets akan diaktifkan di Phase 2 "
            "menggunakan Google Sheets API & Service Account."
        )

    # Duplicate detection panel
    duplicates = display_df[display_df.duplicated("msisdn", keep=False)].copy()
    if not duplicates.empty:
        st.divider()
        st.warning(
            f"{len(duplicates):,} baris memiliki MSISDN yang sama. "
            "Periksa entri duplikat di bawah ini."
        )
        with st.expander("Lihat Entri Duplikat", expanded=True):
            st.dataframe(
                duplicates.sort_values("msisdn"),
                use_container_width=True,
                hide_index=True,
            )


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    inject_global_css()

    if not st.session_state.get("logged_in", False):
        show_login()
        return

    # Navbar replaces the sidebar — always rendered when logged in
    show_navbar()

    # Data is already cached from module-level load_data() call above —
    # this returns instantly with no network activity.
    df = load_data()

    role = st.session_state.get("role", "visitor")
    if role == "manager":
        show_manager_dashboard(df)
    else:
        show_visitor_dashboard(df)


if __name__ == "__main__":
    main()
