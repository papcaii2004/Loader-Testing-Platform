#pragma once
#include "../context.h"

#ifdef T2_ALLOC_LOCAL
#include "../2_allocation/alloc_local.h"
#endif

inline void Run_T2_Allocation(TechniqueContext* ctx)
{

#ifdef T2_ALLOC_LOCAL
    if (!Stage2_Alloc_Local(ctx)) return;
#endif

}