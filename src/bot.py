import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID_RAW = os.getenv("DISCORD_GUILD_ID")


async def toggle_role(
    interaction: discord.Interaction,
    role_name: str,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "This control only works inside the Guild.",
            ephemeral=True,
        )
        return

    member = interaction.user

    if not isinstance(member, discord.Member):
        await interaction.response.send_message(
            "I couldn't identify your server membership.",
            ephemeral=True,
        )
        return

    role = discord.utils.get(
        interaction.guild.roles,
        name=role_name,
    )

    if role is None:
        await interaction.response.send_message(
            f"The **{role_name}** role hasn't been configured yet.",
            ephemeral=True,
        )
        return

    try:
        if role in member.roles:
            await member.remove_roles(
                role,
                reason="Self-service onboarding role removal",
            )

            await interaction.response.send_message(
                f"✓ Removed **{role_name}**.",
                ephemeral=True,
            )

        else:
            await member.add_roles(
                role,
                reason="Self-service onboarding role selection",
            )

            await interaction.response.send_message(
                f"✓ Added **{role_name}**.",
                ephemeral=True,
            )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I can't manage that role. Make sure "
            "**Wolf Labs Architect** is above it in the role hierarchy.",
            ephemeral=True,
        )


class RoleButton(discord.ui.Button):
    def __init__(
        self,
        *,
        label: str,
        role_name: str,
        emoji: str,
        style: discord.ButtonStyle,
        custom_id: str,
        row: int,
    ) -> None:

        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            custom_id=custom_id,
            row=row,
        )

        self.role_name = role_name

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await toggle_role(
            interaction,
            self.role_name,
        )


class OnboardingRolesView(discord.ui.View):

    def __init__(self) -> None:
        super().__init__(timeout=None)

        # ---------------------------------
        # ROW 0 — HOW DO YOU PLAY?
        # ---------------------------------

        self.add_item(
            RoleButton(
                label="Game Master",
                role_name="Game Master",
                emoji="🎲",
                style=discord.ButtonStyle.primary,
                custom_id="guild_role_gm",
                row=0,
            )
        )

        self.add_item(
            RoleButton(
                label="Player",
                role_name="Player",
                emoji="🧙",
                style=discord.ButtonStyle.primary,
                custom_id="guild_role_player",
                row=0,
            )
        )

        self.add_item(
            RoleButton(
                label="Developer",
                role_name="Developer",
                emoji="💻",
                style=discord.ButtonStyle.primary,
                custom_id="guild_role_developer",
                row=0,
            )
        )

        # ---------------------------------
        # ROW 1 — WHAT BRINGS YOU HERE?
        # ---------------------------------

        self.add_item(
            RoleButton(
                label="AI for GMing",
                role_name="AI for GMing",
                emoji="🤖",
                style=discord.ButtonStyle.secondary,
                custom_id="guild_interest_ai_gming",
                row=1,
            )
        )

        self.add_item(
            RoleButton(
                label="Worldbuilding",
                role_name="Worldbuilding",
                emoji="🌍",
                style=discord.ButtonStyle.secondary,
                custom_id="guild_interest_worldbuilding",
                row=1,
            )
        )

        self.add_item(
            RoleButton(
                label="Foundry Tools",
                role_name="Foundry Tools",
                emoji="🔨",
                style=discord.ButtonStyle.secondary,
                custom_id="guild_interest_foundry",
                row=1,
            )
        )

        # ---------------------------------
        # ROW 2 — MORE INTERESTS
        # ---------------------------------

        self.add_item(
            RoleButton(
                label="AI Development",
                role_name="AI Development",
                emoji="🧠",
                style=discord.ButtonStyle.secondary,
                custom_id="guild_interest_ai_dev",
                row=2,
            )
        )

        self.add_item(
            RoleButton(
                label="Learning TTRPGs",
                role_name="Learning TTRPGs",
                emoji="📚",
                style=discord.ButtonStyle.secondary,
                custom_id="guild_interest_learning",
                row=2,
            )
        )

        # ---------------------------------
        # ROW 3 — EARLY ACCESS
        # ---------------------------------

        self.add_item(
            RoleButton(
                label="Beta Tester",
                role_name="Beta Tester",
                emoji="🧪",
                style=discord.ButtonStyle.success,
                custom_id="guild_role_beta",
                row=3,
            )
        )


class ArchitectBot(commands.Bot):

    def __init__(self) -> None:

        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self) -> None:

        # Persistent onboarding controls.
        self.add_view(OnboardingRolesView())

        if GUILD_ID_RAW and GUILD_ID_RAW.isdigit():

            guild_object = discord.Object(
                id=int(GUILD_ID_RAW)
            )

            self.tree.copy_global_to(
                guild=guild_object
            )

            await self.tree.sync(
                guild=guild_object
            )

    async def on_ready(self) -> None:

        print(
            f"Bot online as: {self.user}"
        )


bot = ArchitectBot()


@bot.tree.command(
    name="post-onboarding",
    description="Post the Guild onboarding panel.",
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def post_onboarding(
    interaction: discord.Interaction,
) -> None:

    embed = discord.Embed(
        title="🏰 Welcome to The AI GM Guild",
        description=(
            "Let's personalize your place in the Guild.\n\n"

            "**🎲 How do you play?**\n"
            "Choose Game Master, Player, Developer — "
            "or any combination that describes you.\n\n"

            "**🧭 What brings you here?**\n"
            "Choose the things you're interested in. "
            "Pick as many as you like.\n\n"

            "**🧪 Want early access?**\n"
            "Choose Beta Tester if you'd like to help "
            "test experimental Wolf Labs tools.\n\n"

            "Clicking a selected role again removes it.\n\n"

            "**There are no wrong choices.** "
            "The Guild is here to help you explore, "
            "create, and enjoy tabletop gaming."
        ),
    )

    embed.set_footer(
        text=(
            "Every feature should give the GM "
            "more time to create."
        )
    )

    await interaction.response.send_message(
        embed=embed,
        view=OnboardingRolesView(),
    )


@post_onboarding.error
async def post_onboarding_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:

    if isinstance(
        error,
        app_commands.MissingPermissions,
    ):

        await interaction.response.send_message(
            "Only an administrator can post "
            "the onboarding panel.",
            ephemeral=True,
        )

        return

    raise error


def main() -> None:

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is missing from .env"
        )

    if (
        not GUILD_ID_RAW
        or not GUILD_ID_RAW.isdigit()
    ):
        raise RuntimeError(
            "DISCORD_GUILD_ID is missing or invalid"
        )

    bot.run(TOKEN)


if __name__ == "__main__":
    main()