// SPDX-License-Identifier: GPL-2.0
/*
 * EIP-93 AES-128-CBC kernel Crypto API KAT.
 *
 * This deliberately requests the EIP-93 driver by cra_driver_name and sends
 * 1024 bytes, above PonWrt's configured 512-byte AES-128 software fallback
 * threshold. It is a diagnostic module, not a production feature.
 */

#include <crypto/skcipher.h>
#include <linux/crypto.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/scatterlist.h>
#include <linux/slab.h>
#include <linux/string.h>

#define EIP93_TEST_LEN 1024
#define EIP93_DRIVER_NAME "cbc(aes-eip93)"

static const u8 eip93_key[16] = {
	0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
	0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c,
};

static const u8 eip93_iv[16] = {
	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
	0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
};

static const u8 eip93_plain_first[16] = {
	0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
	0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a,
};

static const u8 eip93_cipher_first[16] = {
	0x76, 0x49, 0xab, 0xac, 0x81, 0x19, 0xb2, 0x46,
	0xce, 0xe9, 0x8e, 0x9b, 0x12, 0xe9, 0x19, 0x7d,
};

static int __init eip93_kat_init(void)
{
	struct crypto_skcipher *tfm;
	struct skcipher_request *req;
	DECLARE_CRYPTO_WAIT(wait);
	struct scatterlist src_sg, dst_sg;
	u8 *plain = NULL, *cipher = NULL, *recovered = NULL;
	u8 iv[sizeof(eip93_iv)];
	unsigned int i;
	int ret;

	tfm = crypto_alloc_skcipher(EIP93_DRIVER_NAME, 0, 0);
	if (IS_ERR(tfm)) {
		ret = PTR_ERR(tfm);
		pr_err("eip93-kat: cannot allocate %s: %d\n",
		       EIP93_DRIVER_NAME, ret);
		return ret;
	}

	if (strcmp(crypto_skcipher_driver_name(tfm), EIP93_DRIVER_NAME)) {
		pr_err("eip93-kat: wrong provider selected: %s\n",
		       crypto_skcipher_driver_name(tfm));
		ret = -ENODEV;
		goto out_tfm;
	}

	plain = kmalloc(EIP93_TEST_LEN, GFP_KERNEL);
	cipher = kmalloc(EIP93_TEST_LEN, GFP_KERNEL);
	recovered = kmalloc(EIP93_TEST_LEN, GFP_KERNEL);
	if (!plain || !cipher || !recovered) {
		ret = -ENOMEM;
		goto out_buf;
	}

	memcpy(plain, eip93_plain_first, sizeof(eip93_plain_first));
	for (i = sizeof(eip93_plain_first); i < EIP93_TEST_LEN; i++)
		plain[i] = (i * 29 + 7) & 0xff;
	memset(cipher, 0, EIP93_TEST_LEN);
	memset(recovered, 0, EIP93_TEST_LEN);

	ret = crypto_skcipher_setkey(tfm, eip93_key, sizeof(eip93_key));
	if (ret) {
		pr_err("eip93-kat: setkey failed: %d\n", ret);
		goto out_buf;
	}

	req = skcipher_request_alloc(tfm, GFP_KERNEL);
	if (!req) {
		ret = -ENOMEM;
		goto out_buf;
	}

	skcipher_request_set_callback(req, CRYPTO_TFM_REQ_MAY_BACKLOG |\n\t\t\t\t      CRYPTO_TFM_REQ_MAY_SLEEP,
				      crypto_req_done, &wait);
	sg_init_one(&src_sg, plain, EIP93_TEST_LEN);
	sg_init_one(&dst_sg, cipher, EIP93_TEST_LEN);
	memcpy(iv, eip93_iv, sizeof(iv));
	skcipher_request_set_crypt(req, &src_sg, &dst_sg,
				   EIP93_TEST_LEN, iv);
	crypto_init_wait(&wait);
	ret = crypto_wait_req(crypto_skcipher_encrypt(req), &wait);
	if (ret) {
		pr_err("eip93-kat: encrypt request failed: %d\n", ret);
		goto out_req;
	}

	if (memcmp(cipher, eip93_cipher_first, sizeof(eip93_cipher_first))) {
		pr_err("eip93-kat: NIST AES-CBC first-block KAT failed\n");
		ret = -EBADMSG;
		goto out_req;
	}

	sg_init_one(&src_sg, cipher, EIP93_TEST_LEN);
	sg_init_one(&dst_sg, recovered, EIP93_TEST_LEN);
	memcpy(iv, eip93_iv, sizeof(iv));
	skcipher_request_set_crypt(req, &src_sg, &dst_sg,
				   EIP93_TEST_LEN, iv);
	crypto_init_wait(&wait);
	ret = crypto_wait_req(crypto_skcipher_decrypt(req), &wait);
	if (ret) {
		pr_err("eip93-kat: decrypt request failed: %d\n", ret);
		goto out_req;
	}

	if (memcmp(recovered, plain, EIP93_TEST_LEN)) {
		pr_err("eip93-kat: 1024-byte decrypt round-trip failed\n");
		ret = -EBADMSG;
		goto out_req;
	}

	pr_info("eip93-kat: PASS provider=%s bytes=%u key=AES-128 mode=CBC\n",
		crypto_skcipher_driver_name(tfm), EIP93_TEST_LEN);
	pr_info("eip93-kat: request exceeds configured 512-byte AES-128 fallback threshold\n");
	ret = 0;

out_req:
	skcipher_request_free(req);
out_buf:
	kfree(recovered);
	kfree(cipher);
	kfree(plain);
out_tfm:
	crypto_free_skcipher(tfm);
	return ret;
}

static void __exit eip93_kat_exit(void)
{
}

module_init(eip93_kat_init);
module_exit(eip93_kat_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("EIP-93 AES-128-CBC kernel Crypto API known-answer test");
