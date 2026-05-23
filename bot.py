import discord
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

GUILD_CHANNEL_ID = 1507797912111939755
PING_ROLE_ID = 1507799489312985238

HUNT_DAYS = [4, 5, 6]   # Fri/Sat/Sun
DANCE_DAYS = [4]        # Friday only

def get_today_schedule(now_utc):
    weekday = now_utc.weekday()
    events = []

    # Guild Hunt (9 AM PDT ≈ 16 UTC)
    if weekday in HUNT_DAYS:
        hunt_start = now_utc.replace(hour=16, minute=0, second=0, microsecond=0)
        # Ends at 6:00 UTC the NEXT day
        hunt_end = now_utc.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # CRITICAL FIX: Check if it's before the END time, not the start time
        if now_utc < hunt_end:
            events.append(("hunt", hunt_start, hunt_end))

    # Guild Dance (10:30 AM PDT ≈ 17:30 UTC)
    if weekday in DANCE_DAYS:
        dance_start = now_utc.replace(hour=17, minute=30, second=0, microsecond=0)
        # Ends at 5:30 UTC the NEXT day
        dance_end = now_utc.replace(hour=5, minute=30, second=0, microsecond=0) + timedelta(days=1)

        if now_utc < dance_end:
            events.append(("dance", dance_start, dance_end))

    return min(events, key=lambda x: x[1], default=None)

async def scheduler():
    await client.wait_until_ready()

    channel = client.get_channel(GUILD_CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(GUILD_CHANNEL_ID)

    role_mention = f"<@&{PING_ROLE_ID}>"
    last_fired = None

    while not client.is_closed():
        now = datetime.now(timezone.utc)
        event = get_today_schedule(now)

        if event:
            event_type, start_time, end_time = event

            # Prevent spamming the channel once it fires
            if last_fired == start_time:
                await asyncio.sleep(60)
                continue

            # Check if it's time to fire
            if now >= start_time:
                last_fired = start_time

                if event_type == "hunt":
                    await channel.send(
                        f"{role_mention} ⚔️ **Guild Hunt is live!**\n"
                        f"Ends in: <t:{int(end_time.timestamp())}:R>"
                    )

                elif event_type == "dance":
                    await channel.send(
                        f"{role_mention} 💃 **Guild Dance is live!**\n"
                        f"Ends in: <t:{int(end_time.timestamp())}:R>"
                    )

        # Check every minute
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (PRODUCTION MODE)")
    client.loop.create_task(scheduler())

keep_alive()
client.run(TOKEN)
