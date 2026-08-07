import asyncio
import os
from pathlib import Path
from typing import Any

import discord
import yaml
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "server.yml"

load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID_RAW = os.getenv("DISCORD_GUILD_ID")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError("server.yml must contain a YAML object.")

    return config


async def deploy_server(
    guild: discord.Guild,
    config: dict[str, Any],
) -> None:
    categories = config.get("categories", [])

    for category_spec in categories:
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
            config = load_config()
            await deploy_server(guild, config)
            print("Deployment completed successfully.")

        except discord.Forbidden:
            print(
                "Discord denied an action. Confirm that the bot "
                "has Administrator permission."
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