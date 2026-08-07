import os
from pathlib import Path
from typing import Any

import discord
import yaml
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ONBOARDING_PATH = BASE_DIR / "config" / "onboarding.yml"

load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID_RAW = os.getenv("DISCORD_GUILD_ID")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.name} must contain a YAML object."
        )

    return data


ONBOARDING_CONFIG = load_yaml(ONBOARDING_PATH)["onboarding"]


STYLE_MAP = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


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
            f"The **{role_name}** role hasn't been configured.",
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
            "**Wolf Labs Architect** is above it.",
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

        for index, item in enumerate(
            ONBOARDING_CONFIG.get("roles", [])
        ):

            style_name = item.get(
                "style",
                "secondary",
            )

            style = STYLE_MAP.get(
                style_name,
                discord.ButtonStyle.secondary,
            )

            self.add_item(
                RoleButton(
                    label=item["label"],
                    role_name=item["role"],
                    emoji=item["emoji"],
                    style=style,
                    custom_id=f"guild_onboarding_{index}",
                    row=int(item.get("row", 0)),
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

        self.add_view(
            OnboardingRolesView()
        )

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
        title=ONBOARDING_CONFIG["title"],
        description=ONBOARDING_CONFIG["description"],
        color=discord.Color.from_rgb(0, 127, 255),
    )

    footer = ONBOARDING_CONFIG.get("footer")

    if footer:
        embed.set_footer(
            text=footer
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

@bot.tree.command(
    name="my-path",
    description="Show recommended places in the Guild based on your roles.",
)
async def my_path(
    interaction: discord.Interaction,
) -> None:

    if interaction.guild is None:
        await interaction.response.send_message(
            "This command only works inside the Guild.",
            ephemeral=True,
        )
        return

    member = interaction.user

    if not isinstance(member, discord.Member):
        await interaction.response.send_message(
            "I couldn't identify your Guild membership.",
            ephemeral=True,
        )
        return

    member_roles = {
        role.name
        for role in member.roles
    }

    paths = ONBOARDING_CONFIG.get(
        "paths",
        {},
    )

    matched_paths = []

    for role_name, path in paths.items():
        if role_name in member_roles:
            matched_paths.append(path)

    if not matched_paths:
        await interaction.response.send_message(
            "You haven't selected any onboarding roles yet. "
            "Visit **#start-here** and choose what interests you first.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="🧭 Your Guild Path",
        description=(
            "Based on the interests you've selected, "
            "here are some great places to start."
        ),
    )

    for path in matched_paths:

        channel_mentions = []

        for channel_name in path.get(
            "channels",
            [],
        ):

            channel = discord.utils.get(
                interaction.guild.channels,
                name=channel_name,
            )

            if channel is not None:
                channel_mentions.append(
                    channel.mention
                )

        channel_text = "\n".join(
            f"→ {mention}"
            for mention in channel_mentions
        )

        value = path.get(
            "intro",
            "",
        )

        if channel_text:
            value += (
                "\n\n"
                + channel_text
            )

        embed.add_field(
            name=path["title"],
            value=value,
            inline=False,
        )

    embed.set_footer(
        text=(
            "Explore at your own pace. "
            "There is no wrong way through the Guild."
        )
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )
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