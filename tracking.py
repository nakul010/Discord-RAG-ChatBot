import os, re
import discord
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, time, timedelta, timezone
from supabase import create_client, Client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

USER_PATTERN = re.compile(r"^[a-zA-Z0-9_\.]{2,32}")
COIN_EARNED_PATTERN = re.compile(r"(?<=You gain\s)\d+(?=\s<:Stackcoin:)")
track = {}

scheduler = AsyncIOScheduler()


async def process_embeds(embeds: discord.Embed, message_id: int):
    """
    Process embeds to extract user activity.
    """
    for embed in embeds:
        leaderboard = embed.description
        if leaderboard:
            user_match = re.search(USER_PATTERN, leaderboard)
            user = user_match.group(0) if user_match else None

            coins_match = re.search(COIN_EARNED_PATTERN, leaderboard)
            coins = coins_match.group(0) if coins_match else None

            if user and coins:
                await upsert_user_data(user, int(coins), message_id)
                if user not in track:
                    track[user] = {"coins": int(coins), "count": 1}
                else:
                    track[user]["coins"] += int(coins)
                    track[user]["count"] += 1


async def upsert_user_data(
    username: str,
    coins_earned: int,
    message_id: int,
    count: int = 1,
):
    """
    Upsert user activity into the database.
    """
    try:
        existing_data = (
            supabase.table("stacking_activity")
            .select("*")
            .eq("username", username)
            .execute()
        )
        if existing_data.data:
            supabase.table("stacking_activity").update(
                {
                    "coins_earned": existing_data.data[0]["coins_earned"]
                    + coins_earned,
                    "count": existing_data.data[0]["count"] + count,
                    "modified_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("username", username).execute()

            supabase.table("message_tracking").insert(
                {
                    "username": username,
                    "message_id": message_id,
                }
            ).execute()
        else:
            supabase.table("stacking_activity").insert(
                {
                    "username": username,
                    "coins_earned": coins_earned,
                    "count": count,
                }
            ).execute()

            supabase.table("message_tracking").insert(
                {
                    "username": username,
                    "message_id": message_id,
                }
            ).execute()
    except Exception as e:
        print(f"Error upserting user data: {e}")


async def generate_report():
    try:
        data = supabase.table("stacking_activity").select("*").execute()

        if data.data:
            milestone_achieved_lines = []
            milestone_not_achieved_lines = []

            for user in data.data:
                if user["count"] >= 7:
                    milestone_achieved_lines.append(
                        f"!give-coins @{user['username']} 1200"
                    )
                else:
                    milestone_not_achieved_lines.append(
                        f"!give-coins @{user['username']} {user['count'] * 100}"
                    )

            milestone_achieved_report = (
                "\n".join(milestone_achieved_lines)
                if milestone_not_achieved_lines
                else ""
            )
            milestone_not_achieved_report = (
                "\n".join(milestone_not_achieved_lines)
                if milestone_not_achieved_lines
                else ""
            )
            return milestone_achieved_report, milestone_not_achieved_report
        else:
            return "No data available for generating the report.", ""

    except Exception as e:
        print(f"Error generating report: {e}")
        return "An error occurred while generating the report.", ""
