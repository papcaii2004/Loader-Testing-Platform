#pragma once
#include "../../api/api_wrappers.h"
#include "../../core/utils.h"
#include <cstring>

BOOL Stage4_Write_Local(LPVOID dest, unsigned char* src, int len) {

    #ifdef DEBUG_MODE
        DEBUG_MSG("Stage 4",
                  "Writing %d bytes to %p from %p",
                  len, dest, src);
    #endif

    memcpy(dest, src, len);

    #ifdef DEBUG_MODE
        DEBUG_MSG("Stage 4", "Write completed");
        unsigned char* check = (unsigned char*)dest;
        DEBUG_MSG("Stage 4",
          "Dest bytes: %02X %02X %02X %02X %02X %02X %02X %02X",
          check[0], check[1], check[2], check[3], check[4], check[5], check[6], check[7]);
    #endif

    return TRUE;
}