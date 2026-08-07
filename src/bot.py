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

ROLE_NAMES = {
    "gm": "Game Master",
    "player": "Player",
    "developer": "Developer",
    "beta": "Beta Tester",
}


class RoleButton(discord.ui.Button):
    def __init__(
        self,
        *,
        label: str,
        role_name: str,
        emoji: str,
        style: discord.ButtonStyle,
        custom_id: str,
    ) -> None:
        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            custom_id=custom_id,
        )
        self.role_name = role_name

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This button only works inside the server.",
                ephemeral=True,
            )
            return

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "I could not identify your server membership.",
                ephemeral=True,
            )
            return

        role = discord.utils.get(
            interaction.guild.roles,
            name=self.role_name,
        )

        if role is None:
            await interaction.response.send_message(
                f"The `{self.role_name}` role does not exist.",
                ephemeral=True,
            )
            return

        try:
            if role in member.roles:
                await member.remove_roles(
                    role,
                    reason="Self-service role removal",
                )
                await interaction.response.send_message(
                    f"Removed the **{role.name}** role.",
                    ephemeral=True,
                )
            else:
                await member.add_roles(
                    role,
                    reason="Self-service role selection",
                )
                await interaction.response.send_message(
                    f"Added the **{role.name}** role.",
                    ephemeral=True,
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I cannot manage that role. Move the Wolf Labs Architect "
                "role above the self-assigned roles.",
                ephemeral=True,
            )


class OnboardingRolesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        self.add_item(
            RoleButton(
                label="Game Master",
                role_name=ROLE_NAMES["gm"],
                emoji="🎲",
                style=discord.ButtonStyle.primary,
                custom_id="onboarding_role_gm",
            )
        )

        self.add_item(
            RoleButton(
                label="Player",
                role_name=ROLE_NAMES["player"],
                emoji="🧙",
                style=discord.ButtonStyle.secondary,
                custom_id="onboarding_role_player",
            )
        )

        self.add_item(
            RoleButton(
                label="Developer",
                role_name=ROLE_NAMES["developer"],
                emoji="💻",
                style=discord.ButtonStyle.success,
                custom_id="onboarding_role_developer",
            )
        )

        self.add_item(
            RoleButton(
                label="Beta Tester",
                role_name=ROLE_NAMES["beta"],
                emoji="🧪",
                style=discord.ButtonStyle.danger,
                custom_id="onboarding_role_beta",
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
        self.add_view(OnboardingRolesView())

        if GUILD_ID_RAW and GUILD_ID_RAW.isdigit():
            guild_object = discord.Object(id=int(GUILD_ID_RAW))
            self.tree.copy_global_to(guild=guild_object)
            await self.tree.sync(guild=guild_object)

    async def on_ready(self) -> None:
        print(f"Bot online as: {self.user}")


bot = ArchitectBot()


@bot.tree.command(
    name="post-onboarding",
    description="Post the self-service role selection panel.",
)
@app_commands.checks.has_permissions(administrator=True)
async def post_onboarding(
    interaction: discord.Interaction,
) -> None:
    embed = discord.Embed(
        title="🎲 Choose Your Guild Roles",
        description=(
            "Choose every role that fits you.\n\n"
            "You can be both a **Game Master** and a **Player**. "
            "Clicking a role again removes it.\n\n"
            "These choices help personalize your experience in the Guild."
        ),
    )

    embed.set_footer(
        text="The AI GM Guild • Powered by Wolf Labs"
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
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "Only an administrator can post the onboarding panel.",
            ephemeral=True,
        )
        return

    raise error


def main() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is missing from .env")

    if not GUILD_ID_RAW or not GUILD_ID_RAW.isdigit():
        raise RuntimeError("DISCORD_GUILD_ID is missing or invalid")

    bot.run(TOKEN)


if __name__ == "__main__":
    main()