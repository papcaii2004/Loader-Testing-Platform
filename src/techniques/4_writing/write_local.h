#pragma once
#include "../../api/api_wrappers.h"

BOOL Stage4_Write_Local(LPVOID dest, unsigned char* src, int len) {
    // RtlMoveMemory không phải là syscall, nhưng là hàm safe
    RtlMoveMemory(dest, src, len);
    return TRUE;
}