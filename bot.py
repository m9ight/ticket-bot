import disnake
from disnake.ext import commands
import json
import os
from utils.config import Config
from utils.command_logging import log_command_error
from utils.embeds import EmbedBuilder
from utils.logger import setup_logger

logger = setup_logger("bot")

PREFIX_USAGES = {
    "ban": "{prefix}ban @member [delete_days] reason",
    "unban": "{prefix}unban user_id reason",
    "kick": "{prefix}kick @member reason",
    "mute": "{prefix}mute @member duration reason",
    "unmute": "{prefix}unmute @member reason",
    "clear": "{prefix}clear amount [@member]",
    "slowmode": "{prefix}slowmode seconds",
    "lock": "{prefix}lock [#channel] reason",
    "unlock": "{prefix}unlock [#channel] reason",
    "ticket setup": "{prefix}ticket setup #panel-channel [@support_role] [category]",
    "ticket open": "{prefix}ticket open reason",
    "ticket close": "{prefix}ticket close reason",
    "ticket add": "{prefix}ticket add @member",
    "ticket remove": "{prefix}ticket remove @member",
    "welcome setchannel": "{prefix}welcome setchannel #channel",
    "welcome setleave": "{prefix}welcome setleave #channel",
    "welcome setmessage": "{prefix}welcome setmessage message",
    "welcome setautorole": "{prefix}welcome setautorole @role",
    "log setchannel": "{prefix}log setchannel #channel",
    "setup": "{prefix}setup [#log_channel] [#welcome_channel] [#leave_channel] [@autorole]",
    "userinfo": "{prefix}userinfo [@member]",
    "avatar": "{prefix}avatar [@member]",
    "roleinfo": "{prefix}roleinfo @role",
}

def get_prefix(bot, message):
    return Config.PREFIX

intents = disnake.Intents.all()

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    test_guilds=None,  # Remove for global commands, or set guild IDs for instant update
)
bot.remove_command("help")

# Load all cogs
COGS = [
    "cogs.moderation",
    "cogs.tickets",
    "cogs.welcome",
    "cogs.logging",
    "cogs.info",
]

for cog in COGS:
    try:
        bot.load_extension(cog)
        logger.info(f"✅ Loaded cog: {cog}")
    except Exception as e:
        logger.error(f"❌ Failed to load cog {cog}: {e}")


@bot.event
async def on_ready():
    logger.info(f"🚀 Bot is online as {bot.user} (ID: {bot.user.id})")
    logger.info(f"📡 Connected to {len(bot.guilds)} guild(s)")
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.watching,
            name=f"{len(bot.guilds)} servers | /help"
        )
    )


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    command_name = ctx.command.qualified_name if ctx.command else ctx.invoked_with
    usage = PREFIX_USAGES.get(command_name)
    if isinstance(error, commands.MissingRequiredArgument) and usage:
        await ctx.send(
            embed=EmbedBuilder.warning(
                "Missing Argument",
                f"Required argument: `{error.param.name}`\nUsage: `{usage.format(prefix=Config.PREFIX)}`",
            ),
            delete_after=10,
        )
    elif isinstance(error, commands.BadArgument) and usage:
        await ctx.send(
            embed=EmbedBuilder.error(
                "Invalid Argument",
                f"Check the argument format.\nUsage: `{usage.format(prefix=Config.PREFIX)}`",
            ),
            delete_after=10,
        )

    await log_command_error(ctx.guild, ctx.author, ctx.channel, f"{Config.PREFIX}{command_name}", error, getattr(ctx, "kwargs", {}))
    logger.error(f"Prefix command error in {command_name}: {error}")


@bot.event
async def on_slash_command_error(inter, error):
    command = getattr(inter, "application_command", None)
    command_name = getattr(command, "qualified_name", getattr(command, "name", "unknown"))
    await log_command_error(inter.guild, inter.author, inter.channel, f"/{command_name}", error, getattr(inter, "filled_options", {}))

    embed = EmbedBuilder.error("Command Error", "Something went wrong while running this command.")
    try:
        if inter.response.is_done():
            await inter.followup.send(embed=embed, ephemeral=True)
        else:
            await inter.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass
    logger.error(f"Slash command error in {command_name}: {error}")


if __name__ == "__main__":
    token = Config.TOKEN
    if not token:
        logger.error("❌ BOT_TOKEN not found in .env file!")
        exit(1)
    bot.run(token)
