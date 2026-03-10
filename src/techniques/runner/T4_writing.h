#pragma once
#include "../context.h"

#ifdef T4_WRITE_LOCAL
#include "../4_writing/write_local.h"
#endif

inline BOOL Run_T4_Write(TechniqueContext* ctx)
{
#ifdef T4_WRITE_LOCAL
    return Stage4_Write_Local(ctx);
#endif

    return FALSE;
}