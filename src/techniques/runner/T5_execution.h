#pragma once
#include "../context.h"

#ifdef T5_EXEC_LOCAL
#include "../5_execution/exec_local.h"
#endif

inline BOOL Run_T5_Execute(TechniqueContext* ctx)
{

#ifdef T5_EXEC_LOCAL
    return Stage5_Exec_LocalThread(ctx);
#endif

    return FALSE;
}