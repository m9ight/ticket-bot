import disnake
from disnake.ext import commands
from datetime import datetime
from utils.embeds import EmbedBuilder
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger("info")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _status_emoji(status: disnake.Status) -> str:
    return {
        disnake.Status.online:    "🟢 Online",
        disnake.Status.idle:      "🟡 Idle",
        disnake.Status.dnd:       "🔴 Do Not Disturb",
        disnake.Status.offline:   "⚫ Offline",
        disnake.Status.invisible: "⚫ Invisible",
    }.get(status, "❓ Unknown")

def _badge_str(flags: disnake.PublicUserFlags) -> str:
    badges = []
    mapping = {
        "staff":                    "👨‍💼 Discord Staff",
        "partner":                  "🤝 Partner",
        "hypesquad":                "🏠 HypeSquad Events",
        "bug_hunter":               "🐛 Bug Hunter",
        "bug_hunter_level_2":       "🐛 Bug Hunter Lvl.2",
        "hypesquad_bravery":        "🏠 HypeSquad Bravery",
        "hypesquad_brilliance":     "🏠 HypeSquad Brilliance",
        "hypesquad_balance":        "🏠 HypeSquad Balance",
        "early_supporter":          "💎 Early Supporter",
        "verified_bot_developer":   "🤖 Verified Bot Dev",
        "active_developer":         "🛠️ Active Developer",
        "discord_certified_moderator": "🛡️ Certified Moderator",
    }
    for attr, label in mapping.items():
        if getattr(flags, attr, False):
            badges.append(label)
    return "\n".join(badges) if badges else "None"


# ── Cog ──────────────────────────────────────────────────────────────────────

class Info(commands.Cog):
    """ℹ️ Informational commands."""

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

    # ── /help ────────────────────────────────────────────────────────

    @commands.slash_command(name="help", description="📖 Show all available commands")
    async def help(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="📖  Command Reference",
            description="Here's everything you can do with this bot.",
            color=Config.COLOR_PRIMARY,
            timestamp=datetime.utcnow(),
        )
        if inter.guild and inter.guild.icon:
            embed.set_thumbnail(url=inter.guild.icon.url)

        embed.add_field(
            name=f"{Config.EMOJI_SHIELD} Moderation",
            value=(
                "`/ban` · `/unban` · `/kick`\n"
                "`/mute` · `/unmute`\n"
                "`/clear` · `/slowmode`\n"
                "`/lock` · `/unlock`"
            ),
            inline=True,
        )
        embed.add_field(
            name=f"{Config.EMOJI_TICKET} Tickets",
            value=(
                "`/ticket setup` — send panel\n"
                "`/ticket add` — add member\n"
                "`/ticket remove` — remove member"
            ),
            inline=True,
        )
        embed.add_field(
            name=f"{Config.EMOJI_WELCOME} Welcome",
            value=(
                "`/welcome setchannel`\n"
                "`/welcome setleave`\n"
                "`/welcome setmessage`\n"
                "`/welcome setautorole`\n"
                "`/welcome test`"
            ),
            inline=True,
        )
        embed.add_field(
            name="📋 Logging",
            value=(
                "`/log setchannel`\n"
                "`/log disable`"
            ),
            inline=True,
        )
        embed.add_field(
            name="ℹ️ Info",
            value=(
                "`/help` · `/userinfo`\n"
                "`/serverinfo` · `/avatar`\n"
                "`/roleinfo` · `/botinfo`\n"
                "`/setup`"
            ),
            inline=True,
        )
        embed.add_field(
            name="🔧 Setup Guide",
            value=(
                "1️⃣ `/log setchannel` — set log channel\n"
                "2️⃣ `/welcome setchannel` — set welcome channel\n"
                "3️⃣ `/ticket setup` — deploy ticket panel\n"
                "4️⃣ Done! ✅"
            ),
            inline=False,
        )
        embed.set_footer(text=f"Bot: {self.bot.user} • {len(self.bot.slash_commands)} commands")
        await inter.response.send_message(embed=embed)

    # ── /setup ───────────────────────────────────────────────────────

    @commands.slash_command(name="setup", description="⚙️ Quick server setup wizard")
    @commands.has_permissions(administrator=True)
    async def setup_cmd(
        self,
        inter: disnake.ApplicationCommandInteraction,
        log_channel:     disnake.TextChannel = commands.Param(default=None, description="Log channel"),
        welcome_channel: disnake.TextChannel = commands.Param(default=None, description="Welcome channel"),
        leave_channel:   disnake.TextChannel = commands.Param(default=None, description="Leave channel"),
        autorole:        disnake.Role        = commands.Param(default=None, description="Auto-role on join"),
    ):
        from utils.data_manager import set_guild_config
        changes = []

        if log_channel:
            set_guild_config(inter.guild.id, "log_channel", log_channel.id)
            changes.append(f"📋 Log channel → {log_channel.mention}")

        if welcome_channel:
            set_guild_config(inter.guild.id, "welcome_channel", welcome_channel.id)
            changes.append(f"👋 Welcome channel → {welcome_channel.mention}")

        if leave_channel:
            set_guild_config(inter.guild.id, "leave_channel", leave_channel.id)
            changes.append(f"👋 Leave channel → {leave_channel.mention}")

        if autorole:
            set_guild_config(inter.guild.id, "autorole", autorole.id)
            changes.append(f"🎭 Auto-role → {autorole.mention}")

        if not changes:
            await inter.response.send_message(
                embed=EmbedBuilder.warning("Nothing Changed", "Provide at least one option to configure."),
                ephemeral=True,
            )
            return

        embed = EmbedBuilder.success(
            "Server Configured",
            "The following settings have been saved:\n\n" + "\n".join(changes)
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    # ── /userinfo ────────────────────────────────────────────────────

    @commands.slash_command(name="userinfo", description="👤 Get information about a member")
    async def userinfo(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(default=None, description="Member to look up"),
    ):
        target = member or inter.author

        roles = [r.mention for r in reversed(target.roles) if r != inter.guild.default_role]
        roles_str = " ".join(roles[:15]) if roles else "`None`"
        if len(roles) > 15:
            roles_str += f" *+{len(roles) - 15} more*"

        embed = disnake.Embed(
            title=f"👤  {target}",
            color=target.color if target.color.value else Config.COLOR_PRIMARY,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="🆔 User ID",      value=f"`{target.id}`",                                       inline=True)
        embed.add_field(name="🤖 Bot?",          value="Yes" if target.bot else "No",                          inline=True)
        embed.add_field(name="📶 Status",        value=_status_emoji(target.status),                           inline=True)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(target.created_at.timestamp())}:F>\n<t:{int(target.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="📥 Joined Server", value=f"<t:{int(target.joined_at.timestamp())}:F>\n<t:{int(target.joined_at.timestamp())}:R>",    inline=True)
        embed.add_field(name="🎨 Top Role",      value=target.top_role.mention,                               inline=True)
        embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=roles_str,                                     inline=False)

        badges = _badge_str(target.public_flags)
        if badges != "None":
            embed.add_field(name="🏅 Badges", value=badges, inline=False)

        embed.set_footer(text=f"Requested by {inter.author}")
        await inter.response.send_message(embed=embed)

    # ── /serverinfo ──────────────────────────────────────────────────

    @commands.slash_command(name="serverinfo", description="🏠 Get information about this server")
    async def serverinfo(self, inter: disnake.ApplicationCommandInteraction):
        guild = inter.guild

        bots    = sum(1 for m in guild.members if m.bot)
        humans  = guild.member_count - bots
        online  = sum(1 for m in guild.members if m.status != disnake.Status.offline)
        boosts  = guild.premium_subscription_count
        tier    = guild.premium_tier

        text_channels  = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories     = len(guild.categories)
        roles          = len(guild.roles)

        embed = disnake.Embed(
            title=f"🏠  {guild.name}",
            description=guild.description or "*No description*",
            color=Config.COLOR_PRIMARY,
            timestamp=datetime.utcnow(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="🆔 Server ID",      value=f"`{guild.id}`",                                    inline=True)
        embed.add_field(name="👑 Owner",           value=guild.owner.mention if guild.owner else "Unknown",  inline=True)
        embed.add_field(name="📅 Created",         value=f"<t:{int(guild.created_at.timestamp())}:R>",       inline=True)
        embed.add_field(name="👥 Members",         value=f"👤 `{humans}` humans\n🤖 `{bots}` bots\n🟢 `{online}` online", inline=True)
        embed.add_field(name="📁 Channels",        value=f"💬 `{text_channels}` text\n🔊 `{voice_channels}` voice\n📂 `{categories}` categories", inline=True)
        embed.add_field(name="🔖 Roles",           value=f"`{roles}`",                                       inline=True)
        embed.add_field(name="💎 Boost Level",     value=f"Tier `{tier}` — `{boosts}` boosts",              inline=True)
        embed.add_field(name="🔐 Verification",    value=str(guild.verification_level).replace("_", " ").title(), inline=True)
        embed.add_field(name="😀 Emojis",          value=f"`{len(guild.emojis)}`",                           inline=True)

        embed.set_footer(text=f"Requested by {inter.author}")
        await inter.response.send_message(embed=embed)

    # ── /avatar ──────────────────────────────────────────────────────

    @commands.slash_command(name="avatar", description="🖼️ Get a member's avatar")
    async def avatar(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(default=None, description="Member whose avatar to fetch"),
    ):
        target = member or inter.author
        embed = disnake.Embed(
            title=f"🖼️  {target.display_name}'s Avatar",
            color=Config.COLOR_INFO,
            timestamp=datetime.utcnow(),
        )
        embed.set_image(url=target.display_avatar.with_size(4096).url)
        embed.add_field(
            name="🔗 Links",
            value=" | ".join([
                f"[PNG]({target.display_avatar.with_format('png').url})",
                f"[JPG]({target.display_avatar.with_format('jpg').url})",
                f"[WEBP]({target.display_avatar.with_format('webp').url})",
            ]),
        )
        embed.set_footer(text=f"ID: {target.id}")
        await inter.response.send_message(embed=embed)

    # ── /roleinfo ────────────────────────────────────────────────────

    @commands.slash_command(name="roleinfo", description="🎭 Get information about a role")
    async def roleinfo(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(description="Role to inspect"),
    ):
        members_with_role = len(role.members)
        perms = [p.replace("_", " ").title() for p, v in role.permissions if v]

        embed = disnake.Embed(
            title=f"🎭  @{role.name}",
            color=role.color if role.color.value else Config.COLOR_DARK,
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="🆔 Role ID",       value=f"`{role.id}`",                                inline=True)
        embed.add_field(name="🎨 Color",          value=f"`#{role.color.value:06X}`",                  inline=True)
        embed.add_field(name="👥 Members",        value=f"`{members_with_role}`",                      inline=True)
        embed.add_field(name="📌 Position",       value=f"`#{role.position}`",                         inline=True)
        embed.add_field(name="🔔 Mentionable",    value="Yes" if role.mentionable else "No",           inline=True)
        embed.add_field(name="📤 Hoisted",        value="Yes" if role.hoist else "No",                 inline=True)
        embed.add_field(name="📅 Created",        value=f"<t:{int(role.created_at.timestamp())}:R>",   inline=True)
        embed.add_field(name="🤖 Managed",        value="Yes" if role.managed else "No",               inline=True)

        if perms:
            perms_str = ", ".join(perms[:20])
            if len(perms) > 20:
                perms_str += f" *+{len(perms)-20} more*"
            embed.add_field(name="🔑 Permissions", value=f"```{perms_str}```", inline=False)

        await inter.response.send_message(embed=embed)

    # ── /botinfo ─────────────────────────────────────────────────────

    @commands.slash_command(name="botinfo", description="🤖 Information about this bot")
    async def botinfo(self, inter: disnake.ApplicationCommandInteraction):
        import sys, platform
        import disnake as _disnake

        bot = self.bot
        guilds   = len(bot.guilds)
        members  = sum(g.member_count for g in bot.guilds)
        commands_count = len(bot.slash_commands)

        embed = disnake.Embed(
            title=f"🤖  {bot.user.name}",
            description="A fully-featured moderation & utility bot.",
            color=Config.COLOR_PRIMARY,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name="📟 Library",    value=f"`disnake {_disnake.__version__}`",         inline=True)
        embed.add_field(name="🐍 Python",     value=f"`{sys.version.split()[0]}`",               inline=True)
        embed.add_field(name="🖥️ Platform",   value=f"`{platform.system()} {platform.release()}`", inline=True)
        embed.add_field(name="🏠 Servers",    value=f"`{guilds}`",                               inline=True)
        embed.add_field(name="👥 Users",      value=f"`{members}`",                              inline=True)
        embed.add_field(name="📋 Commands",   value=f"`{commands_count}`",                       inline=True)
        embed.add_field(name="🆔 Bot ID",     value=f"`{bot.user.id}`",                          inline=False)
        embed.set_footer(text="Made with ❤️ using disnake")
        await inter.response.send_message(embed=embed)


    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        await self.help.callback(self, self._ctx_inter(ctx))

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_prefix(
        self,
        ctx: commands.Context,
        log_channel: disnake.TextChannel = None,
        welcome_channel: disnake.TextChannel = None,
        leave_channel: disnake.TextChannel = None,
        autorole: disnake.Role = None,
    ):
        await self.setup_cmd.callback(self, self._ctx_inter(ctx), log_channel, welcome_channel, leave_channel, autorole)

    @commands.command(name="userinfo")
    async def userinfo_prefix(self, ctx: commands.Context, member: disnake.Member = None):
        await self.userinfo.callback(self, self._ctx_inter(ctx), member)

    @commands.command(name="serverinfo")
    async def serverinfo_prefix(self, ctx: commands.Context):
        await self.serverinfo.callback(self, self._ctx_inter(ctx))

    @commands.command(name="avatar")
    async def avatar_prefix(self, ctx: commands.Context, member: disnake.Member = None):
        await self.avatar.callback(self, self._ctx_inter(ctx), member)

    @commands.command(name="roleinfo")
    async def roleinfo_prefix(self, ctx: commands.Context, role: disnake.Role):
        await self.roleinfo.callback(self, self._ctx_inter(ctx), role)

    @commands.command(name="botinfo")
    async def botinfo_prefix(self, ctx: commands.Context):
        await self.botinfo.callback(self, self._ctx_inter(ctx))


def setup(bot):
    bot.add_cog(Info(bot))
