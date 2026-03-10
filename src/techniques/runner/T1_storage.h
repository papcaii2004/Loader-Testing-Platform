#pragma once

#include "../context.h"

#ifdef T1_STORAGE_RDATA
#include "../1_storage/storage_rdata.h"
#endif

inline void Run_T1_Storage(TechniqueContext* ctx)
{

#ifdef T1_STORAGE_RDATA
    Stage1_Storage_Rdata(ctx);
#endif

}