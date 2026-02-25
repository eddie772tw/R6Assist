import os
import sys
import subprocess
import threading
import queue
import time
import json
import customtkinter as ctk

# Ensure working directory is the project root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT_DIR)

# Aesthetics Setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LanguageManager:
    def __init__(self, lang_dir="lang", default_lang="en"):
        self.lang_dir = os.path.join(ROOT_DIR, lang_dir)
        self.current_lang = default_lang
        self.strings = {}
        self.load_lang(self.current_lang)

    def load_lang(self, lang_code):
        path = os.path.join(self.lang_dir, f"{lang_code}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.strings = json.load(f)
            self.current_lang = lang_code
        except Exception as e:
            print(f"Warning: Failed to load language {lang_code} from {path}. {e}")
            self.strings = {}

    def get(self, key, **kwargs):
        text = self.strings.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text

class R6AssistLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.lm = LanguageManager(default_lang="en-us")
        
        self.title(self.lm.get("window_title"))
        self.geometry("900x650")
        self.minsize(800, 500)

        # Process management
        self.processes = {}
        self.log_queue = queue.Queue()
        
        self.setup_ui()
        self.update_ui_text() # Enforce text load
        
        # Start log polling
        self.after(100, self.poll_log_queue)
        
    def setup_ui(self):
        # Configure grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(9, weight=1) # Spacer

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Main operations
        self.dashboard_label = ctk.CTkLabel(self.sidebar_frame, font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        self.dashboard_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="ew")

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, command=self.toggle_dashboard, fg_color="green")
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=10)

        self.btn_cli = ctk.CTkButton(self.sidebar_frame, command=self.toggle_cli)
        self.btn_cli.grid(row=3, column=0, padx=20, pady=10)

        # Tools Header
        self.tools_label = ctk.CTkLabel(self.sidebar_frame, font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        self.tools_label.grid(row=4, column=0, padx=20, pady=(20, 0), sticky="ew")

        # Tools buttons
        self.btn_update_db = ctk.CTkButton(self.sidebar_frame, command=lambda: self.run_tool("get_op_stat.py"))
        self.btn_update_db.grid(row=5, column=0, padx=20, pady=(10, 5))

        self.btn_download_icons = ctk.CTkButton(self.sidebar_frame, command=lambda: self.run_tool("get_raw_icon.py"))
        self.btn_download_icons.grid(row=6, column=0, padx=20, pady=5)

        self.btn_gen_dataset = ctk.CTkButton(self.sidebar_frame, command=lambda: self.run_tool("generate_dataset.py"))
        self.btn_gen_dataset.grid(row=7, column=0, padx=20, pady=5)

        self.btn_train = ctk.CTkButton(self.sidebar_frame, command=lambda: self.run_tool("train.py"))
        self.btn_train.grid(row=8, column=0, padx=20, pady=5)
        
        self.btn_verify = ctk.CTkButton(self.sidebar_frame, command=lambda: self.run_tool("verify_roi.py"))
        self.btn_verify.grid(row=9, column=0, padx=20, pady=5, sticky="n")

        # Status
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text_color="gray")
        self.status_label.grid(row=10, column=0, padx=20, pady=10)
        
        # Language Selector
        self.lang_label = ctk.CTkLabel(self.sidebar_frame, font=ctk.CTkFont(size=12))
        self.lang_label.grid(row=11, column=0, padx=20, pady=(5, 0))
        
        self.lang_combo = ctk.CTkComboBox(self.sidebar_frame, values=["English (en-us)", "繁體中文 (zh-tw)"], command=self.change_language)
        self.lang_combo.grid(row=12, column=0, padx=20, pady=(0, 20))
        if self.lm.current_lang == "zh-tw":
            self.lang_combo.set("繁體中文 (zh-tw)")
        else:
            self.lang_combo.set("English (en-us)")

        # --- Main View (Logs) ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.console_title = ctk.CTkLabel(self.main_frame, font=ctk.CTkFont(size=16, weight="bold"))
        self.console_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.textbox = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        self.textbox.grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        
        self.btn_clear_log = ctk.CTkButton(self.main_frame, command=lambda: self.textbox.delete('1.0', ctk.END), width=100)
        self.btn_clear_log.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="e")
        
        self.append_log(self.lm.get("welcome_1"))
        self.append_log(self.lm.get("welcome_2"))

    def change_language(self, choice):
        if choice == "繁體中文 (zh-tw)":
            self.lm.load_lang("zh-tw")
        else:
            self.lm.load_lang("en-us")
        self.update_ui_text()
        self.append_log(f"Language Output -> {choice}")

    def update_ui_text(self):
        self.title(self.lm.get("window_title"))
        self.logo_label.configure(text=self.lm.get("logo_text"))
        self.dashboard_label.configure(text=self.lm.get("runtime_modules"))
        self.tools_label.configure(text=self.lm.get("dev_tools"))
        self.btn_update_db.configure(text=self.lm.get("update_db"))
        self.btn_download_icons.configure(text=self.lm.get("download_icons"))
        self.btn_gen_dataset.configure(text=self.lm.get("gen_dataset"))
        self.btn_train.configure(text=self.lm.get("train_model"))
        self.btn_verify.configure(text=self.lm.get("verify_roi"))
        self.console_title.configure(text=self.lm.get("system_logs"))
        self.btn_clear_log.configure(text=self.lm.get("clear_logs"))
        self.lang_label.configure(text=self.lm.get("language"))
        
        self.update_status_labels()

    def update_status_labels(self):
        is_dash_running = "API" in self.processes and self.processes["API"].poll() is None
        if is_dash_running:
            self.btn_dashboard.configure(text=self.lm.get("stop_dashboard"))
        else:
            self.btn_dashboard.configure(text=self.lm.get("start_dashboard"))
            
        is_cli_running = "MONITOR" in self.processes and self.processes["MONITOR"].poll() is None
        if is_cli_running:
            self.btn_cli.configure(text=self.lm.get("stop_cli"))
        else:
            self.btn_cli.configure(text=self.lm.get("start_cli"))

        if is_dash_running:
             self.status_label.configure(text=self.lm.get("status_dashboard"))
        elif is_cli_running:
             self.status_label.configure(text=self.lm.get("status_cli"))
        else:
             self.status_label.configure(text=self.lm.get("status_idle"))

    def append_log(self, text):
        self.log_queue.put(text)

    def poll_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.textbox.insert(ctk.END, msg + "\n")
            self.textbox.see(ctk.END) # Auto-scroll
        self.after(100, self.poll_log_queue)
        
    def read_process_output(self, process, process_name):
        for line in iter(process.stdout.readline, b''):
            try:
                line_str = line.decode('utf-8').rstrip()
            except UnicodeDecodeError:
                line_str = line.decode('cp950', errors='ignore').rstrip()
            if line_str:
                self.append_log(f"[{process_name}] {line_str}")
                
        # Handle stderr as well
        if process.stderr:
            for line in iter(process.stderr.readline, b''):
                try:
                    line_str = line.decode('utf-8').rstrip()
                except UnicodeDecodeError:
                    line_str = line.decode('cp950', errors='ignore').rstrip()
                if line_str:
                    self.append_log(f"[{process_name} WARN] {line_str}")
                    
        process.stdout.close()
        process.wait()
        
        code = process.returncode
        self.append_log(self.lm.get("process_exited", process_name=process_name, code=code))

        # Refresh UI states strictly on the main thread
        self.after(0, self.update_status_labels)

    def run_command_async(self, cmd_list, process_name, cwd=None):
        self.append_log(self.lm.get("starting_process", process_name=process_name))
        try:
            # Use shell=True for npm commands on Windows if necessary
            is_shell = True if os.name == 'nt' and cmd_list[0] == 'npm' else False
            
            p = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr into stdout thread
                cwd=cwd or ROOT_DIR,
                shell=is_shell
            )
            self.processes[process_name] = p
            
            # Start background thread to read output
            t = threading.Thread(target=self.read_process_output, args=(p, process_name), daemon=True)
            t.start()
            
            return True
        except Exception as e:
            self.append_log(self.lm.get("failed_to_start", process_name=process_name, error=e))
            return False

    def toggle_dashboard(self):
        # We need to start API (api.py) and Web UI (npm run dev)
        is_running = "API" in self.processes and self.processes["API"].poll() is None
        
        if is_running:
            # Stop them
            self.append_log(self.lm.get("stopping_dashboard"))
            if "API" in self.processes:
                self.processes["API"].terminate()
            if "WEB_UI" in self.processes:
                os.system(f"taskkill /F /PID {self.processes['WEB_UI'].pid} /T >nul 2>&1")
                
            self.btn_dashboard.configure(fg_color="green")
        else:
            # Start them
            self.btn_dashboard.configure(fg_color="red")
            
            # 1. Start API Backend
            self.run_command_async([sys.executable, "api.py"], "API")
            
            # 2. Start Web UI Frontend
            web_cwd = os.path.join(ROOT_DIR, "r6assist-webui")
            self.run_command_async(["npm", "run", "dev"], "WEB_UI", cwd=web_cwd)
            
        self.update_status_labels()

    def toggle_cli(self):
        is_running = "MONITOR" in self.processes and self.processes["MONITOR"].poll() is None
        
        if is_running:
            self.append_log(self.lm.get("stopping_cli"))
            self.processes["MONITOR"].terminate()
            self.btn_cli.configure(fg_color=["#3B8ED0", "#1F6AA5"])
        else:
            self.btn_cli.configure(fg_color="red")
            self.run_command_async([sys.executable, "monitor.py"], "MONITOR")
            
        self.update_status_labels()

    def run_tool(self, tool_file):
        tool_path = os.path.join("tools", tool_file)
        if not os.path.exists(tool_path):
            self.append_log(self.lm.get("tool_not_found", tool_path=tool_path))
            return
            
        process_name = f"TOOL: {tool_file}"
        self.run_command_async([sys.executable, tool_path], process_name)

    def destroy(self):
        # Clean up any running child processes when the GUI is closed
        self.append_log(self.lm.get("shutting_down"))
        for name, p in self.processes.items():
            if p.poll() is None:
                try:
                    if name == "WEB_UI" and os.name == 'nt':
                         os.system(f"taskkill /F /PID {p.pid} /T >nul 2>&1")
                    else:
                        p.terminate()
                except Exception:
                    pass
        super().destroy()

if __name__ == "__main__":
    app = R6AssistLauncher()
    app.mainloop()
