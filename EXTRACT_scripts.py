# ==============================================================================
# EXTRACT-1 | Save predict_lstm.py and selftest.py from the REAL-1 cell of your notebook file. Runs no model, needs no notebook state.
# Needs: miniproject_CLEAN_v1.ipynb uploaded to /content (Files panel -> upload; use the copy you downloaded from Colab).
# ==============================================================================
import os, re, json, hashlib, py_compile
NB = "/content/miniproject_CLEAN_v1.ipynb"; assert os.path.exists(NB), "upload the .ipynb to /content first"
OUTD = "/content/member3_scripts"; assert not os.path.exists(OUTD), "folder exists - not overwriting"
cells = json.load(open(NB))["cells"]
r1 = [''.join(c["source"]) for c in cells if c["cell_type"] == "code" and "REAL-1 |" in ''.join(c["source"])[:300]]
assert len(r1) == 1, f"expected exactly one REAL-1 cell, found {len(r1)}"
mod = re.search(r"MODSRC = r'''(.*?)'''\nSELFSRC", r1[0], re.S).group(1)
st = re.search(r"SELFSRC = r'''(.*?)'''\nos\.makedirs", r1[0], re.S).group(1)
os.makedirs(OUTD); open(f"{OUTD}/predict_lstm.py", "w").write(mod); open(f"{OUTD}/selftest.py", "w").write(st)
for f in ("predict_lstm.py", "selftest.py"):
    py_compile.compile(f"{OUTD}/{f}", doraise=True)
    print(f"{f:16s} {os.path.getsize(f'{OUTD}/{f}'):>6,} B  sha256 {hashlib.sha256(open(f'{OUTD}/{f}','rb').read()).hexdigest()}")
print("Both files compile. Download them from", OUTD)
try:
    from google.colab import files as _f; [_f.download(f"{OUTD}/{x}") for x in ("predict_lstm.py", "selftest.py")]
except Exception as e: print("Auto-download unavailable; use the Files panel.", type(e).__name__)
