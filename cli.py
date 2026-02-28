import argparse
import os
import sys
import time

# --- MÀU SẮC CHO TERMINAL (ANSI Codes) ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# --- IMPORTS ---
try:
    from controller import core_engine
    from controller.config import VMS_CONFIG, PROJECT_ROOT, OUTPUT_DIR, BUILD_DIR, LOGS_DIR
except ImportError as e:
    print(f"{Colors.FAIL}[!] Error importing modules: {e}{Colors.ENDC}")
    sys.exit(1)

def print_pipeline_banner(options, shellcode_path):
    """Hiển thị cấu hình dưới dạng 5 Stages"""
    
    # Chuẩn bị dữ liệu hiển thị
    s0_status = f"{Colors.GREEN}[ ENABLED ]{Colors.ENDC}" if options.get('anti_evasion') else f"{Colors.WARNING}[ DISABLED ]{Colors.ENDC}"
    
    s1_method = ".rdata (Embedded Variable)" # Hiện tại hardcode, sau này lấy từ options
    
    s3_algo = options.get('encryption').upper()
    s3_color = Colors.GREEN if s3_algo != "NONE" else Colors.FAIL
    
    api_mode = options.get('api_method').upper()
    api_color = Colors.CYAN if "SYSCALL" in api_mode else (Colors.WARNING if "INDIRECT" in api_mode else Colors.FAIL)
    
    inj_tech = options.get('injection').upper()
    
    sc_name = os.path.basename(shellcode_path)

    print(f"\n{Colors.BOLD}{Colors.HEADER}=== EVASION ENGINEERING PIPELINE CONFIGURATION ==={Colors.ENDC}")
    print(f"Payload Source: {Colors.CYAN}{sc_name}{Colors.ENDC}")
    print("│")
    
    # STAGE 0
    print(f"├── {Colors.BOLD}Stage 0: Anti-Analysis{Colors.ENDC}")
    print(f"│   └── Checks: {s0_status}")
    print("│")
    
    # STAGE 1 & 3 (Static Defense)
    print(f"├── {Colors.BOLD}Stage 1 & 3: Storage & Transformation{Colors.ENDC}")
    print(f"│   ├── Storage:      {s1_method}")
    print(f"│   └── Encryption:   {s3_color}{s3_algo}{Colors.ENDC}")
    print("│")
    
    # API LAYER
    print(f"├── {Colors.BOLD}Abstraction Layer: API Obfuscation{Colors.ENDC}")
    print(f"│   └── Method:       {api_color}{api_mode}{Colors.ENDC}")
    print("│")
    
    # STAGE 2 & 4 (Dynamic Execution)
    print(f"└── {Colors.BOLD}Stage 2 & 4: Allocation & Execution{Colors.ENDC}")
    print(f"    └── Technique:    {Colors.GREEN}{inj_tech}{Colors.ENDC}")
    print("")

def main():
    parser = argparse.ArgumentParser(
        description="FUD Testing Platform - Automated Evasion Engineering",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # --- GLOBAL OPTIONS ---
    grp_global = parser.add_argument_group(f'{Colors.CYAN}Global Options{Colors.ENDC}')
    grp_global.add_argument("-s", "--shellcode", required=True, metavar="PATH", help="Path to raw shellcode (.bin)")
    grp_global.add_argument("-v", "--vms", nargs='*', metavar="VM", help="Target VMs (e.g., 'Windows Defender').")
    grp_global.add_argument("--build-only", action="store_true", help="Build only, do not run tests.")
    grp_global.add_argument("--debug", action="store_true", help="Enable debug popups in payload.")

    # --- STAGE 0 ---
    grp_s0 = parser.add_argument_group(f'{Colors.CYAN}Stage 0: Anti-Analysis{Colors.ENDC}')
    grp_s0.add_argument("--anti-evasion", action="store_true", help="Enable sandbox/debugger checks.")

    # --- STAGE 1 & 3 ---
    grp_s3 = parser.add_argument_group(f'{Colors.CYAN}Stage 1 & 3: Storage & Transformation{Colors.ENDC}')
    grp_s3.add_argument("-e", "--encryption", default="none", choices=["none", "xor", "aes"], help="Payload encryption algorithm.")
    # (Sau này thêm --storage-method vào đây)

    # --- STAGE 2 & 4 ---
    grp_s24 = parser.add_argument_group(f'{Colors.CYAN}Stage 2 & 4: Allocation & Execution{Colors.ENDC}')
    grp_s24.add_argument("-i", "--injection", default="classic", choices=["classic", "hollowing", "apc"], help="Injection technique.")
    
    # --- API LAYER ---
    grp_api = parser.add_argument_group(f'{Colors.CYAN}API Abstraction Layer{Colors.ENDC}')
    grp_api.add_argument("--api-method", default="winapi", choices=["winapi", "winapi-indirect", "syscalls"], help="API calling convention.")

    args = parser.parse_args()

    # --- VALIDATION ---
    if not args.build_only and not args.vms:
        parser.error("You must specify target VMs with -v/--vms OR use --build-only.")

    # --- PREPARE ---
    # Đường dẫn tuyệt đối
    if not os.path.isabs(args.shellcode):
        shellcode_path = os.path.join(PROJECT_ROOT, args.shellcode)
    else:
        shellcode_path = args.shellcode

    build_options = vars(args)

    # --- HIỂN THỊ BANNER ---
    print_pipeline_banner(build_options, shellcode_path)
    
    # Giả lập thời gian suy nghĩ một chút cho ngầu (optional)
    # time.sleep(1) 

    # --- BUILD ---
    payload_path = core_engine.build_payload(shellcode_path, build_options)

    if not payload_path:
        print(f"\n{Colors.FAIL}[!] Payload build failed. Aborting.{Colors.ENDC}")
        return
    
    print(f"\n{Colors.GREEN}[SUCCESS] Payload built at: {payload_path}{Colors.ENDC}")

    if args.build_only:
        return

    # --- TEST ---
    for vm_name in args.vms:
        if vm_name not in VMS_CONFIG:
            print(f"{Colors.FAIL}[!] Error: VM '{vm_name}' not defined in config.{Colors.ENDC}")
            continue

        result = core_engine.run_single_test(vm_name, payload_path, build_options)
        
        # In báo cáo ngắn gọn
        status = result.get('status', 'UNKNOWN')
        color = Colors.GREEN if "SUCCESS" in status else Colors.FAIL
        
        print(f"\n{Colors.BOLD}--- Result for {vm_name} ---{Colors.ENDC}")
        print(f"Status: {color}{status}{Colors.ENDC}")
        
        if 'FAILED' in status or 'ERROR' in status:
            print(f"{Colors.WARNING}Log Preview:{Colors.ENDC}")
            # Chỉ in 3 dòng đầu của log để đỡ rối
            logs = result.get('log', '').split('\n')
            for line in logs[:5]:
                if line.strip(): print(f"  > {line}")
            print(f"  > (See full logs in test_logs/)")

if __name__ == "__main__":
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    main()