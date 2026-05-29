import disnake
from disnake.ext import commands
import re
from datetime import timedelta
from utils.command_logging import log_command_error
from utils.embeds import EmbedBuilder
from utils.config import Config
from utils.logger import setup_logger
from utils.data_manager import get_config_value

logger = setup_logger("moderation")

# ── Duration parser ──────────────────────────────────────────────────────────

DURATION_RE = re.compile(r"(\d+)([smhd])")
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

def parse_duration(text: str) -> int | None:
    """Return total seconds or None if invalid. E.g. '1h30m' -> 5400"""
    matches = DURATION_RE.findall(text.lower())
    if not matches:
        return None
    return sum(int(v) * UNITS[u] for v, u in matches)


async def warn_missing_reason(ctx: commands.Context, usage: str) -> None:
    await ctx.send(
        embed=EmbedBuilder.warning(
            "Reason Required",
            f"Prefix commands cannot open Discord modals. Add a reason to the command.\nUsage: `{usage}`"
        ),
        delete_after=10,
    )
    await log_command_error(ctx.guild, ctx.author, ctx.channel, f"{Config.PREFIX}{ctx.command.qualified_name}", "Missing reason", getattr(ctx, "kwargs", {}))


def parse_optional_delete_days(payload: str | None) -> tuple[int, str | None]:
    if not payload:
        return 0, None
    parts = payload.split(maxsplit=1)
    if parts[0].isdigit():
        return min(max(int(parts[0]), 0), 7), parts[1] if len(parts) > 1 else None
    return 0, payload


def parse_optional_channel(ctx: commands.Context, payload: str | None) -> tuple[disnake.TextChannel | None, str | None]:
    if not payload:
        return None, None
    if ctx.message.channel_mentions:
        channel = ctx.message.channel_mentions[0]
        reason = payload.replace(channel.mention, "", 1).strip() or None
        return channel, reason
    return None, payload


# ── Cog ─────────────────────────────────────────────────────────────────────

class Moderation(commands.Cog):
    """🛡️ Moderation commands: ban, kick, mute, unmute, warn, clear."""

    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @staticmethod
    def _ctx_inter(ctx: commands.Context):
        class PrefixResponse:
            @staticmethod
            async def send_message(embed=None, ephemeral=False):
                await ctx.send(embed=embed)

            @staticmethod
            async def defer(ephemeral=False):
                return None

        class PrefixFollowup:
            @staticmethod
            async def send(embed=None, ephemeral=False):
                await ctx.send(embed=embed)

        class PrefixInter:
            guild = ctx.guild
            channel = ctx.channel
            author = ctx.author
            response = PrefixResponse
            followup = PrefixFollowup

        return PrefixInter

    async def _log(self, guild: disnake.Guild, embed: disnake.Embed):
        log_channel_id = get_config_value(guild.id, "log_channel")
        if log_channel_id:
            ch = guild.get_channel(int(log_channel_id))
            if ch:
                await ch.send(embed=embed)

    # ── /ban ────────────────────────────────────────────────────────

    @commands.slash_command(name="ban", description="🔨 Ban a member from the server")
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Member to ban"),
        reason: str = commands.Param(default="No reason provided", description="Reason for ban"),
        delete_days: int = commands.Param(default=0, description="Days of messages to delete (0-7)", ge=0, le=7),
    ):
        if member.top_role >= inter.author.top_role:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Permission Denied", "You cannot ban someone with an equal or higher role."),
                ephemeral=True,
            )
            return

        try:
            # DM the user before banning
            try:
                await member.send(embed=EmbedBuilder.warning(
                    f"You were banned from {inter.guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {inter.author}"
                ))
            except Exception:
                pass

            await inter.guild.ban(member, reason=f"{inter.author}: {reason}", delete_message_days=delete_days)

            embed = EmbedBuilder.mod_action(
                "Member Banned", Config.EMOJI_BAN, Config.COLOR_ERROR,
                inter.author, member, reason,
                [("🗑️ Messages Deleted", f"`{delete_days} day(s)`", True)]
            )
            await inter.response.send_message(embed=embed)
            await self._log(inter.guild, embed)

        except disnake.Forbidden:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Missing Permissions", "I don't have permission to ban this member."),
                ephemeral=True,
            )

    # ── /unban ──────────────────────────────────────────────────────

    @commands.slash_command(name="unban", description="🔓 Unban a user by ID or tag")
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user_id: str = commands.Param(description="User ID to unban"),
        reason: str = commands.Param(default="No reason provided", description="Reason for unban"),
    ):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await inter.guild.unban(user, reason=f"{inter.author}: {reason}")

            embed = EmbedBuilder.success(
                "Member Unbanned",
                f"**User:** {user} (`{user.id}`)\n**Moderator:** {inter.author.mention}\n**Reason:** {reason}"
            )
            await inter.response.send_message(embed=embed)
            await self._log(inter.guild, embed)
        except (ValueError, disnake.NotFound):
            await inter.response.send_message(
                embed=EmbedBuilder.error("User Not Found", "Could not find a banned user with that ID."),
                ephemeral=True,
            )

    # ── /kick ───────────────────────────────────────────────────────

    @commands.slash_command(name="kick", description="👢 Kick a member from the server")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Member to kick"),
        reason: str = commands.Param(default="No reason provided", description="Reason for kick"),
    ):
        if member.top_role >= inter.author.top_role:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Permission Denied", "You cannot kick someone with an equal or higher role."),
                ephemeral=True,
            )
            return

        try:
            try:
                await member.send(embed=EmbedBuilder.warning(
                    f"You were kicked from {inter.guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {inter.author}"
                ))
            except Exception:
                pass

            await member.kick(reason=f"{inter.author}: {reason}")

            embed = EmbedBuilder.mod_action(
                "Member Kicked", Config.EMOJI_KICK, Config.COLOR_WARNING,
                inter.author, member, reason
            )
            await inter.response.send_message(embed=embed)
            await self._log(inter.guild, embed)

        except disnake.Forbidden:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Missing Permissions", "I don't have permission to kick this member."),
                ephemeral=True,
            )

    # ── /mute ───────────────────────────────────────────────────────

    @commands.slash_command(name="mute", description="🔇 Timeout (mute) a member")
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Member to mute"),
        duration: str = commands.Param(description="Duration: e.g. 10m, 1h, 2d (max 28d)"),
        reason: str = commands.Param(default="No reason provided", description="Reason for mute"),
    ):
        seconds = parse_duration(duration)
        if not seconds:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Invalid Duration", "Use format: `10s`, `5m`, `2h`, `1d` or combinations like `1h30m`"),
                ephemeral=True,
            )
            return

        if seconds > 60 * 60 * 24 * 28:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Duration Too Long", "Maximum timeout duration is **28 days**."),
                ephemeral=True,
            )
            return

        if member.top_role >= inter.author.top_role:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Permission Denied", "You cannot mute someone with an equal or higher role."),
                ephemeral=True,
            )
            return

        try:
            until = disnake.utils.utcnow() + timedelta(seconds=seconds)
            await member.timeout(duration=timedelta(seconds=seconds), reason=f"{inter.author}: {reason}")

            embed = EmbedBuilder.mod_action(
                "Member Muted", Config.EMOJI_MUTE, Config.COLOR_WARNING,
                inter.author, member, reason,
                [
                    (f"{Config.EMOJI_CLOCK} Duration", f"`{duration}`", True),
                    ("⏱️ Expires", f"<t:{int(until.timestamp())}:R>", True),
                ]
            )
            await inter.response.send_message(embed=embed)
            await self._log(inter.guild, embed)

        except disnake.Forbidden:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Missing Permissions", "I don't have permission to timeout this member."),
                ephemeral=True,
            )

    # ── /unmute ─────────────────────────────────────────────────────

    @commands.slash_command(name="unmute", description="🔊 Remove timeout from a member")
    @commands.has_permissions(moderate_members=True)
    async def unmute(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Member to unmute"),
        reason: str = commands.Param(default="No reason provided", description="Reason"),
    ):
        if not member.current_timeout:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Not Muted", f"{member.mention} is not currently muted."),
                ephemeral=True,
            )
            return

        await member.timeout(duration=None, reason=f"{inter.author}: {reason}")

        embed = EmbedBuilder.mod_action(
            "Member Unmuted", Config.EMOJI_UNMUTE, Config.COLOR_SUCCESS,
            inter.author, member, reason
        )
        await inter.response.send_message(embed=embed)
        await self._log(inter.guild, embed)

    # ── /clear ──────────────────────────────────────────────────────

    @commands.slash_command(name="clear", description="🗑️ Delete messages in bulk")
    @commands.has_permissions(manage_messages=True)
    async def clear(
        self,
        inter: disnake.ApplicationCommandInteraction,
        amount: int = commands.Param(description="Number of messages to delete (1-100)", ge=1, le=100),
        member: disnake.Member = commands.Param(default=None, description="Delete only messages from this member"),
    ):
        await inter.response.defer(ephemeral=True)

        def check(msg):
            if member:
                return msg.author == member
            return True

        deleted = await inter.channel.purge(limit=amount, check=check)

        embed = EmbedBuilder.success(
            "Messages Cleared",
            f"🗑️ Deleted **{len(deleted)}** message(s)"
            + (f" from {member.mention}" if member else "")
            + f" in {inter.channel.mention}"
        )
        await inter.followup.send(embed=embed, ephemeral=True)
        await self._log(inter.guild, EmbedBuilder.log_event(
            "Bulk Message Delete", Config.COLOR_WARNING,
            [
                ("📌 Channel", inter.channel.mention, True),
                ("🛡️ Moderator", inter.author.mention, True),
                ("🗑️ Count", f"`{len(deleted)}`", True),
            ]
        ))

    # ── /slowmode ───────────────────────────────────────────────────

    @commands.slash_command(name="slowmode", description="⏱️ Set channel slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        inter: disnake.ApplicationCommandInteraction,
        seconds: int = commands.Param(description="Slowmode in seconds (0 to disable)", ge=0, le=21600),
    ):
        await inter.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            embed = EmbedBuilder.success("Slowmode Disabled", f"Slowmode has been disabled in {inter.channel.mention}.")
        else:
            embed = EmbedBuilder.success("Slowmode Set", f"Slowmode set to **{seconds}s** in {inter.channel.mention}.")
        await inter.response.send_message(embed=embed)
        await self._log(inter.guild, EmbedBuilder.log_event(
            "Slowmode Updated", Config.COLOR_WARNING,
            [
                ("📌 Channel", inter.channel.mention, True),
                ("🛡️ Moderator", inter.author.mention, True),
                ("⏱️ Seconds", f"`{seconds}`", True),
            ]
        ))

    # ── /lock / /unlock ─────────────────────────────────────────────

    @commands.slash_command(name="lock", description="🔒 Lock a channel")
    @commands.has_permissions(manage_channels=True)
    async def lock(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(default=None, description="Channel to lock"),
        reason: str = commands.Param(default="No reason provided"),
    ):
        ch = channel or inter.channel
        overwrite = ch.overwrites_for(inter.guild.default_role)
        overwrite.send_messages = False
        await ch.set_permissions(inter.guild.default_role, overwrite=overwrite, reason=reason)

        embed = EmbedBuilder.warning("Channel Locked", f"{Config.EMOJI_LOCK} {ch.mention} has been **locked**.\n**Reason:** {reason}")
        await inter.response.send_message(embed=embed)
        await self._log(inter.guild, EmbedBuilder.log_event(
            "Channel Locked", Config.COLOR_WARNING,
            [
                ("📌 Channel", ch.mention, True),
                ("🛡️ Moderator", inter.author.mention, True),
                ("📝 Reason", f"```{reason}```", False),
            ]
        ))

    @commands.slash_command(name="unlock", description="🔓 Unlock a channel")
    @commands.has_permissions(manage_channels=True)
    async def unlock(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(default=None, description="Channel to unlock"),
        reason: str = commands.Param(default="No reason provided"),
    ):
        ch = channel or inter.channel
        overwrite = ch.overwrites_for(inter.guild.default_role)
        overwrite.send_messages = None
        await ch.set_permissions(inter.guild.default_role, overwrite=overwrite, reason=reason)

        embed = EmbedBuilder.success("Channel Unlocked", f"{Config.EMOJI_UNLOCK} {ch.mention} has been **unlocked**.\n**Reason:** {reason}")
        await inter.response.send_message(embed=embed)
        await self._log(inter.guild, EmbedBuilder.log_event(
            "Channel Unlocked", Config.COLOR_SUCCESS,
            [
                ("📌 Channel", ch.mention, True),
                ("🛡️ Moderator", inter.author.mention, True),
                ("📝 Reason", f"```{reason}```", False),
            ]
        ))

    # ── Error handling ──────────────────────────────────────────────

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_prefix(self, ctx: commands.Context, member: disnake.Member, *, payload: str = None):
        delete_days, reason = parse_optional_delete_days(payload)
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}ban @member [delete_days] reason")
            return
        await self.ban.callback(self, self._ctx_inter(ctx), member, reason, delete_days)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban_prefix(self, ctx: commands.Context, user_id: str, *, reason: str = None):
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}unban user_id reason")
            return
        await self.unban.callback(self, self._ctx_inter(ctx), user_id, reason)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx: commands.Context, member: disnake.Member, *, reason: str = None):
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}kick @member reason")
            return
        await self.kick.callback(self, self._ctx_inter(ctx), member, reason)

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx: commands.Context, member: disnake.Member, duration: str, *, reason: str = None):
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}mute @member duration reason")
            return
        await self.mute.callback(self, self._ctx_inter(ctx), member, duration, reason)

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute_prefix(self, ctx: commands.Context, member: disnake.Member, *, reason: str = None):
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}unmute @member reason")
            return
        await self.unmute.callback(self, self._ctx_inter(ctx), member, reason)

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear_prefix(self, ctx: commands.Context, amount: int, member: disnake.Member = None):
        await self.clear.callback(self, self._ctx_inter(ctx), amount, member)

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_prefix(self, ctx: commands.Context, seconds: int):
        await self.slowmode.callback(self, self._ctx_inter(ctx), seconds)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock_prefix(self, ctx: commands.Context, *, payload: str = None):
        channel, reason = parse_optional_channel(ctx, payload)
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}lock [#channel] reason")
            return
        await self.lock.callback(self, self._ctx_inter(ctx), channel, reason)

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock_prefix(self, ctx: commands.Context, *, payload: str = None):
        channel, reason = parse_optional_channel(ctx, payload)
        if not reason:
            await warn_missing_reason(ctx, f"{Config.PREFIX}unlock [#channel] reason")
            return
        await self.unlock.callback(self, self._ctx_inter(ctx), channel, reason)

    @ban.error
    @kick.error
    @mute.error
    @unmute.error
    @clear.error
    @lock.error
    @unlock.error
    async def mod_error(self, inter: disnake.ApplicationCommandInteraction, error):
        command = getattr(inter, "application_command", None)
        command_name = getattr(command, "qualified_name", getattr(command, "name", "unknown"))
        await log_command_error(inter.guild, inter.author, inter.channel, f"/{command_name}", error, getattr(inter, "filled_options", {}))
        if isinstance(error, commands.MissingPermissions):
            await inter.response.send_message(
                embed=EmbedBuilder.error("Missing Permissions", "You don't have permission to use this command."),
                ephemeral=True,
            )
        else:
            logger.error(f"Moderation error: {error}")


def setup(bot):
    bot.add_cog(Moderation(bot))
