# Blackjack with embed UI
active_games = {}

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, player_id, player_data, game, message):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.pid = player_id
        self.pdata = player_data
        self.game = game
        self.message = message  # Embed message to edit

    async def interaction_check(self, interaction):
        return interaction.user.id == int(self.pid)

    async def on_timeout(self):
        self.pdata["finished"] = True
        self.stop()
        user = await bot.fetch_user(int(self.pid))
        await self.message.edit(embed=self.build_embed(), view=None)
        await self.ctx.send(f"⏰ {user.mention} timed out. Standing automatically.")

    def build_embed(self):
        embed = discord.Embed(title=f"🃏 Blackjack", color=discord.Color.green())
        embed.add_field(name="Your Hand", value=f"{format_hand(self.pdata['hand'])} ({calculate_score(self.pdata['hand'])})", inline=False)
        dealer_card = self.game['dealer_hand'][0]
        embed.add_field(name="Dealer Showing", value=f"{dealer_card[0]}{dealer_card[1]} ?", inline=False)
        embed.add_field(name="Bet", value=f"{self.pdata['bet']} CP", inline=False)
        return embed

    async def update_embed(self):
        await self.message.edit(embed=self.build_embed(), view=self)

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
async def bjstart(ctx):
    cid = ctx.channel.id
    if cid not in active_games:
        return await ctx.send("❌ No players have joined yet")
    
    game = active_games[cid]
    dealer = game["dealer_hand"]

    # Player turns
    for uid in game["turn_order"]:
        pid = uid.split("_")[0]
        player = game["players"][uid]
        pl_user = await bot.fetch_user(int(pid))

        # Check for natural blackjack
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

        # Interactive embed for player
        embed = discord.Embed(title=f"🃏 Blackjack", color=discord.Color.green())
        embed.add_field(name="Your Hand", value=f"{format_hand(player['hand'])} ({calculate_score(player['hand'])})", inline=False)
        embed.add_field(name="Dealer Showing", value=f"{dealer[0][0]}{dealer[0][1]} ?", inline=False)
        embed.add_field(name="Bet", value=f"{player['bet']} CP", inline=False)
        msg = await ctx.send(f"{pl_user.mention} it's your turn!", embed=embed)
        view = BlackjackView(ctx, pid, player, game, msg)
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
            continue  # Already handled blackjack
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
