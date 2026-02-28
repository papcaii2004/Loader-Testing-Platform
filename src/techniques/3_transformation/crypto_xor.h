#pragma once
#include "../1_storage/storage_data.h"

// Giải mã tại chỗ (In-place) hoặc giải mã ra buffer tạm
void Stage3_Transform_XOR(PayloadContext* ctx) {
    int key_len = 0;
    while(ctx->key[key_len] != 0) key_len++;
    
    for (int i = 0; i < ctx->length; i++) {
        ctx->data[i] = ctx->data[i] ^ ctx->key[i % key_len];
    }
    #ifdef DEBUG_MODE
        DEBUG_MSG("Stage 3", "XOR Decryption Complete");
    #endif
}