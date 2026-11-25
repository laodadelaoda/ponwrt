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
| 4 | `930-crypto-eip93-unwind-sg-copies-on-sync-failure.patch` | Release driver-owned SG copies on synchronous exits |
| 5 | `931-crypto-eip93-unwind-request-idr-and-state-dma.patch` | Track successful cipher state DMA mappings before unmapping |
| 6 | `932-crypto-eip93-map-sa-state-bidirectionally.patch` | Use bidirectional DMA mapping for mutable hash state |
| 7 | `933-crypto-eip93-guard-hash-dma-cleanup.patch` | Track hash data, SA and state mapping ownership |
| 8 | `934-crypto-eip93-check-request-id-and-result-order.patch` | DMA read barrier and missing async-request guard in result dispatch |
| 9 | `935-crypto-eip93-reject-hmac-before-setkey.patch` | Reject HMAC init/import before a successful setkey |
| 10 | `935a-crypto-eip93-atomic-paired-ring-advance.patch` | Keep command/result ring pointer advancement paired under one lock |
| 11 | `935b-crypto-eip93-copy-result-before-ring-release.patch` | Pin result slot until descriptor contents have been copied |
| 12 | `936-crypto-eip93-transactional-hash-staging.patch` | Stage hash input, map resources and reserve IDR before descriptor publication |
| 13 | `937-crypto-eip93-validate-imported-hash-state.patch` | Validate imported hash tail length and HMAC key state |
| 14 | `938-crypto-eip93-check-hash-length-overflow-before-staging.patch` | Reject hash byte-count overflow before staging allocations |
| 15 | `939-crypto-eip93-respect-hash-request-sleepability.patch` | Prevent sleeping or partial publication for non-sleepable requests |
| 16 | `941-crypto-eip93-encode-aead-aad-offset.patch` | Encode aligned/unaligned AAD offsets without truncation |
| 17 | `942-crypto-eip93-reject-zero-length-hash-final.patch` | Reject an inconsistent zero-length final descriptor |

The missing sequence numbers are intentional: patch 926 was removed when the
small-request software-fallback change was dropped; patch 940 is not part of
the current series. Do not recreate either file merely to make numbering
contiguous. The current design keeps AES-CTR available to the EIP93 path used
by the AF_ALG/GCM composition.

## Dependency groups

- **Request and DMA lifetime:** 927–933. Keep this order; later patches rely
  on the request-local SA and mapping-ownership fields.
- **Completion and ring ownership:** 934, 935a, 935b. The paired-ring lock
  and pinned result-slot design must be reviewed together.
- **Hash/HMAC transaction:** 935, 936–939, 942. Patch 936 replaces the
  earlier hash submission path and owns hash request ID allocation/unwind.
- **AEAD encoding:** 941. It follows request-local SA creation in 927.

IDR allocation is bounded by `EIP93_RING_NUM - 1`, matching the maximum
number of outstanding entries in the one-slot-empty descriptor ring. The
obsolete 16-bit-wide IDR expansion was removed from patch 934; patch 936 uses
the native ring-capacity bound as well.

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
passed. The current patch edits still require the full ordered replay and
native build to establish those results.
