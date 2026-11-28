# EIP93 patch set index

Target platform: Airoha AN7581 (Nokia XG-040G-MD)  
Kernel baseline: Linux v6.18.60  
Patch directory: `target/linux/generic/hack-6.18/`

This file is an index only. It is not a kernel patch and is ignored by the
OpenWrt kernel patch application.

## Current patch order

| Order | Patch | Source file | Original changes retained |
|---:|---|---|---|
| 1 | `927-crypto-eip93-aead.patch` | `drivers/crypto/inside-secure/eip93/eip93-aead.c` | 927,930a,941 |
| 2 | `928-crypto-eip93-cipher.patch` | `drivers/crypto/inside-secure/eip93/eip93-cipher.c` | 927,930a |
| 3 | `929-crypto-eip93-cipher-h.patch` | `drivers/crypto/inside-secure/eip93/eip93-cipher.h` | 927,930a |
| 4 | `930a-crypto-eip93-common.patch` | `drivers/crypto/inside-secure/eip93/eip93-common.c` | 928,930a,931,935a,935b,936,939 |
| 5 | `931-crypto-eip93-common-h.patch` | `drivers/crypto/inside-secure/eip93/eip93-common.h` | 935b,936 |
| 6 | `932-crypto-eip93-hash.patch` | `drivers/crypto/inside-secure/eip93/eip93-hash.c` | 932,933,935,935a,936,937,938,939,942 |
| 7 | `933-crypto-eip93-hash-h.patch` | `drivers/crypto/inside-secure/eip93/eip93-hash.h` | 933,935 |
| 8 | `935-crypto-eip93-main.patch` | `drivers/crypto/inside-secure/eip93/eip93-main.c` | 929,935a,935b |
| 9 | `935a-crypto-eip93-main-h.patch` | `drivers/crypto/inside-secure/eip93/eip93-main.h` | 935a |

Each patch modifies exactly one EIP93 source file. The original 16 patches
were replayed in documented order; the nine generated patches were replayed
against a pristine Linux v6.18.60 tree. Final source files were compared
byte-for-byte. Patch text was regenerated from final source diffs, not
concatenated from original unified diffs.

## Retained dependency and behavior groups

- **Cipher request lifetime and DMA:** per-request SA handling, DMA direction,
  IDR unwind and mapping ownership remain in the cipher/common patches.
- **SG cleanup and completion ownership:** synchronous SG-copy cleanup, paired
  ring advancement and result-slot lifetime remain in common/main patches.
- **Hash DMA and request lifecycle:** mapping ownership, HMAC key-state checks,
  transactional staging, import validation, overflow checks, sleepability and
  zero-length-final validation remain in hash/common patches.
- **AEAD:** AAD offset encoding remains in the AEAD patch and retains its
  dependency on the request-local SA implementation.

The original patch numbers in the last table column identify provenance;
they are not separate patch files after this reorganization.
## Upstream comparison (2026-11-28)

- The PonWrt upstream `pbs05/ponwrt` patch directory currently contains the
  small-request fallback `926-crypto-eip93-use-AES-fallback-for-small-requests.patch`
  and the unrelated `930-Revert-Revert-Revert-driver-core-Set-fw_devlink-on-b.patch`.
  Patch 926 remains intentionally excluded from this device patchset; do not
  reintroduce it as part of this reorganization.
- The exact Linux v6.18.60 baseline is stable commit
  `f45ed76d6791cf72ff1265ee93511175bbbc2f18`.
  Comparing Linux v6.18.60 with v6.18.64 shows no EIP93 driver files changed
  in that stable update range.
- The inspected Torvalds mainline snapshot is commit
  `7cd8495c0f16275c4f9abe1cef09a7b5fcd6d046` (2026-11-28). The EIP93 driver
  still has the baseline paired-ring, DMA/IDR and hash-request lifecycle
  structure; no directly substitutable upstream implementation for the
  PonWrt fixes was identified in this review.

Therefore, no current patch is being dropped on the assumption that Linux
6.18.64 or mainline has already absorbed it. This is a source comparison
decision, not a claim that the patch series has passed replay or testing.

## Rebase and acceptance requirements

1. Replay the complete ordered series against the exact Linux v6.18.60 source.
2. Require GNU `patch` with zero fuzz, zero offset, zero rejects and no
   partially applied hunks. Record each patch SHA256 and the kernel commit.
3. Review the final source diff against the unpatched kernel, not only the
   patch text. Check DMA map/unmap pairing, mapping direction, IDR lifetime,
   descriptor ownership, callback paths and request-context reuse.
4. Build the EIP93 module and its DES/MD5 providers through the native PonWrt
   kernel build. Confirm the module dependency metadata and package contents.
5. Run Crypto API tests for AES-CTR, AF_ALG AEAD/GCM, HMAC and SHA hash
   operations, including concurrent requests, short/unaligned SGs, AAD
   boundary lengths, import/export, ring pressure and synchronous failures.
6. Treat patch replay, successful compilation, functional crypto tests and
   Nokia XG-040G-MD hardware validation as separate results.

This index does not claim that replay, compilation or device testing has
passed. The complete ordered series still requires replay against the exact
Linux v6.18.60 source and a native build to establish those results.

## AN7581 integration outside the patch series

The EIP93 engine itself remains the upstream Linux driver. The platform
integration is kept in the native PonWrt files rather than duplicated as
another driver patch:

- `target/linux/airoha/an7581/config-6.18`: `CONFIG_CRYPTO_DEV_EIP93=m`,
  `CONFIG_CRYPTO_USER_API_AEAD=y` and `CONFIG_CRYPTO_USER_API_SKCIPHER=y`.
- `package/kernel/linux/modules/crypto.mk`: `kmod-crypto-hw-eip93` depends
  on the required Crypto API providers and AF_ALG/GCM support.
- `target/linux/airoha/dts/an7581.dtsi`: the EIP93 node uses the binding's
  Airoha-specific compatible followed by
  `inside-secure,safexcel-eip93ies`. The driver matches the generic second
  compatible, while the first satisfies the AN7581 binding.

The AN7583 DTS node is not changed by the AN7581 binding correction; its
SoC-specific compatible must be grounded in a corresponding upstream binding
before changing it.
