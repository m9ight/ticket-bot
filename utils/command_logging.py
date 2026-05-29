import disnake

from utils.config import Config
from utils.data_manager import get_config_value
from utils.embeds import EmbedBuilder


def _format_value(value) -> str:
    if isinstance(value, (disnake.Member, disnake.User, disnake.Role, disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel)):
        return getattr(value, "mention", str(value))
    return str(value)


async def log_command_error(
    guild: disnake.Guild | None,
    author: disnake.Member | disnake.User,
    channel,
    command_name: str,
    error: Exception | str,
    arguments: dict | None = None,
) -> None:
    if not guild:
        return

    log_channel_id = get_config_value(guild.id, "log_channel")
    if not log_channel_id:
        return

    log_channel = guild.get_channel(int(log_channel_id))
    if not log_channel:
        return

    arguments = arguments or {}
    args_text = "\n".join(f"**{name}:** {_format_value(value)}" for name, value in arguments.items() if value is not None)
    embed = EmbedBuilder.log_event(
        "Command Error",
        Config.COLOR_ERROR,
        [
            ("💬 Command", f"`{command_name}`", True),
            ("👤 User", f"{author.mention}\n`{author}`", True),
            ("📌 Channel", getattr(channel, "mention", "`DM`"), True),
            ("🧾 Arguments", args_text[:1024] if args_text else "`None`", False),
            ("⚠️ Error", f"```{str(error)[:1000]}```", False),
        ],
    )
    await log_channel.send(embed=embed)
