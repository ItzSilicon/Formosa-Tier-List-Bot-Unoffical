import sqlite3
import requests
import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
from random import choice
from random import shuffle
from random import random as rd
import stat_method
from stat_method import fetch_overall_rank
from stat_method import fetch_core_rank

load_dotenv()
render=["default",
        "marching",
        "walking",
        "crossed",
        "criss_cross",
        "ultimate",
        "isometric",
        "relaxing",
        "pointing",
        "lunging",
        "dungeons",
        "archer",
        "reading"]


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents,owner_id=1110595121591898132)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Sync failed: {e}")
        
    with open("message_to_restore.txt", "r") as f:
        channel_id,msg_id=f.read().split("\n")
        channel = await bot.fetch_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id)) # type: ignore
        await msg.edit(embed=discord.Embed(title="機器人重啟成功",description="可以繼續使用"))



@app_commands.choices(mode = [
    Choice(name="Overall", value=0),
    Choice(name="Sword", value=1),
    Choice(name="UHC", value=2),
    Choice(name="Axe", value=3),
    Choice(name="NPot", value=4),
    Choice(name="DPot",value=5),
    Choice(name="CPVP",value=6),
    Choice(name="SMP",value=7),
    Choice(name="Cart",value=8)
])
@app_commands.describe(player="玩家名稱",mode="遊戲模式")
@bot.tree.command(name="search_player", description="查詢玩家Tier") 
async def search_player(interaction: discord.Interaction,player: str,mode:int):
    modes={0:"Overall",
    1:"Sword",
    2:"UHC",
    3:"Axe",
    4:"NPot",
    5:"DPot",
    6:"CPVP",
    7:"SMP",
    8:"Cart"}
    print(f"""
    --- REQUEST ---
    Request from {interaction.user.name} ({interaction.user.id})
    Player: {player}
    Mode: {modes[mode]}
    """)
    name_changed_message=""
    conn=sqlite3.connect('tier_list_latest.db')
    cursor=conn.cursor()
    cursor.execute("SELECT player,uuid FROM players")
    tmp=cursor.fetchall()
    p2uuid={x[0].lower():x[1] for x in tmp}
    uuid2p={x[1]:x[0].lower() for x in tmp}
    uuid_db=p2uuid.get(player.lower())
    if uuid_db:
        print(f"{player} is in Database")
        if uuid_db.startswith("unknown#"):
            print(f"{player}'s uuid is unknown, but recorded")
            name_changed_message = "(此玩家名稱及對應的Tier已經不可考)"
        ## uuid is in DB
        else:
            print(f"{player} may have valid uuid: {uuid_db}")
            response=requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid_db}")
            if response.status_code == 200:
                ## uuid is available
                print("UUID is available")
                player_mojang=response.json()["name"]
                if player_mojang != player:
                    print(f"Detect name difference between database and API, so update name to {player_mojang}")
                    cursor.execute("UPDATE players SET player=? WHERE uuid=?",(player_mojang,uuid_db))
                    conn.commit()
                    name_changed_message=f"({player} --> {player_mojang})"
                    player=player_mojang
            elif response.status_code == 404:
                print("UUID DOES NOT EXIST ??? THIS IS FU*KING IMPOSSIBLE")
                cursor.execute("DELETE FROM players WHERE uuid=?",(uuid_db,))
                conn.commit()
                await interaction.response.send_message(f"(無效的uuid: {player}|{uuid_db}，已移除)")
            
            else:
                print(f"Network Error: {response.status_code}")
                await interaction.response.send_message(f"網路錯誤: {response.status_code}",ephemeral=True)
                return
        uuid=uuid_db
    else:
        print(f"Player {player} is not in Database")
        #Player not in DB
        response=requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player}")
        if response.status_code == 200:
            print(f"{player} does exist in Mojang API")
            uuid=response.json()["id"]
            print("UUID:",uuid)
            uuid=uuid.strip("-")
            player=response.json()["name"]
            player_db=uuid2p.get(uuid)
            if player_db:
                print(f"Player {player} has changed name to {player_db}, so datebase needs to be updated")
                name_changed_message=f"({player_db} --> {player})"
                print(f"Player {player_db} name has changed to {player}")
                cursor.execute("UPDATE players SET player=? WHERE uuid=?",(player,uuid))
                
            else:
                print(f"New player: {player}")
                cursor.execute("INSERT INTO players(player,uuid,is_banned,reason,is_famous,nickname,intro) VALUES(?,?,0,NULL,0,NULL,NULL)",(player,uuid))
            conn.commit()
        elif response.status_code == 404:
            print("Player does not exist.")
            await interaction.response.send_message(f"無效的玩家名稱: {player}",ephemeral=True)
            return
        else:
            print(f"Network Error: {response.status_code}")
            await interaction.response.send_message(f"網路錯誤: {response.status_code}",ephemeral=True)
            return
    player_info=cursor.execute("SELECT is_banned,reason,intro,is_famous,nickname FROM players WHERE uuid=?",(uuid,)).fetchone()
    print(player_info)
    if mode:
        cursor.execute("""SELECT players.player,mode.short AS MODE ,tier_table.short as TIER, players.uuid, tier_list.is_retired FROM tier_list
    JOIN mode ON tier_list.mode_id=mode.mode_id
    JOIN tier_table ON tier_list.tier_id = tier_table.tier_id
    JOIN players ON tier_list.uuid = players.uuid
    WHERE players.uuid= ? AND tier_list.mode_id=?""",(uuid,mode))
    else:
        cursor.execute("""SELECT players.player,mode.short AS MODE ,tier_table.short as TIER, players.uuid, tier_list.is_retired FROM tier_list
    JOIN mode ON tier_list.mode_id=mode.mode_id
    JOIN tier_table ON tier_list.tier_id = tier_table.tier_id
    JOIN players ON tier_list.uuid = players.uuid
    WHERE players.uuid= ? ORDER BY tier_list.mode_id""",(uuid,))
    lst=cursor.fetchall()
    conn.close()
    dsc=""
    embed=discord.Embed()
    embed.color=discord.Color.blue()
    player_display=player.replace("_","\\_")
    if player=="ItzMyGO":
        player_display+=" (測試用，不計入Tier)"
    if player_info[3]:
        player_display='👑 '+player_display+' 👑'
        embed.color=discord.Color.gold()
    name_changed_message=name_changed_message.replace("_","\\_")
    embed.add_field(name="UUID",value=uuid,inline=False)
    if player_info[4]:
        embed.add_field(name="暱稱",value=player_info[4],inline=False)
    # if player_info[2]:
    #     if player_info[3]:
    #         embed.add_field(name="⭐ 名人介紹 ⭐",value=f"**{player_info[2]}**",inline=False)
    #     else:
    #         embed.add_field(name="介紹",value=player_info[2],inline=False)
    if player_info[0]:
        title=f"{player_display} {name_changed_message}  |  Banned, Reason: {player_info[1]}"
    elif mode!=0 and lst:
        is_retired=lst[0][4]
        title=f"{player_display} {name_changed_message}  |  {lst[0][1]} {"R" if is_retired else ""}{lst[0][2]} "
    elif not lst:
        title=f"{player_display} {name_changed_message}  |  {modes.get(mode)}"
        dsc+=f"**{player_display} 沒有得到任何Tier**"
    else:
        title=f"{player_display} {name_changed_message}"
        embed.add_field(name="排名 (Overall)",value=f"# {fetch_overall_rank(player)}")
        core_rank=fetch_core_rank(player)
        if core_rank:
            embed.add_field(name="核心排名 (Core)",value=f"# {core_rank}",inline=False)
        for i in lst:
            is_retired=i[4]
            tmp="R" if is_retired else ""
            embed.add_field(name=i[1],value=tmp+i[2],inline=True)
    embed.set_image(url=f"https://starlightskins.lunareclipse.studio/render/{choice(render)}/{uuid}/full?borderHighlight=true&borderHighlightRadius=5&dropShadow=true&renderScale=2")
    embed.set_thumbnail(url=f"https://mc-heads.net/head/{uuid}/left")
    # response=requests.get(f"https://starlightskins.lunareclipse.studio/render/marching/{uuid}/full")
    embed.title=title
    embed.set_footer(text="Powered by Lunar Eclipse Render API")
    embed.description=dsc
    if interaction.guild_id!=990378958501584916 and rd()>0.7:
        embed.add_field(name="你是 Minecraft 高版本PVP玩家嗎?",value="快加入 [福爾摩沙 Tier List Discord Server](https://discord.gg/hamescZvtP) 證明你的實力吧!",inline=False)
        await interaction.response.send_message(embed=embed,content="[᠌](https://discord.gg/hamescZvtP)")
    else:
        await interaction.response.send_message(embed=embed)

        

@app_commands.describe(mode="模式",x_axis="統計對象")
@bot.tree.command(name="statistics_count_by_tier", description="各等級之人數之統計") 
@app_commands.choices(
    mode = [
    Choice(name="Overall", value=0),
    Choice(name="Sword", value=1),
    Choice(name="UHC", value=2),
    Choice(name="Axe", value=3),
    Choice(name="NPot", value=4),
    Choice(name="DPot",value=5),
    Choice(name="CPVP",value=6),
    Choice(name="SMP",value=7),
    Choice(name="Cart",value=8),
    ],
    x_axis=[
    Choice(name="Tier",value="Tier"),
    Choice(name="大約正規化點數",value="正規化點數"),
    Choice(name="大約正規化Tier",value="正規化Tier"),
    ] # type: ignore
)
async def point_statistics(interaction: discord.Interaction, mode:Choice[int], x_axis:Choice[str]):
    bf,stats=stat_method.tier_list_count_by_tier(mode.value, x_axis.value)
    embed=discord.Embed(title=f"Tier List 統計 | 以模式分類 | {x_axis.name} | {mode.name}",)
    embed.set_image(url="attachment://plot.png")
    bf.seek(0)
    if stats:
        stat_dic={
            f"總筆數":stats[0],
            f"總人數":stats[1],
            f"平均{x_axis.name}":stats[2], # type: ignore
            f"{x_axis.name}中位數":stats[3],
            f"{x_axis.name}眾數":stats[4],
            f"標準差":stats[5], # type: ignore
        }
        for k,v in stat_dic.items():
            embed.add_field(name=k,value=v)
    await interaction.response.send_message(embed=embed,file=discord.File(fp=bf,filename="plot.png"))

@app_commands.describe(rang="模式涵蓋範圍",page="範圍")
@bot.tree.command(name="rank", description="顯示排名") 
@app_commands.choices(
    rang=[
        Choice(name="Overall",value=0),
        Choice(name="Core",value=1)
    ],
    page=[Choice(name=f"{x*20+1} - {min(x*20+20,stat_method.get_player_amount_in_list())}",value=x) 
          for x in range(0,stat_method.get_player_amount_in_list()//20)]
)
async def rank(interaction: discord.Interaction, rang:Choice[int], page:Choice[int]):
    if rang.value:
        rank_list=fetch_core_rank()
    else:
        rank_list=fetch_overall_rank()
    r=range(page.value*20,min(page.value*20+20,stat_method.get_player_amount_in_list()))
    embed=discord.Embed(title=f"Tier List 排名 | {rang.name} | # {page.name}")
    rank_list_items=list(rank_list.items()) # type: ignore
    for i in r:
        embed.add_field(name=f"# {rank_list_items[i][1]}",value=rank_list_items[i][0].replace('_','\\_'),inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="statistics_point", description="積分統計長條圖") 
async def statistics(interaction: discord.Interaction):
    bf,stats=stat_method.overall_point_stat()
    embed=discord.Embed(title=f"Tier List 積分統計長條圖",)
    embed.set_image(url="attachment://plot.png")
    bf.seek(0)
    if stats:
        stat_dic={
            f"總人數":stats[0],
            f"平均積分":stats[1], # type: ignore
            f"中位數":stats[2],
            f"標準差":stats[4], # type: ignore
        }
        for k,v in stat_dic.items():
            embed.add_field(name=k,value=v)
    await interaction.response.send_message(embed=embed,file=discord.File(fp=bf,filename="plot.png"))

@bot.tree.command(name="kill", description="重啟機器人") 
async def kill(interaction: discord.Interaction):
    if interaction.user.id==bot.owner_id:
        fallback = await interaction.response.send_message(embed=discord.Embed(title="機器人重啟",description="請稍後..."))
        msg=fallback.message_id
        with open("message_to_restore.txt", "w") as f:
            f.write(f"{interaction.channel_id}\n{msg}") # type: ignore
        exit(0)
    else:
        print(f"{interaction.user.name} ({interaction.user.id}) tried to kill the bot, but he is not the owner")
        await interaction.response.send_message(embed=discord.Embed(title="你沒有權限重啟機器人",description="只有開發者可以重啟"),ephemeral=True)

@bot.tree.command(name="update_tier", description="更新玩家Tier資料")
@app_commands.choices(
    mode = [
    Choice(name="Sword", value=1),
    Choice(name="UHC", value=2),
    Choice(name="Axe", value=3),
    Choice(name="NPot", value=4),
    Choice(name="DPot",value=5),
    Choice(name="CPVP",value=6),
    Choice(name="SMP",value=7),
    Choice(name="Cart",value=8),
    ],
    tier=[
        Choice(name="HT1",value=11),
        Choice(name="LT1",value=12),
        Choice(name="HT2",value=21),
        Choice(name="LT2",value=22),
        Choice(name="HT3",value=31),
        Choice(name="MT3",value=32),
        Choice(name="LT3",value=33),
        Choice(name="HT4",value=41),
        Choice(name="LT4",value=42),
        Choice(name="HT5",value=51),
        Choice(name="LT5",value=52),
        ]
)
async def update_tier(interaction: discord.Interaction,player:str,mode:Choice[int],tier:Choice[int],is_retired:bool=False):
    if interaction.user.id==bot.owner_id:
        with sqlite3.connect("tier_list_latest.db") as conn:
            cursor=conn.cursor()
            cursor.execute("SELECT uuid FROM players WHERE player=?",(player,))
            tmp=cursor.fetchone()
            if tmp:
                uuid=tmp[0]
            else:
                await interaction.response.send_message("找不到此玩家",ephemeral=True)
                return
            cursor.execute("SELECT mode_id FROM tier_list WHERE uuid=?",(uuid,))
            modes=cursor.fetchone()
            if not modes or mode.value not in modes:
                cursor.execute("INSERT INTO tier_list(uuid,mode_id,tier_id,is_retired) VALUES(?,?,?,?)",(uuid,mode.value,tier.value,is_retired))
            else:
                cursor.execute("UPDATE tier_list SET tier_id=?,is_retired=? WHERE uuid=? AND mode_id=?",(tier.value,is_retired,uuid,mode.value))
            conn.commit()
        await interaction.response.send_message(embed=discord.Embed(title="更新成功",description=f"已將 {player} ({uuid}) {mode.name} 項目的 Tier 更改為 {tier.name}"))
    else:
        print(f"{interaction.user.name} ({interaction.user.id}) tried to run update_tier command, but he is not the owner")
        await interaction.response.send_message(embed=discord.Embed(title="你沒有權限更改玩家資料",description="只有開發者可以更改"),ephemeral=True)

@search_player.autocomplete("player")
@update_tier.autocomplete("player")
async def auto_complete_player(interaction: discord.Interaction, current: str):
    conn=sqlite3.connect('tier_list_latest.db')
    cursor=conn.cursor()
    cursor.execute("SELECT player FROM players")
    l=[x[0] for x in cursor.fetchall()]
    conn.close()
    if current == "":
        shuffle(l)
    else:
        match_=set([x for x in l if current.lower() in x.lower()])
        starts_with=set([x for x in l if [x.lower()][0].startswith(current.lower())])
        sec=match_-starts_with
        l=sorted(list(starts_with))+sorted(list(sec))
    return [app_commands.Choice(name=x,value=x) for x in l if current.lower() in x.lower()][:25]

@bot.tree.command(name="sql_query_select", description="SQL查詢 (僅限SELECT)")
@app_commands.describe(script="SQL查詢語法，僅限SELECT，切分至第一個分號為止")
async def query(interaction: discord.Interaction,script:str):
    if not script.startswith("SELECT"):
        await interaction.response.send_message("只能輸入SELECT開頭的查詢語法",ephemeral=True)
    script=script.split(';')[0]
    for i in ('UPDATE',"DELETE","INSERT","DROP","CREATE","ALTER","PRAGMA","ATTACH",'DETACH','REINDEX','VACUUM','--'):
        if i.lower() in script.lower():
            await interaction.response.send_message(f"偵測到非法詞彙：{i}",ephemeral=True)
            return
    with sqlite3.connect("tier_list_latest.db") as conn:
        cursor=conn.cursor()
        try:
            cursor.execute(script)
        except sqlite3.OperationalError:
            await interaction.response.send_message("SQL語法錯誤",ephemeral=True)
            return
        cursor.execute(script)
        l=cursor.fetchall()
    display=f"查詢語法:\n```sql\n{script}```\n結果:\n```"
    for i in l:
        for j in i:
            display+=f"{j}\t"
        display+="\n"
    display+="```"
    if len(display)>750:
        await interaction.response.send_message("輸出長度過長 (請使用 LIMIT 或 WHERE 限定條件)",ephemeral=True)
        return
    await interaction.response.send_message(display)
    
    



@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.message.reply("Command not found")
    if isinstance(error, commands.CommandError):
        await ctx.message.reply(str(error))



bot.run(os.getenv("BOT_TOKEN")) # type: ignore
