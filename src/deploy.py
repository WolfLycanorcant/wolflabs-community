import asyncio
import os
from pathlib import Path
from typing import Any

import discord
import yaml
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_CONFIG_PATH = BASE_DIR / "config" / "server.yml"
ROLES_CONFIG_PATH = BASE_DIR / "config" / "roles.yml"

PERMISSIONS_CONFIG_PATH = BASE_DIR / "config" / "permissions.yml"

load_dotenv(BASE_DIR / ".env")

MESSAGES_CONFIG_PATH = BASE_DIR / "config" / "messages.yml"

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID_RAW = os.getenv("DISCORD_GUILD_ID")

async def deploy_forum_messages(
    guild: discord.Guild,
    config: dict[str, Any],
) -> None:
    for forum_name, message_spec in (
        config.get("forum_messages", {}).items()
    ):
        forum = discord.utils.get(
            guild.forums,
            name=forum_name,
        )

        if forum is None:
            print(f"Forum not found: {forum_name}")
            continue

        title = message_spec.get(
            "title",
            "📌 Read Before Posting",
        )

        content = message_spec.get(
            "content",
            "",
        )

        # Avoid creating another copy on every deployment.
        existing_thread = discord.utils.get(
            forum.threads,
            name=title,
        )

        if existing_thread is not None:
            print(
                f"Forum guidance already exists: "
                f"#{forum_name}"
            )
            continue

        print(
            f"Creating forum guidance in #{forum_name}"
        )

        await forum.create_thread(
            name=title,
            content=content,
            reason="Wolf Labs forum guidance deployment",
        )

async def deploy_messages(
    guild: discord.Guild,
    config: dict[str, Any],
) -> None:
    for channel_name, message_spec in (
        config.get("messages", {}).items()
    ):
        channel = discord.utils.get(
            guild.text_channels,
            name=channel_name,
        )

        if channel is None:
            print(f"Message channel not found: {channel_name}")
            continue

        title = message_spec.get("title")
        description = message_spec.get("description")
        footer = message_spec.get("footer")

        embed = discord.Embed(
            title=title,
            description=description,
        )

        if footer:
            embed.set_footer(text=footer)

        existing_message = None

        async for message in channel.history(limit=50):
            if message.author == guild.me and message.embeds:
                existing_message = message
                break

        if existing_message:
            print(f"Updating message in #{channel_name}")
            await existing_message.edit(embed=embed)
        else:
            print(f"Publishing message in #{channel_name}")
            await channel.send(embed=embed)

def build_overwrite(
    permission_spec: dict[str, bool],
) -> discord.PermissionOverwrite:
    overwrite = discord.PermissionOverwrite()

    for permission_name, value in permission_spec.items():
        if not hasattr(overwrite, permission_name):
            raise ValueError(
                f"Unknown channel permission: {permission_name}"
            )

        setattr(overwrite, permission_name, bool(value))

    return overwrite
    
async def apply_permission_profile(
    guild: discord.Guild,
    target,
    profile_name: str,
    profiles: dict[str, Any],
) -> None:
    profile = profiles.get(profile_name)

    if profile is None:
        print(f"Permission profile not found: {profile_name}")
        return

    overwrites = {}

    everyone_spec = profile.get("everyone")

    if everyone_spec:
        overwrites[guild.default_role] = build_overwrite(
            everyone_spec
        )

    for role_name, role_permissions in (
        profile.get("roles", {}).items()
    ):
        role = discord.utils.get(
            guild.roles,
            name=role_name,
        )

        if role is None:
            print(f"Role not found: {role_name}")
            continue

        overwrites[role] = build_overwrite(
            role_permissions
        )

    print(
        f"Applying '{profile_name}' permissions "
        f"to {target.name}"
    )

    await target.edit(
        overwrites=overwrites,
        reason="Wolf Labs permissions deployment",
    )    
    
async def deploy_permissions(
    guild: discord.Guild,
    config: dict[str, Any],
) -> None:
    profiles = config.get("permission_profiles", {})

    # Category-level permissions
    for category_name, category_spec in (
        config.get("categories", {}).items()
    ):
        category = discord.utils.get(
            guild.categories,
            name=category_name,
        )

        if category is None:
            print(
                f"Permission category not found: "
                f"{category_name}"
            )
            continue

        profile_name = category_spec.get("profile")

        await apply_permission_profile(
            guild,
            category,
            profile_name,
            profiles,
        )

    # Channel-level permissions
    for channel_name, channel_spec in (
        config.get("channels", {}).items()
    ):
        channel = discord.utils.get(
            guild.channels,
            name=channel_name,
        )

        if channel is None:
            print(
                f"Permission channel not found: "
                f"{channel_name}"
            )
            continue

        profile_name = channel_spec.get("profile")

        await apply_permission_profile(
            guild,
            channel,
            profile_name,
            profiles,
        )    
    
    
  

def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file)

    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a YAML object.")

    return data


def parse_color(value: str | None) -> discord.Color:
    if not value:
        return discord.Color.default()

    cleaned = value.strip().lstrip("#")

    try:
        return discord.Color(int(cleaned, 16))
    except ValueError as error:
        raise ValueError(f"Invalid role color: {value}") from error


def build_permissions(
    permission_spec: dict[str, bool] | None,
) -> discord.Permissions:
    permissions = discord.Permissions.none()

    for permission_name, enabled in (permission_spec or {}).items():
        if not hasattr(permissions, permission_name):
            raise ValueError(
                f"Unknown Discord permission: {permission_name}"
            )

        setattr(permissions, permission_name, bool(enabled))

    return permissions


async def deploy_roles(
    guild: discord.Guild,
    config: dict[str, Any],
) -> None:
    for role_spec in config.get("roles", []):
        role_name = role_spec["name"]

        existing_role = discord.utils.get(
            guild.roles,
            name=role_name,
        )

        if existing_role is not None:
            print(f"Role already exists: {role_name}")
            continue

        print(f"Creating role: {role_name}")

        await guild.create_role(
            name=role_name,
            color=parse_color(role_spec.get("color")),
            hoist=bool(role_spec.get("hoist", False)),
            mentionable=bool(role_spec.get("mentionable", False)),
            permissions=build_permissions(
                role_spec.get("permissions")
            ),
            reason="Wolf Labs infrastructure deployment",
        )

def build_forum_tags(
    tag_names: list[str],
) -> list[discord.ForumTag]:
    return [
        discord.ForumTag(
            name=tag_name
        )
        for tag_name in tag_names
    ]

async def deploy_server(
    guild: discord.Guild,
    config: dict[str, Any],
) -> None:
    for category_spec in config.get("categories", []):
        category_name = category_spec["name"]

        category = discord.utils.get(
            guild.categories,
            name=category_name,
        )

        if category is None:
            print(f"Creating category: {category_name}")

            category = await guild.create_category(
                category_name,
                reason="Wolf Labs infrastructure deployment",
            )

        else:
            print(f"Category already exists: {category_name}")

        for channel_spec in category_spec.get("channels", []):
            channel_name = channel_spec["name"]
            channel_type = channel_spec.get("type", "text")
            topic = channel_spec.get("topic")

            existing_channel = discord.utils.get(
                category.channels,
                name=channel_name,
            )

            if existing_channel is not None:
                print(f"Channel already exists: {channel_name}")
                continue

            if channel_type == "text":
                print(f"Creating text channel: #{channel_name}")

                await guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=topic,
                    reason="Wolf Labs infrastructure deployment",
                )

            elif channel_type == "voice":
                print(f"Creating voice channel: {channel_name}")

                await guild.create_voice_channel(
                    channel_name,
                    category=category,
                    reason="Wolf Labs infrastructure deployment",
                )

            elif channel_type == "forum":
                print(f"Creating forum channel: #{channel_name}")

                tag_names = channel_spec.get(
                    "tags",
                    [],
                )

                available_tags = build_forum_tags(
                    tag_names
                )

                await guild.create_forum(
                    channel_name,
                    category=category,
                    topic=topic,
                    available_tags=available_tags,
                    reason="Wolf Labs infrastructure deployment",
                )

            else:
                print(
                    f"Skipping unsupported channel type "
                    f"{channel_type!r} for {channel_name!r}"
                )


class ArchitectClient(discord.Client):
    async def on_ready(self) -> None:
        print(f"Connected as: {self.user}")

        guild = self.get_guild(int(GUILD_ID_RAW))

        if guild is None:
            print(
                "Could not find the server. Check the guild ID "
                "and confirm the bot is installed."
            )
            await self.close()
            return

        print(f"Deploying to: {guild.name}")

        try:
            roles_config = load_yaml(ROLES_CONFIG_PATH)
            server_config = load_yaml(SERVER_CONFIG_PATH)
            permissions_config = load_yaml(PERMISSIONS_CONFIG_PATH)
            messages_config = load_yaml(MESSAGES_CONFIG_PATH)

            await deploy_roles(guild, roles_config)
            await deploy_server(guild, server_config)
            await deploy_permissions(guild, permissions_config)
            await deploy_messages(guild, messages_config)
            await deploy_forum_messages(guild, messages_config)

            print("Deployment completed successfully.")

        except discord.Forbidden:
            print(
                "Discord denied an action. Confirm that the bot "
                "has Administrator permission and sits above the "
                "roles it needs to manage."
            )

        except discord.HTTPException as error:
            print(f"Discord API error: {error}")

        except (OSError, ValueError, KeyError) as error:
            print(f"Configuration error: {error}")

        finally:
            await self.close()



async def main() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is missing.")

    if not GUILD_ID_RAW or not GUILD_ID_RAW.isdigit():
        raise RuntimeError("DISCORD_GUILD_ID is missing or invalid.")

    intents = discord.Intents.default()
    client = ArchitectClient(intents=intents)

    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())