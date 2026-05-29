import disnake
from datetime import datetime
from utils.config import Config


class EmbedBuilder:
    """Factory for creating beautiful, consistent embeds."""

    @staticmethod
    def _base(color: int, title: str = None, description: str = None) -> disnake.Embed:
        embed = disnake.Embed(color=color, timestamp=datetime.utcnow())
        if title:
            embed.title = title
        if description:
            embed.description = description
        embed.set_footer(text="⚡ Moderation System", icon_url=None)
        return embed

    # ── Generic types ───────────────────────────────────────────────

    @staticmethod
    def success(title: str, description: str = None) -> disnake.Embed:
        return EmbedBuilder._base(Config.COLOR_SUCCESS, f"{Config.EMOJI_SUCCESS}  {title}", description)

    @staticmethod
    def error(title: str, description: str = None) -> disnake.Embed:
        return EmbedBuilder._base(Config.COLOR_ERROR, f"{Config.EMOJI_ERROR}  {title}", description)

    @staticmethod
    def warning(title: str, description: str = None) -> disnake.Embed:
        return EmbedBuilder._base(Config.COLOR_WARNING, f"{Config.EMOJI_WARNING}  {title}", description)

    @staticmethod
    def info(title: str, description: str = None) -> disnake.Embed:
        return EmbedBuilder._base(Config.COLOR_INFO, f"{Config.EMOJI_INFO}  {title}", description)

    # ── Moderation actions ──────────────────────────────────────────

    @staticmethod
    def mod_action(
        action: str,
        emoji: str,
        color: int,
        moderator: disnake.Member,
        target: disnake.Member | disnake.User,
        reason: str,
        extra_fields: list[tuple[str, str, bool]] = None,
    ) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"{emoji}  {action}",
            color=color,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👤 Target", value=f"{target.mention}\n`{target}`", inline=True)
        embed.add_field(name="🛡️ Moderator", value=f"{moderator.mention}\n`{moderator}`", inline=True)
        embed.add_field(name="📝 Reason", value=f"```{reason or 'No reason provided'}```", inline=False)
        if extra_fields:
            for name, value, inline in extra_fields:
                embed.add_field(name=name, value=value, inline=inline)
        embed.set_footer(text=f"User ID: {target.id}")
        return embed

    # ── Welcome ─────────────────────────────────────────────────────

    @staticmethod
    def welcome(member: disnake.Member, guild: disnake.Guild, message: str = None) -> disnake.Embed:
        member_count = guild.member_count
        embed = disnake.Embed(
            title=f"👋  Welcome to {guild.name}!",
            description=(
                message or
                f"Hey {member.mention}, we're so happy to have you here!\n"
                f"You are our **#{member_count}** member. Enjoy your stay! 🎉"
            ),
            color=Config.COLOR_PRIMARY,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=guild.banner.url if guild.banner else None)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="👥 Member Count", value=f"`{member_count}`", inline=True)
        embed.set_footer(text=f"ID: {member.id}")
        return embed

    # ── Tickets ─────────────────────────────────────────────────────

    @staticmethod
    def ticket_panel(guild: disnake.Guild) -> disnake.Embed:
        embed = disnake.Embed(
            title="🎫  Support Tickets",
            description=(
                "Need help? Click the button below to open a support ticket.\n\n"
                "**Guidelines:**\n"
                f"{Config.EMOJI_ARROW} Describe your issue clearly\n"
                f"{Config.EMOJI_ARROW} Be patient — staff will respond soon\n"
                f"{Config.EMOJI_ARROW} Do not abuse the ticket system\n\n"
                "Click **📩 Open Ticket** to get started!"
            ),
            color=Config.COLOR_TICKET,
            timestamp=datetime.utcnow(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=guild.name)
        return embed

    @staticmethod
    def ticket_opened(member: disnake.Member, ticket_id: int, reason: str = "No reason provided") -> disnake.Embed:
        embed = disnake.Embed(
            title=f"🎫  Ticket #{ticket_id:04d}",
            description=(
                f"Hello {member.mention}! 👋\n\n"
                "A staff member will be with you shortly.\n"
                "Please describe your issue in detail.\n\n"
                f"To close this ticket, click **🔒 Close Ticket** below."
            ),
            color=Config.COLOR_TICKET,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📌 Opened by", value=member.mention, inline=True)
        embed.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id:04d}`", inline=True)
        embed.add_field(name="📝 Reason", value=f"```{reason}```", inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        return embed

    @staticmethod
    def ticket_closed(
        closed_by: disnake.Member,
        opened_by: disnake.Member,
        ticket_id: int,
        reason: str = "No reason provided",
    ) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"🔒  Ticket #{ticket_id:04d} Closed",
            description="This ticket has been closed.",
            color=Config.COLOR_ERROR,
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="📌 Opened by", value=opened_by.mention, inline=True)
        embed.add_field(name="🔒 Closed by", value=closed_by.mention, inline=True)
        embed.add_field(name="🧾 Close Reason", value=f"```{reason}```", inline=False)
        embed.set_footer(text="Ticket System")
        return embed

    # ── Logging ─────────────────────────────────────────────────────

    @staticmethod
    def log_event(event: str, color: int, fields: list[tuple[str, str, bool]]) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"📋  {event}",
            color=color,
            timestamp=datetime.utcnow(),
        )
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        return embed
