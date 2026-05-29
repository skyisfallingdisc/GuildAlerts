import discord
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Handles standard/daylight savings time automatically
from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

GUILD_CHANNEL_ID = 1507797912111939755
PING_ROLE_ID = 1507799489312985238

HUNT_DAYS = [4, 5, 6]   # Fri/Sat/Sun
DANCE_DAYS = [4]        # Friday only

def get_today_schedule(now_pacific):
    weekday = now_pacific.weekday()
    events = []

    # Guild Hunt (9:00 AM - 11:00 PM PDT/PST)
    if weekday in HUNT_DAYS:
        hunt_start = now_pacific.replace(hour=11, minute=29, second=0, microsecond=0)
        hunt_end = now_pacific.replace(hour=23, minute=0, second=0, microsecond=0)

        if now_pacific < hunt_end:
            events.append(("hunt", hunt_start, hunt_end))

    # Guild Dance (10:30 AM - 10:30 PM PDT/PST)
    if weekday in DANCE_DAYS:
        dance_start = now_pacific.replace(hour=11, minute=27, second=0, microsecond=0)
        dance_end = now_pacific.replace(hour=22, minute=30, second=0, microsecond=0)

        if now_pacific < dance_end:
            events.append(("dance", dance_start, dance_end))

    return events 

async def scheduler():
    await client.wait_until_ready()

    channel = client.get_channel(GUILD_CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(GUILD_CHANNEL_ID)

    role_mention = f"<@&{PING_ROLE_ID}>"
    
    # Use a set to track multiple fired events uniquely
    last_fired = set() 

    while not client.is_closed():
        # Track everything using Pacific Time to avoid UTC day-rollover issues
        now_pacific = datetime.now(ZoneInfo("America/Los_Angeles"))
        events = get_today_schedule(now_pacific)

        for event_type, start_time, end_time in events:
            # If this specific instance of the event has already fired, skip it
            if (event_type, start_time) in last_fired:
                continue

            # Check if it's time to fire
            if now_pacific >= start_time:
                last_fired.add((event_type, start_time))

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

        # Housekeeping: Clean up the last_fired set so it doesn't grow infinitely
        last_fired = {item for item in last_fired if now_pacific - item[1] < timedelta(days=1)}

        # Check every minute
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (PRODUCTION MODE)")
    client.loop.create_task(scheduler())

keep_alive()
client.run(TOKEN)
