import streamlit as st
import requests, json, time
from collections import defaultdict

# --- Sidebar: API Key Input ---
st.sidebar.header("Zerion API Key")
api_key = st.sidebar.text_input(
    "Enter your Zerion API key",
    type="password",
    help="Get free key at: https://zerion.io/api"
)

if not api_key:
    st.warning("Please enter your Zerion API key in the sidebar to scan wallets.")
    st.stop()

HEADERS = {"Authorization": f"Bearer {api_key}"}
BASE = "https://api.zerion.io/v1"

# --- Core Functions ---
def fetch_data(url, params):
    while True:
        r = requests.get(url, headers=HEADERS, params=params).json()
        yield r
        token = r.get("meta", {}).get("next_page_token")
        if not token:
            break
        params["page[token]"] = token
        time.sleep(0.2)

def get_portfolio(address):
    data = next(fetch_data(f"{BASE}/wallets/{address}/portfolio", {"currency": "usd"}))
    value = data["data"]["attributes"].get("total_value", 0)
    assets = [pos["id"] for pos in data["data"]["relationships"]["positions"]["data"]]
    return value, assets

def get_tx_count(address):
    return sum(1 for _ in fetch_data(f"{BASE}/wallets/{address}/transactions", {"limit": 100}))

def build_profile(address):
    value, assets = get_portfolio(address)
    txs = get_tx_count(address)
    score = txs * 10 + value / 100 + len(assets) * 5
    return {
        "wallet": address,
        "value_usd": round(value, 2),
        "tx_count": txs,
        "assets": len(assets),
        "reputation_score": round(score, 2),
        "top_3": assets[:3]
    }

def find_communities(wallets, min_overlap=2):
    holdings = {w: set(get_portfolio(w)[1]) for w in wallets}
    groups = defaultdict(list)
    for i, w1 in enumerate(wallets):
        for w2 in wallets[i+1:]:
            common = holdings[w1] & holdings[w2]
            if len(common) >= min_overlap:
                key = ", ".join(sorted(common)[:3]) + ("..." if len(common) > 3 else "")
                groups[key].extend([w1, w2])
    return {k: list(dict.fromkeys(v)) for k, v in groups.items()}

def analyze(wallets):
    profiles = {w: build_profile(w) for w in wallets}
    communities = find_communities(wallets)
    return {
        "profiles": profiles,
        "communities": communities,
        "summary": f"{len(communities)} group(s) from {len(wallets)} wallet(s)"
    }

# --- Streamlit UI ---
st.set_page_config(page_title="Onchain Social Hub", layout="centered")
st.title("Onchain Social Hub")
st.markdown("**Your wallet = your social profile. Your holdings = your network.**")

wallets_input = st.text_area(
    "Enter wallet addresses (one per line)",
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045\n0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
    height=120
)

if st.button("Scan Onchain Network", type="primary"):
    wallets = [w.strip() for w in wallets_input.split("\n") if w.strip()]
    if not wallets:
        st.error("Please enter at least one wallet address.")
    else:
        with st.spinner("Fetching onchain data from Zerion API..."):
            result = analyze(wallets)
        st.success("Scan Complete!")
        st.json(result, expanded=False)
        st.balloons()
