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
   contains `eip93`. Record its `priority` and compare it with all other
   `cbc(aes)` providers. AF_ALG by algorithm name selects the highest-priority
   registered implementation.
4. Run `tools/testing/eip93-afalg-aes-cbc-kat.py` on the device with Python 3.
   It checks that an EIP-93-backed `cbc(aes)` provider is registered and has
   the highest priority, then performs AES-128-CBC encryption/decryption via
   AF_ALG. The 1024-byte request exceeds the configured 512-byte AES-128
   software-fallback threshold; the first block is checked against the NIST
   SP 800-38A AES-CBC known-answer vector.
5. Record `/proc/interrupts` before and after repeated AF_ALG runs. Identify
   the Linux IRQ line associated with the EIP-93 device from the driver's
   probe output/device name, and verify its interrupt count increases. Do not
   assume the GIC hardware interrupt number is also the Linux virtual IRQ.
6. Repeat the AF_ALG test under concurrent CPU load and record throughput,
   CPU utilization, errors, and interrupt deltas. Compare against a software
   baseline with the EIP-93 module unavailable/disabled; do not compare a
   different cipher mode or request size.

## AF_ALG test

The test helper is deliberately independent of OpenSSL. A passing known-answer
test proves the AF_ALG request returns correct ciphertext/plaintext; combined
with EIP-93 provider priority and increasing device IRQ counts, it provides
evidence that requests are reaching the hardware driver. If the driver falls
back to software for a request, do not count that run as hardware throughput.

## Acceptance gates

- [ ] Kernel config enables EIP-93 and the module is included in the MD image.
- [ ] Driver probes successfully with no DMA, IRQ, reset, or timeout errors.
- [ ] `/proc/crypto` registers EIP-93 AES-CBC with expected driver name/priority.
- [ ] AF_ALG AES-128-CBC encrypt/decrypt known-answer test passes.
- [ ] EIP-93 IRQ activity is observed during requests above the fallback threshold.
- [ ] No kernel warnings, DMA faults, hangs, or data corruption under repeated load.
- [ ] Hardware throughput/CPU measurements are recorded against a software baseline.

Only after these gates pass should OpenSSL 3.x integration be investigated as a
separate follow-up. OpenSSL is not modified by this validation item.
