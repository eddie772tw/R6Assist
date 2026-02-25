import os
import io
import fnmatch
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# Use custom fonts globally
try:
    from tkinter import font as tkfont
except ImportError:
    tkfont = None

class R6AssistLabeler(tk.Tk):
    def __init__(self, harvest_dir, dataset_dir):
        super().__init__()
        self.harvest_dir = harvest_dir
        self.dataset_dir = dataset_dir
        
        self.title("R6Assist 截圖自動標註輔助分類器")
        self.geometry("900x700")
        self.configure(bg="#2b2b2b")
        self.minsize(600, 500)
        
        # UI Styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Color palette
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.btn_bg = "#3c3f41"
        self.btn_fg = "#ffffff"
        self.btn_active_bg = "#585b5d"
        self.accent_color = "#1f6aa5"
        self.danger_color = "#c84031"
        self.danger_active_color = "#e55747"
        
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 12))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10), foreground="#a0a0a0")
        
        style.configure("Blue.TButton", background=self.accent_color, foreground="white", font=("Segoe UI", 10, "bold"), padding=5)
        style.map("Blue.TButton", background=[("active", "#2580c7")])
        
        style.configure("Danger.TButton", background=self.danger_color, foreground="white", font=("Segoe UI", 10, "bold"), padding=5)
        style.map("Danger.TButton", background=[("active", self.danger_active_color)])
        
        style.configure("TCombobox", fieldbackground=self.btn_bg, background=self.btn_bg, foreground=self.fg_color, selectbackground=self.accent_color)
        
        # Load operators list from dataset dirs
        self.operators = self.load_operator_list()
        
        # Images state
        self.image_files = self.find_unknown_images()
        self.current_idx = 0
        self.photo_img = None  # To prevent GC
        
        self.setup_ui()
        self.load_image()
        
        # Bind keyboard shortcuts
        self.bind("<Left>", lambda e: self.prev_image())
        self.bind("<Right>", lambda e: self.next_image())
        self.bind("<Delete>", lambda e: self.delete_image())
        self.bind("<Return>", lambda e: self.save_classification())

    def load_operator_list(self):
        # Scan train and val datasets to get all known operator names
        operators = set()
        
        # Check both train and val dirs
        for subset in ['train', 'val']:
            subset_dir = os.path.join(self.dataset_dir, subset)
            if not os.path.isdir(subset_dir): continue
            
            for op in os.listdir(subset_dir):
                if os.path.isdir(os.path.join(subset_dir, op)):
                    if op.lower() != 'unknown':
                        operators.add(op)
                        
        op_list = sorted(list(operators))
        return op_list

    def find_unknown_images(self):
        unknown_dir = os.path.join(self.harvest_dir, "unknown")
        if not os.path.isdir(unknown_dir):
            return []
            
        images = []
        for file in os.listdir(unknown_dir):
            if fnmatch.fnmatch(file.lower(), '*.jpg') or fnmatch.fnmatch(file.lower(), '*.png'):
                images.append(os.path.join(unknown_dir, file))
                
        return sorted(images)

    def setup_ui(self):
        # Main layout
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(header_frame, text="R6Assist Image Classification Tool", style="Header.TLabel").pack(side=tk.LEFT)
        self.status_lbl = ttk.Label(header_frame, text="Loading...", style="Status.TLabel")
        self.status_lbl.pack(side=tk.RIGHT, pady=5)
        
        # Image Display Area (with border)
        img_frame = tk.Frame(main_frame, bg="#1e1e1e", bd=2, relief=tk.SUNKEN)
        img_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Container to center the image
        img_center = tk.Frame(img_frame, bg="#1e1e1e")
        img_center.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        self.img_lbl = tk.Label(img_center, bg="#1e1e1e", text="尚無需要分類的圖片", fg=self.fg_color, font=("Segoe UI", 14))
        self.img_lbl.pack()
        
        self.file_lbl = ttk.Label(main_frame, text="", style="Status.TLabel")
        self.file_lbl.pack(pady=5)
        
        # Controls Area
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Target Selection
        ttk.Label(controls_frame, text="目標幹員:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.op_var = tk.StringVar()
        self.cb_operator = ttk.Combobox(controls_frame, textvariable=self.op_var, values=self.operators, state="normal", width=30, font=("Segoe UI", 12))
        self.cb_operator.pack(side=tk.LEFT, padx=10)
        
        # Allow typing to filter
        self.cb_operator.bind('<KeyRelease>', self.on_cb_type)
        self.cb_operator.bind('<<ComboboxSelected>>', lambda e: self.cb_operator.select_clear())
        
        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="⬅ 上一張 (Left)", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下一張 (Right) ➡", command=self.next_image).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="分類並儲存 (Enter)", style="Blue.TButton", command=self.save_classification).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="這不是圖標 / 刪除 (Del)", style="Danger.TButton", command=self.delete_image).pack(side=tk.RIGHT, padx=20)
        
        # Shortcuts helper
        ttk.Label(main_frame, text="快捷鍵：鍵盤左右切換、Delete 刪除、Enter 確定分類", style="Status.TLabel").pack(pady=10)

    def on_cb_type(self, event):
        # Custom dropdown filtering logic
        val = event.widget.get()
        if val == '':
            self.cb_operator['values'] = self.operators
        else:
            filtered = [item for item in self.operators if val.lower() in item.lower()]
            self.cb_operator['values'] = filtered

    def load_image(self):
        if not self.image_files:
            self.img_lbl.config(image='', text="恭喜！Unknown 資料夾內已無任何需要分類的圖片。")
            self.status_lbl.config(text="0 / 0")
            self.file_lbl.config(text="")
            self.cb_operator.set('')
            self.cb_operator.config(state="disabled")
            return
            
        # Ensure bounds
        if self.current_idx >= len(self.image_files):
            self.current_idx = len(self.image_files) - 1
        elif self.current_idx < 0:
            self.current_idx = 0
            
        img_path = self.image_files[self.current_idx]
        
        try:
            # Load with PIL to support resizing nicely
            pil_img = Image.open(img_path)
            
            # Upscale the 64x64 or small crop for user to actually see it easily
            # Resize 4x with NEAREST interpolation to keep it pixelated/sharp if small
            w, h = pil_img.size
            if w <= 128:
                pil_img = pil_img.resize((w*4, h*4), Image.Resampling.NEAREST)
            else:
                # If it's already big, just fit within 400x400
                pil_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                
            self.photo_img = ImageTk.PhotoImage(pil_img)
            self.img_lbl.config(image=self.photo_img, text='')
            
        except Exception as e:
            self.img_lbl.config(image='', text=f"無法讀取圖片: {e}")
            
        # Update UI info
        self.status_lbl.config(text=f"{self.current_idx + 1} / {len(self.image_files)}")
        self.file_lbl.config(text=os.path.basename(img_path))
        
        # Focus combo for quick typing
        if self.image_files:
            self.cb_operator.config(state="normal")
            self.cb_operator.focus_set()
            # Clear text
            self.cb_operator.set('')

    def next_image(self):
        if self.image_files and self.current_idx < len(self.image_files) - 1:
            self.current_idx += 1
            self.load_image()

    def prev_image(self):
        if self.image_files and self.current_idx > 0:
            self.current_idx -= 1
            self.load_image()

    def delete_image(self):
        if not self.image_files: return
        
        img_path = self.image_files[self.current_idx]
        try:
            os.remove(img_path)
            del self.image_files[self.current_idx]
            
            # If we deleted the last item, bounds check happens in load_image
            self.load_image()
        except Exception as e:
            messagebox.showerror("刪除失敗", f"無法刪除檔案:\n{e}")

    def save_classification(self):
        if not self.image_files: return
        
        target_op = self.op_var.get().strip()
        if not target_op:
            messagebox.showwarning("警告", "請先選擇或輸入欲分類的幹員名稱！")
            return
            
        # Create directory if it doesn't exist
        dest_dir = os.path.join(self.harvest_dir, target_op)
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir)
                # Ensure it's added to combobox list for future use
                if target_op not in self.operators:
                    self.operators.append(target_op)
                    self.operators.sort()
                    self.cb_operator['values'] = self.operators
            except Exception as e:
                messagebox.showerror("資料夾建立失敗", f"無法建立目錄 {dest_dir}:\n{e}")
                return
                
        img_path = self.image_files[self.current_idx]
        filename = os.path.basename(img_path)
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            import shutil
            shutil.move(img_path, dest_path)
            del self.image_files[self.current_idx]
            self.load_image()
        except Exception as e:
            messagebox.showerror("移動失敗", f"無法儲存分類檔案:\n{e}")

if __name__ == "__main__":
    # Resolve paths
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(tools_dir)
    harvest_dir = os.path.join(root_dir, "dataset_harvested")
    dataset_dir = os.path.join(root_dir, "dataset")
    
    if not os.path.exists(os.path.join(harvest_dir, "unknown")):
        print(f"找不到未知分類資料夾: {os.path.join(harvest_dir, 'unknown')}")
        print("請確保您已經運行過 crop_and_label.py 來擷取遊戲截圖。")
        
    app = R6AssistLabeler(harvest_dir, dataset_dir)
    app.mainloop()
