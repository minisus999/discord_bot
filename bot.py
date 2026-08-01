import asyncio
import hashlib
import os
import random
import uuid
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# URL Settings
JOIN_URL = "https://blackhammerco.com/def4/join_20250818.php"
REWARD_URL = "https://blackhammerco.com/def4/reward_2026_06_15.php"

LID = "English"
OID = "and"

# === DISCORD USER MAPPINGS -> (GAME ID, NICKNAME) ===
USER_DATA = {
    498781215306809344: {
        "game_id": "a_3693527683322122883",
        "nickname": "pokida",
    },
    1107683363457876029: {
        "game_id": "a_7857234430897713376",
        "nickname": "OverdoseM",
    },
    535111936178651171: {
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


async def get_session_data(account_id):
    pid = uuid.uuid4().hex
    sid = "join"
    input1 = "English"
    input2 = account_id
    input3 = "and"
    input4 = "0"
    did = "did"

    raw_string = f"{account_id}{sid}{pid}{input1}{input2}{input3}{input4}"
    eid = hashlib.md5(raw_string.encode("utf-8")).hexdigest()

    form = aiohttp.FormData()
    form.add_field("id", account_id)
    form.add_field("sid", sid)
    form.add_field("pid", pid)
    form.add_field("lid", LID)
    form.add_field("oid", OID)
    form.add_field("did", did)
    form.add_field("input1", input1)
    form.add_field("input2", input2)
    form.add_field("input3", input3)
    form.add_field("input4", input4)
    form.add_field("eid", eid)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                JOIN_URL, data=form, headers=HEADERS, timeout=10
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    parts = text.strip().split("|")
                    extracted_did = parts[-1]
                    return pid, extracted_did
    except Exception as e:
        print(f"Join error: {e}")

    return pid, "1028451"


def generate_reward_payload(user_game_id, user_nickname, pid, did):
    round_seconds = random.randint(360, 420)

    start_time = random.uniform(70_000_000.0, 71_000_000.0)
    end_time = start_time + random.uniform(100_000.0, 999_999.0)

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
    return payload


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
        pid, did = await get_session_data(user_game_id)

        for i in range(1, games_count + 1):
            if user_game_id not in active_farmers:
                await channel.send(
                    f"⏹️ Auto-farm for **{user_nickname}** was stopped"
                    " prematurely."
                )
                return

            data = generate_reward_payload(user_game_id, user_nickname, pid, did)

            reward_headers = HEADERS.copy()
            reward_headers["Content-Type"] = "application/x-www-form-urlencoded"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        REWARD_URL,
                        data=data,
                        headers=reward_headers,
                        timeout=10,
                    ) as response:
                        response_text = await response.text()
                        if response.status == 200:
                            await channel.send(
                                f"🎮 [{i}/{games_count}] Game sent for"
                                f" **{user_nickname}** (PID: `{pid[:8]}...`)."
                                f" Response: `{response_text.strip()}`"
                            )
                        else:
                            await channel.send(
                                f"❌ [{i}/{games_count}] Server error:"
                                f" {response.status}"
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


@bot.tree.command(name="startdef", description="Запустить автофарм для себя")
@app_commands.describe(
    games_count="Количество игр (по умолчанию 1)",
    min_delay="Мин. задержка в сек (по умолчанию 10)",
    max_delay="Макс. задержка в сек (по умолчанию 20)",
)
async def startdef_slash(
    interaction: discord.Interaction,
    games_count: int = 1,
    min_delay: int = 10,
    max_delay: int = 20,
):
    await interaction.response.defer(ephemeral=True)

    user_to_farm = interaction.user.id

    if user_to_farm not in USER_DATA:
        await interaction.followup.send(
            "❌ У вашего аккаунта Discord нет привязанного игрового профиля!",
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


@bot.tree.command(
    name="stop", description="Остановить свой активный фарм"
)
async def stop_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id
    if user_id not in USER_DATA:
        await interaction.followup.send(
            "❌ У вас нет привязанного аккаунта.", ephemeral=True
        )
        return

    account_id = USER_DATA[user_id]["game_id"]
    if account_id in active_farmers:
        active_farmers.discard(account_id)
        await interaction.followup.send(
            "🛑 Ваш процесс фарминга остановлен.", ephemeral=True
        )
    else:
        await interaction.followup.send(
            "⚠️ У вас нет активных запущенных процессов фарминга.",
            ephemeral=True,
        )


bot.run(os.getenv("DISCORD_TOKEN"))
