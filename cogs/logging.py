import disnake
from disnake.ext import commands
from utils.embeds import EmbedBuilder
from utils.config import Config
from utils.logger import setup_logger
from utils.data_manager import get_config_value, set_guild_config

logger = setup_logger("logging")


class Logging(commands.Cog):
    """📋 Event logging — messages, roles, voice, channels."""

    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @staticmethod
    def _ctx_inter(ctx: commands.Context):
        class PrefixResponse:
            @staticmethod
            async def send_message(embed=None, ephemeral=False):
                await ctx.send(embed=embed)

        class PrefixInter:
            guild = ctx.guild
            channel = ctx.channel
            author = ctx.author
            response = PrefixResponse

        return PrefixInter

    async def _get_log_channel(self, guild: disnake.Guild) -> disnake.TextChannel | None:
        cid = get_config_value(guild.id, "log_channel")
        return guild.get_channel(int(cid)) if cid else None

    # ── Message events ───────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        if not message.guild or message.author.bot:
            return
        ch = await self._get_log_channel(message.guild)
        if not ch:
            return

        content = message.content or "*[No text content]*"
        if len(content) > 1024:
            content = content[:1021] + "..."

        embed = EmbedBuilder.log_event(
            "Message Deleted", Config.COLOR_ERROR,
            [
                ("👤 Author",   f"{message.author.mention} `{message.author}`", True),
                ("📌 Channel",  message.channel.mention,                         True),
                ("🆔 Msg ID",   f"`{message.id}`",                               True),
                ("💬 Content",  f"```{content}```",                              False),
            ]
        )
        if message.attachments:
            embed.add_field(
                name="📎 Attachments",
                value="\n".join(a.url for a in message.attachments),
                inline=False,
            )
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return
        ch = await self._get_log_channel(before.guild)
        if not ch:
            return

        before_c = (before.content or "*empty*")[:512]
        after_c  = (after.content  or "*empty*")[:512]

        embed = EmbedBuilder.log_event(
            "Message Edited", Config.COLOR_WARNING,
            [
                ("👤 Author",   f"{before.author.mention} `{before.author}`", True),
                ("📌 Channel",  before.channel.mention,                        True),
                ("🔗 Jump",     f"[View Message]({after.jump_url})",           True),
                ("📝 Before",   f"```{before_c}```",                          False),
                ("✏️ After",    f"```{after_c}```",                           False),
            ]
        )
        await ch.send(embed=embed)

    # ── Member events ────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        ch = await self._get_log_channel(before.guild)
        if not ch:
            return

        # Nickname change
        if before.nick != after.nick:
            embed = EmbedBuilder.log_event(
                "Nickname Changed", Config.COLOR_INFO,
                [
                    ("👤 Member",       after.mention,                    True),
                    ("📝 Before",       f"`{before.nick or 'None'}`",     True),
                    ("✏️ After",        f"`{after.nick  or 'None'}`",     True),
                ]
            )
            await ch.send(embed=embed)

        # Role changes
        added   = [r for r in after.roles  if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]

        if added or removed:
            fields = [("👤 Member", after.mention, False)]
            if added:
                fields.append(("➕ Roles Added",   " ".join(r.mention for r in added),   False))
            if removed:
                fields.append(("➖ Roles Removed", " ".join(r.mention for r in removed), False))
            embed = EmbedBuilder.log_event("Roles Updated", Config.COLOR_PURPLE, fields)
            await ch.send(embed=embed)

        # Timeout applied / removed
        if before.current_timeout != after.current_timeout:
            if after.current_timeout:
                embed = EmbedBuilder.log_event(
                    "Member Timed Out", Config.COLOR_WARNING,
                    [
                        ("👤 Member",  after.mention,                                           True),
                        ("⏱️ Until",  f"<t:{int(after.current_timeout.timestamp())}:F>",       True),
                    ]
                )
            else:
                embed = EmbedBuilder.log_event(
                    "Timeout Removed", Config.COLOR_SUCCESS,
                    [("👤 Member", after.mention, True)]
                )
            await ch.send(embed=embed)

    # ── Ban / Unban events ───────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.User):
        ch = await self._get_log_channel(guild)
        if not ch:
            return
        # Try to get audit log entry for ban reason
        reason = "Unknown"
        try:
            async for entry in guild.audit_logs(action=disnake.AuditLogAction.ban, limit=5):
                if entry.target.id == user.id:
                    reason = entry.reason or "No reason provided"
                    break
        except Exception:
            pass

        embed = EmbedBuilder.log_event(
            "Member Banned", Config.COLOR_ERROR,
            [
                ("👤 User",     f"{user.mention} `{user}`", True),
                ("🆔 User ID",  f"`{user.id}`",             True),
                ("📝 Reason",   f"```{reason}```",          False),
            ]
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: disnake.Guild, user: disnake.User):
        ch = await self._get_log_channel(guild)
        if not ch:
            return
        embed = EmbedBuilder.log_event(
            "Member Unbanned", Config.COLOR_SUCCESS,
            [
                ("👤 User",    f"{user.mention} `{user}`", True),
                ("🆔 User ID", f"`{user.id}`",             True),
            ]
        )
        await ch.send(embed=embed)

    # ── Voice events ─────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ):
        ch = await self._get_log_channel(member.guild)
        if not ch:
            return

        if before.channel == after.channel:
            # Mute / deafen state changes — skip to reduce spam
            return

        if before.channel is None and after.channel is not None:
            # Joined
            embed = EmbedBuilder.log_event(
                "Voice Joined", Config.COLOR_SUCCESS,
                [
                    ("👤 Member",   member.mention,         True),
                    ("🔊 Channel",  after.channel.mention,  True),
                ]
            )
        elif before.channel is not None and after.channel is None:
            # Left
            embed = EmbedBuilder.log_event(
                "Voice Left", Config.COLOR_ERROR,
                [
                    ("👤 Member",   member.mention,          True),
                    ("🔇 Channel",  before.channel.mention,  True),
                ]
            )
        else:
            # Moved
            embed = EmbedBuilder.log_event(
                "Voice Moved", Config.COLOR_WARNING,
                [
                    ("👤 Member",   member.mention,          True),
                    ("📤 From",     before.channel.mention,  True),
                    ("📥 To",       after.channel.mention,   True),
                ]
            )

        await ch.send(embed=embed)

    # ── Channel events ───────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        ch = await self._get_log_channel(channel.guild)
        if not ch:
            return
        embed = EmbedBuilder.log_event(
            "Channel Created", Config.COLOR_SUCCESS,
            [
                ("📌 Channel",  channel.mention,                        True),
                ("🗂️ Type",    str(channel.type).replace("_", " ").title(), True),
            ]
        )
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        ch = await self._get_log_channel(channel.guild)
        if not ch:
            return
        embed = EmbedBuilder.log_event(
            "Channel Deleted", Config.COLOR_ERROR,
            [
                ("📌 Name",   f"`#{channel.name}`",                     True),
                ("🗂️ Type",  str(channel.type).replace("_", " ").title(), True),
            ]
        )
        await ch.send(embed=embed)

    # ── Role events ──────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        ch = await self._get_log_channel(role.guild)
        if not ch:
            return
        embed = EmbedBuilder.log_event(
            "Role Created", Config.COLOR_SUCCESS,
            [
                ("🎭 Role",   role.mention,  True),
                ("🆔 ID",    f"`{role.id}`", True),
            ]
        )
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        ch = await self._get_log_channel(role.guild)
        if not ch:
            return
        embed = EmbedBuilder.log_event(
            "Role Deleted", Config.COLOR_ERROR,
            [
                ("🎭 Name",  f"`@{role.name}`", True),
                ("🆔 ID",   f"`{role.id}`",     True),
            ]
        )
        await ch.send(embed=embed)

    # ── /log setup ───────────────────────────────────────────────────

    @commands.slash_command(name="log")
    async def log_cmd(self, inter):
        pass

    @log_cmd.sub_command(name="setchannel", description="📋 Set the logging channel")
    @commands.has_permissions(administrator=True)
    async def log_setchannel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Channel to send logs to"),
    ):
        set_guild_config(inter.guild.id, "log_channel", channel.id)
        await inter.response.send_message(
            embed=EmbedBuilder.success("Log Channel Set", f"All events will be logged to {channel.mention}."),
            ephemeral=True,
        )

    @log_cmd.sub_command(name="disable", description="🚫 Disable logging")
    @commands.has_permissions(administrator=True)
    async def log_disable(self, inter: disnake.ApplicationCommandInteraction):
        set_guild_config(inter.guild.id, "log_channel", None)
        await inter.response.send_message(
            embed=EmbedBuilder.warning("Logging Disabled", "Event logging has been disabled."),
            ephemeral=True,
        )


    @commands.group(name="log", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def log_prefix(self, ctx: commands.Context):
        await ctx.send(embed=EmbedBuilder.info("Log Commands", "`log setchannel #channel`, `log disable`"))

    @log_prefix.command(name="setchannel")
    @commands.has_permissions(administrator=True)
    async def log_setchannel_prefix(self, ctx: commands.Context, channel: disnake.TextChannel):
        await self.log_setchannel.callback(self, self._ctx_inter(ctx), channel)

    @log_prefix.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def log_disable_prefix(self, ctx: commands.Context):
        await self.log_disable.callback(self, self._ctx_inter(ctx))


def setup(bot):
    bot.add_cog(Logging(bot))
