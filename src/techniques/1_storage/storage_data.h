#pragma once
#include <windows.h>

// Các biến toàn cục do Python tạo ra
extern unsigned char shellcode[];
extern unsigned int shellcode_len;
extern char* key;

struct PayloadContext {
    unsigned char* data;
    int length;
    char* key;
    LPVOID allocated_mem; // Lưu địa chỉ vùng nhớ sau khi allocate
};

PayloadContext Stage1_Storage_GetData() {
    PayloadContext ctx;
    ctx.data = shellcode;
    ctx.length = shellcode_len;
    ctx.key = key;
    ctx.allocated_mem = NULL;
    return ctx;
}