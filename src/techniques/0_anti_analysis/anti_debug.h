##pragma once
#include "../../core/utils.h"

// Hàm kiểm tra debug cơ bản
// Nếu không bật cờ EVASION_CHECKS_ENABLED thì luôn trả về FALSE (Không bị debug)
BOOL IsDebugged() {
#ifdef EVASION_CHECKS_ENABLED
    // Kiểm tra cờ BeingDebugged trong PEB
    PPEB pPeb = GetPeb();
    if (pPeb->BeingDebugged) {
        #ifdef DEBUG_MODE
            DEBUG_MSG("Anti-Analysis", "Debugger detected via PEB!");
        #endif
        return TRUE;
    }
#endif
    return FALSE;
}