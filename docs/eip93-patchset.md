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
merely to make numbering contiguous. The current design keeps AES-CTR available to the EIP93 path used
by the AF_ALG/GCM composition.

## Dependency groups

- **Request and DMA lifetime:** 927–933. Keep this order; later patches rely
  on the request-local SA and mapping-ownership fields.
- **Completion and ring ownership:** 935a, 935b. The paired-ring lock
  and pinned result-slot design must be reviewed together.
- **Hash/HMAC transaction:** 935, 936–939, 942. Patch 936 replaces the
  earlier hash submission path and owns hash request ID allocation/unwind.
- **AEAD encoding:** 941. It follows request-local SA creation in 927.

IDR allocation is bounded by `EIP93_RING_NUM - 1`, matching the maximum
number of outstanding entries in the one-slot-empty descriptor ring. The
The obsolete 16-bit-wide IDR expansion is absent from the current series;
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
