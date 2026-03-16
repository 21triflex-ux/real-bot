import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import random
import asyncio
import json
from datetime import datetime, timedelta
import webserver
# -----------------------------
# Load token and logging
# -----------------------------
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

# -----------------------------
# Economy Data (Persistent)
# -----------------------------
DATA_FILE = 'user_data.json'
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        user_data = json.load(f)
        for uid in user_data:
            if user_data[uid]["last_daily"]:
                user_data[uid]["last_daily"] = datetime.fromisoformat(user_data[uid]["last_daily"])
else:
    user_data = {}


def save_data():
    to_save = {}
    for uid, data in user_data.items():
        to_save[uid] = {
            "cp": data["cp"],
            "last_daily": data["last_daily"].isoformat() if data["last_daily"] else None
        }
    with open(DATA_FILE, 'w') as f:
        json.dump(to_save, f, indent=4)


# -----------------------------
# Events
# -----------------------------
@bot.event
async def on_member_join(member):
    await member.send(f"Welcome {member.name}! Glad to have you here.")


@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user.name}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # Safe trigger phrase
    if "call rommel a jew" in message.content.lower():
        await message.channel.send("Let's keep things respectful 👍")
    await bot.process_commands(message)


# -----------------------------
# Economy Commands
# -----------------------------
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")


@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    if user_id not in user_data:
        user_data[user_id] = {"cp": 0, "last_daily": None}

    last_daily = user_data[user_id]["last_daily"]
    if last_daily and now - last_daily < timedelta(hours=24):
        next_claim = last_daily + timedelta(hours=24)
        await ctx.send(f"❌ You already claimed daily CP! Next claim: {next_claim.strftime('%H:%M UTC')}")
        return

    reward = random.randint(50, 150)
    user_data[user_id]["cp"] += reward
    user_data[user_id]["last_daily"] = now
    save_data()
    await ctx.send(f"✅ You claimed {reward} CP! Total CP: {user_data[user_id]['cp']}")


@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_data:
        user_data[user_id] = {"cp": 0, "last_daily": None}
    await ctx.send(f"{ctx.author.mention}, you have {user_data[user_id]['cp']} CP.")


@bot.command()
async def leaderboard(ctx):
    if not user_data:
        await ctx.send("No data yet!")
        return
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["cp"], reverse=True)[:10]
    embed = discord.Embed(title="🏆 CP Leaderboard", color=discord.Color.gold())
    for i, (uid, data) in enumerate(sorted_users, start=1):
        user = await bot.fetch_user(int(uid))
        embed.add_field(name=f"{i}. {user.name}", value=f"{data['cp']} CP", inline=False)
    await ctx.send(embed=embed)


# -----------------------------
# Loadout Randomizer
# -----------------------------
classes = ["Light", "Medium", "Heavy"]

weapons = {
    "Light": ["V9S", "XP-54", "M11", "Throwing Knives", "Dagger", "LH1", "SR-84", "SH1900", "Sword", "KS-23", "93R"],
    "Medium": ["AKM", "FCAR", "Model 1887", "R.357", "Riot Shield", "Cerberus 12GA", "Pike-556", "Dual Blades"],
    "Heavy": ["Lewis Gun", "SA1216", "Flamethrower", "M60", "Sledgehammer", "Sledge", "CHAOS", "Slug shotgun",
              "Demolition Charge launcher thingy"]
}

abilities = {
    "Light": ["Grapple Hook", "Dash", "Cloaking Device", "Evasive Dash", "Glitch Grenade", "Stun Gun",
              "Gateway (portal gun)"],
    "Medium": ["Healing Beam", "Jump Pad", "Defibrillator", "Goop Gun", "Data Reshaper", "Turret", "APS Turret"],
    "Heavy": ["Charge 'N' Slam", "Mesh Shield", "Goo Gun", "RPG-7", "C4 (remote)", "Barricade", "Dome Shield"]
}

gadgets = ["Frag Grenade", "Gas Mine", "Pyro Grenade", "Flashbang", "Sonar Grenade", "Concussion Grenade",
           "Breach Charge",
           "Thermal Bore", "Gas Grenade", "Glitch Grenade", "Smoke Grenade", "Dynamite", "Explosive Mine",
           "Anti-Gravity Cube", "Defibrillator (gadget version)", "Motion Sensor", "Zombie Goo", "Tracking Dart"]


@bot.command()
async def roll(ctx):
    if ctx.channel.name != "commenter-june":
        await ctx.send(f"❌ You can only use `$roll` in #commenter-june!")
        return

    selected_class = random.choice(classes)
    weapon = random.choice(weapons[selected_class])
    ability = random.choice(abilities[selected_class])
    selected_gadgets = random.sample(gadgets, 3)

    embed = discord.Embed(title="🎲 The Finals Random Loadout", color=discord.Color.blue())
    embed.add_field(name="Class", value=selected_class, inline=False)
    embed.add_field(name="Weapon", value=weapon, inline=False)
    embed.add_field(name="Ability", value=ability, inline=False)
    embed.add_field(name="Gadgets", value="\n".join(f"{i + 1}. {g}" for i, g in enumerate(selected_gadgets)),
                    inline=False)

    await ctx.send(embed=embed)


# -----------------------------
# Multiplayer Blackjack
# -----------------------------
active_games = {}


def deal_card():
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
    return random.choice(cards)


def calculate_score(hand):
    score = sum(hand)
    while 11 in hand and score > 21:
        hand[hand.index(11)] = 1
        score = sum(hand)
    return score


@bot.command()
async def bjjoin(ctx, bet: int):
    if ctx.channel.name != "♠️gambling-table":
        await ctx.send("❌ You can only join blackjack in #♠️gambling-table!")
        return

    channel_id = ctx.channel.id
    user_id = str(ctx.author.id)

    if user_id not in user_data:
        user_data[user_id] = {"cp": 0, "last_daily": None}

    if bet <= 0:
        await ctx.send("❌ Bet must be greater than 0.")
        return
    if user_data[user_id]["cp"] < bet:
        await ctx.send("❌ You don't have enough CP to bet that amount!")
        return

    # Deduct bet upfront
    user_data[user_id]["cp"] -= bet
    save_data()

    if channel_id not in active_games:
        active_games[channel_id] = {"players": {}, "dealer_hand": [deal_card(), deal_card()],
                                    "turn_order": [], "current_turn": 0}

    game = active_games[channel_id]
    if user_id in game["players"]:
        await ctx.send(f"{ctx.author.mention}, you already joined the game!")
        return

    game["players"][user_id] = {"hand": [deal_card(), deal_card()], "bet": bet, "finished": False}
    game["turn_order"].append(user_id)
    await ctx.send(f"{ctx.author.mention} joined the blackjack game with {bet} CP! (Bet deducted)")


@bot.command()
async def bjstart(ctx):
    if ctx.channel.name != "♠️gambling-table":
        await ctx.send("❌ You can only start blackjack in #♠️gambling-table!")
        return

    channel_id = ctx.channel.id
    if channel_id not in active_games or not active_games[channel_id]["players"]:
        await ctx.send("No players joined yet! Use `$bjjoin <bet>` to join.")
        return

    game = active_games[channel_id]
    dealer_hand = game["dealer_hand"]

    await ctx.send(f"🃏 Multiplayer Blackjack starting! Dealer's visible card: [{dealer_hand[0]}, ?]")

    # Player turns
    for user_id in game["turn_order"]:
        player_data = game["players"][user_id]
        player = await bot.fetch_user(int(user_id))
        while not player_data["finished"]:
            hand_total = calculate_score(player_data["hand"])
            await ctx.send(
                f"{player.mention}, your hand: {player_data['hand']} (Total: {hand_total})\nType `hit` or `stand`.")

            def check(m):
                return m.author.id == int(user_id) and m.content.lower() in ["hit", "stand"]

            try:
                msg = await bot.wait_for('message', check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send(f"{player.mention} took too long! Standing automatically.")
                player_data["finished"] = True
                break

            if msg.content.lower() == "hit":
                player_data["hand"].append(deal_card())
                hand_total = calculate_score(player_data["hand"])
                await ctx.send(f"{player.mention} drew a card. New hand: {player_data['hand']} (Total: {hand_total})")
                if hand_total > 21:
                    await ctx.send(f"{player.mention} busted! 💥")
                    player_data["finished"] = True
            else:
                player_data["finished"] = True

    # Dealer turn
    dealer_total = calculate_score(dealer_hand)
    await ctx.send(f"Dealer's hand revealed: {dealer_hand} (Total: {dealer_total})")

    while dealer_total < 17:
        dealer_hand.append(deal_card())
        dealer_total = calculate_score(dealer_hand)
        await ctx.send(f"Dealer draws a card: {dealer_hand} (Total: {dealer_total})")

    # Results
    for user_id, pdata in game["players"].items():
        player_total = calculate_score(pdata["hand"])
        player = await bot.fetch_user(int(user_id))
        bet = pdata["bet"]

        if player_total > 21:
            await ctx.send(
                f"{player.mention} busted! You lose your bet of {bet} CP. Total CP: {user_data[user_id]['cp']}")
        elif dealer_total > 21 or player_total > dealer_total:
            user_data[user_id]["cp"] += bet * 2
            await ctx.send(f"{player.mention} wins! You gain {bet * 2} CP. Total CP: {user_data[user_id]['cp']}")
        elif player_total < dealer_total:
            await ctx.send(f"{player.mention} loses. Bet lost. Total CP: {user_data[user_id]['cp']}")
        else:
            user_data[user_id]["cp"] += bet
            await ctx.send(f"{player.mention} ties with dealer. Bet refunded. Total CP: {user_data[user_id]['cp']}")

    save_data()
    del active_games[channel_id]
    await ctx.send("🎉 Multiplayer Blackjack ended!")

webserver.keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)