import asyncio

import disnake
from disnake.ext import commands

from utils.config import Config
from utils.command_logging import log_command_error
from utils.data_manager import (
    close_ticket,
    create_ticket,
    get_config_value,
    get_ticket_by_channel,
    get_ticket_by_user,
    set_guild_config,
    set_ticket_closed,
    update_ticket_channel,
)
from utils.embeds import EmbedBuilder
from utils.logger import setup_logger

logger = setup_logger("tickets")


def _clean_reason(reason: str | None) -> str:
    reason = (reason or "").strip()
    return reason[:1000]


async def _warn_missing_reason(ctx: commands.Context, usage: str) -> None:
    await ctx.send(
        embed=EmbedBuilder.warning(
            "Reason Required",
            f"Prefix commands cannot open Discord modals. Add a reason to the command.\nUsage: `{usage}`",
        ),
        delete_after=10,
    )
    await log_command_error(ctx.guild, ctx.author, ctx.channel, f"{Config.PREFIX}{ctx.command.qualified_name}", "Missing reason", getattr(ctx, "kwargs", {}))


async def _log_ticket(guild: disnake.Guild, title: str, color: int, fields: list[tuple[str, str, bool]]) -> None:
    log_channel_id = get_config_value(guild.id, "log_channel")
    if not log_channel_id:
        return
    log_channel = guild.get_channel(int(log_channel_id))
    if log_channel:
        await log_channel.send(embed=EmbedBuilder.log_event(title, color, fields))


class TicketOpenModal(disnake.ui.Modal):
    def __init__(self, cog: "Tickets"):
        self.cog = cog
        components = [
            disnake.ui.TextInput(
                label="Reason",
                placeholder="Briefly describe your issue or question",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                min_length=5,
                max_length=1000,
            )
        ]
        super().__init__(title="Open Ticket", custom_id="ticket:open_modal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await self.cog.create_ticket_for(inter, inter.author, _clean_reason(inter.text_values["reason"]))


class TicketCloseModal(disnake.ui.Modal):
    def __init__(self, cog: "Tickets"):
        self.cog = cog
        components = [
            disnake.ui.TextInput(
                label="Close reason",
                placeholder="Example: solved, duplicate, no response",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                min_length=3,
                max_length=1000,
            )
        ]
        super().__init__(title="Close Ticket", custom_id="ticket:close_modal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await self.cog.close_ticket_channel(inter, _clean_reason(inter.text_values["reason"]))


class TicketPanelView(disnake.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @disnake.ui.button(label="Open Ticket", style=disnake.ButtonStyle.primary, emoji="📩", custom_id="ticket:open")
    async def open_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(TicketOpenModal(self.cog))


class TicketCloseView(disnake.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @disnake.ui.button(label="Close Ticket", style=disnake.ButtonStyle.danger, emoji="🔒", custom_id="ticket:close")
    async def close_ticket_btn(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(TicketCloseModal(self.cog))


class TicketClosedView(disnake.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @disnake.ui.button(label="Reopen Ticket", style=disnake.ButtonStyle.success, emoji="🔓", custom_id="ticket:reopen")
    async def reopen_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not self.cog.can_manage_ticket(inter.author):
            await inter.response.send_message(
                embed=EmbedBuilder.error("Permission Denied", "Only moderators can reopen tickets."),
                ephemeral=True,
            )
            return
        await self.cog.reopen_ticket_channel(inter)

    @disnake.ui.button(label="Delete Ticket", style=disnake.ButtonStyle.danger, emoji="🗑️", custom_id="ticket:delete")
    async def delete_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not self.cog.can_manage_ticket(inter.author):
            await inter.response.send_message(
                embed=EmbedBuilder.error("Permission Denied", "Only moderators can delete tickets."),
                ephemeral=True,
            )
            return
        await self.cog.delete_ticket_channel(inter)


class Tickets(commands.Cog):
    """Ticket system with slash, prefix, buttons, reasons and modals."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanelView(self))
        self.bot.add_view(TicketCloseView(self))
        self.bot.add_view(TicketClosedView(self))

    def can_manage_ticket(self, member: disnake.Member) -> bool:
        if member.guild_permissions.manage_channels or member.guild_permissions.administrator:
            return True
        support_role_id = get_config_value(member.guild.id, "support_role")
        return bool(support_role_id and any(role.id == int(support_role_id) for role in member.roles))

    async def create_ticket_for(self, responder, member: disnake.Member, reason: str):
        reason = _clean_reason(reason) or "No reason provided"
        guild = responder.guild
        existing = get_ticket_by_user(guild.id, member.id)
        if existing:
            channel_id, _ticket_data = existing
            channel = guild.get_channel(channel_id)
            mention = channel.mention if channel else f"`{channel_id}`"
            await responder.response.send_message(
                embed=EmbedBuilder.warning("Ticket Already Open", f"You already have an open ticket: {mention}"),
                ephemeral=True,
            )
            return

        category_id = get_config_value(guild.id, "ticket_category")
        category = guild.get_channel(int(category_id)) if category_id else None
        support_role_id = get_config_value(guild.id, "support_role")
        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False),
            member: disnake.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: disnake.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if support_role_id:
            role = guild.get_role(int(support_role_id))
            if role:
                overwrites[role] = disnake.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_id = create_ticket(guild.id, 0, member.id, reason)
        channel_name = f"ticket-{member.name.lower().replace(' ', '-')}-{ticket_id:04d}"
        ticket_channel = await guild.create_text_channel(
            name=channel_name[:100],
            category=category,
            overwrites=overwrites,
            topic=f"Support ticket for {member} | Ticket #{ticket_id:04d} | Reason: {reason[:120]}",
            reason=f"Ticket opened by {member}: {reason}",
        )
        update_ticket_channel(guild.id, ticket_id, 0, ticket_channel.id)

        await ticket_channel.send(member.mention, delete_after=5)
        await ticket_channel.send(embed=EmbedBuilder.ticket_opened(member, ticket_id, reason), view=TicketCloseView(self))
        await responder.response.send_message(
            embed=EmbedBuilder.success("Ticket Created", f"Your ticket has been opened: {ticket_channel.mention}"),
            ephemeral=True,
        )
        await _log_ticket(
            guild,
            "Ticket Opened",
            Config.COLOR_TICKET,
            [
                ("🎫 Ticket", f"{ticket_channel.mention} (`#{ticket_id:04d}`)", True),
                ("👤 User", member.mention, True),
                ("📝 Reason", f"```{reason}```", False),
            ],
        )

    async def close_ticket_channel(self, responder, reason: str):
        reason = _clean_reason(reason) or "No reason provided"
        guild = responder.guild
        channel = responder.channel
        member = responder.author
        ticket_data = get_ticket_by_channel(guild.id, channel.id)
        if not ticket_data:
            await responder.response.send_message(
                embed=EmbedBuilder.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True,
            )
            return

        opener = guild.get_member(ticket_data["user_id"])
        ticket_id = ticket_data["id"]
        await responder.response.send_message(
            embed=EmbedBuilder.warning(
                "Ticket Closing",
                "This ticket is being closed. The author will lose access, moderators will keep this channel.",
            )
        )
        if opener:
            await channel.set_permissions(
                opener,
                view_channel=False,
                send_messages=False,
                reason=f"Ticket closed by {member}: {reason}",
            )
            try:
                await opener.send(embed=EmbedBuilder.ticket_closed(member, opener, ticket_id, reason))
            except disnake.Forbidden:
                pass

        set_ticket_closed(guild.id, channel.id, True)
        await channel.send(embed=EmbedBuilder.ticket_closed(member, opener or member, ticket_id, reason), view=TicketClosedView(self))
        await _log_ticket(
            guild,
            "Ticket Closed",
            Config.COLOR_ERROR,
            [
                ("🎫 Ticket", f"`#{ticket_id:04d}`", True),
                ("🔒 Closed by", member.mention, True),
                ("👤 Opened by", opener.mention if opener else f"`{ticket_data['user_id']}`", True),
                ("📝 Open Reason", f"```{ticket_data.get('reason', 'No reason provided')}```", False),
                ("🧾 Close Reason", f"```{reason}```", False),
            ],
        )

    async def reopen_ticket_channel(self, responder):
        guild = responder.guild
        channel = responder.channel
        member = responder.author
        ticket_data = get_ticket_by_channel(guild.id, channel.id)
        if not ticket_data:
            await responder.response.send_message(
                embed=EmbedBuilder.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True,
            )
            return

        opener = guild.get_member(ticket_data["user_id"])
        if opener:
            await channel.set_permissions(
                opener,
                view_channel=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                reason=f"Ticket reopened by {member}",
            )
        set_ticket_closed(guild.id, channel.id, False)
        await responder.response.send_message(
            embed=EmbedBuilder.success("Ticket Reopened", f"Ticket `#{ticket_data['id']:04d}` has been reopened.")
        )
        await _log_ticket(
            guild,
            "Ticket Reopened",
            Config.COLOR_SUCCESS,
            [
                ("🎫 Ticket", f"`#{ticket_data['id']:04d}`", True),
                ("🔓 Reopened by", member.mention, True),
                ("👤 Opened by", opener.mention if opener else f"`{ticket_data['user_id']}`", True),
            ],
        )

    async def delete_ticket_channel(self, responder):
        guild = responder.guild
        channel = responder.channel
        member = responder.author
        ticket_data = get_ticket_by_channel(guild.id, channel.id)
        if not ticket_data:
            await responder.response.send_message(
                embed=EmbedBuilder.error("Not a Ticket", "This channel is not a ticket."),
                ephemeral=True,
            )
            return

        ticket_id = ticket_data["id"]
        close_ticket(guild.id, channel.id)
        await responder.response.send_message(embed=EmbedBuilder.warning("Ticket Deleting", "This channel will be deleted in 5 seconds."))
        await _log_ticket(
            guild,
            "Ticket Deleted",
            Config.COLOR_ERROR,
            [
                ("🎫 Ticket", f"`#{ticket_id:04d}`", True),
                ("🗑️ Deleted by", member.mention, True),
            ],
        )
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket deleted by {member}")

    @commands.slash_command(name="ticket")
    async def ticket(self, inter):
        pass

    @ticket.sub_command(name="setup", description="🎫 Send the ticket panel to a channel")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Channel to send the panel to"),
        support_role: disnake.Role = commands.Param(default=None, description="Role that can see tickets"),
        category: disnake.CategoryChannel = commands.Param(default=None, description="Category for ticket channels"),
    ):
        await self._ticket_setup(inter, channel, support_role, category)

    @ticket.sub_command(name="open", description="📩 Open a ticket with a reason modal")
    async def ticket_open(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(TicketOpenModal(self))

    @ticket.sub_command(name="close", description="🔒 Close this ticket with a reason modal")
    @commands.has_permissions(manage_channels=True)
    async def ticket_close(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(TicketCloseModal(self))

    @ticket.sub_command(name="add", description="➕ Add a member to this ticket")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        await self._ticket_add(inter, member)

    @ticket.sub_command(name="remove", description="➖ Remove a member from this ticket")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        await self._ticket_remove(inter, member)

    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket_prefix(self, ctx: commands.Context):
        await ctx.send(embed=EmbedBuilder.info("Ticket Commands", "`ticket open <reason>`, `ticket close <reason>`, `ticket setup`, `ticket add`, `ticket remove`"))

    @ticket_prefix.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup_prefix(
        self,
        ctx: commands.Context,
        channel: disnake.TextChannel,
        support_role: disnake.Role = None,
        category: disnake.CategoryChannel = None,
    ):
        await self._ticket_setup(ctx, channel, support_role, category)

    @ticket_prefix.command(name="open")
    async def ticket_open_prefix(self, ctx: commands.Context, *, reason: str = None):
        if not reason:
            await _warn_missing_reason(ctx, f"{Config.PREFIX}ticket open reason")
            return

        class PrefixResponder:
            guild = ctx.guild
            author = ctx.author
            channel = ctx.channel

            class response:
                @staticmethod
                async def send_message(embed=None, ephemeral=False):
                    await ctx.send(embed=embed)

        await self.create_ticket_for(PrefixResponder, ctx.author, reason)

    @ticket_prefix.command(name="close")
    @commands.has_permissions(manage_channels=True)
    async def ticket_close_prefix(self, ctx: commands.Context, *, reason: str = None):
        if not reason:
            await _warn_missing_reason(ctx, f"{Config.PREFIX}ticket close reason")
            return

        class PrefixResponder:
            guild = ctx.guild
            author = ctx.author
            channel = ctx.channel

            class response:
                @staticmethod
                async def send_message(embed=None, ephemeral=False):
                    await ctx.send(embed=embed)

        await self.close_ticket_channel(PrefixResponder, reason)

    @ticket_prefix.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add_prefix(self, ctx: commands.Context, member: disnake.Member):
        await self._ticket_add(ctx, member)

    @ticket_prefix.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove_prefix(self, ctx: commands.Context, member: disnake.Member):
        await self._ticket_remove(ctx, member)

    async def _ticket_setup(self, target, channel: disnake.TextChannel, support_role: disnake.Role = None, category: disnake.CategoryChannel = None):
        if support_role:
            set_guild_config(target.guild.id, "support_role", support_role.id)
        if category:
            set_guild_config(target.guild.id, "ticket_category", category.id)

        await channel.send(embed=EmbedBuilder.ticket_panel(target.guild), view=TicketPanelView(self))
        embed = EmbedBuilder.success("Ticket Panel Sent", f"Panel sent to {channel.mention}!")
        if isinstance(target, commands.Context):
            await target.send(embed=embed)
        else:
            await target.response.send_message(embed=embed, ephemeral=True)

    async def _ticket_add(self, target, member: disnake.Member):
        ticket_data = get_ticket_by_channel(target.guild.id, target.channel.id)
        if not ticket_data:
            embed = EmbedBuilder.error("Not a Ticket", "This command can only be used in a ticket channel.")
        else:
            await target.channel.set_permissions(member, view_channel=True, send_messages=True)
            embed = EmbedBuilder.success("Member Added", f"{member.mention} has been added to this ticket.")

        if isinstance(target, commands.Context):
            await target.send(embed=embed)
        else:
            await target.response.send_message(embed=embed, ephemeral=not ticket_data)

    async def _ticket_remove(self, target, member: disnake.Member):
        ticket_data = get_ticket_by_channel(target.guild.id, target.channel.id)
        if not ticket_data:
            embed = EmbedBuilder.error("Not a Ticket", "This command can only be used in a ticket channel.")
        else:
            await target.channel.set_permissions(member, overwrite=None)
            embed = EmbedBuilder.success("Member Removed", f"{member.mention} has been removed from this ticket.")

        if isinstance(target, commands.Context):
            await target.send(embed=embed)
        else:
            await target.response.send_message(embed=embed, ephemeral=not ticket_data)


def setup(bot):
    bot.add_cog(Tickets(bot))
