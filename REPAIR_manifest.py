# ==============================================================================
# REPAIR-1 | Make a CORRECTED-MANIFEST copy of the existing comparison zip. No models, no notebook state, no setup cells needed.
# - Reads the zip you already have; writes a NEW zip next to it (never overwrites, never edits the original).
# - Only MANIFEST_sha256.txt is rewritten (without the self-entry). README.md gets ONE sentence corrected if FIX_README_WORDING=True.
# - All other 8 files (metrics, predictions, configs) are proven byte-identical to the original before the zip is built.
# Needs: comparison_VALID_v1_20261101_0505.zip uploaded to /content (Files panel -> upload).
# ==============================================================================
import os, glob, zipfile, shutil, hashlib, tempfile
FIX_README_WORDING = True
cands = sorted(p for p in glob.glob("/content/comparison_VALID_v1_*.zip") if "manifest-corrected" not in p)
assert len(cands) == 1, f"expected exactly one original comparison zip in /content, found {cands} - upload comparison_VALID_v1_20261101_0505.zip in the Files panel"
SRC = cands[0]; NEWZ = SRC[:-4] + "_manifest-corrected.zip"
assert not os.path.exists(NEWZ), f"{NEWZ} already exists - not overwriting"
sha = lambda b: hashlib.sha256(b).hexdigest()
WORK = tempfile.mkdtemp(prefix="manifest_repair_", dir="/content")          # brand-new empty folder
with zipfile.ZipFile(SRC) as z:
    orig = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}; z.extractall(WORK)
folders = {n.split("/")[0] for n in orig}; assert len(folders) == 1, folders
F = folders.pop(); D = os.path.join(WORK, F)
names = sorted(n.split("/", 1)[1] for n in orig); assert "MANIFEST_sha256.txt" in names and len(names) == 10, names

# 1) audit the OLD manifest
old = [l.split("  ", 1) for l in orig[f"{F}/MANIFEST_sha256.txt"].decode().strip().splitlines()]
bad = [f for h, f in old if f != "MANIFEST_sha256.txt" and sha(orig[f"{F}/{f}"]) != h]
selfe = [(h, f) for h, f in old if f == "MANIFEST_sha256.txt"]
print(f"OLD manifest: {len(old)} entries | real files whose hash mismatches: {bad} | self-entry: {[h[:12] for h,_ in selfe]} (e3b0c44298fc = SHA-256 of an empty file)")
assert not bad, "a real file does not match its old hash - STOP, do not use this zip"

# 2) optional one-sentence README correction
if FIX_README_WORDING:
    p = os.path.join(D, "README.md"); t = open(p, "rb").read()
    o = b"the holdout was evaluated once."
    n = b"the GRU holdout was evaluated once for the decision and later re-run once, unchanged, after a runtime reset (exact reproduction; no selection changed)."
    assert t.count(o) == 1, "README sentence not found exactly once - not touching README"
    open(p, "wb").write(t.replace(o, n)); print("README: one sentence corrected")

# 3) new manifest = every file EXCEPT itself (hashes computed from the files on disk)
files = sorted(f for f in os.listdir(D) if f != "MANIFEST_sha256.txt")
open(os.path.join(D, "MANIFEST_sha256.txt"), "w").write("\n".join(f"{sha(open(os.path.join(D, f), 'rb').read())}  {f}" for f in files) + "\n")

# 4) prove nothing else changed
changed = [f for f in files if open(os.path.join(D, f), "rb").read() != orig[f"{F}/{f}"]]
allowed = {"README.md"} if FIX_README_WORDING else set()
assert set(changed) <= allowed, f"unexpected change in {changed}"
print(f"Byte-identical to the original: {len(files) - len(changed)} of {len(files)} files | changed: {changed or 'none'} | rewritten: MANIFEST_sha256.txt")

# 5) build the new zip, then re-open it and verify it like Member 3 would
shutil.make_archive(NEWZ[:-4], "zip", root_dir=WORK, base_dir=F)
with zipfile.ZipFile(NEWZ) as z:
    assert z.testzip() is None
    m = [l.split("  ", 1) for l in z.read(f"{F}/MANIFEST_sha256.txt").decode().strip().splitlines()]
    assert len(m) == 9 and all(f != "MANIFEST_sha256.txt" for _, f in m)
    mism = [f for h, f in m if sha(z.read(f"{F}/{f}")) != h]; assert not mism, mism
    inzip = sorted(n.split("/", 1)[1] for n in z.namelist() if not n.endswith("/"))
    assert inzip == names, "file list differs from the original"
print(f"NEW zip verified: {len(m)} manifest entries, all hashes match, no self-entry, same 10 files as the original.")
print("NEW:", NEWZ, f"({os.path.getsize(NEWZ):,} B)   ORIGINAL (untouched):", SRC)
try:
    from google.colab import files as _f; _f.download(NEWZ)
except Exception as e: print("Auto-download unavailable; use the Files panel.", type(e).__name__)
print("── REPAIR-1 complete ──")
