import random
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
from tabulate import tabulate
import logging
from enetities import Player
from enetities import db_backup,get_modes_dict,get_examiner_dict,new_conn,get_tier_table
import enetities
import datetime
import os
import time
import json

def today():
    return datetime.date.today().isoformat()



    

class Exit(Exception):
    def __init__(self) -> None:
        super().__init__("Exit the process.")


logging.basicConfig(
    level=logging.INFO,  # 設定最低記錄等級
    format='%(asctime)s - %(levelname)s - %(message)s',  # 記錄格式
    filename='latest.log',  # 輸出到檔案（可省略則輸出到 console）
    filemode='w'  # 'w' 表示覆寫，'a' 表示追加
)

logging.debug("這是除錯訊息")
logging.info("這是一般訊息")
logging.warning("這是警告")
logging.error("這是錯誤")
logging.critical("這是嚴重錯誤")




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
if bot.owner_id:
    owner=bot.get_user(bot.owner_id)
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        logging.info(f"Sync failed: {e}")
        
    with open("message_to_restore.txt", "r") as f:
        channel_id,msg_id=f.read().split("\n")
        channel = await bot.fetch_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id)) # type: ignore
        await msg.edit(embed=discord.Embed(title="機器人重啟成功",description="可以繼續使用"))


@bot.tree.command(name="send_message", description="傳送訊息") 
async def send_message(interaction: discord.Interaction,channel_id:str="0",msg:str="測試"):
    channel_id=int(channel_id)  
    if interaction.user.id==bot.owner_id:
        if not channel_id:
            channel=interaction.channel
        else:
            channel=bot.get_channel(channel_id)
        await channel.send(content=msg)
        await interaction.response.send_message("傳送成功")
        return 
    else:
        raise Exception("No permission | 權限不足。")


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
    await interaction.response.send_message(embed=discord.Embed(color=discord.Colour.yellow(),title="本指令已經廢除",description="請改用``/tier``指令。"))
    return

@app_commands.describe(player_or_uuid="玩家名稱 | UUID")
@bot.tree.command(name="tier", description="查詢玩家資料及Tier (New)") 
async def tier(interaction: discord.Interaction,player_or_uuid:str):
    await interaction.response.defer() 
    try:
        target=Player(player_or_uuid)
        embed=discord.Embed()
        
        embed.color=discord.Color.gold() if target.is_famous else discord.Color.blue()
        embed.title=target.name.replace("_","\_")  # type: ignore
        embed.set_thumbnail(url=target.head_pic_url)
        # embed.set_thumbnail(url=f"https://mc-heads.net/head/{target.uuid}/left")
        embed.set_image(url=f"https://starlightskins.lunareclipse.studio/render/{choice(render)}/{target.uuid}/full?borderHighlight=true&borderHighlightRadius=5&dropShadow=true&renderScale=2")
        embed.description="\n".join(target.extra_info)
        embed.add_field(name="UUID",value=target.uuid,inline=False)
        embed.add_field(name="暱稱",value=target.nickname,inline=False) if target.nickname else None
        data=target.info_dict
        tier_dict=data.get("tier_data")
        if not tier_dict:
            raise Exception("Target has no tier_dict.")

        if tier_dict.get("tiers"):
            embed.add_field(name="全域積分",value=f"{target.overall_points} (Rank #{target.overall_rank})",inline=False)
            embed.add_field(name="核心積分",value=f"{target.core_points} (Rank #{target.core_rank})",inline=False)
            for field,tier in target.tier_dict["tiers"].items():
                embed.add_field(name=field,value=tier)
        else:
            embed.add_field(name="哎呀...這裡什麼都沒有",value="加入 [福爾摩沙 Tier List Discord Server](https://discord.gg/hamescZvtP) 開單並且完成考試以獲取 Tier!")
        
        if tier_dict.get("other_tiers"):
            other_tier=""
            for item,tier in target.tier_dict["other_tiers"].items():
                other_tier+=f"\n**{item}** : `{tier}`"
            embed.add_field(name="其他未計入Tier",value=other_tier)

        if target.test_records:
            embed.add_field(name="近5次考試紀錄 (自2025年12月統計)",value="\n".join(target.test_records.values()),inline=False)
        else:
            embed.add_field(name="近5次考試紀錄 (自2025年12月統計)",value="無",inline=False)
        
        if interaction.guild_id!=990378958501584916 and rd()>0.7:
            embed.add_field(name="你是 Minecraft 高版本PVP玩家嗎?",value="快加入 [福爾摩沙 Tier List Discord Server](https://discord.gg/hamescZvtP) 證明你的實力吧!",inline=False)
            await interaction.followup.send(embed=embed,content="[᠌](https://discord.gg/hamescZvtP)")
        else:
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=(discord.Embed(colour=0xFF0000, title="⚠️ 發生錯誤", description="```"+str(e)+"```")),ephemeral=True)
        logging.exception(e)
        raise e

# @app_commands.describe(player_or_uuid="玩家名稱 | UUID",reason="原因",expire_date="結束日期",effected_date="生效日期",ban_id="指定封鎖ID")
# @bot.tree.command(name="tier_ban", description="封鎖玩家") 
# async def tier_ban(interaction: discord.Interaction,player_or_uuid:str,reason:str,expire_date:str,effected_date:str="Now",ban_id:str="Default"):
#     if interaction.user.id==bot.owner_id:
#         await interaction.response.defer()
#         player=Player(player_or_uuid)
#         ban_id=None if ban_id == "Default" else ban_id
#         if effected_date=="Now":
#             bid,efd,exd=player.ban(reason,expired_date=expire_date,ban_id=ban_id) 
#         else:
#             bid,efd,exd=player.ban(reason,expired_date=expire_date,effect_date=effected_date,ban_id=ban_id) 
#         player.check_ban()
#         await interaction.followup.send(embed=discord.Embed(color=discord.Colour.dark_embed(),
#                                                             title=f"已封鎖玩家{player.name} ",
#                                                             description=f"封鎖原因: {reason} (uuid:{player.uuid})\n封鎖期間: {efd} - {exd} \nBan ID: {bid}"))
    #     return
    # else:
    #     raise Exception("No permission | 權限不足。")

@app_commands.describe(player_or_uuid="玩家名稱 | UUID")
@bot.tree.command(name="tier_unban", description="解封鎖玩家") 
async def tier_unban(interaction: discord.Interaction,player_or_uuid:str):
    await interaction.response.defer() 
    if interaction.user.id==bot.owner_id:
        await interaction.response.defer()
        player=Player(player_or_uuid)
        player.unban()
        await interaction.followup.send(embed=discord.Embed(color=discord.Colour.dark_embed(),
                                                            title=f"已解封鎖玩家 {player.name}",
                                                            description=f"(uuid:{player.uuid})"))
        return
    else:
        raise Exception("No permission | 權限不足。")
        

# @app_commands.describe(mode="模式",x_axis="統計對象")
# @bot.tree.command(name="statistics_count_by_tier", description="各等級之人數之統計") 
# @app_commands.choices(
#     mode = [
#     Choice(name="Overall", value=0),
#     Choice(name="Sword", value=1),
#     Choice(name="UHC", value=2),
#     Choice(name="Axe", value=3),
#     Choice(name="NPot", value=4),
#     Choice(name="DPot",value=5),
#     Choice(name="CPVP",value=6),
#     Choice(name="SMP",value=7),
#     Choice(name="Cart",value=8),
#     ],
#     x_axis=[
#     Choice(name="Tier",value="Tier"),
#     Choice(name="大約正規化點數",value="正規化點數"),
#     Choice(name="大約正規化Tier",value="正規化Tier"),
#     ] # type: ignore
# )
# async def point_statistics(interaction: discord.Interaction, mode:Choice[int], x_axis:Choice[str]):
#     bf,stats=stat_method.tier_list_count_by_tier(mode.value, x_axis.value)
#     embed=discord.Embed(title=f"Tier List 統計 | 以模式分類 | {x_axis.name} | {mode.name}",)
#     embed.set_image(url="attachment://plot.png")
#     bf.seek(0)
#     if stats:
#         stat_dic={
#             f"總筆數":stats[0],
#             f"總人數":stats[1],
#             f"平均{x_axis.name}":stats[2], # type: ignore
#             f"{x_axis.name}中位數":stats[3],
#             f"{x_axis.name}眾數":stats[4],
#             f"標準差":stats[5], # type: ignore
#         }
#         for k,v in stat_dic.items():
#             embed.add_field(name=k,value=v)
#     await interaction.response.send_message(embed=embed,file=discord.File(fp=bf,filename="plot.png"))

@app_commands.describe(rang="模式涵蓋範圍",page="範圍")
@bot.tree.command(name="rank", description="顯示排名") 
@app_commands.choices(
    rang=[
        Choice(name="Overall",value=0),
        Choice(name="Core",value=1)
    ],
    page=[Choice(name=f"{x*50+1} - {min(x*50+50,stat_method.get_player_amount_in_list())}",value=x) 
          for x in range(0,stat_method.get_player_amount_in_list()//50+1)]
)
async def rank(interaction: discord.Interaction, rang:Choice[int], page:Choice[int]):
    await interaction.response.defer() 
    if rang.value:
        rank_list=fetch_core_rank()
    else:
        rank_list=fetch_overall_rank()
    embed=discord.Embed(title=f"Tier List 排名 | {rang.name} | # {page.name}")
    desc=""
    rank_list_item=list(rank_list.items()) #type:ignore
    r=range(page.value*50,min(page.value*50+50,stat_method.get_player_amount_in_list(),len(rank_list_item)))
    for i in r: #type:ignore
        data=rank_list_item[i] 
        name=data[0]
        rk=data[1]["rank"]
        points=data[1]["points"]
        desc+=f"\n **#{rk}** | `{name}` | {points}pt"
    embed.description=desc
        
    await interaction.followup.send(embed=embed)

# @bot.tree.command(name="statistics_point", description="積分統計長條圖") 
# async def statistics(interaction: discord.Interaction):
#     bf,stats=stat_method.overall_point_stat()
#     embed=discord.Embed(title=f"Tier List 積分統計長條圖",)
#     embed.set_image(url="attachment://plot.png")
#     bf.seek(0)
#     if stats:
#         stat_dic={
#             f"總人數":stats[0],
#             f"平均積分":stats[1], # type: ignore
#             f"中位數":stats[2],
#             f"標準差":stats[4], # type: ignore
#         }
#         for k,v in stat_dic.items():
#             embed.add_field(name=k,value=v)
#     await interaction.response.send_message(embed=embed,file=discord.File(fp=bf,filename="plot.png"))

@bot.tree.command(name="kill", description="重啟機器人 | 只有開發者可以使用") 
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

@bot.tree.command(name="update_tier", description="更新玩家Tier資料 | 只有開發者可以使用")
@app_commands.describe(player="玩家名稱",mode="遊戲模式",tier="Tier,表示移除",is_retired="是否退役")
@app_commands.choices(
    mode = [
        Choice(name=y,value=int(x)) for x,y in get_modes_dict().items()
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
        Choice(name="None",value=0),
        ]
)
async def update_tier(interaction: discord.Interaction,player:str,mode:Choice[int],tier:Choice[int],is_retired:bool=False):
    await interaction.response.defer()
    if interaction.user.id==bot.owner_id:
        with sqlite3.connect("tier_list_latest.db") as conn:
            cursor=conn.cursor()
            cursor.execute("SELECT uuid FROM players WHERE player=?",(player,))
            tmp=cursor.fetchone()
            if tmp:
                uuid=tmp[0]
            else:
                await interaction.followup.send("找不到此玩家",ephemeral=True)
                return
            cursor.execute("DELETE FROM tier_list WHERE uuid=? AND mode_id=?",(uuid,mode.value))
            if tier:
                cursor.execute("INSERT INTO tier_list(uuid,mode_id,tier_id,is_retired) VALUES(?,?,?,?)",(uuid,mode.value,tier.value,is_retired))
            conn.commit()
        await interaction.followup.send(embed=discord.Embed(title="更新成功",description=f"已將 {player} ({uuid}) {mode.name} 項目的 Tier 更改為 {tier.name}"))
    else:
        print(f"{interaction.user.name} ({interaction.user.id}) tried to run update_tier command, but he is not the owner")
        await interaction.followup.send(embed=discord.Embed(title="你沒有權限更改玩家資料",description="只有開發者可以更改"),ephemeral=True)

@bot.tree.command(name="add_test_record",description="考試成果寫入資料庫(update_tier替代方案)")
@app_commands.describe(examinee="受試玩家",mode="考試項目",examiner="執試考官",examinee_score="受試玩家得分",examiner_score="執試考官得分",new_tier="受試玩家Tier評測結果",date="考試日期，預設為指令執行當下日期")
@app_commands.choices(
    mode = [
        Choice(name=y,value=int(x)) for x,y in get_modes_dict().items()
    ],
    new_tier=[
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
        Choice(name="None",value=0),
        ]
)      
async def add_test_record(interaction:discord.Interaction, examinee:str, mode:Choice[int],examiner:str,examinee_score:int,examiner_score:int,new_tier:Choice[int],date:str="today",test_id:str="Default"):
    await interaction.response.defer()
    if date == "today":
        date=today()
    if interaction.user.id != bot.owner_id:
        await interaction.response.send_message(embed=discord.Embed(title="你沒有權限更改資料",description="只有開發者可以更改"),ephemeral=True)
        return
    examiner=Player(examiner)
    examiner_id= enetities.query(f"SELECT examiner_id FROM examiners WHERE uuid = '{examiner.uuid}'")
    # logging.info(f"{examiner_id=} {examiner=}")
    examinee=Player(examinee)
    tier_dict=examinee.tier_dict.get('tiers')
    old_tier_name=tier_dict.get(mode.name)
    tier_table=get_tier_table()
    old_tier_id=tier_table.get(old_tier_name)
    try:
        
        with new_conn() as conn:
            cursor=conn.cursor()
            date_list=date.split("-")
            ym=str(date_list[0])+str(date_list[1])
            if test_id == "Default":
                cursor.execute(f"SELECT test_id FROM tests WHERE test_id LIKE 'T{ym}%' ORDER BY test_id DESC LIMIT 1")
                sub_id=str(int(cursor.fetchone()[0][-3:])+1)
                test_id="T"+ym+sub_id.zfill(3)

            cursor.execute("INSERT INTO tests VALUES(?,?,?,?,?,?,?,?,?)",(test_id,mode.value,examinee.uuid,examiner.uuid,examinee_score,examiner_score,old_tier_id,new_tier.value,date))
            conn.commit()
            examinee.update_tier(mode.value,new_tier.value)
            
        await interaction.followup.send(embed=discord.Embed(title="考試成果已收錄於資料庫中",
description=f"""受試者: {examinee.name}
uuid: {examinee.uuid}
項目: {mode.name}
考官: {examiner.name} (ID: {examiner_id})
日期: {date}
結果:
{examinee.name}   **{examinee_score} : {examiner_score}**   {examiner.name}
Tier 變化: {old_tier_name} → {new_tier.name}""".replace("_","\_")))
        return
    
    except Exception as e:
        raise e


@bot.tree.command(name="add_examiner", description="新增考官")
async def add_examiner(interaction: discord.Interaction,player:str):
    await interaction.response.defer()
    num=enetities.query("SELECT examiner_id FROM examiners ORDER by examiner_id DESC LIMIT 1")[1:]
    examier_id="E"+str(int(num)+1).zfill(4)
    player=enetities.Player(player)
    enetities.query(f"INSERT INTO examiners VALUES('{examier_id}','{player.uuid}')")
    await interaction.followup.send(embed=discord.Embed(title="操作成功",description=f"已將 {player.name} ({player.uuid}) 新增至考官資料庫，ID: {examier_id}".replace("_","\_")))
    return

@bot.tree.command(name="remove_examiner", description="移除考官")
async def remove_examiner(interaction: discord.Interaction,examiner:str):
    await interaction.response.defer()
    examiner=Player(examiner)
    examiner_id = enetities.query(f"SELECT examiner_id FROM examiners WHERE uuid = '{examiner.uuid}'")
    enetities.query(f"DELETE FROM examiners WHERE examiner_id = '{examiner}'")
    await interaction.followup.send(embed=discord.Embed(title="操作成功",description=f"已將 {examiner.name} 從考官資料庫移除".replace("_","\_")))
    return


# @tier_ban.autocomplete("player_or_uuid")
@add_examiner.autocomplete("player")
@search_player.autocomplete("player")
@tier.autocomplete("player_or_uuid")
@update_tier.autocomplete("player")
@tier_unban.autocomplete("player_or_uuid")
@add_test_record.autocomplete("examinee")
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

@remove_examiner.autocomplete("examiner")
@add_test_record.autocomplete("examiner")
async def auto_complete_examiner(interaction: discord.Interaction,current: str):
    l=enetities.query("SELECT player,examiners.examiner_id FROM players,examiners WHERE examiners.uuid = players.uuid ")
    if current:
        match_=set([x for x in l if current.lower() in x[0].lower()])
        starts_with=set([x for x in l if [x[0].lower()][0].startswith(current.lower())])
        sec=match_-starts_with
        l=sorted(list(starts_with),key= lambda x:x[0])+sorted(list(sec),key= lambda x:x[0])
        return [app_commands.Choice(name=x[0],value=x[0]) for x in l if current.lower() in x[0].lower()][:25]
    else:
        return [app_commands.Choice(name=x[0],value=x[0]) for x in l]



@bot.tree.command(name="query", description="SQL查詢 (僅限SELECT) ")
@app_commands.describe(script="SQL查詢語法，僅限SELECT，切分至第一個分號為止")
async def query(interaction: discord.Interaction,script:str):
    await interaction.response.defer() 
    db_backup()
    if bot.is_owner(interaction.user):
        pass
    else:
        if not script.startswith("SELECT"):
            await interaction.followup.sends("只能輸入SELECT開頭的查詢語法",ephemeral=True)
        script=script.split(';')[0]
        for i in ('UPDATE',"DELETE","INSERT","DROP","CREATE","ALTER","PRAGMA","ATTACH",'DETACH','REINDEX','VACUUM','--'):
            if i.lower() in script.lower():
                await interaction.followup.send(f"偵測到非法詞彙：{i}",ephemeral=True)
                return
    with sqlite3.connect("tier_list_latest.db") as conn:
        cursor=conn.cursor()
        display=f"查詢語法:\n```sql\n{script}```"
        try:
            cursor.execute(script)
        except sqlite3.OperationalError as e:
            await interaction.followup.send("SQL錯誤: "+f"```{e}```",ephemeral=True)
            return
        if cursor.description:
            column_headers = [desc[0] for desc in cursor.description]
            l=cursor.fetchall()
            display+="\n結果:\n```"+tabulate(l,headers=column_headers)+"```"
    if len(display)>1800:
        await interaction.followup.send("輸出長度過長 (請使用 LIMIT 或 WHERE 限定條件)",ephemeral=True)
        return
    await interaction.followup.send(display)
    return

@bot.tree.command(name="play_pvp_server",description="列出可玩的 1.9 PVP伺服器")
@app_commands.choices(
    ping_range=[
        Choice(name="極低延遲 - 超爽!",value="極低延遲"),
        Choice(name="低延遲 - 打起來不卡，手感up up!",value="低延遲"),
        Choice(name="中等延遲 - 國際等級延遲，和世界各地玩家一起PVP",value="中等延遲"),
        Choice(name="中等延遲以上 - 國外大型伺服器，模式更多、玩法更廣",value="中等延遲以上"),
        Choice(name="不分延遲 - 比起延遲我更喜歡 看~心~情~",value="不分延遲"),
    ]
)
async def play_server(interaction: discord.Interaction, ping_range:Choice[str]):
    await interaction.response.defer() 
    conn=sqlite3.connect('tier_list_latest.db')
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM server WHERE server_id=1")
    if ping_range.value=="不分延遲":
        cursor.execute("SELECT * FROM server")
    else:
        cursor.execute("SELECT * FROM server WHERE ping_range=?",(ping_range.value,))
    result=cursor.fetchall()
    print(tabulate(result))
    conn.close()
    random.shuffle(result)
    recommand=result[:3]
    print(tabulate(recommand))
    embeds=[]
    for i,j in enumerate(recommand):
        embed=discord.Embed()
        # if i==0:
        #     embed.title=f":fire: {j[1]} :fire: (強力推薦!!!)"
        # else:
        embed.title=j[1]+" - "+j[4]
        
        embed.add_field(name="IP",value=j[3])
        embed.add_field(name="地區",value=j[2])
        embed.set_thumbnail(url=f"https://sr-api.sfirew.com/server/{j[3]}/icon.png")
        embed.add_field(name="介紹",value=j[5],inline=False)
        embed.set_image(url=f'https://sr-api.sfirew.com/server/{j[3]}/banner/motd.png')
        try:
            response=requests.get(f"https://sr-api.sfirew.com/server/{j[3]}",timeout=(5,10))
        except Exception as e:
            embed.set_footer(text="目前網路發生問題，僅能從資料庫擷取資料")
        if response.status_code==200:
            data=response.json()
            if data["online"]:
                embed.add_field(name="狀態",value="🟢在線")
                embed.add_field(name="Ping (台北)",value=f"{data.get('ping')} ms")
                embed.add_field(name="在線人數",value=data.get('players').get('online'))
                embed.add_field(name="版本",value=data.get('version').get("raw"))
            else:
                embed.add_field(name="狀態",value="🔴離線")
        embeds.append(embed)
    print([x.title for x in embeds])
    await interaction.followup.send(embeds=embeds)

@bot.tree.command(name="dashboard",description="資料庫資訊儀錶板")     
@app_commands.choices(
    factor=[
        Choice(name="總覽",value=1),
        Choice(name="玩家",value=2),
        Choice(name="Tier List",value=3),
        Choice(name="考官",value=4),
        Choice(name="考試數據",value=5),
    ]
)
async def dashboard(interaction:discord.Interaction,factor:Choice[int]):
    await interaction.response.defer()
    embed=discord.Embed(title=f"Tier List 資料庫儀錶板 - {factor.name}")
    today=datetime.date.today().isoformat()
    last_month=(datetime.date.today().replace(day=1)-datetime.timedelta(days=1)).isoformat()
    embed.set_footer(text=datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"))
    if factor.value==1:
        embed.add_field(name="資料庫紀錄玩家數",value=enetities.get_players_amount())
        embed.add_field(name="封禁玩家數", value=enetities.get_banned_amount())
        embed.add_field(name="取得Tier玩家數",value=enetities.get_tier_list_amount())
        embed.add_field(name="考官數",value=enetities.query("SELECT COUNT(*) FROM examiners"))
        embed.add_field(name=f"本月({datetime.date.today().strftime("%m月")})考試人次",value=enetities.query(f"SELECT COUNT(*) FROM tests WHERE test_date LIKE '{today[:-2]}%'"))
        embed.add_field(name="上月考試人次",value=enetities.query(f"SELECT COUNT(*) FROM tests WHERE test_date LIKE '{last_month[:-2]}%'"))
        embed.add_field(name=f"累計考試人次(2025年12月-)",value=enetities.query("SELECT COUNT(*) FROM tests"))
        r=enetities.query(f"SELECT player,COUNT(*) AS x FROM tests,players WHERE players.uuid = tests.examiner AND test_date LIKE '{datetime.date.today().isoformat()[:-2]}%' GROUP BY player ORDER BY x DESC LIMIT 1")
        if r:
            embed.add_field(name="本月目前執試最多次考官",value=f"{r[0]} (共 {r[1]} 次)")
        else:
            embed.add_field(name="本月目前執試最多次考官",value="無")
    else:
        embed.add_field(name="其他儀錶板開發中",value="敬請期待")
        
    await interaction.followup.send(embed=embed)
    return
        
@bot.tree.command(name="examiners_leaderboard",description="考官執試排行榜")             
async def examiners_leaderboard(interaction:discord.Interaction):
    await interaction.response.defer()
    embed=discord.Embed(title="考官執試排行榜")
    l_total=enetities.query("SELECT players.player,COUNT(*) FROM tests,players WHERE tests.examiner=players.uuid GROUP BY examiner ORDER BY COUNT(*) DESC")
    l_month=enetities.query(f"SELECT players.player,COUNT(*) FROM tests,players WHERE tests.examiner=players.uuid AND tests.test_date LIKE '{datetime.date.today().isoformat()[:-2]}%' GROUP BY examiner ORDER BY COUNT(*) DESC")

    desc=""
    rank=1
    for i,j in enumerate(l_total):
        if i == 0 or j[1]!=l_total[i-1][1]:
            rank=i+1
        else:
            pass
        desc+=f"第 {rank} 名 : {j[0].replace("_","\_")} - `{j[1]}` 次\n"
    embed.add_field(name='總排行',value=desc)
    desc=""
    for i,j in enumerate(l_month):
        if i == 0 or j[1]!=l_month[i-1][1]:
            rank=i+1
        else:
            pass
        desc+=f"第 {rank} 名 : {j[0].replace("_","\_")} - `{j[1]}` 次\n"
    embed.add_field(name='月度排行',value=desc)
    await interaction.followup.send(embed=embed)

# @play_server.autocomplete("mode")
# async def auto_complete_mode(interaction: discord.Interaction, current: str):
#     conn=sqlite3.connect('tier_list_latest.db')
#     cursor=conn.cursor()
#     cursor.execute("SELECT zh_tw FROM mode")
#     l=[x[0] for x in cursor.fetchall()]
#     conn.close()
#     if current == "":
#         shuffle(l)
#     else:
#         match_=set([x for x in l if current.lower() in x.lower()])
#         starts_with=set([x for x in l if [x.lower()][0].startswith(current.lower())])
#         sec=match_-starts_with
#         l=sorted(list(starts_with))+sorted(list(sec))
#     return [app_commands.Choice(name=x,value=x) for x in l if current.lower() in x.lower()][:25]




@bot.tree.command(name="help", description="打開指令手冊，查看所有詳細指南！")
async def help_command(interaction: discord.Interaction):
    try:
        # 讀取 JSON 檔案 (假設 key 分別為 "查詢類 🔍", "統計類 📊", "管理類 🛠️")
        with open("commands.json", "r", encoding="utf-8") as f:
            commands_data = json.load(f)

        # 這裡建立一個 Field Name 的映射表，讓你可以在不改 JSON 的情況下自定義標題
        # 如果 JSON 的 key 匹配，就使用這裡更生動的文字
        category_mapping = {
            "查詢類 🔍": "🔎 玩家與戰力查詢 (Public)",
            "統計類 📊": "📈 伺服器數據統計 (Stats)",
            "管理類 🛠️": "🛡️ 開發者管理權限 (Admin Only)"
        }

        embed = discord.Embed(
            title="📖 福爾摩沙 Tier List 指令手冊",
            description="這裡是目前所有可用的魔法指令！\n若有任何疑問，請聯繫開發人員或考官。",
            color=0x2ecc71  # 活潑的翡翠綠
        )

        # 動態生成 Field
        for raw_key, cmd_list in commands_data.items():
            # 取得對應的生動名稱，若找不到則使用原始 key
            field_name = category_mapping.get(raw_key, raw_key)
            
            # 過濾管理類指令 (非擁有者不顯示，增加隱私性與整潔度)
            if "管理" in raw_key and interaction.user.id != bot.owner_id:
                continue

            field_value = ""
            for cmd in cmd_list:
                field_value += f"**`/{cmd['name']}`**\n> {cmd['description']}\n\n"
            
            if field_value:
                embed.add_field(name=field_name, value=field_value, inline=False)

        # 裝飾 Embed
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
        embed.set_footer(
            text=f"查詢者: {interaction.user.display_name} • {datetime.datetime.now().strftime('%H:%M')}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

    except FileNotFoundError:
        await interaction.response.send_message("❌ 錯誤：找不到 `commands.json` 檔案。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ 發生未知錯誤：{e}", ephemeral=True)

@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logging.error(error.with_traceback(error.__traceback__))
    logging.exception(error)
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"指令冷卻中，請等待 {error.retry_after:.2f} 秒", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("你沒有使用這個指令的權限", ephemeral=True)
    else:
        # 預設未捕捉的錯誤，選擇丟出或回報
        dm = bot.get_partial_messageable(1410204311715315722)
        params = []
        if interaction.data:
            if "options" in interaction.data: # type: ignore
                for option in interaction.data["options"]: # type: ignore
                    params.append(f'{option["name"]}: {option["value"]}\n') # type: ignore
        params_str = ", ".join(params)
        if interaction.guild:
            guild_name=interaction.guild
            guild_id=interaction.guild_id
        else:
            guild_name="Private_guild"
            guild_id=None
        if type(interaction.channel) is discord.DMChannel:
            channel_name=f"{interaction.user.name}'s Direct Message"
        else:
            channel_name=interaction.channel.name #type:ignore
        user_embed=discord.Embed(colour=discord.Colour.red(),title="⚠️ 發生錯誤", description="```"+str(error.with_traceback(error.__traceback__))+"```"+"\n錯誤報告已經回報給開發者")
        try:
            await interaction.followup.send(embed=user_embed,ephemeral=True)
        except:
            await interaction.response.send_message(embed=user_embed,ephemeral=True)
        await dm.send(embed=discord.Embed(colour=discord.Colour.red(),title="⚠️ 錯誤報告", description="```"+str(error.with_traceback(error.__traceback__))+"```"+f"\n時間: {datetime.datetime.now().isoformat()}\n伺服器: {guild_name} ({guild_id}) \n頻道: {channel_name} ({interaction.channel_id})\n使用者: {interaction.user.name} ({interaction.user.id}) \n指令: {interaction.command.name}\n參數: \n{params_str}")) #type:ignore
        


try:
    bot.run(os.getenv("BOT_TOKEN")) # type: ignore
except Exception as e:
    with open("error.txt",w,encoding='utf-8') as fd:
        fd.write(e.with_traceback(e.__traceback__()))
    time.sleep(5)
