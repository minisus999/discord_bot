import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import threading
import hashlib
import random
import uuid
import discord
from discord.ext import commands
import requests as r

# === ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы бот не засыпал) ===


class SimpleHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Bot is alive!")

  def log_message(self, format, *args):
    pass


def run_server():
  port = int(os.environ.get("PORT", 10000))
  server = HTTPServer(("0.0.0.0", port), SimpleHandler)
  server.serve_forever()


# Запускаем веб-сервер в отдельном потоке
threading.Thread(target=run_server, daemon=True).start()

# ====================================================

# URL Settings
JOIN_URL = "https://blackhammerco.com/def4/join_20250818.php"
REWARD_URL = "https://blackhammerco.com/def4/reward_2026_06_15.php"

LID = "English"
OID = "and"

# === DISCORD USER MAPPINGS -> (GAME ID, NICKNAME) ===
USER_DATA = {
    1107683363457876029: {
        "game_id": "a_7857234430897713376",
        "nickname": "OverdoseM",
    },
    535111936178651171: {
        "game_id": "a_3066415753614056779",
        "nickname": "JonSmith",
    },
    498781215306809344: {
        "game_id": "a_3693527683322122883",
        "nickname": "pokida",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Set to track active farming processes
active_farmers = set()


def get_session_data(account_id):
  pid = uuid.uuid4().hex
  sid = "join"
  input1 = "English"
  input2 = account_id
  input3 = "and"
  input4 = "0"
  did = "did"

  raw_string = f"{account_id}{sid}{pid}{input1}{input2}{input3}{input4}"
  eid = hashlib.md5(raw_string.encode("utf-8")).hexdigest()

  files = {
      "id": (None, account_id),
      "sid": (None, sid),
      "pid": (None, pid),
      "lid": (None, LID),
      "oid": (None, OID),
      "did": (None, did),
      "input1": (None, input1),
      "input2": (None, input2),
      "input3": (None, input3),
      "input4": (None, input4),
      "eid": (None, eid),
  }

  try:
    response = r.post(JOIN_URL, files=files, timeout=10)
    if response.status_code == 200:
      text = response.text.strip()
      parts = text.split("|")
      extracted_did = parts[-1]
      return pid, extracted_did
  except Exception as e:
    print(e)

  return pid, "1028451"


def generate_reward_payload(user_game_id, user_nickname, pid, did):
  round_seconds = random.randint(360, 420)

  start_time = random.uniform(70_000_000.0, 71_000_000.0)
  end_time = start_time + random.uniform(100_000.0, 999_999.0)

  damage1 = start_time
  damage2 = end_time

  input5_val = f"5,{round_seconds},3,{start_time:.5f},{end_time:.5f},"
  input6_val = f"{user_nickname},{damage2},Necromancer_default,0!"

  payload = {
      "id": user_game_id,
      "sid": "reward",
      "pid": pid,
      "lid": LID,
      "oid": OID,
      "did": did,
      "input1": "0",
      "input2": "26",
      "input3": "15",
      "input4": "1",
      "input5": input5_val,
      "input6": input6_val,
      "input7": "1110010000",
      "input8": "0",
  }

  hash_fields = [
      payload["id"],
      payload["sid"],
      payload["pid"],
      payload["input1"],
      payload["input2"],
      payload["input3"],
      payload["input4"],
      payload["input5"],
      payload["input6"],
      payload["input7"],
      payload["input8"],
  ]
  payload["eid"] = hashlib.md5("".join(hash_fields).encode("utf-8")).hexdigest()
  return payload, round_seconds


async def run_farming_process(
    user_discord_id, channel, games_count, min_delay, max_delay
):
  user_game_id = USER_DATA[user_discord_id]["game_id"]
  user_nickname = USER_DATA[user_discord_id]["nickname"]

  active_farmers.add(user_discord_id)

  await channel.send(
      f"🚀 Starting auto-farm for <@{user_discord_id}> (nickname:"
      f" **{user_nickname}**): **{games_count}** game(s) with a delay from"
      f" **{min_delay}** to **{max_delay}** sec...\n*(To stop, send `/stop` or"
      " `!stop`)*"
  )

  try:
    pid, did = get_session_data(user_game_id)

    for i in range(1, games_count + 1):
      if user_discord_id not in active_farmers:
        await channel.send(
            f"⏹️ Auto-farm for <@{user_discord_id}> was stopped prematurely."
        )
        return

      data, round_sec = generate_reward_payload(
          user_game_id, user_nickname, pid, did
      )

      reward_headers = HEADERS.copy()
      reward_headers["Content-Type"] = "application/x-www-form-urlencoded"

      try:
        response = r.post(
            REWARD_URL, data=data, headers=reward_headers, timeout=10
        )
        if response.status_code == 200:
          await channel.send(
              f"🎮 [{i}/{games_count}] Game sent (PID: `{pid[:8]}...`)."
              f" Response: `{response.text.strip()}`"
          )
        else:
          await channel.send(
              f"❌ [{i}/{games_count}] Server error: {response.status_code}"
          )
      except Exception as e:
        await channel.send(f"❌ [{i}/{games_count}] Network error: `{e}`")

      if i < games_count:
        sleep_time = random.randint(min_delay, max_delay)
        await channel.send(
            f"⏳ Waiting {sleep_time} sec. before the next launch..."
        )

        for _ in range(sleep_time):
          if user_discord_id not in active_farmers:
            await channel.send(
                f"⏹️ Auto-farm for <@{user_discord_id}> was stopped prematurely."
            )
            return
          await asyncio.sleep(1)

    await channel.send(
        f"✅ All scheduled games for <@{user_discord_id}> are completed!"
    )
  finally:
    active_farmers.discard(user_discord_id)


@bot.event
async def on_ready():
  try:
    # Глобальная синхронизация команд для всех серверов
    synced = await bot.tree.sync()
    print(f"Synchronized {len(synced)} global slash commands.")
  except Exception as e:
    print(e)
  print(f"Bot {bot.user} successfully started!")


# 1. Slash command /startdef
@bot.tree.command(
    name="startdef", description="Start auto-farming linked to your Discord ID"
)
@discord.app_commands.describe(
    games_count="Number of games (default 1)",
    min_delay="Minimum delay in sec (default 10)",
    max_delay="Maximum delay in sec (default 20)",
)
async def startdef_slash(
    interaction: discord.Interaction,
    games_count: int = 1,
    min_delay: int = 10,
    max_delay: int = 20,
):
  user_discord_id = interaction.user.id

  if user_discord_id not in USER_DATA:
    await interaction.response.send_message(
        "❌ You do not have a linked game account! Contact the bot"
        " administrator.",
        ephemeral=True,
    )
    return

  if user_discord_id in active_farmers:
    await interaction.response.send_message(
        "⚠️ You already have an active auto-farm running! Wait for it to finish"
        " or send `/stop`.",
        ephemeral=True,
    )
    return

  if min_delay > max_delay:
    await interaction.response.send_message(
        "❌ Error: minimum delay cannot be greater than maximum delay!",
        ephemeral=True,
    )
    return

  await interaction.response.send_message(
      "🚀 Initializing auto-farm slash command...", ephemeral=True
  )
  asyncio.create_task(
      run_farming_process(
          user_discord_id,
          interaction.channel,
          games_count,
          min_delay,
          max_delay,
      )
  )


# 2. Slash command /stop
@bot.tree.command(name="stop", description="Stop the current auto-farm")
async def stop_slash(interaction: discord.Interaction):
  user_discord_id = interaction.user.id
  if user_discord_id in active_farmers:
    active_farmers.discard(user_discord_id)
    await interaction.response.send_message(
        f"🛑 <@{user_discord_id}>, your auto-farm will stop after the current"
        " step.",
        ephemeral=False,
    )
  else:
    await interaction.response.send_message(
        f"❌ <@{user_discord_id}>, you currently have no active farming"
        " processes.",
        ephemeral=True,
    )


# 3. Text command !startdef (fallback)
@bot.command(name="startdef")
async def startdef_text(
    ctx, games_count: int = 1, min_delay: int = 10, max_delay: int = 20
):
  user_discord_id = ctx.author.id

  if user_discord_id not in USER_DATA:
    await ctx.send(
        "❌ You do not have a linked game account! Contact the bot"
        " administrator.",
        delete_after=10,
    )
    return

  if user_discord_id in active_farmers:
    await ctx.send(
        "⚠️ You already have an active auto-farm running! Wait for it to finish"
        " or send `!stop`.",
        delete_after=10,
    )
    return

  if min_delay > max_delay:
    await ctx.send(
        "❌ Error: minimum delay cannot be greater than maximum delay!"
    )
    return

  asyncio.create_task(
      run_farming_process(
          user_discord_id, ctx.channel, games_count, min_delay, max_delay
      )
  )


# 4. Text command !stop (fallback)
@bot.command(name="stop")
async def stop_text(ctx):
  user_discord_id = ctx.author.id
  if user_discord_id in active_farmers:
    active_farmers.discard(user_discord_id)
    await ctx.send(
        f"🛑 <@{user_discord_id}>, your auto-farm will stop after the current"
        " step."
    )
  else:
    await ctx.send(
        f"❌ <@{user_discord_id}>, you currently have no active farming"
        " processes.",
        delete_after=10,
    )


# Запуск бота через переменную окружения Render
bot.run(os.environ.get("DISCORD_TOKEN"))
