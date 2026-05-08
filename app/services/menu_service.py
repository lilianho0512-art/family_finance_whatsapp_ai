GREETING_KEYWORDS = {
    "hi", "hello", "menu", "start", "你好", "菜单", "嗨", "hey", "开始",
}

WELCOME_TEXT = (
    "你好，我是你的家庭财务 AI 助理 👋\n\n"
    "我可以帮你记录：\n"
    "A. 家庭开销\n"
    "B. 家庭储蓄\n"
    "C. 家庭收入\n"
    "D. 查看本月总结\n"
    "E. 查看今天开销\n"
    "F. 查看储蓄率\n"
    "G. 导出月报\n"
    "H. 上传收据 / 截图 / PDF\n\n"
    "你可以这样发我：\n\n"
    "1. 今天 Tesco RM88\n"
    "2. 今天存钱 RM500\n"
    "3. 工资 RM3800\n"
    "4. 这个月花了多少？\n"
    "5. 这个月储蓄多少？\n"
    "6. Baby 类别花多少？\n"
    "7. 上传收据照片\n"
    "8. 撤销 / 删除 #5（删除最近一笔 / 指定 ID）\n"
    "9. 余额（查各账户当前计算余额）\n"
    "10. 设置 Maybank 5000（记录今天 Maybank 余额快照）\n"
    "11. 加账户 OCBC（注册新账户）\n\n"
    "请回复 A/B/C/D，或直接发送账单资料。"
)


def is_greeting(text: str) -> bool:
    if not text:
        return False
    # Strip leading "/" so Telegram-style commands like "/start" / "/menu" / "/hi" match.
    return text.strip().lower().lstrip("/") in GREETING_KEYWORDS


def get_welcome_text() -> str:
    return WELCOME_TEXT
