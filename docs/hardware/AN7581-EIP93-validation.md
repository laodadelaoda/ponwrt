# AN7581 EIP-93 validation

## Scope

This is an isolated validation item for the EIP-93 crypto engine on Airoha AN7581,
initially enabled only in the Nokia XG-040G-MD UBI and UBI-USB-SFP images.

It does not change PON encryption, WAN configuration, or OpenSSL provider/engine
selection. It does not claim hardware acceleration is proven merely because the
kernel module is present.

## Build checks

Build the Nokia XG-040G-MD image and confirm the package manifest contains
`kmod-crypto-hw-eip93`. Confirm the generated kernel configuration has
`CONFIG_CRYPTO_DEV_EIP93=m` (or `=y` if deliberately built in), and that
`crypto-hw-eip93.ko` is packaged. The package definition selects
`CONFIG_CRYPTO_HW` and `CONFIG_CRYPTO_DEV_EIP93`.

The EIP-93 package is added to the MD profiles only; the shared MD/TF common
profile is intentionally unchanged so TF does not inherit this experiment.

## Device-side checks

After booting the test image:

1. Confirm the driver probes without errors:
   `dmesg | grep -i -E 'eip93|crypto|safexcel'`
2. Confirm the module is loaded:
   `lsmod | grep eip93` (or verify the built-in driver through dmesg).
3. Inspect `/proc/crypto` and find the `cbc(aes)` entry whose `driver`
   contains `eip93`. Record its driver name, priority, and registration
   parameters. The driver source sets `CRYPTO_ALG_KERN_DRIVER_ONLY`, so this
   implementation is intentionally restricted to kernel Crypto API consumers.
4. Run `tools/testing/eip93-afalg-aes-cbc-kat.py` with Python 3. It first
   confirms that the EIP-93 provider is registered, then performs a separate
   AES-128-CBC known-answer and round-trip test through AF_ALG. **The AF_ALG
   test is a user-space API baseline, not an EIP-93 hardware test**: the
   kernel-only driver flag prevents AF_ALG from selecting the EIP-93 provider.
   The 1024-byte request is deliberately larger than the configured 512-byte
   AES-128 fallback threshold, but this does not override the kernel-only
   restriction.
5. Verify the EIP-93 driver's own Crypto API self-test result in the kernel
   log when the algorithm is registered. Record `/proc/interrupts` before
   and after a kernel-side workload that explicitly allocates the EIP-93
   driver by its driver name (`cbc(aes-eip93)`). Do not use AF_ALG traffic as
   the hardware workload. Do not assume the GIC hardware interrupt number is
   also the Linux virtual IRQ.
6. Benchmark the kernel-side EIP-93 path and a software-only baseline using
   identical key size, mode, buffer sizes, and concurrency. Record throughput,
   CPU utilization, errors, and interrupt deltas. The AF_ALG result is reported
   separately as the user-space baseline.

## AF_ALG test

The EIP-93 algorithms in the Linux driver are marked
`CRYPTO_ALG_KERN_DRIVER_ONLY`. This is a material API boundary: AF_ALG cannot
select this provider, and the ordinary OpenSSL EVP path does not automatically
route operations through the Linux kernel Crypto API. Therefore the AF_ALG
helper validates the user-space AF_ALG path only. It must not be used as proof
of EIP-93 execution or as EIP-93 throughput evidence.

Hardware execution requires a kernel-side test that explicitly requests the
driver name `cbc(aes-eip93)`, verifies the known-answer result, and correlates
the request with EIP-93 IRQ activity. The existing `tcrypt` mode that requests
generic `cbc(aes)` is not sufficient evidence by itself unless its log proves
the selected driver name is `cbc(aes-eip93)`.

OpenSSL 3.x must be evaluated separately. A normal `openssl speed -evp
aes-128-cbc` run is a user-space provider benchmark and does not prove EIP-93
use. Do not modify OpenSSL or claim EIP-93 acceleration until an explicit,
supported kernel-crypto integration path is demonstrated.

## Acceptance gates

- [ ] Kernel config enables EIP-93 and the module is included in the MD image.
- [ ] Driver probes successfully with no DMA, IRQ, reset, or timeout errors.
- [ ] `/proc/crypto` registers EIP-93 AES-CBC with expected driver name/priority.
- [ ] AF_ALG AES-128-CBC user-space known-answer test passes (reported separately).
- [ ] Kernel-side EIP-93 driver-name test passes its known-answer test.
- [ ] EIP-93 IRQ activity is observed during kernel-side requests above the fallback threshold.
- [ ] No kernel warnings, DMA faults, hangs, or data corruption under repeated load.
- [ ] Hardware throughput/CPU measurements are recorded against a software baseline.
- [ ] OpenSSL 3.x actual provider path is traced independently; no assumption that EVP uses EIP-93.

OpenSSL 3.x integration remains a separate follow-up. OpenSSL is not modified by
this validation item.
