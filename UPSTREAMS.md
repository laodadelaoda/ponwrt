# Upstream source policy

PonWrt is maintained against two distinct upstreams. They must not be merged or treated as interchangeable.

## Source ownership

- **ImmortalWrt** (`immortalwrt/immortalwrt`): base distribution, kernel integration, common build system and general system packages.
- **PonWrt** (`pbs05/ponwrt`): Airoha platform support (including AN7581/AN7583), PON-specific integration and the platform build configuration.
- **Feeds** are independent source streams and are tracked separately:
  - ImmortalWrt: `packages`, `luci`
  - OpenWrt: `routing`, `telephony`, `video`
  - PonWrt ecosystem: `pon_drivers`, `pon_userspace`

## Synchronization policy

1. Track the two main repositories and every configured feed independently.
2. Treat upstream movement as a request for compatibility review, not permission to merge automatically.
3. Review base-system/kernel changes separately from Airoha/PON changes.
4. Before accepting a feed update, verify its compatibility with the selected main-source revision and package/kernel ABI.
5. Do not replace the working AN7581 PON implementation or update kernel modules independently of the matching kernel.
6. Do not run a firmware build merely because an upstream reference moved. A reviewed change must pass static/source checks first; build and hardware validation are separate gates.
7. Update `upstream-sources.json` only after the corresponding upstream change has been reviewed and accepted.

## Baseline semantics

`upstream-sources.json` records the initial observed commit for each source. These starting references are a monitoring baseline, **not a declaration that all nine source revisions have been compatibility-tested**, and not a build lock. The daily workflow reports movement relative to this baseline and opens one tracking issue. The baseline must only be advanced after reviewing the corresponding source changes. This keeps upstream monitoring separate from source integration.

## Current build behavior

The standard PonWrt build entry point remains the upstream workflow:

```sh
./scripts/feeds update -a
./scripts/feeds install -a
cp configs/an7581.config .config
make defconfig
make -j"$(nproc)"
```

The feed revisions resolved by a real build should be captured in that build's provenance before a release is considered reproducible. This monitoring change does not alter the build or the device's configured APK repositories.
