#pragma once
#include "../1_storage/storage_data.h"
#include "../../core/utils.h"
#include "aes.h"

// T2: XOR Decryption Primitive
void Stage3_Transform_AES(PayloadContext* ctx) {
    if (!ctx->key || ctx->key_len != 16) return;
    if (!ctx->nonce || ctx->nonce_len != 8) return;

    uint8_t iv[16] = {0};
    memcpy(iv, ctx->nonce, 8);
    // 8 byte sau = counter

    struct AES_ctx aes_ctx;
    AES_init_ctx_iv(&aes_ctx, ctx->key, iv);
    
    // CTR_xcrypt_buffer decrypt in-place
    AES_CTR_xcrypt_buffer(&aes_ctx, ctx->data, ctx->length);

    #ifdef DEBUG_MODE
        DEBUG_MSG("Stage 3", "AES-128-CTR Decryption Complete");
    #endif
}