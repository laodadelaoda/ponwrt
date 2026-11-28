#!/usr/bin/env python3
"""Rebuild the EIP93 patch series as one patch per touched source file."""
from __future__ import annotations
import hashlib, re, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path.cwd()
PATCH_DIR = ROOT / "target/linux/generic/hack-6.18"
DOC = ROOT / "docs/eip93-patchset.md"
BASELINE = "f45ed76d6791cf72ff1265ee93511175bbbc2f18"
KERNEL_URL = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
SOURCE_DIR = "drivers/crypto/inside-secure/eip93"
TICK = chr(96)
GROUPS = [
    ("927-crypto-eip93-aead.patch", "eip93-aead.c", "927,930a,941"),
    ("928-crypto-eip93-cipher.patch", "eip93-cipher.c", "927,930a"),
    ("929-crypto-eip93-cipher-h.patch", "eip93-cipher.h", "927,930a"),
    ("930a-crypto-eip93-common.patch", "eip93-common.c", "928,930a,931,935a,935b,936,939"),
    ("931-crypto-eip93-common-h.patch", "eip93-common.h", "935b,936"),
    ("932-crypto-eip93-hash.patch", "eip93-hash.c", "932,933,935,935a,936,937,938,939,942"),
    ("933-crypto-eip93-hash-h.patch", "eip93-hash.h", "933,935"),
    ("935-crypto-eip93-main.patch", "eip93-main.c", "929,935a,935b"),
    ("935a-crypto-eip93-main-h.patch", "eip93-main.h", "935a"),
]
EXPECTED_FILES = {f"{SOURCE_DIR}/{filename}" for _, filename, _ in GROUPS}

def run(args, cwd=None, capture=False):
    p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.STDOUT if capture else None)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(str,args))}\n{p.stdout or ''}")
    return p.stdout or ""

def apply_patch(patch_file, tree, label):
    output = run(["patch", "-p1", "--fuzz=0", "--batch", "--forward", "-i", str(patch_file)],
                 cwd=tree, capture=True)
    if re.search(r"\boffset\b|\bfuzz\b|FAILED|malformed patch|Reversed \(or previously applied\)", output, re.I):
        raise RuntimeError(f"{label}: patch reported offset/fuzz/reject:\n{output}")
    print(f"[replay] {label}: clean")

def main():
    if not DOC.is_file() or not PATCH_DIR.is_dir():
        raise SystemExit("Run this script from the PonWrt repository root.")
    doc = DOC.read_text()
    original_names = re.findall(r"^\|\s*\d+\s*\|\s*" + TICK + r"([^" + TICK + r"]+\.patch)" + TICK, doc, re.M)
    if len(original_names) != 16 or len(set(original_names)) != 16:
        raise SystemExit(f"Expected 16 indexed original patches, found {len(original_names)}.")
    originals = [PATCH_DIR / name for name in original_names]
    missing = [str(p) for p in originals if not p.is_file()]
    if missing:
        raise SystemExit("Missing indexed patches:\n" + "\n".join(missing))

    with tempfile.TemporaryDirectory(prefix="ponwrt-eip93-") as tmpdir:
        tmp = Path(tmpdir)
        kernel, pristine = tmp / "kernel", tmp / "pristine"
        run(["git", "clone", "--quiet", "--depth", "1", "--branch", "v6.18.60", KERNEL_URL, str(kernel)])
        actual = run(["git", "rev-parse", "HEAD"], cwd=kernel, capture=True).strip()
        if actual != BASELINE:
            raise SystemExit(f"Linux v6.18.60 baseline mismatch: expected {BASELINE}, got {actual}")
        run(["git", "clone", "--quiet", "--shared", str(kernel), str(pristine)])
        print(f"[baseline] Linux v6.18.60 {actual}")

        for patch_file in originals:
            apply_patch(patch_file.resolve(), kernel, patch_file.name)

        changed = set(run(["git", "diff", "--name-only"], cwd=kernel, capture=True).splitlines())
        if changed != EXPECTED_FILES:
            raise SystemExit(f"Unexpected source file set. Missing={sorted(EXPECTED_FILES-changed)} Extra={sorted(changed-EXPECTED_FILES)}")

        generated, final_bytes = tmp / "generated", {}
        generated.mkdir()
        for new_name, filename, _ in GROUPS:
            rel = f"{SOURCE_DIR}/{filename}"
            final_bytes[rel] = (kernel / rel).read_bytes()
            diff = run(["git", "diff", "--no-ext-diff", "--full-index", "--binary", "--", rel],
                       cwd=kernel, capture=True)
            if not diff.strip():
                raise SystemExit(f"No final diff generated for {rel}")
            (generated / new_name).write_text(diff)
            print(f"[generated] {new_name}: sha256={hashlib.sha256(diff.encode()).hexdigest()}")

        run(["git", "reset", "--hard", "HEAD"], cwd=pristine)
        for new_name, _, _ in GROUPS:
            apply_patch(generated / new_name, pristine, new_name)
        for rel, expected in final_bytes.items():
            if (pristine / rel).read_bytes() != expected:
                raise SystemExit(f"Byte-for-byte final source mismatch: {rel}")
        replay_changed = set(run(["git", "diff", "--name-only"], cwd=pristine, capture=True).splitlines())
        if replay_changed != EXPECTED_FILES:
            raise SystemExit("Rebuilt patch set changed an unexpected file set.")
        print("[verify] Nine generated patches reproduce all nine final files byte-for-byte.")

        # Replace originals only after both replay paths pass.
        for old in originals:
            old.unlink()
        for new_name, _, _ in GROUPS:
            shutil.copy2(generated / new_name, PATCH_DIR / new_name)

    table = [
        "## Current patch order", "",
        "| Order | Patch | Source file | Original changes retained |",
        "|---:|---|---|---|",
    ]
    for i, (name, filename, origins) in enumerate(GROUPS, 1):
        table.append(f"| {i} | {TICK}{name}{TICK} | {TICK}{SOURCE_DIR}/{filename}{TICK} | {origins} |")
    table += [
        "", "Each patch modifies exactly one EIP93 source file. The original 16 patches",
        "were replayed in documented order; the nine generated patches were replayed",
        "against a pristine Linux v6.18.60 tree. Final source files were compared",
        "byte-for-byte. Patch text was regenerated from final source diffs, not",
        "concatenated from original unified diffs.", "",
        "## Retained dependency and behavior groups", "",
        "- **Cipher request lifetime and DMA:** per-request SA handling, DMA direction,",
        "  IDR unwind and mapping ownership remain in the cipher/common patches.",
        "- **SG cleanup and completion ownership:** synchronous SG-copy cleanup, paired",
        "  ring advancement and result-slot lifetime remain in common/main patches.",
        "- **Hash DMA and request lifecycle:** mapping ownership, HMAC key-state checks,",
        "  transactional staging, import validation, overflow checks, sleepability and",
        "  zero-length-final validation remain in hash/common patches.",
        "- **AEAD:** AAD offset encoding remains in the AEAD patch and retains its",
        "  dependency on the request-local SA implementation.", "",
        "The original patch numbers in the last table column identify provenance;",
        "they are not separate patch files after this reorganization.", "",
    ]
    marker = "## Upstream comparison"
    if marker not in doc:
        raise SystemExit("Cannot preserve upstream comparison section: heading missing.")
    DOC.write_text(doc[:doc.index("## Current patch order")] + "\n".join(table) + doc[doc.index(marker):])
    (ROOT / "eip93-rebuild-report.txt").write_text(
        f"Linux baseline: {BASELINE}\nOriginal patches replayed: 16\nGenerated patches: 9\n"
        "Fuzz: 0\nOffset: 0\nRejects: 0\nFinal source equivalence: byte-for-byte PASS\n"
    )
    print("Patch rebuild and byte-for-byte equivalence checks passed.")

if __name__ == "__main__":
    main()
