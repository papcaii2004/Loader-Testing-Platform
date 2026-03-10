#pragma once
#include "../context.h"

#ifdef T3_TRANSFORM_XOR
#include "../3_transformation/crypto_xor.h"
#endif

#ifdef T3_TRANSFORM_AES
#include "../3_transformation/crypto_aes.h"
#endif

inline BOOL Run_T3_Transform(TechniqueContext* ctx)
{

#ifdef T3_TRANSFORM_NONE
    return TRUE;
#endif

#ifdef T3_TRANSFORM_XOR
    return Stage3_Transform_XOR(ctx);
#endif

#ifdef T3_TRANSFORM_AES
    return Stage3_Transform_AES(ctx);
#endif

    return FALSE;
}