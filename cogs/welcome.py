import disnake
from disnake.ext import commands
from utils.embeds import EmbedBuilder
from utils.config import Config
from utils.logger import setup_logger
from utils.data_manager import get_config_value, set_guild_config

logger = setup_logger("welcome")


class Welcome(commands.Cog):
    """👋 Welcome/leave messages and autorole."""

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

    # ── Events ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        guild = member.guild

        # Welcome message
        welcome_channel_id = get_config_value(guild.id, "welcome_channel")
        if welcome_channel_id:
            ch = guild.get_channel(int(welcome_channel_id))
            if ch:
                custom_msg = get_config_value(guild.id, "welcome_message")
                embed = EmbedBuilder.welcome(member, guild, custom_msg)
                await ch.send(embed=embed)

        # Auto-role
        autorole_id = get_config_value(guild.id, "autorole")
        if autorole_id:
            role = guild.get_role(int(autorole_id))
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role on join")
                except disnake.Forbidden:
                    logger.warning(f"Cannot assign autorole in {guild.name}")

        # Log
        log_channel_id = get_config_value(guild.id, "log_channel")
        if log_channel_id:
            log_ch = guild.get_channel(int(log_channel_id))
            if log_ch:
                await log_ch.send(embed=EmbedBuilder.log_event(
                    "Member Joined", Config.COLOR_SUCCESS,
                    [
                        ("👤 Member", f"{member.mention}\n`{member}`", True),
                        ("📅 Account Age", f"<t:{int(member.created_at.timestamp())}:R>", True),
                        ("👥 Member Count", f"`{guild.member_count}`", True),
                        ("🆔 User ID", f"`{member.id}`", False),
                    ]
                ))

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        guild = member.guild

        # Leave message
        leave_channel_id = get_config_value(guild.id, "leave_channel")
        if leave_channel_id:
            ch = guild.get_channel(int(leave_channel_id))
            if ch:
                embed = disnake.Embed(
                    title=f"👋  Goodbye, {member.name}!",
                    description=f"{member.mention} has left the server.\nWe now have **{guild.member_count}** members.",
                    color=Config.COLOR_DARK,
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await ch.send(embed=embed)

        # Log
        log_channel_id = get_config_value(guild.id, "log_channel")
        if log_channel_id:
            log_ch = guild.get_channel(int(log_channel_id))
            if log_ch:
                roles = [r.mention for r in member.roles if r != guild.default_role]
                await log_ch.send(embed=EmbedBuilder.log_event(
                    "Member Left", Config.COLOR_ERROR,
                    [
                        ("👤 Member", f"`{member}`", True),
                        ("👥 Member Count", f"`{guild.member_count}`", True),
                        ("🎭 Roles", " ".join(roles) if roles else "`None`", False),
                        ("🆔 User ID", f"`{member.id}`", False),
                    ]
                ))

    # ── Commands ─────────────────────────────────────────────────────

    @commands.slash_command(name="welcome")
    async def welcome_cmd(self, inter):
        pass

    @welcome_cmd.sub_command(name="setchannel", description="📌 Set the welcome channel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Welcome channel"),
    ):
        set_guild_config(inter.guild.id, "welcome_channel", channel.id)
        await inter.response.send_message(
            embed=EmbedBuilder.success("Welcome Channel Set", f"Welcome messages will be sent to {channel.mention}."),
            ephemeral=True,
        )

    @welcome_cmd.sub_command(name="setleave", description="📌 Set the leave channel")
    @commands.has_permissions(administrator=True)
    async def set_leave_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Leave channel"),
    ):
        set_guild_config(inter.guild.id, "leave_channel", channel.id)
        await inter.response.send_message(
            embed=EmbedBuilder.success("Leave Channel Set", f"Leave messages will be sent to {channel.mention}."),
            ephemeral=True,
        )

    @welcome_cmd.sub_command(name="setmessage", description="✏️ Set a custom welcome message")
    @commands.has_permissions(administrator=True)
    async def set_welcome_message(
        self,
        inter: disnake.ApplicationCommandInteraction,
        message: str = commands.Param(description="Custom welcome message (use {member} for mention, {server} for name)"),
    ):
        set_guild_config(inter.guild.id, "welcome_message", message)
        await inter.response.send_message(
            embed=EmbedBuilder.success("Welcome Message Set", f"New message:\n```{message}```"),
            ephemeral=True,
        )

    @welcome_cmd.sub_command(name="setautorole", description="🎭 Set a role to assign on join")
    @commands.has_permissions(administrator=True)
    async def set_autorole(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(description="Role to assign"),
    ):
        set_guild_config(inter.guild.id, "autorole", role.id)
        await inter.response.send_message(
            embed=EmbedBuilder.success("Auto-Role Set", f"New members will receive {role.mention} on join."),
            ephemeral=True,
        )

    @welcome_cmd.sub_command(name="test", description="🔧 Test the welcome message")
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, inter: disnake.ApplicationCommandInteraction):
        welcome_channel_id = get_config_value(inter.guild.id, "welcome_channel")
        if not welcome_channel_id:
            await inter.response.send_message(
                embed=EmbedBuilder.error("Not Configured", "Use `/welcome setchannel` first."),
                ephemeral=True,
            )
            return
        ch = inter.guild.get_channel(int(welcome_channel_id))
        if ch:
            custom_msg = get_config_value(inter.guild.id, "welcome_message")
            embed = EmbedBuilder.welcome(inter.author, inter.guild, custom_msg)
            await ch.send(embed=embed)
            await inter.response.send_message(
                embed=EmbedBuilder.success("Test Sent", f"Test welcome message sent to {ch.mention}."),
                ephemeral=True,
            )


    @commands.group(name="welcome", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome_prefix(self, ctx: commands.Context):
        await ctx.send(embed=EmbedBuilder.info("Welcome Commands", "`welcome setchannel`, `welcome setleave`, `welcome setmessage`, `welcome setautorole`, `welcome test`"))

    @welcome_prefix.command(name="setchannel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel_prefix(self, ctx: commands.Context, channel: disnake.TextChannel):
        await self.set_welcome_channel.callback(self, self._ctx_inter(ctx), channel)

    @welcome_prefix.command(name="setleave")
    @commands.has_permissions(administrator=True)
    async def set_leave_channel_prefix(self, ctx: commands.Context, channel: disnake.TextChannel):
        await self.set_leave_channel.callback(self, self._ctx_inter(ctx), channel)

    @welcome_prefix.command(name="setmessage")
    @commands.has_permissions(administrator=True)
    async def set_welcome_message_prefix(self, ctx: commands.Context, *, message: str):
        await self.set_welcome_message.callback(self, self._ctx_inter(ctx), message)

    @welcome_prefix.command(name="setautorole")
    @commands.has_permissions(administrator=True)
    async def set_autorole_prefix(self, ctx: commands.Context, role: disnake.Role):
        await self.set_autorole.callback(self, self._ctx_inter(ctx), role)

    @welcome_prefix.command(name="test")
    @commands.has_permissions(administrator=True)
    async def test_welcome_prefix(self, ctx: commands.Context):
        await self.test_welcome.callback(self, self._ctx_inter(ctx))


def setup(bot):
    bot.add_cog(Welcome(bot))
