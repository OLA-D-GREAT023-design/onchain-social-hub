import streamlit as st
import requests, json, time
from collections import defaultdict
from dotenv import load_dotenv
import os

# --- Load Zerion API Key ---
load_dotenv()
API_KEY = os.getenv("ZERION_API_KEY")
if not API_KEY:
    st.error("⚠️ Add ZERION_API_KEY to your environment or Streamlit secrets.")
    st.stop()

HEADERS = {"Authorization": f"Bearer {API_KEY}"}
BASE = "https://api.zerion.io/v1"

# --- Helper to GET with pagination ---
def get(url, params):
    while True:
        try:
            r = requests.get(url, headers=HEADERS, params=params)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.warning(f"Failed to fetch data from {url}: {e}")
            yield {}
            break

        yield data
        token = data.get("meta", {}).get("next_page_token")
        if not token:
            break
        params["page[token]"] = token
        time.sleep(0.2)

# --- Safe portfolio fetch ---
def portfolio(address):
    try:
        p = next(get(f"{BASE}/wallets/{address}/portfolio", {"currency": "usd"}))
        if not isinstance(p, dict) or "data" not in p:
            st.warning(f"No portfolio data found for {address}.")
            return 0, []

        attributes = p["data"].get("attributes", {})
        relationships = p["data"].get("relationships", {})
        total_value = attributes.get("total_value", 0)
        assets = [x["id"] for x in relationships.get("positions", {}).get("data", [])]

        return total_value, assets

    except Exception as e:
        st.warning(f"Error fetching portfolio for {address}: {e}")
        return 0, []

# --- Transactions count ---
def tx_count(address):
    try:
        return sum(1 for _ in get(f"{BASE}/wallets/{address}/transactions", {"limit": 100}))
    except Exception as e:
        st.warning(f"Error fetching transactions for {address}: {e}")
        return 0

# --- Wallet profile ---
def profile(address):
    value, assets = portfolio(address)
    txs = tx_count(address)
    score = txs * 10 + value / 100 + len(assets) * 5
    return {
        "wallet": address,
        "value_usd": round(value, 2),
        "tx_count": txs,
        "assets": len(assets),
        "reputation_score": round(score, 2),
        "top_3": assets[:3]
    }

# --- Communities from holdings overlap ---
def communities(wallets, min_overlap=2):
    holdings = {w: set(portfolio(w)[1]) for w in wallets}
    groups = defaultdict(list)
    for i, a in enumerate(wallets):
        for b in wallets[i+1:]:
            common = holdings[a] & holdings[b]
            if len(common) >= min_overlap:
                key = ", ".join(sorted(common)[:3]) + ("..." if len(common) > 3 else "")
                groups[key].extend([a, b])
    return {k: list(dict.fromkeys(v)) for k, v in groups.items()}

# --- Full analysis ---
def run(wallets):
    profiles = {}
    for w in wallets:
        st.info(f"📊 Analyzing wallet {w}...")
        profiles[w] = profile(w)
    comms = communities(wallets)
    return {
        "profiles": profiles,
        "communities": comms,
        "summary": f"{len(comms)} group(s) from {len(wallets)} wallet(s)"
    }

# --- Streamlit UI ---
st.set_page_config(page_title="Onchain Social Hub", layout="centered")
st.title("🧠 Onchain Social Hub")
st.write("Enter wallet addresses (one per line to analyze shared assets and activity).")

wallets_input = st.text_area(
    "Wallets",
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045\n0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
    height=100
)

if st.button("🔍 Scan Onchain Network", type="primary"):
    wallets = [w.strip() for w in wallets_input.split("\n") if w.strip()]
    if not wallets:
        st.error("Enter at least one wallet address.")
    else:
        with st.spinner("🔗 Fetching onchain data from Zerion..."):
            result = run(wallets)
        st.success("✅ Done!")
        st.json(result, expanded=False)
        st.balloons()
