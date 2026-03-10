#pragma once
#include "../context.h"
#include "../../core/utils.h"
#include "../../api/api_wrappers.h"
#include "aes.h"
#include <minwindef.h>

// T2: XOR Decryption Primitive
BOOL Stage3_Transform_AES(TechniqueContext* ctx) {
    if (!ctx->key || ctx->key_len != 16) return FALSE;
    if (!ctx->nonce || ctx->nonce_len != 8) return FALSE;

    uint8_t iv[16] = {0};
    memcpy(iv, ctx->nonce, 8);
    // 8 byte sau = counter

    struct AES_ctx aes_ctx;
    AES_init_ctx_iv(&aes_ctx, ctx->key, iv);
    
    AES_CTR_xcrypt_buffer(&aes_ctx, ctx->data, ctx->length);

    SecureZeroMemory(ctx->key, ctx->key_len);

    #ifdef DEBUG_MODE
        DEBUG_MSG("Stage 3", "AES-128-CTR Decryption Complete");
    #endif

    return TRUE;
}