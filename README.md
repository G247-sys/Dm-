# TOMORROW — Discord bot

TOMORROW lets server members write a message to their future self. Each message is scheduled for one random delivery time between the configured minimum and maximum delay, then sent once by DM.

## Commands

- `/tomorrow write message:<your message>` — available to everyone in the server.
- `/tomorrow test delay:<delay>` — available only to the server owner, administrators, and moderators.

Test delay examples: `1m`, `10m`, `1h`, `1d`.

The test command sends a test DM only to the person who ran it. It does not alter or accelerate real messages.

## Requirements

- Python 3.10 or newer
- A Discord application and bot
- The bot invited to your server with permission to use application commands and send DMs

## Setup on Windows

1. Install Python 3.10+ from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP into a folder.
3. Open PowerShell in that folder.
4. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env`.
6. Open `.env` and paste your bot token after `DISCORD_TOKEN=`.
7. Run the bot:

   ```powershell
   py bot.py
   ```

Keep the computer and bot process running for scheduled messages to be delivered. For 24/7 delivery, host it on an always-on VPS or other Python hosting service.

## Discord Developer Portal

1. Open https://discord.com/developers/applications
2. Create an application, open **Bot**, and create/reset its token.
3. Keep the token private. Never paste it into a public channel or share it.
4. Open **OAuth2 → URL Generator**.
5. Select scopes: `bot` and `applications.commands`.
6. Select bot permissions: `View Channels`, `Send Messages`, and `Embed Links`.
7. Use the generated URL to invite the bot.

No privileged Message Content intent is needed.

## Who can use test mode?

- Server owner: yes
- Members with Administrator: yes
- Moderators with Manage Server, Manage Messages, or Kick Members: yes
- Regular members: no

The moderator permission checks are built into the bot; regular members cannot use `/tomorrow_test`.

## Random delivery behavior

By default, each real message is scheduled at a random time from 1 to 365 days after it is written. The day and time are randomized. Each message is marked delivered after Discord accepts the DM.

You can change the window in `.env`:
- `MIN_DELAY_DAYS=1`
- `MAX_DELAY_DAYS=365`

For example, `MAX_DELAY_DAYS=730` allows delivery up to two years later. Restart the bot after changing these settings.

## Important notes

- Users must allow DMs from server members (or otherwise allow DMs from the bot) to receive messages.
- If a user's DMs are closed, the bot keeps the message pending and retries on later checks.
- The SQLite database `tomorrow.db` contains scheduled messages. Back it up regularly.
- The bot must remain online to send messages at their scheduled times.
- Do not share your bot token. If it is exposed, reset it immediately in the Developer Portal.
