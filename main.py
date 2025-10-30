import requests, json, time
from collections import defaultdict

API_KEY = "zk_dev_7e9875b4e9ed4411a81eddd44f3b8add"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
BASE = "https://api.zerion.io/v1"

def get(url, params):
    while True:
        r = requests.get(url, headers=HEADERS, params=params).json()
        yield r
        token = r.get("meta", {}).get("next_page_token")
        if not token: break
        params["page[token]"] = token
        time.sleep(0.2)

def portfolio(address):
    try:
        p = next(get(f"{BASE}/wallets/{address}/portfolio", {"currency": "usd"}))
        
        # Make sure 'data' exists
        if not isinstance(p, dict) or "data" not in p:
            print(f"⚠️ No data found for wallet: {address}")
            return 0, []

        attributes = p["data"].get("attributes", {})
        relationships = p["data"].get("relationships", {})
        total_value = attributes.get("total_value", 0)
        assets = [x["id"] for x in relationships.get("positions", {}).get("data", [])]

        return total_value, assets

    except Exception as e:
        print(f"❌ Error fetching portfolio for {address}: {e}")
        return 0, []

def tx_count(address):
    return sum(1 for _ in get(f"{BASE}/wallets/{address}/transactions", {"limit": 100}))

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

def run(wallets):
    return {
        "profiles": {w: profile(w) for w in wallets},
        "communities": communities(wallets),
        "summary": f"{len(communities(wallets))} group(s) from {len(wallets)} wallets"
    }

if __name__ == "__main__":
    wallets = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"
    ]
    print(json.dumps(run(wallets), indent=2))
