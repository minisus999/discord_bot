import hashlib
import os
import threading
import uuid
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Set to track active farming processes
active_farmers = set()

# URL Settings
JOIN_URL = "https://blackhammerco.com/def4/join_20250818.php"
REWARD_URL = "https://blackhammerco.com/def4/reward_2026_06_15.php"

LID = "English"
OID = "and"

# === ID АДМИНИСТРАТОРА (Твой Discord ID) ===
ADMIN_DISCORD_ID = 535111936178651171

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
    return files


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Бот {bot.user} успешно запущен и синхронизирован!")


@bot.tree.command(name="startdef", description="Запустить автофарм")
@app_commands.describe(
    target_user="Кому запустить фарм (доступно только создателю)"
)
async def startdef(
    interaction: discord.Interaction, target_user: discord.Member = None
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
            "❌ Этот пользователь не настроен в словаре USER_DATA!",
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

    active_farmers.add(account_id)
    await interaction.followup.send(
        f"🚀 Автофарм успешно запущен для игрока **{nickname}**!", ephemeral=True
    )


@bot.tree.command(name="stop", description="Остановить фарм")
async def stop(interaction: discord.Interaction):
    await interaction.response.send_message(
        "⏹ Остановка процессов...", ephemeral=True
    )
    active_farmers.clear()
    await interaction.followup.send(
        "🛑 Все активные процессы фарминга остановлены.", ephemeral=True
    )


# Токен подтягивается из переменных окружения Render
bot.run(os.getenv("DISCORD_TOKEN"))
