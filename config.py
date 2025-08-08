# config.py
import os

# Lấy token từ biến môi trường (Render hoặc .env khi chạy local)
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("⚠️ Không tìm thấy DISCORD_TOKEN trong biến môi trường!")
