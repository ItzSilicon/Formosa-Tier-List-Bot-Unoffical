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
        "reading",
        "clown"]


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Sync failed: {e}")



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
    name_changed_message=""
    conn=sqlite3.connect('tier_list_latest.db')
    cursor=conn.cursor()
    cursor.execute("SELECT player,uuid FROM players")
    p2uuid={x[0]:x[1] for x in cursor.fetchall()}
    uuid2p={x[1]:x[0] for x in cursor.fetchall()}
    uuid_db=p2uuid.get(player)
    if uuid_db:
        if uuid_db.startswith("unknown#"):
            name_changed_message = "(此玩家名稱及對應的Tier已經不可考)"
        ## uuid is in DB
        else:
            response=requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid_db}")
            if response.status_code == 200:
                ## uuid is available
                player_mojang=response.json()["name"]
                if player_mojang != player:
                    cursor.execute("UPDATE players SET player=? WHERE uuid=?",(player_mojang,uuid_db))
                    conn.commit()
                    name_changed_message=f"({player} --> {player_mojang})"
                    player=player_mojang
            elif response.status_code == 404:
                cursor.execute("DELETE FROM players WHERE uuid=?",(uuid_db,))
                conn.commit()
                await interaction.response.send_message(f"(無效的uuid: {player}|{uuid_db}，已移除)")
            
            else:
                await interaction.response.send_message(f"網路錯誤: {response.status_code}",ephemeral=True)
                return
        uuid=uuid_db
    else:
        #Player not in DB
        response=requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player}")
        if response.status_code == 200:
            uuid=response.json()["id"]
            player_db=uuid2p.get(uuid)
            if player_db:
                name_changed_message=f"({player_db} --> {player})"
                cursor.execute("UPDATE players SET player=? WHERE uuid=?",(player,uuid))
                
            else:
                cursor.execute("INSERT INTO players(player,uuid,is_banned,reason) VALUES(?,?,0,NULL)",(player,uuid))
            conn.commit()
        elif response.status_code == 404:
            await interaction.response.send_message(f"無效的玩家名稱: {player}",ephemeral=True)
            return
        else:
            await interaction.response.send_message(f"網路錯誤: {response.status_code}",ephemeral=True)
            return
    player_info=cursor.execute("SELECT is_banned,reason FROM players WHERE uuid=?",(uuid,)).fetchone()
    if mode:
        cursor.execute("""SELECT players.player,mode.short AS MODE ,tier_table.short as TIER, players.uuid, tier_list.is_retired, players.is_banned,players.reason FROM tier_list
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
    dsc=""
    embed=discord.Embed()
    player=player.replace("_","\\_")
    name_changed_message=name_changed_message.replace("_","\\_")
    embed.add_field(name="UUID",value=uuid,inline=False)
    if player_info[0]:
        title=f"{player} {name_changed_message}  |  Banned, Reason: {player_info[1]}"
    elif len(lst)==1:
        is_retired=lst[0][4]
        title=f"{player} {name_changed_message}  |  {lst[0][1]} {lst[0][2]} {" Retired" if is_retired else ""}"
    elif not lst:
        title=f"{player} {name_changed_message}  |  {modes.get(mode)}"
        dsc+=f"**{player} 沒有得到任何Tier**"
    else:
        title=f"{player} {name_changed_message}"
        for i in lst:
            is_retired=i[4]
            tmp=" Retired" if is_retired else ""
            embed.add_field(name=i[1],value=i[2]+tmp,inline=True)   
    embed.set_image(url=f"https://starlightskins.lunareclipse.studio/render/{choice(render)}/{uuid}/full")
    embed.set_thumbnail(url=f"https://mc-heads.net/head/{uuid}/left")
    # response=requests.get(f"https://starlightskins.lunareclipse.studio/render/marching/{uuid}/full")
    embed.set_footer(text="Powered by Lunar Eclipse Render API")
    embed.description=dsc
    embed.title=title
    await interaction.response.send_message(embed=embed)  
    conn.close()
        
    

@search_player.autocomplete("player")
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



bot.run(os.getenv("BOT_TOKEN")) # type: ignore
