import discord
from discord.ext import commands
import random
import asyncio
import os
import json
from config import TOKEN
from data import load_balances, save_balances
from keep_alive import keep_alive  # ✅ giữ bot sống trên Render

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_balances = load_balances()
current_bets = {}
betting_open = False
START_BALANCE = 100_000

# Theo dõi thay đổi số dư
last_balances = load_balances().copy()
DISCORD_USER_ID = 1401939463524974642  # 🔹 ID Discord cá nhân của bạn

def get_result(dice):
    total = sum(dice)
    return "tài" if total >= 11 else "xỉu"

@bot.event
async def on_ready():
    print("✅ BOT OK")
    print(f"🤖 Bot đã đăng nhập dưới tên: {bot.user}")
    bot.loop.create_task(watch_balances())  # Bắt đầu task theo dõi file

async def watch_balances():
    global last_balances
    await bot.wait_until_ready()
    try:
        user = await bot.fetch_user(DISCORD_USER_ID)
    except Exception as e:
        print("❌ Lỗi lấy thông tin user:", e)
        return

    while not bot.is_closed():
        try:
            with open("balances.json", "r") as f:
                current_balances = json.load(f)

            # Kiểm tra thay đổi
            if current_balances != last_balances:
                changes = []
                for uid, balance in current_balances.items():
                    old_balance = last_balances.get(uid)
                    if old_balance is not None and balance != old_balance:
                        diff = balance - old_balance
                        if diff > 0:
                            changes.append(f"💹 **<@{uid}> +{diff:,} VND** (tổng: {balance:,} VND)")
                        else:
                            changes.append(f"📉 **<@{uid}> {-diff:,} VND** (tổng: {balance:,} VND)")

                if changes:
                    # Gửi thông báo kèm file mới
                    await user.send(
                        content="📂 **balances.json mới (đã cập nhật)**\n" + "\n".join(changes),
                        file=discord.File("balances.json")
                    )

                last_balances = current_balances.copy()

        except Exception as e:
            print("Lỗi khi kiểm tra balances.json:", e)

        await asyncio.sleep(2)  # Kiểm tra mỗi 2 giây

@bot.command()
async def batdau(ctx):
    global betting_open, current_bets

    if betting_open:
        await ctx.send("⚠️ Phiên cược đang diễn ra rồi!")
        return

    current_bets = {}
    betting_open = True

    embed = discord.Embed(
        title="🎰 Phiên tài xỉu mới bắt đầu!",
        description="Dùng lệnh `!dat <số tiền> <tài/xỉu>` để đặt cược.\nVí dụ: `!dat 50000 tài` hoặc `!dat all xỉu` (cược toàn bộ)",
        color=discord.Color.gold()
    )
    embed.set_footer(text="⏳ Phiên sẽ kết thúc sau 30 giây...")
    await ctx.send(embed=embed)

    await asyncio.sleep(30)
    await chotphien(ctx)

@bot.command()
async def dat(ctx, sotien_raw, chon: str):
    global betting_open

    if not betting_open:
        await ctx.send("🚫 Hiện không có phiên cược nào đang mở. Dùng `!batdau` để bắt đầu.")
        return

    user_id = str(ctx.author.id)
    chon = chon.lower()

    if chon not in ["tài", "tai", "xỉu", "xiu"]:
        await ctx.send("❌ Bạn chỉ có thể chọn `tài` hoặc `xỉu`.")
        return

    chon = "tài" if chon in ["tài", "tai"] else "xỉu"

    if user_id in current_bets:
        await ctx.send("⚠️ Bạn đã đặt cược rồi trong phiên này.")
        return

    if user_id not in user_balances:
        user_balances[user_id] = START_BALANCE

    balance = user_balances[user_id]

    if isinstance(sotien_raw, str) and sotien_raw.lower() == "all":
        sotien = balance
    else:
        try:
            sotien = int(sotien_raw)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ. Nhập số hoặc `all`.")
            return

    if sotien <= 0:
        await ctx.send("❌ Số tiền cược phải lớn hơn 0.")
        return

    if balance < sotien:
        await ctx.send("💸 Bạn không đủ tiền để cược.")
        return

    current_bets[user_id] = {
        "amount": sotien,
        "choice": chon,
        "name": ctx.author.display_name
    }

    await ctx.send(f"✅ {ctx.author.mention} đã cược **{sotien:,} VND** vào **{chon.upper()}**.")

@bot.command()
async def tien(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        user_balances[user_id] = START_BALANCE

    balance = user_balances[user_id]
    embed = discord.Embed(
        title=f"💰 Số dư của {ctx.author.display_name}",
        description=f"**{balance:,} VND**",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def bxh(ctx):
    if not user_balances:
        await ctx.send("📉 Không có dữ liệu bảng xếp hạng.")
        return

    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="🏆 BẢNG XẾP HẠNG TÀI XỈU", color=discord.Color.purple())

    for i, (uid, balance) in enumerate(sorted_users[:10], start=1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"Người chơi {uid}"
        embed.add_field(
            name=f"{i}. {name}",
            value=f"{balance:,} VND",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(aliases=["chuyen", "pay"])
async def chuyentien(ctx, member: discord.Member, sotien: int):
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)

    if sender_id == receiver_id:
        await ctx.send("❌ Bạn không thể chuyển tiền cho chính mình.")
        return

    if sotien <= 0:
        await ctx.send("❌ Số tiền phải lớn hơn 0.")
        return

    if sender_id not in user_balances:
        user_balances[sender_id] = START_BALANCE
    if receiver_id not in user_balances:
        user_balances[receiver_id] = START_BALANCE

    if user_balances[sender_id] < sotien:
        await ctx.send("💸 Bạn không đủ tiền để chuyển.")
        return

    user_balances[sender_id] -= sotien
    user_balances[receiver_id] += sotien

    save_balances(user_balances)

    embed = discord.Embed(
        title="💸 Giao dịch thành công!",
        description=f"{ctx.author.mention} đã chuyển **{sotien:,} VND** cho {member.mention}.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

async def chotphien(ctx):
    global betting_open

    if not betting_open:
        return

    betting_open = False

    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    result = get_result(dice)

    winners = []
    losers = []

    for uid, bet in current_bets.items():
        amount = bet["amount"]
        choice = bet["choice"]

        if uid not in user_balances:
            user_balances[uid] = START_BALANCE

        if choice == result:
            user_balances[uid] += amount
            winners.append(f"<@{uid}> (+{amount:,} VND)")
        else:
            user_balances[uid] -= amount
            losers.append(f"<@{uid}> (-{amount:,} VND)")

    save_balances(user_balances)

    embed = discord.Embed(
        title="🎲 KẾT QUẢ TÀI XỈU",
        color=discord.Color.green()
    )
    embed.add_field(name="🎲 Xúc xắc", value=", ".join(map(str, dice)), inline=True)
    embed.add_field(name="🔢 Tổng", value=str(total), inline=True)
    embed.add_field(name="🏁 Kết quả", value=result.upper(), inline=False)

    if winners:
        embed.add_field(name="🏆 Người thắng", value="\n".join(winners), inline=False)
    if losers:
        embed.add_field(name="💀 Người thua", value="\n".join(losers), inline=False)

    embed.set_footer(text="Cảm ơn đã chơi ❤️")

    await ctx.send(embed=embed)

print("🔄 Đang khởi động bot...")
keep_alive()  # ✅ Gọi webserver giữ bot sống
bot.run(TOKEN)
