# EIP93 patch set index

Target platform: Airoha AN7581 (Nokia XG-040G-MD)  
Kernel baseline: Linux v6.18.60  
Patch directory: `target/linux/generic/hack-6.18/`

This file is an index only. It is not a kernel patch and is ignored by the
OpenWrt kernel patch application.

## Current patch order

| Order | Patch | Responsibility |
|---:|---|---|
| 1 | `927-crypto-eip93-per-request-sa-record.patch` | Per-request aligned SA records; removes shared-transform request mutation |
| 2 | `928-crypto-eip93-dma-state-and-idr-fix.patch` | Cipher state DMA direction, IDR allocation failure handling and synchronous unwind |
| 3 | `929-crypto-eip93-enforce-32bit-dma-mask.patch` | Enforce the 32-bit streaming/coherent DMA address limit |
| 4 | `930a-crypto-eip93-unwind-sg-copies-on-sync-failure.patch` | Release driver-owned SG copies on synchronous exits |
| 5 | `931-crypto-eip93-unwind-request-idr-and-state-dma.patch` | Track successful cipher state DMA mappings before unmapping |
| 6 | `932-crypto-eip93-map-sa-state-bidirectionally.patch` | Use bidirectional DMA mapping for mutable hash state |
| 7 | `933-crypto-eip93-guard-hash-dma-cleanup.patch` | Track hash data, SA and state mapping ownership |
| 8 | `935-crypto-eip93-reject-hmac-before-setkey.patch` | Reject HMAC init/import before a successful setkey |
| 9 | `935a-crypto-eip93-atomic-paired-ring-advance.patch` | Keep command/result ring pointer advancement paired under one lock |
| 10 | `935b-crypto-eip93-copy-result-before-ring-release.patch` | Pin result slot until descriptor contents have been copied; DMA read barrier and missing async-request guard |
| 11 | `936-crypto-eip93-transactional-hash-staging.patch` | Stage hash input, map resources and reserve IDR before descriptor publication |
| 12 | `937-crypto-eip93-validate-imported-hash-state.patch` | Validate imported hash tail length and HMAC key state |
| 13 | `938-crypto-eip93-check-hash-length-overflow-before-staging.patch` | Reject hash byte-count overflow before staging allocations |
| 14 | `939-crypto-eip93-respect-hash-request-sleepability.patch` | Prevent sleeping or partial publication for non-sleepable requests |
| 15 | `941-crypto-eip93-encode-aead-aad-offset.patch` | Encode aligned/unaligned AAD offsets without truncation |
| 16 | `942-crypto-eip93-reject-zero-length-hash-final.patch` | Reject an inconsistent zero-length final descriptor |

The missing sequence numbers are intentional: patch 926 (small-request
software fallback), 934 (a malformed duplicate result guard superseded by
935b), and 940 are not part of the current series. Do not recreate these files
merely to make numbering contiguous. The current design keeps AES-CTR available
to the EIP93 path used by the AF_ALG/GCM composition.

The SG-cleanup patch uses the `930a-` prefix because this directory already
contains an unrelated `930-Revert-Revert-Revert-driver-core-Set-fw_devlink-on-b.patch`.
The suffix makes the EIP93 patch's position unambiguous in the filename-sorted
patch application order: after the existing `930-` patch and before `931-`.
Its patch contents are unchanged.

## Dependency groups and retention decisions

- **Request-local SA and cipher request lifetime:** 927 -> 928 -> 931.
  Patch 927 establishes per-request SA storage; 928 fixes DMA direction and
  IDR failure unwinding; 931 prevents unmapping state buffers whose DMA map
  operation did not succeed. These are complementary, not duplicate fixes.
- **Synchronous SG cleanup:** 930a. It releases only driver-owned SG copies
  when validation or submission fails synchronously; it must remain before
  request completion can be assumed.
- **Hash DMA ownership:** 932 -> 933. Patch 932 corrects the direction for
  mutable hash state; 933 records mapping ownership so cleanup only unmaps
  successful mappings. Keep both.
- **HMAC and completion/ring ownership:** 935 -> 935a -> 935b. Patch 935
  establishes valid HMAC key state; 935a makes paired ring pointer updates
  atomic; 935b keeps a result slot pinned until its contents are copied.
  Patches 935a and 935b must remain in this order.
- **Transactional hash path:** 936 depends on the hash ownership fields from
  933, HMAC key state from 935, and the paired ring lock from 935a. Patches
  937, 938, 939 and 942 refine the hash path introduced by 936 and must follow
  it.
- **AEAD offset encoding:** 941 depends on the request-local SA record from
  927. It is independent of the hash staging sequence, but remains after 927
  in the filename-sorted application order.

IDR allocation is bounded by `EIP93_RING_NUM - 1`, matching the maximum
number of outstanding entries in the one-slot-empty descriptor ring. The
obsolete 16-bit-wide IDR expansion is not part of the current series.

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
