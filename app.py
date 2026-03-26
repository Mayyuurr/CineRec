import streamlit as st
import requests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
API_BASE = "https://cinerec.onrender.com/" or "http://127.0.0.1:8000"

st.set_page_config(
    page_title="🎬 CineRec",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #0d0d0d; color: #e8e8e8; }

section[data-testid="stSidebar"] {
    background: linear-gradient(160deg,#1a1a2e,#16213e);
    border-right: 1px solid #2a2a4a;
}

.hero-banner {
    background: linear-gradient(135deg,#e50914,#b20710 60%,#1a0000);
    padding: 2.2rem 2rem; border-radius: 16px; margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(229,9,20,.3);
}
.hero-banner h1 { font-size:2.4rem; font-weight:700; margin:0; color:#fff; }
.hero-banner p  { font-size:1rem; color:#ffcdd2; margin:.3rem 0 0; }

.section-label {
    font-size:1.2rem; font-weight:700; color:#e50914;
    border-left:4px solid #e50914; padding-left:.6rem; margin:1.8rem 0 1rem;
}

/* movie cards */
.movie-card {
    background:#1c1c1c; border-radius:12px; overflow:hidden;
    transition:transform .2s,box-shadow .2s;
}
.movie-card:hover { transform:translateY(-5px) scale(1.02); box-shadow:0 10px 30px rgba(229,9,20,.4); }
.movie-card img { width:100%; display:block; }
.card-info { padding:.5rem .65rem .65rem; }
.card-title { font-size:.8rem; font-weight:600; color:#f0f0f0;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:.15rem; }
.card-meta { font-size:.7rem; color:#888; }
.star { color:#f5c518; }

/* detail banner */
.detail-backdrop { border-radius:16px; overflow:hidden; margin-bottom:1.4rem; position:relative; }
.detail-backdrop img { width:100%; max-height:360px; object-fit:cover; filter:brightness(.45); }
.detail-overlay {
    position:absolute; bottom:0; left:0; right:0;
    padding:1.4rem 1.8rem;
    background:linear-gradient(transparent,rgba(0,0,0,.88));
}
.detail-overlay h2 { font-size:1.9rem; font-weight:700; color:#fff; margin:0; }
.detail-overlay .gmeta { color:#e50914; font-size:.88rem; margin-top:.3rem; }
.overview-text { color:#bbb; font-size:.93rem; line-height:1.65; margin-top:.7rem; }

/* View button */
div[data-testid="stButton"] > button {
    background:#e50914; color:#fff; border:none; border-radius:6px;
    font-size:.78rem; font-weight:600; padding:.3rem 0;
    transition:background .18s;
}
div[data-testid="stButton"] > button:hover { background:#ff2030; color:#fff; }
</style>
""", unsafe_allow_html=True)

PLACEHOLDER = "https://via.placeholder.com/300x450/1c1c2e/e50914?text=No+Image"
CATEGORIES = {
    "🔥 Trending":    "trending",
    "⭐ Popular":     "popular",
    "🏆 Top Rated":  "top_rated",
    "🎬 Now Playing": "now_playing",
    "📅 Upcoming":   "upcoming",
}


# ─────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────
def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Backend not reachable — run: `uvicorn main:app --reload`")
    except requests.exceptions.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:250]}")
    except Exception as e:
        st.error(f"Error: {e}")
    return None


def fetch_home(category, limit=24):
    return api_get("/home", {"category": category, "limit": limit}) or []

def fetch_search_results(query, page=1):
    """TMDB keyword search — returns list of movie dicts."""
    data = api_get("/tmdb/search", {"query": query, "page": page})
    return data.get("results", []) if data else []

def fetch_bundle(query):
    """Full bundle: details + TF-IDF recs + genre recs."""
    return api_get("/movie/search", {"query": query, "tfidf_top_n": 12, "genre_limit": 12})


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
_defaults = {
    "view":          "home",      # "home" | "search" | "detail"
    "bundle":        None,        # current detail bundle
    "search_results": [],         # TMDB search result list
    "search_query":  "",          # last executed search query
    "home_movies":   [],
    "home_category": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# NAVIGATION HELPERS  (call → then st.rerun())
# ─────────────────────────────────────────────
def go_detail(title: str):
    """Fetch bundle for title, switch to detail view."""
    with st.spinner(f"Loading **{title}**…"):
        bundle = fetch_bundle(title)
    if bundle:
        st.session_state["bundle"] = bundle
        st.session_state["view"]   = "detail"
        st.rerun()
    else:
        st.warning("Could not load movie details. Try another title.")

def go_home():
    st.session_state["view"]   = "home"
    st.session_state["bundle"] = None
    st.rerun()

def go_search():
    st.session_state["view"]   = "search"
    st.session_state["bundle"] = None
    st.rerun()


# ─────────────────────────────────────────────
# RENDER: MOVIE CARD + GRID
# ─────────────────────────────────────────────
def _poster(m):
    if m.get("poster_url"):   return m["poster_url"]
    if m.get("poster_path"):  return f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
    return PLACEHOLDER

def render_card(movie, btn_key):
    title  = movie.get("title") or movie.get("name") or "Unknown"
    poster = _poster(movie)
    rating = movie.get("vote_average")
    year   = (movie.get("release_date") or "")[:4]
    star   = f"<span class='star'>★</span> {rating:.1f}" if rating else ""
    meta   = " · ".join(p for p in [year, star] if p)

    st.markdown(f"""
<div class="movie-card">
  <img src="{poster}" alt="{title}" onerror="this.src='{PLACEHOLDER}'"/>
  <div class="card-info">
    <div class="card-title" title="{title}">{title}</div>
    <div class="card-meta">{meta}</div>
  </div>
</div>""", unsafe_allow_html=True)

    return st.button("▶ View", key=btn_key, use_container_width=True)

def render_grid(movies, cols=5, prefix="g"):
    """Returns title of clicked movie, or None."""
    if not movies:
        st.info("No movies to show.")
        return None
    for i in range(0, len(movies), cols):
        row = movies[i: i+cols]
        grid = st.columns(cols)
        for col, mv in zip(grid, row):
            uid  = mv.get("tmdb_id") or mv.get("id") or 0
            slug = (mv.get("title") or mv.get("name") or "")[:8].replace(" ", "_")
            key  = f"{prefix}_{uid}_{slug}_{i}"
            with col:
                if render_card(mv, key):
                    return mv.get("title") or mv.get("name") or ""
    return None


# ─────────────────────────────────────────────
# RENDER: DETAIL VIEW
# ─────────────────────────────────────────────
def render_detail(bundle):
    d         = bundle.get("movie_details", {})
    tfidf_rec = bundle.get("tfidf_recommendations", [])
    genre_rec = bundle.get("genre_recommendations", [])

    title    = d.get("title", "")
    overview = d.get("overview") or "No overview available."
    year     = (d.get("release_date") or "")[:4]
    genres   = ", ".join(g.get("name", "") for g in d.get("genres", []))
    backdrop = d.get("backdrop_url") or d.get("poster_url") or ""
    poster   = d.get("poster_url") or PLACEHOLDER

    # backdrop
    if backdrop:
        st.markdown(f"""
<div class="detail-backdrop">
  <img src="{backdrop}" alt="{title}"/>
  <div class="detail-overlay">
    <h2>{title}</h2>
    <div class="gmeta">🎭 {genres}&nbsp;&nbsp;|&nbsp;&nbsp;📅 {year}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # poster + info
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(poster, use_container_width=True)
    with c2:
        if genres:      st.markdown(f"**Genres:** {genres}")
        if year:        st.markdown(f"**Year:** {year}")
        st.markdown(f'<p class="overview-text">{overview}</p>', unsafe_allow_html=True)

    # ── TF-IDF recs ──────────────────────────────────────
    if tfidf_rec:
        st.markdown('<div class="section-label">🤖 AI Recommendations (TF-IDF)</div>', unsafe_allow_html=True)
        tfidf_movies = []
        for item in tfidf_rec:
            card = item.get("tmdb") or {}
            tfidf_movies.append({
                "title":        card.get("title") or item.get("title", ""),
                "tmdb_id":      card.get("tmdb_id", 0),
                "poster_url":   card.get("poster_url"),
                "release_date": card.get("release_date", ""),
                "vote_average": card.get("vote_average"),
            })
        clicked = render_grid(tfidf_movies, cols=6, prefix="tfidf")
        if clicked:
            go_detail(clicked)
    else:
        st.info("ℹ️ No TF-IDF recommendations — this movie may not be in the local dataset. Genre recommendations are shown below.")

    # ── Genre recs ────────────────────────────────────────
    if genre_rec:
        st.markdown('<div class="section-label">🎭 More From This Genre</div>', unsafe_allow_html=True)
        clicked = render_grid(genre_rec, cols=6, prefix="genre")
        if clicked:
            go_detail(clicked)

    # ── Debug expander ────────────────────────────────────
    with st.expander("🛠️ Debug — Raw API response"):
        st.write(f"TF-IDF recs: **{len(tfidf_rec)}**  |  Genre recs: **{len(genre_rec)}**")
        if tfidf_rec:
            st.write("Top TF-IDF matches:")
            for item in tfidf_rec[:5]:
                t = (item.get("tmdb") or {}).get("title") or item.get("title", "?")
                s = item.get("score", 0)
                st.write(f"  • {t}  →  score {s:.4f}")
        st.json(bundle, expanded=False)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 CineRec")
    st.markdown("---")

    nav = st.radio("Navigate", ["🏠 Home", "🔍 Search"], label_visibility="collapsed")

    # sync nav radio → view state (don't rerun if already there)
    target_view = "home" if nav == "🏠 Home" else "search"
    if st.session_state["view"] == "detail":
        pass  # stay in detail; user uses Back button
    elif st.session_state["view"] != target_view:
        st.session_state["view"] = target_view
        st.session_state["bundle"] = None
        st.session_state["search_results"] = []

    st.markdown("---")
    if nav == "🏠 Home":
        cat_label    = st.selectbox("Category", list(CATEGORIES.keys()))
        home_cat_key = CATEGORIES[cat_label]
    else:
        cat_label    = None
        home_cat_key = None

    st.markdown("---")
    if st.session_state["view"] == "detail":
        if st.button("← Back", use_container_width=True):
            prev = "home" if nav == "🏠 Home" else "search"
            st.session_state["view"]   = prev
            st.session_state["bundle"] = None
            st.rerun()

    st.markdown("<small style='color:#555'>TMDB + TF-IDF · FastAPI + Streamlit</small>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <h1>🎬 CineRec</h1>
  <p>AI-powered movie recommendations — TF-IDF similarity + TMDB intelligence</p>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════════

view = st.session_state["view"]

# ─── DETAIL ──────────────────────────────────────────
if view == "detail" and st.session_state["bundle"]:
    bundle_title = (st.session_state["bundle"].get("movie_details") or {}).get("title", "")
    st.markdown(f'<div class="section-label">🎬 {bundle_title}</div>', unsafe_allow_html=True)
    render_detail(st.session_state["bundle"])

# ─── HOME ────────────────────────────────────────────
elif view == "home":
    # fetch only when category changes or list is empty
    if st.session_state["home_category"] != home_cat_key or not st.session_state["home_movies"]:
        with st.spinner("Loading movies…"):
            movies = fetch_home(home_cat_key, limit=24)
        st.session_state["home_movies"]   = movies
        st.session_state["home_category"] = home_cat_key
    else:
        movies = st.session_state["home_movies"]

    st.markdown(f'<div class="section-label">{cat_label}</div>', unsafe_allow_html=True)
    clicked = render_grid(movies, cols=6, prefix="home")
    if clicked:
        go_detail(clicked)

# ─── SEARCH ──────────────────────────────────────────
else:
    # ── Search bar (inside a form so Enter key works) ──
    with st.form("search_form", clear_on_submit=False):
        q_col, btn_col = st.columns([5, 1])
        with q_col:
            query = st.text_input(
                "Search",
                value=st.session_state["search_query"],
                placeholder="e.g. Inception, Avatar, The Dark Knight…",
                label_visibility="collapsed",
            )
        with btn_col:
            submitted = st.form_submit_button("🔍 Search", use_container_width=True)

    if submitted:
        if query.strip():
            st.session_state["search_query"] = query.strip()
            with st.spinner(f"Searching for **{query.strip()}**…"):
                results = fetch_search_results(query.strip())
            st.session_state["search_results"] = results
            if not results:
                st.warning("No results found. Try a different title.")
        else:
            st.warning("Please enter a movie title.")

    # ── Show search results as a clickable grid ──
    results = st.session_state["search_results"]
    if results:
        q_display = st.session_state["search_query"]
        st.markdown(
            f'<div class="section-label">🔍 Results for "{q_display}" — click a movie to see recommendations</div>',
            unsafe_allow_html=True,
        )
        clicked = render_grid(results, cols=5, prefix="sr")
        if clicked:
            go_detail(clicked)

    elif not st.session_state["search_query"]:
        st.markdown("""
<div style="text-align:center;padding:3.5rem 1rem;color:#444">
  <div style="font-size:4.5rem">🍿</div>
  <div style="font-size:1.2rem;font-weight:600;margin-top:1rem;color:#666">Search for any movie above</div>
  <div style="font-size:.9rem;margin-top:.4rem;color:#444">
    Results will appear as a grid — click any card to load details &amp; recommendations
  </div>
</div>""", unsafe_allow_html=True)
