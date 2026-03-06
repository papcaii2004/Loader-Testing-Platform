# controller/modules/crypto_utils.py
import random
import string
import logging
import tinyaes
import os

logger = logging.getLogger("CryptoUtils")

def xor_encrypt(data):
    key = os.urandom(16)
    ciphertext = bytearray(b ^ key[i % len(key)] for i, b in enumerate(data))
    return ciphertext, key

def aes_encrypt(data):
    key = os.urandom(16)   
    nonce = os.urandom(8)

    # tinyaes cần iv 16 bytes: [8-byte nonce] + [8-byte zero counter]
    iv = nonce + b'\x00' * 8

    cipher = tinyaes.AES(key, iv)
    ciphertext = cipher.CTR_xcrypt_buffer(bytes(data))
    
    return ciphertext, key, nonce

# Dispatcher: Hàm điều phối chính
def apply_encryption(data, method):
    
    if method == 'xor':
        encrypted_data, key = xor_encrypt(data)
        return {
            "method": "xor",
            "ciphertext": encrypted_data,
            "key": key
        }

    elif method == 'aes':
        encrypted_data, key, nonce = aes_encrypt(data)
        return {
            "method": "aes-ctr",
            "ciphertext": encrypted_data,
            "key": key,
            "nonce": nonce
        }

    else:
        return {
            "method": "none",
            "ciphertext": data,
            "key": ""
        }