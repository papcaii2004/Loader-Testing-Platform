#pragma once
#include "../../core/utils.h"
#include "../context.h"

inline BOOL Stage4_Write_Local(TechniqueContext* ctx)
{
    if (!ctx || !ctx->allocated_mem || !ctx->data)
        return FALSE;

#ifdef DEBUG_MODE
    DEBUG_MSG("Stage 4",
              "Writing %llu bytes to %p",
              ctx->length,
              ctx->allocated_mem);
#endif

    memcpy(ctx->allocated_mem, ctx->data, ctx->length);

#ifdef DEBUG_MODE
    unsigned char* check = (unsigned char*)ctx->allocated_mem;

    DEBUG_MSG("Stage 4",
              "Dest bytes: %02X %02X %02X %02X %02X %02X %02X %02X",
              check[0], check[1], check[2], check[3],
              check[4], check[5], check[6], check[7]);
#endif

    return TRUE;
}