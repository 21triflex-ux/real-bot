import discord,logging,os,random,asyncio,json,webserver
from discord.ext import commands
from datetime import datetime,timedelta

token=os.getenv("DISCORD_TOKEN")
if not token:raise ValueError("DISCORD_TOKEN environment variable not set!")

handler=logging.FileHandler(filename='discord.log',encoding='utf-8',mode='w')
intents=discord.Intents.default();intents.message_content=True;intents.members=True
bot=commands.Bot(command_prefix='$',intents=intents)

DATA_FILE='user_data.json'
try:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,'r') as f:
            user_data=json.load(f)
            for uid in user_data:
                if user_data[uid]["last_daily"]:
                    user_data[uid]["last_daily"]=datetime.fromisoformat(user_data[uid]["last_daily"])
    else:user_data={}
except:user_data={}

def save_data():
    d={}
    for uid,data in user_data.items():
        d[uid]={"cp":data["cp"],
               "last_daily":data["last_daily"].isoformat() if data["last_daily"] else None,
               "stats":data.get("stats",{"blackjack_wins":0,"blackjack_losses":0,"blackjack_pushes":0,"total_blackjack_games":0,"daily_claims":0,"cp_sent":0,"cp_received":0})}
    with open(DATA_FILE,'w') as f:json.dump(d,f,indent=4)

suits=["♠","♥","♦","♣"];ranks=["A","2","3","4","5","6","7","8","9","10","J","Q","K"];deck=[]
def build_deck():
    global deck
    deck=[(r,s) for s in suits for r in ranks];random.shuffle(deck)
def deal_card():
    global deck
    if not deck:build_deck()
    return deck.pop()
def card_value(c):
    r=c[0]
    if r in["J","Q","K"]:return 10
    if r=="A":return 11
    return int(r)
def calculate_score(hand):
    score=sum(card_value(c) for c in hand);aces=sum(1 for c in hand if c[0]=="A")
    while score>21 and aces:score-=10;aces-=1
    return score
def format_hand(hand):return" ".join([f"{r}{s}" for r,s in hand])

@bot.event
async def on_ready():
    build_deck()
    print(f"Bot ready as {bot.user.name}")

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome {member.name}! Glad to have you here.")

@bot.event
async def on_message(message):
    if message.author==bot.user:return
    if "call rommel a jew" in message.content.lower():
        await message.channel.send("Let's keep things respectful 👍")
    await bot.process_commands(message)

@bot.command()
async def hello(ctx):await ctx.send(f"Hello {ctx.author.mention}!")

def ensure_user(uid):
    if uid not in user_data:
        user_data[uid]={"cp":0,"last_daily":None,"stats":{"blackjack_wins":0,"blackjack_losses":0,"blackjack_pushes":0,"total_blackjack_games":0,"daily_claims":0,"cp_sent":0,"cp_received":0}}

@bot.command()
async def daily(ctx):
    uid=str(ctx.author.id);ensure_user(uid)
    now=datetime.utcnow()
    last=user_data[uid]["last_daily"]
    if last and now-last<timedelta(hours=24):
        nxt=last+timedelta(hours=24)
        return await ctx.send(f"❌ Next claim: {nxt.strftime('%H:%M UTC')}")
    reward=random.randint(50,150)
    user_data[uid]["cp"]+=reward
    user_data[uid]["last_daily"]=now
    user_data[uid]["stats"]["daily_claims"]+=1
    save_data()
    await ctx.send(f"✅ {ctx.author.mention} claimed {reward} CP")

@bot.command()
async def balance(ctx):
    uid=str(ctx.author.id);ensure_user(uid)
    await ctx.send(f"{ctx.author.mention} has {user_data[uid]['cp']} CP")

@bot.command()
async def bal(ctx, member:discord.Member=None):
    if member is None: member=ctx.author
    uid=str(member.id);ensure_user(uid)
    await ctx.send(f"{member.mention} has {user_data[uid]['cp']} CP")

@bot.command()
async def pay(ctx, member:discord.Member, amount:int):
    sender=str(ctx.author.id);receiver=str(member.id)
    ensure_user(sender);ensure_user(receiver)
    if amount<=0:return await ctx.send("Amount must be >0")
    if user_data[sender]["cp"]<amount:return await ctx.send("Not enough CP")
    user_data[sender]["cp"]-=amount
    user_data[receiver]["cp"]+=amount
    user_data[sender]["stats"]["cp_sent"]+=amount
    user_data[receiver]["stats"]["cp_received"]+=amount
    save_data()
    await ctx.send(f"💸 {ctx.author.mention} sent {amount} CP to {member.mention}")

@bot.command()
async def leaderboard(ctx):
    if not user_data:return await ctx.send("No data yet")
    top=sorted(user_data.items(),key=lambda x:x[1]["cp"],reverse=True)[:10]
    e=discord.Embed(title="🏆 CP Leaderboard",color=discord.Color.gold())
    for i,(uid,d) in enumerate(top,start=1):
        u=bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
        e.add_field(name=f"{i}. {u.name}",value=f"{d['cp']} CP",inline=False)
    await ctx.send(embed=e)

@bot.command()
async def stats(ctx, member: discord.Member = None):
    if member is None: member = ctx.author
    uid = str(member.id);ensure_user(uid)
    s = user_data[uid]["stats"]
    e = discord.Embed(title=f"📈 {member.name}'s Casino Stats", color=discord.Color.green())
    e.add_field(name="💰 CP", value=user_data[uid]["cp"], inline=False)
    e.add_field(name="🎲 Daily Claims", value=s["daily_claims"], inline=True)
    e.add_field(name="♠️ Blackjack Wins", value=s["blackjack_wins"], inline=True)
    e.add_field(name="♠️ Blackjack Losses", value=s["blackjack_losses"], inline=True)
    e.add_field(name="♠️ Blackjack Pushes", value=s["blackjack_pushes"], inline=True)
    e.add_field(name="🎮 Total Blackjack Games", value=s["total_blackjack_games"], inline=True)
    e.add_field(name="📤 CP Sent", value=s["cp_sent"], inline=True)
    e.add_field(name="📥 CP Received", value=s["cp_received"], inline=True)
    await ctx.send(embed=e)

classes=["Light","Medium","Heavy"]
weapons={"Light":["V9S","XP-54","M11","Throwing Knives","Dagger","LH1","SR-84","Sword","93R","RECRUVE BOW","M26 MATTER"],
"Medium":["AKM","FCAR","Model 1887","R.357","Riot Shield","Cerberus 12GA","Pike-556","Dual Blades","CL-40","CB-01","P90","FMAS"],
"Heavy":["Lewis Gun","SA1216","Flamethrower","M60","Sledgehammer","KS-23","Slug shotgun","Titan","Spear","50's","Shak","Mini Gun"]}
abilities={"Light":["Grapple Hook","Dash","Cloaking Device"],"Medium":["Healing Beam","Dematerializer","Turret"],
"Heavy":["Charge 'N' Slam","Mesh Shield","Cum Gun","Winch Claw"]}
gadgets=["Frag Grenade","Gas Mine","Pyro Grenade","Flashbang","Sonar Grenade","Jump Pad","Defib","APS Turret","Breach Drill","Proxy Sensor","Dome Shield","Anti-Grav",
"Concussion Grenade","Breach Charge","Thermal Bore","Gas Grenade","Gate Way","ZipLine","Glitch Trap","Barricade","LockBolt","RPG","Healing Emitter",
"Glitch Grenade","Smoke Grenade","Dynamite","Explosive Mine","Goo Grenade","Gravity Vortex","Tracking Dart","H+ Infuser","Vanishing Bomb"]

@bot.command()
async def roll(ctx):
    if ctx.channel.name!="🤤commentor-june":return await ctx.send("Use in 🤤commentor-june")
    c=random.choice(classes);w=random.choice(weapons[c]);a=random.choice(abilities[c]);g=random.sample(gadgets,3)
    e=discord.Embed(title="🎲 Random Loadout",color=discord.Color.blue())
    e.add_field(name="Class",value=c,inline=False)
    e.add_field(name="Weapon",value=w,inline=False)
    e.add_field(name="Ability",value=a,inline=False)
    e.add_field(name="Gadgets",value="\n".join(g),inline=False)
    await ctx.send(embed=e)

active_games={}

class BlackjackView(discord.ui.View):
    def __init__(self,ctx,pid,pdata,game):super().__init__(timeout=60);self.pid=pid;self.pdata=pdata;self.game=game
    async def interaction_check(self,i):return i.user.id==int(self.pid)
    @discord.ui.button(label="Hit",style=discord.ButtonStyle.green)
    async def hit(self,i,b):
        self.pdata["hand"].append(deal_card());t=calculate_score(self.pdata["hand"])
        if t>21:await i.response.send_message(f"BUST {format_hand(self.pdata['hand'])} ({t})");self.pdata["finished"]=True;self.stop();return
        await i.response.send_message(f"{format_hand(self.pdata['hand'])} ({t})")
    @discord.ui.button(label="Stand",style=discord.ButtonStyle.red)
    async def stand(self,i,b):
        self.pdata["finished"]=True;await i.response.send_message("Stand");self.stop()
    @discord.ui.button(label="Double",style=discord.ButtonStyle.blurple)
    async def double(self,i,b):
        uid=str(i.user.id)
        if user_data[uid]["cp"]<self.pdata["bet"]:return await i.response.send_message("Not enough CP",ephemeral=True)
        user_data[uid]["cp"]-=self.pdata["bet"];self.pdata["bet"]*=2
        self.pdata["hand"].append(deal_card())
        await i.response.send_message(f"Double → {format_hand(self.pdata['hand'])}")
        self.pdata["finished"]=True;self.stop()
    @discord.ui.button(label="Split",style=discord.ButtonStyle.gray)
    async def split(self,i,b):
        if len(self.pdata["hand"])!=2 or self.pdata["hand"][0][0]!=self.pdata["hand"][1][0]:
            return await i.response.send_message("Cannot split",ephemeral=True)
        c=self.pdata["hand"][0];h1=[c,deal_card()];h2=[c,deal_card()]
        self.pdata["hand"]=h1
        sid=self.pid+"_split"
        self.game["players"][sid]={"hand":h2,"bet":self.pdata["bet"],"finished":False}
        idx=self.game["turn_order"].index(self.pid);self.game["turn_order"].insert(idx+1,sid)
        await i.response.send_message("Split");self.stop()

@bot.command()
async def bjjoin(ctx,bet:int):
    if ctx.channel.name!="♠️gambling-table":return await ctx.send("Use in #♠️gambling-table")
    uid=str(ctx.author.id);ensure_user(uid)
    if bet<=0:return await ctx.send("Bet must be >0")
    if user_data[uid]["cp"]<bet:return await ctx.send("Not enough CP")
    cid=ctx.channel.id
    if cid not in active_games:active_games[cid]={"players":{},"dealer_hand":[deal_card(),deal_card()],"turn_order":[]}
    game=active_games[cid]
    user_data[uid]["cp"]-=bet
    game["players"][uid]={"hand":[deal_card(),deal_card()],"bet":bet,"finished":False}
    game["turn_order"].append(uid)
    await ctx.send(f"{ctx.author.mention} joined blackjack with {bet} CP")

@bot.command()
async def bjstart(ctx):
    if ctx.channel.name!="♠️gambling-table":return await ctx.send("Use in #♠️gambling-table")
    cid=ctx.channel.id
    if cid not in active_games:return await ctx.send("No players joined")
    game=active_games[cid];dealer=game["dealer_hand"];dt=calculate_score(dealer)

    if dt==21:
        await ctx.send(f"Dealer BLACKJACK {format_hand(dealer)}")
        for uid,p in game["players"].items():
            pid=uid.split("_")[0];pl=await bot.fetch_user(int(pid))
            pt=calculate_score(p["hand"])
            user_data[pid]["stats"]["total_blackjack_games"]+=1
            if pt==21:user_data[pid]["cp"]+=p["bet"];user_data[pid]["stats"]["blackjack_pushes"]+=1;await ctx.send(f"{pl.mention} push")
            else:user_data[pid]["stats"]["blackjack_losses"]+=1;await ctx.send(f"{pl.mention} loses")
        del active_games[cid];save_data();return

    await ctx.send(f"Dealer shows: {dealer[0][0]}{dealer[0][1]} ?")

    for uid in game["turn_order"]:
        pid=uid.split("_")[0];pl=await bot.fetch_user(int(pid));p=game["players"][uid]
        while not p["finished"]:
            t=calculate_score(p["hand"])
            if t==21 and len(p["hand"])==2:
                win=int(p["bet"]*2.5);user_data[pid]["cp"]+=win
                user_data[pid]["stats"]["blackjack_wins"]+=1
                user_data[pid]["stats"]["total_blackjack_games"]+=1
                await ctx.send(f"🃏 {pl.mention} BLACKJACK wins {win} CP")
                p["finished"]=True;break
            v=BlackjackView(ctx,pid,p,game)
            await ctx.send(f"{pl.mention} {format_hand(p['hand'])} ({t})",view=v)
            await v.wait()

    dt=calculate_score(dealer)
    while dt<17:dealer.append(deal_card());dt=calculate_score(dealer)
    await ctx.send(f"Dealer {format_hand(dealer)} ({dt})")

    for uid,p in game["players"].items():
        pid=uid.split("_")[0];pl=await bot.fetch_user(int(pid));pt=calculate_score(p["hand"]);bet=p["bet"]
        if pt>21:user_data[pid]["stats"]["blackjack_losses"]+=1;user_data[pid]["stats"]["total_blackjack_games"]+=1;await ctx.send(f"{pl.mention} busted")
        elif dt>21 or pt>dt:user_data[pid]["cp"]+=bet*2;user_data[pid]["stats"]["blackjack_wins"]+=1;user_data[pid]["stats"]["total_blackjack_games"]+=1;await ctx.send(f"{pl.mention} wins {bet*2}")
        elif pt<dt:user_data[pid]["stats"]["blackjack_losses"]+=1;user_data[pid]["stats"]["total_blackjack_games"]+=1;await ctx.send(f"{pl.mention} loses")
        else:user_data[pid]["cp"]+=bet;user_data[pid]["stats"]["blackjack_pushes"]+=1;user_data[pid]["stats"]["total_blackjack_games"]+=1;await ctx.send(f"{pl.mention} push")

    save_data();del active_games[cid];await ctx.send("🎉 Blackjack ended")

webserver.keep_alive()
bot.run(token,log_handler=handler,log_level=logging.DEBUG)
