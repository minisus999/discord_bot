import asyncio
import hashlib
import os
import random
import uuid
import discord
from discord import app_commands
from discord.ext import commands
import requests as r

# URL Settings
JOIN_URL = "https://blackhammerco.com/def4/join_20250818.php"
REWARD_URL = "https://blackhammerco.com/def4/reward_2026_06_15.php"

LID = "English"
OID = "and"

# === ID АДМИНИСТРАТОРА (Твой Discord ID) ===
ADMIN_DISCORD_ID = 535111936178651171

# === DISCORD USER MAPPINGS -> (GAME ID, NICKNAME) ===
USER_DATA = {
    # Твой аккаунт
    535111936178651171: {
        "game_id": "a_3693527683322122883",
        "nickname": "pokida",
    },
    # Другие игроки
    1107683363457876029: {
        "game_id": "a_7857234430897713376",
        "nickname": "OverdoseM",
    },
    # Если у JonSmith другой Discord ID, его можно будет обновить отдельно
    999999999999999999: {
        "game_id": "a_3066415753614056779",
        "nickname": "JonSmith",
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
    user_game_id, user_nickname, channel, games_count, min_delay, max_delay
):
    active_farmers.add(user_game_id)

    await channel.send(
        f"🚀 Starting auto-farm for (nickname: **{user_nickname}**):"
        f" **{games_count}** game(s) with a delay from **{min_delay}** to"
        f" **{max_delay}** sec...\n*(To stop, send `/stop`)*"
    )

    try:
        pid, did = get_session_data(user_game_id)

        for i in range(1, games_count + 1):
            if user_game_id not in active_farmers:
                await channel.send(
                    f"⏹️ Auto-farm for **{user_nickname}** was stopped"
                    " prematurely."
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
                        f"🎮 [{i}/{games_count}] Game sent for **{user_nickname}**"
                        f" (PID: `{pid[:8]}...`). Response:"
                        f" `{response.text.strip()}`"
                    )
                else:
                    await channel.send(
                        f"❌ [{i}/{games_count}] Server error:"
                        f" {response.status_code}"
                    )
            except Exception as e:
                await channel.send(f"❌ [{i}/{games_count}] Network error: `{e}`")

            if i < games_count:
                sleep_time = random.randint(min_delay, max_delay)
                await channel.send(
                    f"⏳ Waiting {sleep_time} sec. before the next launch..."
                )

                for _ in range(sleep_time):
                    if user_game_id not in active_farmers:
                        await channel.send(
                            f"⏹️ Auto-farm for **{user_nickname}** was stopped"
                            " prematurely."
                        )
                        return
                    await asyncio.sleep(1)

        await channel.send(
            f"✅ All scheduled games for **{user_nickname}** are completed!"
        )
    finally:
        active_farmers.discard(user_game_id)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synchronized global slash commands: {len(synced)}")
    except Exception as e:
        print(e)
    print(f"Bot {bot.user} successfully started!")


@bot.tree.command(name="startdef", description="Запустить автофарм")
@app_commands.describe(
    target_user="Кому запустить фарм (доступно только создателю)",
    games_count="Количество игр (по умолчанию 1)",
    min_delay="Мин. задержка в сек (по умолчанию 10)",
    max_delay="Макс. задержка в сек (по умолчанию 20)",
)
async def startdef_slash(
    interaction: discord.Interaction,
    target_user: discord.Member = None,
    games_count: int = 1,
    min_delay: int = 10,
    max_delay: int = 20,
):
    await interaction.response.send_message(
        "⚙️ Проверка параметров...", ephemeral=True
    )

    if target_user is not None:
        if interaction.user.id != ADMIN_DISCORD_ID:
            await interaction.followup.send(
                "❌ Только создатель бота может запускать фарм для других аккаунтов!",
                ephemeral=True,
            )
            return
        user_to_farm = target_user.id
    else:
        user_to_farm = interaction.user.id

    if user_to_farm not in USER_DATA:
        await interaction.followup.send(
            "❌ У этого пользователя нет привязанного игрового аккаунта!",
            ephemeral=True,
        )
        return

    acc_info = USER_DATA[user_to_farm]
    account_id = acc_info["game_id"]
    nickname = acc_info["nickname"]

    if account_id in active_farmers:
        await interaction.followup.send(
            f"⚠️ Автофарм для игрока **{nickname}** уже запущен!",
            ephemeral=True,
        )
        return

    if min_delay > max_delay:
        await interaction.followup.send(
            "❌ Ошибка: минимальная задержка не может быть больше максимальной!",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"🚀 Запуск автофарма для **{nickname}**...", ephemeral=True
    )
    asyncio.create_task(
        run_farming_process(
            account_id,
            nickname,
            interaction.channel,
            games_count,
            min_delay,
            max_delay,
        )
    )


@bot.tree.command(name="stop", description="Остановить все активные фармы")
async def stop_slash(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_DISCORD_ID:
        await interaction.response.send_message(
            "❌ Только создатель бота может останавливать процессы.",
            ephemeral=True,
        )
        return

    active_farmers.clear()
    await interaction.response.send_message(
        "🛑 Все активные процессы фарминга принудительно остановлены.",
        ephemeral=False,
    )


bot.run(os.getenv("DISCORD_TOKEN"))
