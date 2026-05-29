import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot settings
    TOKEN: str = os.getenv("BOT_TOKEN", "")
    PREFIX: str = os.getenv("PREFIX", "!")
    
    # Colors (hex)
    COLOR_PRIMARY   = 0x5865F2   # Discord Blurple
    COLOR_SUCCESS   = 0x57F287   # Green
    COLOR_WARNING   = 0xFEE75C   # Yellow
    COLOR_ERROR     = 0xED4245   # Red
    COLOR_INFO      = 0x00B0F4   # Cyan
    COLOR_DARK      = 0x2B2D31   # Dark gray
    COLOR_PURPLE    = 0x9B59B6   # Purple
    COLOR_ORANGE    = 0xE67E22   # Orange
    COLOR_TICKET    = 0x3498DB   # Blue for tickets
    
    # Emojis
    EMOJI_SUCCESS   = "✅"
    EMOJI_ERROR     = "❌"
    EMOJI_WARNING   = "⚠️"
    EMOJI_INFO      = "ℹ️"
    EMOJI_BAN       = "🔨"
    EMOJI_KICK      = "👢"
    EMOJI_MUTE      = "🔇"
    EMOJI_UNMUTE    = "🔊"
    EMOJI_TICKET    = "🎫"
    EMOJI_LOG       = "📋"
    EMOJI_WELCOME   = "👋"
    EMOJI_SHIELD    = "🛡️"
    EMOJI_CLOCK     = "⏰"
    EMOJI_CROWN     = "👑"
    EMOJI_STAR      = "⭐"
    EMOJI_LOCK      = "🔒"
    EMOJI_UNLOCK    = "🔓"
    EMOJI_ARROW     = "➜"
    
    # Data paths
    DATA_DIR        = "data"
    TICKETS_FILE    = "data/tickets.json"
    CONFIG_FILE     = "data/guild_config.json"
