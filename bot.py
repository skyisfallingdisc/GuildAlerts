import discord
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

GUILD_CHANNEL_ID = 1507797912111939755
PING_ROLE_ID = 1507799489312985238
PING_ROLE_ID_2 = 1511085696121700533

HUNT_DAYS = [4, 5, 6]   # Fri/Sat/Sun
DANCE_DAYS = [4]        # Friday only

def get_today_schedule(now_pacific):
    weekday = now_pacific.weekday()  # 0=Mon, 1=Tue, ..., 3=Thu, 4=Fri, 5=Sat, 6=Sun
    events = []

    # 1. Guild Hunt (9:00 AM - 11:00 PM)
    if weekday in HUNT_DAYS:
        hunt_start = now_pacific.replace(hour=9, minute=0, second=0, microsecond=0)
        hunt_end = now_pacific.replace(hour=23, minute=0, second=0, microsecond=0)
        if now_pacific < hunt_end:
            events.append(("hunt", hunt_start, hunt_end))

    # 2. Guild Dance (10:30 AM - 10:30 PM)
    if weekday in DANCE_DAYS:
        dance_start = now_pacific.replace(hour=10, minute=30, second=0, microsecond=0)
        dance_end = now_pacific.replace(hour=22, minute=30, second=0, microsecond=0)
        if now_pacific < dance_end:
            events.append(("dance", dance_start, dance_end))

    # 3. Daily Reset (Every Day 11:00 PM - 12:00 AM)
    daily_start = now_pacific.replace(hour=23, minute=0, second=0, microsecond=0)
    daily_end = daily_start + timedelta(hours=1)
    if now_pacific < daily_end:
        events.append(("daily_reset", daily_start, daily_end))

    # 4. Weekly Reset (Sunday night 12:00 AM ≈ Monday 00:00 AM)
    if weekday == 0: 
        weekly_start = now_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
        events.append(("weekly_reset", weekly_start, None))

    # 5. Raid Reminder (Thursday night 11:00 PM)
    if weekday == 3: 
        raid_rem_start = now_pacific.replace(hour=23, minute=0, second=0, microsecond=0)
        events.append(("raid_reminder", raid_rem_start, None))

    # 6. Raid Start (Friday night 11:00 PM)
    if weekday == 4: 
        raid_start = now_pacific.replace(hour=23, minute=0, second=0, microsecond=0)
        events.append(("raid_actual", raid_start, None))

    # 7. Stimens (Every 2 weeks Sunday night 12:00 AM ≈ Monday 00:00 AM)
    if weekday == 0:
        if now_pacific.isocalendar()[1] % 2 == 1:
            stimens_start = now_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
            events.append(("stimens", stimens_start, None))

    return events 

async def scheduler():
    await client.wait_until_ready()

    channel = client.get_channel(GUILD_CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(GUILD_CHANNEL_ID)

    role_mention = f"<@&{PING_ROLE_ID}> <@&{PING_ROLE_ID_2}> \n"
    
    last_fired = set() 

    # --- RENDER RESTART PROTECTION ---
    print("Scanning channel history to rebuild memory...")
    pacific_tz = ZoneInfo("America/Los_Angeles")
    
    async for message in channel.history(limit=50):
        if message.author == client.user:
            msg_pdt = message.created_at.astimezone(pacific_tz)
            msg_date_str = msg_pdt.strftime("%Y-%m-%d")
            
            if "Guild Hunt is live!" in message.content:
                last_fired.add(("hunt", msg_date_str))
            elif "Guild Dance is live!" in message.content:
                last_fired.add(("dance", msg_date_str))
            elif "Daily Reset is soon!" in message.content:
                last_fired.add(("daily_reset", msg_date_str))
            elif "Weekly Reset has occurred" in message.content:
                last_fired.add(("weekly_reset", msg_date_str))
            elif "Raid Reminder:" in message.content:
                last_fired.add(("raid_reminder", msg_date_str))
            elif "Raid time!" in message.content:
                last_fired.add(("raid_actual", msg_date_str))
            elif "Stimens reset!" in message.content:
                last_fired.add(("stimens", msg_date_str))
                
    print(f"Memory rebuilt. Active restriction count: {len(last_fired)}")
    # ----------------------------------

    while not client.is_closed():
        now_pacific = datetime.now(pacific_tz)
        today_str = now_pacific.strftime("%Y-%m-%d")
        events = get_today_schedule(now_pacific)

        for event_type, start_time, end_time in events:
            if (event_type, today_str) in last_fired:
                continue

            if now_pacific >= start_time:
                last_fired.add((event_type, today_str))

                if event_type == "hunt":
                    await channel.send(f"{role_mention} ⚔️ **Guild Hunt is live!**\nEnds in: <t:{int(end_time.timestamp())}:R>")
                elif event_type == "dance":
                    await channel.send(f"{role_mention} 💃 **Guild Dance is live!**\nEnds in: <t:{int(end_time.timestamp())}:R>")
                elif event_type == "daily_reset":
                    await channel.send(f"{role_mention} 🔄 **Daily Reset is soon!**\nComplete your daily unstables, guild checkin & cargo, daily battlepass, lifeskill focus, and use up boss keys!\nReset in: <t:{int(end_time.timestamp())}:R>")
                elif event_type == "weekly_reset":
                    await channel.send(f"{role_mention} 📅 **Weekly Reset has occurred!**\nMake sure to check reclaim hub, pioneer rewards, season shop (for reforge stones), honor coins, and commissions!")
                elif event_type == "raid_reminder":
                    await channel.send(f"{role_mention} 📢 **Raid Reminder: Raid day is tomorrow night!**")
                elif event_type == "raid_actual":
                    await channel.send(f"{role_mention} 🐉 **Raid time! Come join!**")
                elif event_type == "stimens":
                    await channel.send(f"{role_mention} 🏯 **Stimens reset!**")

        # Clean old records from memory
        yesterday_str = (now_pacific - timedelta(days=1)).strftime("%Y-%m-%d")
        last_fired = {item for item in last_fired if item[1] >= yesterday_str}

        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (PRODUCTION MODE)")
    client.loop.create_task(scheduler())

keep_alive()
client.run(TOKEN)
