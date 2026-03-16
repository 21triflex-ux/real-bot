import discord
from discord.ext import commands
import logging
import os
import random
import asyncio
import json
from datetime import datetime, timedelta
import webserver

# -------------------------
# Token
# -------------------------
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

# -------------------------
# Logging
# -------------------------
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# -------------------------
# Bot Setup
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

# -------------------------
# Data Storage
# -------------------------
DATA_FILE = 'user_data.json'

try:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            user_data = json.load(f)
            for uid in user_data:
                if user_data[uid]["last_daily"]:
                    user_data[uid]["last_daily"] = datetime.fromisoformat(user_data[uid]["last_daily"])
    else:
        user_data = {}
except:
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

# -------------------------
# Events
# -------------------------
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

    if "call rommel a jew" in message.content.lower():
        await message.channel.send("Let's keep things respectful 👍")

    await bot.process_commands(message)

# -------------------------
# Basic Commands
# -------------------------
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

# -------------------------
# Economy
# -------------------------
@bot.command()
async def daily(ctx):

    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    if user_id not in user_data:
        user_data[user_id] = {"cp": 0, "last_daily": None}

    last_daily = user_data[user_id]["last_daily"]

    if last_daily and now - last_daily < timedelta(hours=24):

        next_claim = last_daily + timedelta(hours=24)

        await ctx.send(
            f"❌ You already claimed daily CP! Next claim: {next_claim.strftime('%H:%M UTC')}"
        )
        return

    reward = random.randint(50,150)

    user_data[user_id]["cp"] += reward
    user_data[user_id]["last_daily"] = now

    save_data()

    await ctx.send(
        f"✅ You claimed {reward} CP! Total CP: {user_data[user_id]['cp']}"
    )

@bot.command()
async def balance(ctx):

    user_id = str(ctx.author.id)

    if user_id not in user_data:
        user_data[user_id] = {"cp":0,"last_daily":None}

    await ctx.send(
        f"{ctx.author.mention}, you have {user_data[user_id]['cp']} CP."
    )

@bot.command()
async def leaderboard(ctx):

    if not user_data:
        await ctx.send("No data yet!")
        return

    sorted_users = sorted(
        user_data.items(),
        key=lambda x: x[1]["cp"],
        reverse=True
    )[:10]

    embed = discord.Embed(
        title="🏆 CP Leaderboard",
        color=discord.Color.gold()
    )

    for i,(uid,data) in enumerate(sorted_users,start=1):

        user = bot.get_user(int(uid))
        if not user:
            user = await bot.fetch_user(int(uid))

        embed.add_field(
            name=f"{i}. {user.name}",
            value=f"{data['cp']} CP",
            inline=False
        )

    await ctx.send(embed=embed)

# -------------------------
# THE FINALS Loadout
# -------------------------
classes = ["Light","Medium","Heavy"]

weapons = {
"Light":["V9S","XP-54","M11","Throwing Knives","Dagger","LH1","SR-84","Sword","93R","RECRUVE BOW","M26 MATTER],
"Medium":["AKM","FCAR","Model 1887","R.357","Riot Shield","Cerberus 12GA","Pike-556","Dual Blades","CL-40","CB-01","P90","FMAS"],
"Heavy":["Lewis Gun","SA1216","Flamethrower","M60","Sledgehammer","KS-23","Slug shotgun","Titan","Spear","50's","Shak","Mini Gun"]
}

abilities = {
"Light":["Grapple Hook","Dash","Cloaking Device"],
"Medium":["Healing Beam","Dematerializer","Turret"],
"Heavy":["Charge 'N' Slam","Mesh Shield","Cum Gun","Winch Claw"]
}

gadgets=[
"Frag Grenade","Gas Mine","Pyro Grenade","Flashbang","Sonar Grenade","Jump Pad","Defib","APS Turret","Breach Drill","Proxy Sensor","Dome Shield","Anti-Grav"
"Concussion Grenade","Breach Charge","Thermal Bore","Gas Grenade","Gate Way","ZipLine","Glitch Trap","Barricade","LockBolt","RPG","Healing Emitter",
"Glitch Grenade","Smoke Grenade","Dynamite","Explosive Mine,"Goo Grenade","Gravity Vortex","Tracking Dart","H+ Infuser","Vanishing Bomb"
]

@bot.command()
async def roll(ctx):

    if ctx.channel.name != "🤤commentor-june":
        await ctx.send("❌ You can only use `$roll` in 🤤commentor-june!")
        return

    selected_class=random.choice(classes)

    weapon=random.choice(weapons[selected_class])
    ability=random.choice(abilities[selected_class])
    selected_gadgets=random.sample(gadgets,3)

    embed=discord.Embed(
        title="🎲 Random Loadout",
        color=discord.Color.blue()
    )

    embed.add_field(name="Class",value=selected_class,inline=False)
    embed.add_field(name="Weapon",value=weapon,inline=False)
    embed.add_field(name="Ability",value=ability,inline=False)
    embed.add_field(
        name="Gadgets",
        value="\n".join(selected_gadgets),
        inline=False
    )

    await ctx.send(embed=embed)

# -------------------------
# Blackjack
# -------------------------
active_games={}

def deal_card():
    cards=[2,3,4,5,6,7,8,9,10,10,10,10,11]
    return random.choice(cards)

def calculate_score(hand):

    score=sum(hand)

    while 11 in hand and score>22:
        hand[hand.index(11)]=1
        score=sum(hand)

    return score

@bot.command()
async def bjjoin(ctx,bet:int):

    if ctx.channel.name!="♠️gambling-table":
        await ctx.send("❌ Use this in #♠️gambling-table")
        return

    user_id=str(ctx.author.id)

    if user_id not in user_data:
        user_data[user_id]={"cp":0,"last_daily":None}

    if bet<=0:
        await ctx.send("Bet must be > 0")
        return

    if user_data[user_id]["cp"]<bet:
        await ctx.send("Not enough CP")
        return

    channel_id=ctx.channel.id

    if channel_id not in active_games:
        active_games[channel_id]={
            "players":{},
            "dealer_hand":[deal_card(),deal_card()],
            "turn_order":[]
        }

    game=active_games[channel_id]

    if user_id in game["players"]:
        await ctx.send("You already joined")
        return

    user_data[user_id]["cp"]-=bet
    save_data()

    game["players"][user_id]={
        "hand":[deal_card(),deal_card()],
        "bet":bet,
        "finished":False
    }

    game["turn_order"].append(user_id)

    await ctx.send(
        f"{ctx.author.mention} joined blackjack with {bet} CP"
    )

# -------------------------
# Start Blackjack
# -------------------------
@bot.command()
async def bjstart(ctx):

    if ctx.channel.name!="♠️gambling-table":
        await ctx.send("Use this in #♠️gambling-table")
        return

    channel_id=ctx.channel.id

    if channel_id not in active_games:
        await ctx.send("No players joined")
        return

    game=active_games[channel_id]

    dealer_hand=game["dealer_hand"]

    await ctx.send(
        f"Dealer shows: [{dealer_hand[0]}, ?]"
    )

    for user_id in game["turn_order"]:

        player=await bot.fetch_user(int(user_id))
        pdata=game["players"][user_id]

        while not pdata["finished"]:

            total=calculate_score(pdata["hand"])

            await ctx.send(
                f"{player.mention} hand: {pdata['hand']} ({total})\nType hit or stand"
            )

            def check(m):
                return m.author.id==int(user_id) and m.content.lower() in ["hit","stand"]

            try:
                msg=await bot.wait_for("message",check=check,timeout=60)
            except asyncio.TimeoutError:
                pdata["finished"]=True
                break

            if msg.content.lower()=="hit":

                pdata["hand"].append(deal_card())
                total=calculate_score(pdata["hand"])

                if total>21:
                    await ctx.send(f"{player.mention} busted")
                    pdata["finished"]=True

            else:
                pdata["finished"]=True

    dealer_total=calculate_score(dealer_hand)

    while dealer_total<17:
        dealer_hand.append(deal_card())
        dealer_total=calculate_score(dealer_hand)

    await ctx.send(f"Dealer hand: {dealer_hand} ({dealer_total})")

    for user_id,pdata in game["players"].items():

        player=await bot.fetch_user(int(user_id))
        player_total=calculate_score(pdata["hand"])
        bet=pdata["bet"]

        if player_total>21:

            await ctx.send(f"{player.mention} busted and lost {bet} CP")

        elif dealer_total>21 or player_total>dealer_total:

            user_data[user_id]["cp"]+=bet*2
            await ctx.send(f"{player.mention} wins {bet*2} CP")

        elif player_total<dealer_total:

            await ctx.send(f"{player.mention} loses")

        else:

            user_data[user_id]["cp"]+=bet
            await ctx.send(f"{player.mention} push (bet returned)")

    save_data()

    del active_games[channel_id]

    await ctx.send("🎉 Blackjack ended")

# -------------------------
# Run
# -------------------------
webserver.keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
