from shared.crypto_secure import gen_keypair_b64
pk, sk = gen_keypair_b64()
print("SERVER_PUBLIC_KEY_B64=", pk)
print("WORKER_PRIVATE_KEY_B64=", sk)

