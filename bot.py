
import os
import random
import re
import sqlite3
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv


# ==================================================
# CONFIGURATION
# ==================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Your Discord user ID
OWNER_ID = 1490782575738748938

# Database saved beside this Python file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "tomorrow.db")

# Random delivery period for real messages
MIN_DELAY_DAYS = 1
MAX_DELAY_DAYS = 365


# ==================================================
# DATABASE
# ==================================================

def initialize_database():
    os.makedirs(BASE_DIR, exist_ok=True)

    with sqlite3.connect(DATABASE) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                due_at REAL NOT NULL,
                is_test INTEGER DEFAULT 0,
                delivered INTEGER DEFAULT 0
            )
        """)
        db.commit()


def save_message(user_id, message, due_at, is_test=False):
    with sqlite3.connect(DATABASE) as db:
        db.execute("""
            INSERT INTO scheduled_messages
            (user_id, message, due_at, is_test, delivered)
            VALUES (?, ?, ?, ?, 0)
        """, (
            user_id,
            message,
            due_at,
            int(is_test)
        ))
        db.commit()


# ==================================================
# BOT SETUP
# ==================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==================================================
# OWNER NOTIFICATIONS
# ==================================================

async def notify_owner(user, guild, command):
    try:
        owner = await bot.fetch_user(OWNER_ID)

        embed = discord.Embed(
            title="TOMORROW Activity",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="User",
            value=f"{user} ({user.id})",
            inline=False
        )

        embed.add_field(
            name="Server",
            value=guild.name if guild else "Direct Message",
            inline=False
        )

        embed.add_field(
            name="Command",
            value=command,
            inline=False
        )

        await owner.send(embed=embed)

    except discord.Forbidden:
        print("Could not DM the owner. Check your DM settings.")

    except discord.HTTPException as error:
        print(f"Owner notification failed: {error}")


# ==================================================
# MESSAGE DELIVERY
# ==================================================

@tasks.loop(seconds=30)
async def delivery_loop():
    current_time = time.time()

    with sqlite3.connect(DATABASE) as db:
        rows = db.execute("""
            SELECT id, user_id, message, is_test
            FROM scheduled_messages
            WHERE due_at <= ?
            AND delivered = 0
        """, (current_time,)).fetchall()

    for message_id, user_id, message, is_test in rows:
        try:
            user = await bot.fetch_user(user_id)

            embed = discord.Embed(
                title="A Message From Your Past Self",
                description=message,
                color=discord.Color.blurple()
            )

            if is_test:
                embed.title = "TOMORROW Test Message"

            embed.set_footer(text="Sent by TOMORROW")

            await user.send(embed=embed)

            with sqlite3.connect(DATABASE) as db:
                db.execute("""
                    UPDATE scheduled_messages
                    SET delivered = 1
                    WHERE id = ?
                """, (message_id,))
                db.commit()

            print(f"Delivered message {message_id} to {user_id}")

        except discord.Forbidden:
            # Retry after six hours if the user's DMs are closed
            with sqlite3.connect(DATABASE) as db:
                db.execute("""
                    UPDATE scheduled_messages
                    SET due_at = ?
                    WHERE id = ?
                """, (time.time() + 21600, message_id))
                db.commit()

        except discord.HTTPException as error:
            print(f"Delivery failed: {error}")


@delivery_loop.before_loop
async def before_delivery_loop():
    await bot.wait_until_ready()


# ==================================================
# TOMORROW COMMAND GROUP
# ==================================================

tomorrow = app_commands.Group(
    name="tomorrow",
    description="Send messages to your future self."
)


# ==================================================
# /tomorrow write
# ==================================================

@tomorrow.command(
    name="write",
    description="Write a message to your future self."
)
@app_commands.describe(
    message="The message you want your future self to receive."
)
async def write(
    interaction: discord.Interaction,
    message: str
):
    await interaction.response.defer(ephemeral=True)

    # Choose a random delivery time
    delay_days = random.randint(
        MIN_DELAY_DAYS,
        MAX_DELAY_DAYS
    )

    due_at = time.time() + (delay_days * 86400)

    # Save the message
    save_message(
        interaction.user.id,
        message,
        due_at,
        False
    )

    # Notify the bot owner
    await notify_owner(
        interaction.user,
        interaction.guild,
        "/tomorrow write"
    )

    # Do NOT reveal the waiting time
    await interaction.followup.send(
        "Your message has been saved. "
        "One day, it will find its way back to you.",
        ephemeral=True
    )


# ==================================================
# MODERATOR PERMISSION CHECK
# ==================================================

def can_use_test(member):
    if not isinstance(member, discord.Member):
        return False

    permissions = member.guild_permissions

    return (
        member.guild.owner_id == member.id
        or permissions.administrator
        or permissions.manage_guild
        or permissions.manage_messages
        or permissions.kick_members
    )


# ==================================================
# /tomorrow test
# ==================================================

@tomorrow.command(
    name="test",
    description="Send yourself a test message after a short delay."
)
@app_commands.describe(
    delay="How long to wait: 1m, 10m, 1h, or 1d."
)
async def test(
    interaction: discord.Interaction,
    delay: str
):
    if not can_use_test(interaction.user):
        await interaction.response.send_message(
            "You need moderator or administrator permissions "
            "to use this command.",
            ephemeral=True
        )
        return

    match = re.fullmatch(
        r"(\d+)(s|m|h|d)",
        delay.lower().strip()
    )

    if not match:
        await interaction.response.send_message(
            "Invalid delay. Examples: `1m`, `10m`, `1h`, `1d`.",
            ephemeral=True
        )
        return

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }

    seconds = amount * multipliers[unit]

    if amount < 1 or seconds > 604800:
        await interaction.response.send_message(
            "Test delays must be between 1 second and 7 days.",
            ephemeral=True
        )
        return

    due_at = time.time() + seconds

    test_message = (
        "This is a test message from TOMORROW. "
        "Your scheduled message delivery is working!"
    )

    save_message(
        interaction.user.id,
        test_message,
        due_at,
        True
    )

    await notify_owner(
        interaction.user,
        interaction.guild,
        f"/tomorrow test {delay}"
    )

    await interaction.response.send_message(
        f"Your test message has been scheduled!",
        ephemeral=True
    )


# ==================================================
# BOT STARTUP
# ==================================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not delivery_loop.is_running():
        delivery_loop.start()

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")

    except discord.HTTPException as error:
        print(f"Command sync failed: {error}")


# Register commands
bot.tree.add_command(tomorrow)


# ==================================================
# RUN BOT
# ==================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Check your .env file."
    )

initialize_database()

bot.run(TOKEN)
