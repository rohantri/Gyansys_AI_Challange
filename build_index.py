"""Build the catalogue embedding index once, commit the result.

Run this whenever you change mm_catalogue.json, then commit data/index.npy.
The app loads it from disk instead of calling the embedding API on every
cold start, which Streamlit Cloud triggers whenever the app has been idle.

    export GEMINI_API_KEY="..."
    python build_index.py
"""

import os
import sys
import numpy as np
from engine import llm, retrieval

DATA = os.path.join(os.path.dirname(__file__), "data")

key = os.environ.get("GEMINI_API_KEY")
if not key:
    sys.exit("Set GEMINI_API_KEY first.")
llm.configure(key)

catalogue = retrieval.load_catalogue(os.path.join(DATA, "mm_catalogue.json"))
matrix = retrieval.build_index(catalogue)

out = os.path.join(DATA, "index.npy")
np.save(out, matrix)

print(f"Embedded {matrix.shape[0]} entries, {matrix.shape[1]} dimensions.")
print(f"Wrote {out} ({os.path.getsize(out) / 1024:.0f} KB)")
print("Commit this file. The app will load it instead of calling the API.")
