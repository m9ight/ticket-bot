# 🤖 Discord Moderation Bot

A fully-featured Discord bot built with **disnake** — slash commands, beautiful embeds, moderation, ticket system, welcome messages, and event logging.

---

## ✨ Features

| Module | Commands / Events |
|---|---|
| 🛡️ **Moderation** | `/ban`, `/unban`, `/kick`, `/mute`, `/unmute`, `/clear`, `/slowmode`, `/lock`, `/unlock` |
| 🎫 **Tickets** | Panel with button UI, `/ticket setup/add/remove`, auto-category, support role |
| 👋 **Welcome** | Join/leave embeds, `/welcome setchannel/setleave/setmessage/setautorole/test` |
| 📋 **Logging** | Message delete/edit, member join/leave/ban/unban, roles, nickname, voice, channels |
| ℹ️ **Info** | `/help`, `/userinfo`, `/serverinfo`, `/avatar`, `/roleinfo`, `/botinfo`, `/setup` |

---

## 🚀 Quick Start

### 1. Clone / download the project

```bash
git clone https://github.com/m9ight/ticket-bot.git
cd ticket-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the bot

```bash
cp .env.example .env
# Open .env and paste your BOT_TOKEN
```

### 4. Create your Discord application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → give it a name
3. Go to **Bot** tab → **Add Bot**
4. Copy the token and paste it in `.env`
5. Under **Privileged Gateway Intents** enable all three:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Administrator` (or pick individually)
7. Open the generated URL and invite the bot to your server

### 5. Run the bot

```bash
python bot.py
```

---

## ⚙️ Server Setup (after invite)

Run these slash commands in your server as an administrator:

```
/setup log_channel:#logs welcome_channel:#welcome autorole:@Member
```

Or configure individually:

```
/log setchannel    #channel     — where all events are logged
/welcome setchannel #channel   — welcome messages channel
/welcome setleave   #channel   — leave messages channel
/welcome setautorole @Role     — role given on join
/ticket setup #channel         — deploys the ticket panel
```

---

## 📁 Project Structure

```
discord_bot/
├── bot.py                  # Entry point
├── requirements.txt
├── .env.example
├── cogs/
│   ├── moderation.py       # Ban, kick, mute, clear, lock…
│   ├── tickets.py          # Ticket panel + button UI
│   ├── welcome.py          # Join/leave messages + autorole
│   ├── logging.py          # Event logging
│   └── info.py             # Help, userinfo, serverinfo…
├── utils/
│   ├── config.py           # Colors, emojis, constants
│   ├── embeds.py           # EmbedBuilder — all embed templates
│   ├── data_manager.py     # JSON persistence (guild config, tickets)
│   └── logger.py           # Colored console + file logging
└── data/
    ├── guild_config.json   # Per-guild settings (auto-created)
    └── tickets.json        # Ticket state (auto-created)
```

---

## 🔧 Mute Duration Format

The `/mute` command uses human-readable durations:

| Input | Meaning |
|---|---|
| `30s` | 30 seconds |
| `10m` | 10 minutes |
| `2h` | 2 hours |
| `1d` | 1 day |
| `1h30m` | 1 hour 30 minutes |

Maximum: **28 days** (Discord timeout limit).

---

## 🎨 Customisation

All colors and emojis are centralized in `utils/config.py`:

```python
class Config:
    COLOR_PRIMARY = 0x5865F2   # Discord Blurple
    COLOR_SUCCESS = 0x57F287   # Green
    COLOR_ERROR   = 0xED4245   # Red
    ...
```

To add more commands, create a new file in `cogs/` and add it to the `COGS` list in `bot.py`.

---

## 📜 Required Bot Permissions

- `Administrator` — or individually:
- `Manage Channels`, `Manage Roles`, `Manage Messages`
- `Ban Members`, `Kick Members`, `Moderate Members`
- `View Audit Log`, `Send Messages`, `Embed Links`
- `Read Message History`, `Attach Files`

## Preview
<img width="511" height="584" alt="image" src="https://github.com/user-attachments/assets/efd9b0e5-03f5-4e6e-9750-d27f36db5d2d" />
<img width="714" height="473" alt="image" src="https://github.com/user-attachments/assets/67b70bd0-16d5-4f30-8ce2-af8d49ae8e2c" />
<img width="722" height="522" alt="image" src="https://github.com/user-attachments/assets/cdb057db-e3c5-4355-9873-5d3cbc5137f1" />
<img width="745" height="607" alt="image" src="https://github.com/user-attachments/assets/b00f3048-d834-404a-b2bd-44c991c05746" />


## Contact
Discord: notmac3
Telegram: m9ight
