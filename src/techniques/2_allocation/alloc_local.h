#pragma once
#include "../../api/api_wrappers.h"
#include "../../core/utils.h"
#include "../context.h"

inline BOOL Stage2_Alloc_Local(TechniqueContext* ctx)
{
    ctx->allocated_mem = (unsigned char*)MyVirtualAllocEx(
                            (HANDLE)-1,
                            NULL,
                            ctx->length,
                            MEM_COMMIT | MEM_RESERVE,
                            PAGE_EXECUTE_READWRITE
                        );

#ifdef DEBUG_MODE
    if (ctx->allocated_mem) {
        DEBUG_MSG("Stage2", "Allocated %llu bytes at %p",
                  ctx->length, ctx->allocated_mem);
    } else {
        DEBUG_MSG("Stage2", "Allocation failed");
    }
#endif

    return ctx->allocated_mem != NULL;
}