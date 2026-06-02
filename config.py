import os

# Используем os.getenv, чтобы Railway вставил туда свои значения из Variables
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
GROUP_ID: int = int(os.getenv("GROUP_ID", 0))
ANTISPAM_DELAY: int = int(os.getenv("ANTISPAM_DELAY", 3))

# Для проверки (убери это потом, чтобы токен не светился в логах)
print(f"DEBUG: Token loaded: {'Yes' if BOT_TOKEN else 'No'}")
