#!/usr/bin/env python3
"""AN7581 EIP-93 AF_ALG AES-128-CBC known-answer and provider-priority test."""

import socket
import struct
import sys

SOL_ALG = getattr(socket, "SOL_ALG", 279)
ALG_SET_KEY = 1
ALG_SET_IV = 2
ALG_SET_OP = 3
ALG_OP_DECRYPT = 0
ALG_OP_ENCRYPT = 1

KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
IV = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
PLAINTEXT_BLOCK = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
EXPECTED_CIPHERTEXT_BLOCK = bytes.fromhex("7649abac8119b246cee98e9b12e9197d")
# 1024 bytes forces the configured AES-128 request beyond the 512-byte
# software-fallback threshold while preserving the NIST first-block vector.
PLAINTEXT = PLAINTEXT_BLOCK + bytes((i * 29 + 7) & 0xff for i in range(1008))


def crypto_entries():
    try:
        raw = open("/proc/crypto", encoding="ascii").read()
    except OSError as exc:
        raise RuntimeError("cannot read /proc/crypto: %s" % exc)
    entries = []
    for block in raw.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        if fields.get("name") == "cbc(aes)":
            entries.append(fields)
    return entries


def afalg_crypt(data, operation):
    parent = socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET, 0)
    try:
        parent.bind(("skcipher", "cbc(aes)"))
        parent.setsockopt(SOL_ALG, ALG_SET_KEY, KEY)
        op, _ = parent.accept()
        try:
            iv_control = struct.pack("I", len(IV)) + IV
            controls = [
                (SOL_ALG, ALG_SET_OP, struct.pack("I", operation)),
                (SOL_ALG, ALG_SET_IV, iv_control),
            ]
            sent = op.sendmsg([data], controls)
            if sent != len(data):
                raise RuntimeError("short AF_ALG write: %d/%d" % (sent, len(data)))
            result = bytearray()
            while len(result) < len(data):
                chunk = op.recv(len(data) - len(result))
                if not chunk:
                    break
                result.extend(chunk)
            if len(result) != len(data):
                raise RuntimeError("short AF_ALG read: %d/%d" % (len(result), len(data)))
            return bytes(result)
        finally:
            op.close()
    finally:
        parent.close()


def main():
    entries = crypto_entries()
    eip93 = [e for e in entries if "eip93" in e.get("driver", "").lower()]
    if not eip93:
        raise RuntimeError("no EIP-93 cbc(aes) provider found in /proc/crypto")
    priorities = [(int(e.get("priority", "0")), e.get("driver", "?")) for e in entries]
    best = max((p for p, _ in priorities), default=-1)
    eip_best = max(int(e.get("priority", "0")) for e in eip93)
    if eip_best <= best and any(p > eip_best for p, driver in priorities if "eip93" not in driver.lower()):
        raise RuntimeError(
            "EIP-93 priority %d is below another cbc(aes) provider priority %d"
            % (eip_best, best)
        )

    print("cbc(aes) providers:")
    for entry in sorted(entries, key=lambda e: int(e.get("priority", "0")), reverse=True):
        print("  driver=%s priority=%s" % (
            entry.get("driver", "?"), entry.get("priority", "?")
        ))

    ciphertext = afalg_crypt(PLAINTEXT, ALG_OP_ENCRYPT)
    if ciphertext[:16] != EXPECTED_CIPHERTEXT_BLOCK:
        raise RuntimeError("AES-CBC NIST first-block known-answer check failed")
    recovered = afalg_crypt(ciphertext, ALG_OP_DECRYPT)
    if recovered != PLAINTEXT:
        raise RuntimeError("AES-CBC decrypt/round-trip check failed")

    print("PASS: AF_ALG AES-128-CBC, 1024-byte request, NIST first block and round-trip")
    print("NOTE: verify EIP-93 IRQ counter deltas separately in /proc/interrupts")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        sys.exit(1)
