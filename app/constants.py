from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE = APP_DIR / "assets" / "schedule.jpg"
STATE_FILE = APP_DIR / "widgets.json"
PLANS_FILE = APP_DIR / "plans.json"
COURSES_FILE = APP_DIR / "courses.json"
SETTINGS_FILE = APP_DIR / "settings.json"
IMAGE_FILTER = "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*)"
