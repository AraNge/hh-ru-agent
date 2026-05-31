#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import secrets
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import json

# hh.ru color scheme
HH_RED = "#C3182D"
HH_RED_DARK = "#9E1324"
HH_RED_LIGHT = "#FFE5E8"
HH_GRAY = "#F7F7F8"
HH_GRAY_DARK = "#EAEAED"
HH_GRAY_TEXT = "#7B7B85"
HH_BLACK = "#1A1B22"
HH_WHITE = "#FFFFFF"
HH_BORDER = "#D5D5DC"

FONT_PRIMARY = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_LARGE = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 9)


class HHAutomationApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("hh.ru Автоматизация | Панель управления")
        self.root.geometry("800x700")
        self.root.configure(bg=HH_GRAY)
        self.root.resizable(True, True)
        self.root.minsize(750, 650)
        
        # Process tracking
        self.n8n_process = None
        self.reply_process = None
        self.n8n_running = False
        self.reply_running = False
        self.cleanup_done = False
        
        # Credentials
        self.pg_entries = {}
        self.or_api_entry = None
        self.api_key = ""
        
        # Intercept window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        self.load_all_credentials()
        self.ensure_n8n_token()
        self.log("💡 Приложение готово к работе.", "info")
        
        # Check API key on startup
        if not self.api_key:
            self.log("⚠️ OpenRouter API ключ не настроен! Автоответчик не будет работать.", "warning")
            self.log("💡 Перейдите на вкладку 'Учетные данные' для настройки API ключа", "info")
    
    def setup_ui(self):
        # Header with hh.ru style
        header = tk.Frame(self.root, bg=HH_WHITE, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Top red line
        top_line = tk.Frame(header, bg=HH_RED, height=4)
        top_line.pack(fill=tk.X)
        
        # Logo and title
        title_frame = tk.Frame(header, bg=HH_WHITE)
        title_frame.pack(fill=tk.BOTH, padx=30, pady=15)
        
        logo_label = tk.Label(
            title_frame,
            text="hh.ru",
            font=("Segoe UI", 24, "bold"),
            fg=HH_RED,
            bg=HH_WHITE
        )
        logo_label.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            title_frame,
            text="Автоматизация",
            font=FONT_TITLE,
            fg=HH_BLACK,
            bg=HH_WHITE
        )
        title_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status indicator
        self.status_frame = tk.Frame(title_frame, bg=HH_WHITE)
        self.status_frame.pack(side=tk.RIGHT)
        
        self.status_dot = tk.Canvas(
            self.status_frame, 
            width=12, 
            height=12, 
            bg=HH_WHITE, 
            highlightthickness=0
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self.status_dot.create_oval(2, 2, 10, 10, fill=HH_GRAY_TEXT, outline="")
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Готов к работе",
            font=FONT_PRIMARY,
            fg=HH_GRAY_TEXT,
            bg=HH_WHITE,
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Create Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)
        
        # Style for notebook
        style = ttk.Style()
        style.configure("TNotebook", background=HH_GRAY, borderwidth=0)
        style.configure("TNotebook.Tab", font=FONT_PRIMARY, padding=[12, 4])
        style.map("TNotebook.Tab", background=[("selected", HH_RED), ("active", HH_RED_LIGHT)])
        
        # Tab 1: Main Control
        self.main_tab = tk.Frame(self.notebook, bg=HH_GRAY)
        self.notebook.add(self.main_tab, text="🎮 Управление")
        
        # Tab 2: Credentials
        self.creds_tab = tk.Frame(self.notebook, bg=HH_GRAY)
        self.notebook.add(self.creds_tab, text="🔐 Учетные данные")
        
        # Setup each tab
        self.setup_main_tab()
        self.setup_credentials_tab()
    
    def setup_main_tab(self):
        """Setup main control tab"""
        main_frame = tk.Frame(self.main_tab, bg=HH_GRAY)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Two main buttons
        buttons_frame = tk.Frame(main_frame, bg=HH_GRAY)
        buttons_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Button 1: Search and respond (n8n)
        self.btn_search = tk.Button(
            buttons_frame,
            text="🔍 Поиск работы\nи отклики",
            font=FONT_LARGE,
            bg=HH_RED,
            fg=HH_WHITE,
            activebackground=HH_RED_DARK,
            activeforeground=HH_WHITE,
            bd=0,
            padx=40,
            pady=30,
            cursor="hand2",
            command=self.toggle_n8n,
            relief=tk.FLAT
        )
        self.btn_search.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Button 2: Auto-reply to employers
        self.btn_reply = tk.Button(
            buttons_frame,
            text="💬 Автоответы\nработодателям",
            font=FONT_LARGE,
            bg=HH_BLACK,
            fg=HH_WHITE,
            activebackground=HH_GRAY_TEXT,
            activeforeground=HH_WHITE,
            bd=0,
            padx=40,
            pady=30,
            cursor="hand2",
            command=self.toggle_reply,
            relief=tk.FLAT
        )
        self.btn_reply.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Status cards
        cards_frame = tk.Frame(main_frame, bg=HH_GRAY)
        cards_frame.pack(fill=tk.X, pady=(0, 20))
        
        # n8n status card
        self.n8n_card = self.create_status_card(
            cards_frame, 
            "🔍 Поиск и отклики", 
            "● Остановлен",
            HH_GRAY_TEXT
        )
        self.n8n_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Reply status card
        self.reply_card = self.create_status_card(
            cards_frame, 
            "💬 Автоответчик", 
            "● Остановлен",
            HH_GRAY_TEXT
        )
        self.reply_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Log section
        log_frame = tk.Frame(main_frame, bg=HH_GRAY)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        log_header = tk.Frame(log_frame, bg=HH_GRAY)
        log_header.pack(fill=tk.X, pady=(0, 10))
        
        log_label = tk.Label(
            log_header,
            text="📋 Журнал событий",
            font=FONT_BOLD,
            fg=HH_BLACK,
            bg=HH_GRAY,
        )
        log_label.pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            log_header,
            text="Очистить",
            font=FONT_PRIMARY,
            bg=HH_WHITE,
            fg=HH_GRAY_TEXT,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=3,
            cursor="hand2",
            command=self.clear_log
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # Log text area
        self.log_area = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg=HH_WHITE,
            fg=HH_BLACK,
            bd=1,
            relief=tk.SOLID,
            insertbackground=HH_BLACK,
            selectbackground=HH_RED_LIGHT,
            height=12
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for colored log messages
        self.log_area.tag_config("info", foreground=HH_GRAY_TEXT)
        self.log_area.tag_config("success", foreground="#2E7D32")
        self.log_area.tag_config("error", foreground=HH_RED)
        self.log_area.tag_config("warning", foreground="#F57C00")
        
        # Footer
        footer = tk.Frame(self.root, bg=HH_WHITE, height=35)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        footer_label = tk.Label(
            footer,
            text="hh.ru Automation | Управление процессом поиска и откликов",
            font=("Segoe UI", 8),
            fg=HH_GRAY_TEXT,
            bg=HH_WHITE
        )
        footer_label.pack(pady=8)
    
    def setup_credentials_tab(self):
        """Setup credentials management tab"""
        canvas = tk.Canvas(self.creds_tab, bg=HH_GRAY, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.creds_tab, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=HH_GRAY)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # PostgreSQL Credentials Section
        pg_panel = self.create_panel(scroll_frame, "🐘 PostgreSQL Database", HH_RED)
        pg_panel.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        pg_frame = tk.Frame(pg_panel, bg=HH_WHITE)
        pg_frame.pack(pady=15, padx=20, fill=tk.X)
        
        pg_fields = [
            ("POSTGRES_USER", "admin"),
            ("POSTGRES_PASSWORD", "admin"),
            ("POSTGRES_DB", "n8n_db"),
            ("POSTGRES_NON_ROOT_USER", "n8n_user"),
            ("POSTGRES_NON_ROOT_PASSWORD", "n8n_password")
        ]
        
        self.pg_entries = {}
        for field, default_value in pg_fields:
            row_frame = tk.Frame(pg_frame, bg=HH_WHITE)
            row_frame.pack(fill=tk.X, pady=5)
            
            label = tk.Label(
                row_frame,
                text=field,
                font=FONT_PRIMARY,
                fg=HH_BLACK,
                bg=HH_WHITE,
                width=28,
                anchor="w"
            )
            label.pack(side=tk.LEFT, padx=(0, 10))
            
            entry = tk.Entry(
                row_frame,
                font=FONT_PRIMARY,
                bg=HH_WHITE,
                fg=HH_BLACK,
                bd=1,
                relief=tk.SOLID,
                show="*" if "PASSWORD" in field else ""
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
            entry.insert(0, default_value)
            
            if "PASSWORD" in field:
                toggle_btn = tk.Button(
                    row_frame,
                    text="👁️",
                    font=FONT_SMALL,
                    bg=HH_GRAY,
                    fg=HH_BLACK,
                    bd=1,
                    relief=tk.SOLID,
                    cursor="hand2",
                    command=lambda e=entry: self.toggle_password_visibility(e),
                    width=3
                )
                toggle_btn.pack(side=tk.LEFT)
            
            self.pg_entries[field] = entry
        
        # OpenRouter API Section
        or_panel = self.create_panel(scroll_frame, "🤖 OpenRouter AI", HH_RED)
        or_panel.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        or_frame = tk.Frame(or_panel, bg=HH_WHITE)
        or_frame.pack(pady=15, padx=20, fill=tk.X)
        
        or_key_frame = tk.Frame(or_frame, bg=HH_WHITE)
        or_key_frame.pack(fill=tk.X, pady=5)
        
        or_label = tk.Label(
            or_key_frame,
            text="OPENROUTER_API_KEY",
            font=FONT_PRIMARY,
            fg=HH_BLACK,
            bg=HH_WHITE,
            width=28,
            anchor="w"
        )
        or_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.or_api_entry = tk.Entry(
            or_key_frame,
            font=FONT_PRIMARY,
            bg=HH_WHITE,
            fg=HH_BLACK,
            bd=1,
            relief=tk.SOLID,
            show="*"
        )
        self.or_api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.or_api_entry.insert(0, "")
        
        or_toggle_btn = tk.Button(
            or_key_frame,
            text="👁️",
            font=FONT_SMALL,
            bg=HH_GRAY,
            fg=HH_BLACK,
            bd=1,
            relief=tk.SOLID,
            cursor="hand2",
            command=lambda: self.toggle_password_visibility(self.or_api_entry),
            width=3
        )
        or_toggle_btn.pack(side=tk.LEFT)
        
        info_label = tk.Label(
            or_frame,
            text="💡 API ключ нужен для работы ИИ-автоответов. Получите на https://openrouter.ai/keys",
            font=FONT_SMALL,
            fg=HH_GRAY_TEXT,
            bg=HH_WHITE,
            wraplength=500,
            justify=tk.LEFT
        )
        info_label.pack(pady=(10, 0), anchor="w")
        
        # API Key Status
        self.api_status_label = tk.Label(
            or_frame,
            text="⚪ API ключ не настроен",
            font=FONT_SMALL,
            fg=HH_RED,
            bg=HH_WHITE
        )
        self.api_status_label.pack(pady=(5, 0), anchor="w")
        
        # Save button
        btn_frame = tk.Frame(scroll_frame, bg=HH_GRAY)
        btn_frame.pack(pady=20, padx=10)
        
        save_btn = tk.Button(
            btn_frame,
            text="💾 Сохранить учетные данные",
            font=FONT_BOLD,
            bg=HH_RED,
            fg=HH_WHITE,
            bd=0,
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.save_all_credentials
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(
            btn_frame,
            text="🔄 Сбросить",
            font=FONT_PRIMARY,
            bg=HH_GRAY_DARK,
            fg=HH_BLACK,
            bd=1,
            relief=tk.SOLID,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.reset_default_credentials
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
    
    def create_status_card(self, parent, title, status, status_color):
        """Create a status card"""
        card = tk.Frame(parent, bg=HH_WHITE, bd=1, relief=tk.SOLID, highlightbackground=HH_BORDER, highlightthickness=1)
        
        title_label = tk.Label(
            card,
            text=title,
            font=FONT_BOLD,
            fg=HH_BLACK,
            bg=HH_WHITE
        )
        title_label.pack(pady=(12, 5))
        
        status_label = tk.Label(
            card,
            text=status,
            font=FONT_PRIMARY,
            fg=status_color,
            bg=HH_WHITE
        )
        status_label.pack(pady=(0, 12))
        
        card.status_label = status_label
        return card
    
    def create_panel(self, parent, title, color):
        """Create a styled panel"""
        panel = tk.Frame(parent, bg=HH_WHITE, bd=1, relief=tk.SOLID)
        
        accent = tk.Frame(panel, bg=color, height=3)
        accent.pack(fill=tk.X)
        
        title_label = tk.Label(
            panel,
            text=title,
            font=FONT_BOLD,
            fg=HH_BLACK,
            bg=HH_WHITE,
        )
        title_label.pack(anchor="w", padx=15, pady=(12, 8))
        
        return panel
    
    def toggle_password_visibility(self, entry_widget):
        """Toggle password visibility"""
        if entry_widget.cget('show') == '*':
            entry_widget.config(show='')
        else:
            entry_widget.config(show='*')
    
    def log(self, message, level="info"):
        """Enhanced logging with colors"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        self.log_area.insert(tk.END, f"{formatted_msg}\n", level)
        self.log_area.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log area"""
        self.log_area.delete(1.0, tk.END)
        self.log("Журнал очищен", "info")
    
    def update_status_cards(self):
        """Update status cards"""
        if self.n8n_running:
            self.n8n_card.status_label.config(text="● Запущен", fg="#2E7D32")
        else:
            self.n8n_card.status_label.config(text="● Остановлен", fg=HH_GRAY_TEXT)
        
        if self.reply_running:
            self.reply_card.status_label.config(text="● Запущен", fg="#2E7D32")
            self.btn_reply.config(text="⏹️ Остановить\nавтоответы", bg=HH_GRAY_TEXT)
        else:
            self.reply_card.status_label.config(text="● Остановлен", fg=HH_GRAY_TEXT)
            self.btn_reply.config(text="💬 Автоответы\nработодателям", bg=HH_BLACK)
    
    def load_all_credentials(self):
        """Load all credentials from .env file"""
        env_file = ".env"
        
        defaults = {
            "POSTGRES_USER": "admin",
            "POSTGRES_PASSWORD": "admin",
            "POSTGRES_DB": "n8n_db",
            "POSTGRES_NON_ROOT_USER": "n8n_user",
            "POSTGRES_NON_ROOT_PASSWORD": "n8n_password"
        }
        
        # Set defaults first
        for field, default_value in defaults.items():
            if field in self.pg_entries:
                self.pg_entries[field].delete(0, tk.END)
                self.pg_entries[field].insert(0, default_value)
        
        # Load from .env if exists
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Load PostgreSQL credentials
                for field in self.pg_entries.keys():
                    for line in content.splitlines():
                        if line.startswith(f"{field}="):
                            value = line.split("=", 1)[1].strip()
                            self.pg_entries[field].delete(0, tk.END)
                            self.pg_entries[field].insert(0, value)
                            break
                
                # Load OpenRouter API key
                for line in content.splitlines():
                    if line.startswith("OPENROUTER_API_KEY="):
                        value = line.split("=", 1)[1].strip()
                        if self.or_api_entry:
                            self.or_api_entry.delete(0, tk.END)
                            self.or_api_entry.insert(0, value)
                            self.api_key = value
                        break
            
            self.log("✅ Учетные данные загружены из .env", "success")
        else:
            self.log("📝 Файл .env не найден. Создан новый файл с значениями по умолчанию.", "info")
            self.save_all_credentials()
        
        # Update API status indicator
        self.update_api_status()
    
    def update_api_status(self):
        """Update API key status indicator"""
        if hasattr(self, 'api_status_label'):
            if self.api_key:
                self.api_status_label.config(
                    text="✅ API ключ настроен",
                    fg="#2E7D32"
                )
            else:
                self.api_status_label.config(
                    text="❌ API ключ не настроен",
                    fg=HH_RED
                )
    
    def save_all_credentials(self):
        """Save all credentials to .env file"""
        env_file = ".env"
        
        content_lines = []
        
        # Add PostgreSQL credentials
        for field, entry in self.pg_entries.items():
            value = entry.get().strip()
            content_lines.append(f"{field}={value}")
        
        # Add OpenRouter API key
        if self.or_api_entry:
            or_api_key = self.or_api_entry.get().strip()
            content_lines.append(f"OPENROUTER_API_KEY={or_api_key}")
            self.api_key = or_api_key
            self.update_api_status()
        
        # Preserve existing token if any
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("N8N_RUNNERS_AUTH_TOKEN="):
                        content_lines.append(line.strip())
                        break
        
        content_lines.append("")
        
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))
        
        self.log("✅ Учетные данные сохранены в .env файл", "success")
        
        if self.api_key:
            self.log("✅ OpenRouter API ключ настроен", "success")
        else:
            self.log("⚠️ OpenRouter API ключ не настроен. Автоответчик не будет работать.", "warning")
    
    def reset_default_credentials(self):
        """Reset to default credentials"""
        defaults = {
            "POSTGRES_USER": "admin",
            "POSTGRES_PASSWORD": "admin",
            "POSTGRES_DB": "n8n_db",
            "POSTGRES_NON_ROOT_USER": "n8n_user",
            "POSTGRES_NON_ROOT_PASSWORD": "n8n_password"
        }
        
        for field, entry in self.pg_entries.items():
            if field in defaults:
                entry.delete(0, tk.END)
                entry.insert(0, defaults[field])
        
        if self.or_api_entry:
            self.or_api_entry.delete(0, tk.END)
            self.api_key = ""
            self.update_api_status()
        
        self.log("🔄 Учетные данные сброшены к значениям по умолчанию", "info")
        self.log("⚠️ Не забудьте ввести OpenRouter API ключ для работы автоответчика", "warning")
    
    def ensure_n8n_token(self):
        """Ensure N8N_RUNNERS_AUTH_TOKEN exists in .env"""
        env_file = ".env"
        
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "N8N_RUNNERS_AUTH_TOKEN=" in content:
                    return
        
        token_secret = secrets.token_hex(32)
        
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f"\nN8N_RUNNERS_AUTH_TOKEN={token_secret}\n")
        
        self.log(f"🔑 Сгенерирован N8N_RUNNERS_AUTH_TOKEN", "success")
    
    def get_n8n_container_name(self):
        """Get the actual n8n container name"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=n8n", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            names = result.stdout.strip().split('\n')
            for name in names:
                if 'n8n' in name.lower():
                    return name
        except:
            pass
        return None
    
    def toggle_n8n(self):
        """Toggle n8n server on/off"""
        if self.n8n_running:
            self.stop_n8n()
        else:
            self.start_n8n()
    
    def start_n8n(self):
        """Start n8n server"""
        if self.n8n_running:
            self.log("⚠️ n8n уже запущен", "warning")
            return
        
        def run_server():
            self.n8n_running = True
            self.root.after(0, lambda: self.btn_search.config(text="⏹️ Остановить\nпоиск и отклики", bg=HH_GRAY_TEXT))
            self.root.after(0, self.update_status_cards)
            
            try:
                docker_check = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if docker_check.returncode != 0:
                    self.log("❌ Docker не запущен!", "error")
                    self.n8n_running = False
                    self.root.after(0, lambda: self.btn_search.config(text="🔍 Поиск работы\nи отклики", bg=HH_RED))
                    self.root.after(0, self.update_status_cards)
                    return
                
                if not os.path.exists("hh_cookies.json"):
                    self.log("⚠️ Файл сессии не найден! Запуск авторизации...", "warning")
                    subprocess.run([sys.executable, "scripts/capture_cookies.py"], check=True)
                    self.log("✅ Авторизация завершена", "success")
                
                self.log("🚀 Запуск контейнеров n8n и Postgres...", "info")
                subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, timeout=30)
                
                self.log("⏳ Ожидание запуска n8n...", "info")
                time.sleep(10)
                
                container_name = self.get_n8n_container_name()
                if container_name:
                    if os.path.exists("n8n_credentials.json"):
                        subprocess.run(
                            ["docker", "cp", "n8n_credentials.json", f"{container_name}:/tmp/n8n_credentials.json"],
                            capture_output=True
                        )
                        subprocess.run(
                            ["docker", "exec", container_name, "n8n", "import:credentials", 
                             "--input=/tmp/n8n_credentials.json", "--yes"],
                            capture_output=True
                        )
                    
                    if os.path.exists("hh-ru-n8n-workflow.json"):
                        subprocess.run(
                            ["docker", "cp", "hh-ru-n8n-workflow.json", f"{container_name}:/tmp/hh-workflow.json"],
                            capture_output=True
                        )
                        subprocess.run(
                            ["docker", "exec", container_name, "n8n", "import:workflow", 
                             "--input=/tmp/hh-workflow.json", "--yes"],
                            capture_output=True
                        )
                
                self.log("✅ n8n сервер запущен!", "success")
                self.log("🌐 Панель управления: http://localhost:5678", "info")
                
            except Exception as e:
                self.log(f"❌ Ошибка: {e}", "error")
                self.n8n_running = False
                self.root.after(0, lambda: self.btn_search.config(text="🔍 Поиск работы\nи отклики", bg=HH_RED))
                self.root.after(0, self.update_status_cards)
        
        threading.Thread(target=run_server, daemon=True).start()
    
    def stop_n8n(self):
        """Stop n8n server"""
        if not self.n8n_running:
            return
        
        self.log("🛑 Остановка n8n сервера...", "info")
        
        try:
            subprocess.run(["docker", "compose", "down"], capture_output=True, timeout=30)
            self.log("✅ n8n сервер остановлен", "success")
        except Exception as e:
            self.log(f"❌ Ошибка: {e}", "error")
        
        self.n8n_running = False
        self.btn_search.config(text="🔍 Поиск работы\nи отклики", bg=HH_RED)
        self.update_status_cards()
    
    def toggle_reply(self):
        """Toggle auto-reply script on/off"""
        if self.reply_running:
            self.stop_reply_script()
        else:
            self.start_reply_script()
    
    def start_reply_script(self):
        """Start auto-reply script"""
        if self.reply_running:
            self.log("⚠️ Автоответчик уже запущен", "warning")
            return
        
        # Check if API key is set
        if not self.api_key:
            self.log("❌ Невозможно запустить автоответчик!", "error")
            self.log("🔑 OpenRouter API ключ не настроен", "error")
            self.log("💡 Перейдите на вкладку 'Учетные данные' и введите API ключ", "info")
            messagebox.showerror(
                "API Key Required", 
                "Для работы автоответчика необходим OpenRouter API ключ!\n\n"
                "1. Получите ключ на https://openrouter.ai/keys\n"
                "2. Перейдите на вкладку 'Учетные данные'\n"
                "3. Введите ключ в поле OPENROUTER_API_KEY\n"
                "4. Нажмите 'Сохранить учетные данные'\n"
                "5. Запустите автоответчик снова"
            )
            return
        
        script_path = os.path.join("scripts", "answer_message.py")
        
        if not os.path.exists(script_path):
            self.log(f"❌ Скрипт '{script_path}' не найден!", "error")
            messagebox.showerror("Ошибка", f"Файл {script_path} не найден.")
            return
        
        def run_reply():
            self.reply_running = True
            self.root.after(0, self.update_status_cards)
            
            env = os.environ.copy()
            env["OPENROUTER_API_KEY"] = self.api_key
            
            try:
                self.log("🤖 Запуск автоответчика...", "info")
                self.reply_process = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env
                )
                
                for line in iter(self.reply_process.stdout.readline, ''):
                    if not self.reply_running:
                        break
                    if line.strip():
                        self.root.after(0, lambda l=line.strip(): self.log(l, "info"))
                
                self.reply_process.stdout.close()
                self.reply_process.wait()
                
            except Exception as e:
                self.log(f"❌ Ошибка: {e}", "error")
            finally:
                self.reply_running = False
                self.root.after(0, self.update_status_cards)
        
        threading.Thread(target=run_reply, daemon=True).start()
    
    def stop_reply_script(self):
        """Stop auto-reply script"""
        if self.reply_process and self.reply_running:
            self.log("⏹️ Остановка автоответчика...", "info")
            self.reply_running = False
            try:
                self.reply_process.terminate()
                self.reply_process.wait(timeout=5)
                self.log("✅ Автоответчик остановлен", "success")
            except subprocess.TimeoutExpired:
                self.reply_process.kill()
                self.log("⚠️ Автоответчик принудительно остановлен", "warning")
            except Exception as e:
                self.log(f"❌ Ошибка: {e}", "error")
            
            self.root.after(0, self.update_status_cards)
    
    def stop_all_processes(self):
        """Stop all running processes"""
        self.log("🛑 Остановка всех процессов...", "info")
        
        if self.reply_running:
            self.stop_reply_script()
        
        if self.n8n_running:
            self.stop_n8n()
        
        self.log("✅ Все процессы остановлены", "success")
    
    def on_closing(self):
        """Cleanup all resources before closing"""
        if self.cleanup_done:
            self.root.destroy()
            return
        
        if messagebox.askokcancel("Выход", "Закрыть приложение и остановить все процессы?"):
            self.cleanup_done = True
            self.stop_all_processes()
            self.root.after(500, self.root.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    app = HHAutomationApp(root)
    root.mainloop()