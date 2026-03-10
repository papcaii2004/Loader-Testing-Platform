#pragma once
#include "../context.h"
#include "../../core/utils.h"
#include "../../api/api_wrappers.h"

inline BOOL Stage3_Transform_XOR(TechniqueContext* ctx)
{
    if (!ctx) return FALSE;
    if (!ctx->data) return FALSE;
    if (!ctx->key || ctx->key_len == 0) return FALSE;

    for (SIZE_T i = 0; i < ctx->length; i++) {
        ctx->data[i] = ctx->data[i] ^ ctx->key[i % ctx->key_len];
    }

#ifdef DEBUG_MODE
    DEBUG_MSG("Stage 3", "XOR Decryption Complete (%llu bytes)", ctx->length);
#endif

    return TRUE;
}