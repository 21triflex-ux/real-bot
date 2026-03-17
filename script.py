import discord
from discord.ext import commands
import logging, os, random, asyncio, json
from datetime import datetime, timedelta

# Bot setup
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='$', intents=intents)

# User data
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
    d = {}
    for uid, data in user_data.items():
        d[uid] = {
            "cp": data["cp"],
            "last_daily": data["last_daily"].isoformat() if data["last_daily"] else None,
            "stats": data.get("stats", {
                "blackjack_wins": 0,
                "blackjack_losses": 0,
                "blackjack_pushes": 0,
                "total_blackjack_games": 0,
                "daily_claims": 0,
                "cp_sent": 0,
                "cp_received": 0,
                "cp_earned": 0,
                "cp_lost": 0
            })
        }
    with open(DATA_FILE, 'w') as f:
        json.dump(d, f, indent=4)

def ensure_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "cp": 0,
            "last_daily": None,
            "stats": {
                "blackjack_wins": 0,
                "blackjack_losses": 0,
                "blackjack_pushes": 0,
                "total_blackjack_games": 0,
                "daily_claims": 0,
                "cp_sent": 0,
                "cp_received": 0,
                "cp_earned": 0,
                "cp_lost": 0
            }
        }

# Deck setup
suits = ["♠", "♥", "♦", "♣"]
ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
NUM_DECKS = 6
deck = []

def build_deck():
    global deck
    deck = [(r,s) for _ in range(NUM_DECKS) for s in suits for r in ranks]
    random.shuffle(deck)

def deal_card():
    global deck
    if len(deck) < 20:
        build_deck()
    return deck.pop()

def card_value(c):
    r = c[0]
    if r in ["J","Q","K"]:
        return 10
    if r == "A":
        return 11
    return int(r)

def calculate_score(hand):
    score = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[0]=="A")
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def format_hand(hand):
    return " ".join([f"{r}{s}" for r,s in hand])

# Events
@bot.event
async def on_ready():
    build_deck()
    print(f"Bot ready as {bot.user.name}")

# Economy commands
@bot.command()
async def daily(ctx):
    uid = str(ctx.author.id)
    ensure_user(uid)
    now = datetime.utcnow()
    last = user_data[uid]["last_daily"]
    if last and now - last < timedelta(hours=24):
        nxt = last + timedelta(hours=24)
        return await ctx.send(f"❌ Next claim: {nxt.strftime('%H:%M UTC')}")
    reward = random.randint(50,150)
    user_data[uid]["cp"] += reward
    user_data[uid]["last_daily"] = now
    user_data[uid]["stats"]["daily_claims"] += 1
    save_data()
    await ctx.send(f"✅ {ctx.author.mention} claimed {reward} CP")

# Blackjack game
active_games = {}

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, pid, pdata, game):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.pid = pid
        self.pdata = pdata
        self.game = game
        self.msg = None

    async def interaction_check(self, interaction):
        return interaction.user.id == int(self.pid)

    async def on_timeout(self):
        self.pdata["finished"] = True
        self.stop()
        user = await bot.fetch_user(int(self.pid))
        if self.msg:
            await self.msg.edit(embed=self.build_embed(), view=None)
        await self.ctx.send(f"⏰ {user.mention} timed out. Standing automatically.")

    def build_embed(self):
        embed = discord.Embed(title=f"🃏 Blackjack", color=discord.Color.green())
        embed.add_field(name="Your Hand", value=f"{format_hand(self.pdata['hand'])} ({calculate_score(self.pdata['hand'])})", inline=False)
        dealer_card = self.game['dealer_hand'][0]
        embed.add_field(name="Dealer Showing", value=f"{dealer_card[0]}{dealer_card[1]} ?", inline=False)
        embed.add_field(name="Bet", value=f"{self.pdata['bet']} CP", inline=False)
        return embed

    async def update_embed(self):
        if self.msg:
            await self.msg.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):
        self.pdata["hand"].append(deal_card())
        score = calculate_score(self.pdata["hand"])
        if score > 21:
            self.pdata["finished"] = True
            self.stop()
            self.pdata["outcome"] = ("bust", self.pdata["bet"])
            await self.update_embed()
            await interaction.response.send_message(f"💥 BUST! {format_hand(self.pdata['hand'])} ({score})")
        else:
            await self.update_embed()
            await interaction.response.defer()

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):
        self.pdata["finished"] = True
        self.stop()
        await self.update_embed()
        await interaction.response.defer()

    @discord.ui.button(label="Double", style=discord.ButtonStyle.blurple)
    async def double(self, interaction, button):
        uid = str(interaction.user.id)
        if user_data[uid]["cp"] < self.pdata["bet"]:
            return await interaction.response.send_message("❌ Not enough CP to double", ephemeral=True)
        user_data[uid]["cp"] -= self.pdata["bet"]
        self.pdata["bet"] *= 2
        self.pdata["hand"].append(deal_card())
        self.pdata["finished"] = True
        self.stop()
        await self.update_embed()
        await interaction.response.defer()

@bot.command()
async def bjjoin(ctx, bet: int):
    uid = str(ctx.author.id)
    ensure_user(uid)
    if bet <= 0:
        return await ctx.send("❌ Bet must be greater than 0")
    if user_data[uid]["cp"] < bet:
        return await ctx.send("❌ Not enough CP")
    
    cid = ctx.channel.id
    if cid not in active_games:
        active_games[cid] = {"players": {}, "dealer_hand": [deal_card(), deal_card()], "turn_order": []}
    game = active_games[cid]

    user_data[uid]["cp"] -= bet
    game["players"][uid] = {"hand": [deal_card(), deal_card()], "bet": bet, "finished": False, "outcome": None}
    game["turn_order"].append(uid)
    await ctx.send(f"✅ {ctx.author.mention} joined blackjack with a bet of {bet} CP")

@bot.command()
async def bjstart(ctx):
    cid = ctx.channel.id
    if cid not in active_games:
        return await ctx.send("❌ No players have joined yet")
    
    game = active_games[cid]
    dealer = game["dealer_hand"]
    await ctx.send(f"🂠 Dealer shows: {dealer[0][0]}{dealer[0][1]} ?")

    # Player turns
    for uid in game["turn_order"]:
        pid = uid.split("_")[0]
        player = game["players"][uid]
        pl_user = await bot.fetch_user(int(pid))

        # Check natural blackjack
        score = calculate_score(player["hand"])
        if score == 21 and len(player["hand"]) == 2:
            win = int(player["bet"] * 2.5)
            user_data[pid]["cp"] += win
            user_data[pid]["stats"]["blackjack_wins"] += 1
            user_data[pid]["stats"]["cp_earned"] += int(player["bet"] * 1.5)
            user_data[pid]["stats"]["total_blackjack_games"] += 1
            player["finished"] = True
            player["outcome"] = ("blackjack", win)
            await ctx.send(f"🃏 {pl_user.mention} got BLACKJACK! Wins {win} CP")
            continue

        # Interactive embed
        embed = discord.Embed(title=f"🃏 Blackjack", color=discord.Color.green())
        embed.add_field(name="Your Hand", value=f"{format_hand(player['hand'])} ({calculate_score(player['hand'])})", inline=False)
        embed.add_field(name="Dealer Showing", value=f"{dealer[0][0]}{dealer[0][1]} ?", inline=False)
        embed.add_field(name="Bet", value=f"{player['bet']} CP", inline=False)
        msg = await ctx.send(f"{pl_user.mention} it's your turn!", embed=embed)
        view = BlackjackView(ctx, pid, player, game)
        view.msg = msg
        await msg.edit(view=view)
        await view.wait()

    # Dealer plays
    dealer_score = calculate_score(dealer)
    while dealer_score < 17:
        dealer.append(deal_card())
        dealer_score = calculate_score(dealer)
    await ctx.send(f"🂠 Dealer's hand: {format_hand(dealer)} ({dealer_score})")

    # Resolve outcomes
    for uid, player in game["players"].items():
        pid = uid.split("_")[0]
        pl_user = await bot.fetch_user(int(pid))
        bet = player["bet"]
        player_score = calculate_score(player["hand"])

        if player.get("outcome"):
            continue
        if player_score > 21:
            user_data[pid]["stats"]["blackjack_losses"] += 1
            user_data[pid]["stats"]["cp_lost"] += bet
            await ctx.send(f"❌ {pl_user.mention} busted and loses {bet} CP")
        elif dealer_score > 21 or player_score > dealer_score:
            user_data[pid]["cp"] += bet * 2
            user_data[pid]["stats"]["blackjack_wins"] += 1
            user_data[pid]["stats"]["cp_earned"] += bet
            await ctx.send(f"💰 {pl_user.mention} wins {bet*2} CP")
        elif player_score < dealer_score:
            user_data[pid]["stats"]["blackjack_losses"] += 1
            user_data[pid]["stats"]["cp_lost"] += bet
            await ctx.send(f"❌ {pl_user.mention} loses {bet} CP")
        else:
            user_data[pid]["cp"] += bet
            user_data[pid]["stats"]["blackjack_pushes"] += 1
            await ctx.send(f"🤝 {pl_user.mention} pushes and gets {bet} CP back")

        user_data[pid]["stats"]["total_blackjack_games"] += 1

    save_data()
    del active_games[cid]
    await ctx.send("🏁 Blackjack round finished! Use `$bjjoin <bet>` to play again.")

# Run bot
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
