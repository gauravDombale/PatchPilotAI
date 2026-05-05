from __future__ import annotations

import json

import requests
import streamlit as st

st.set_page_config(page_title="Issue Resolver", layout="wide")
st.title("Multi-Agent GitHub Issue Resolver")

repo = st.text_input("Repo (owner/name)", value="owner/repo")
issue_number = st.number_input("Issue Number", min_value=1, value=1)
api_base = st.text_input("API URL", value="http://localhost:8000")

if st.button("Run"):
    with requests.post(
        f"{api_base}/resolve",
        json={"repo": repo, "issue_number": int(issue_number)},
        stream=True,
        timeout=300,
    ) as r:
        st.write(f"Thread: {r.headers.get('x-thread-id', 'unknown')}")
        box = st.empty()
        logs: list[str] = []
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            logs.append(json.dumps(payload, indent=2))
            box.code("\n\n".join(logs[-10:]), language="json")
