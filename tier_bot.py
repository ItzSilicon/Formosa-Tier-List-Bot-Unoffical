import random
import sqlite3
import os
from discord import app_commands,Interaction,Message,Member,Embed,Colour,DMChannel
from discord import NotFound as discordNotFound
from discord import Forbidden as discordForbidden
from discord import Object as DiscordObject
from discord.app_commands import Choice
from random import choice,shuffle
from random import random as rd
import stat_method
from tabulate import tabulate
import logging
from entities import db_backup,get_modes_dict,get_examiner_dict,new_conn,get_tier_table,Player,EntityException,get_players_amount,get_banned_amount,get_tier_list_amount,fetch_core_rank,fetch_overall_rank
# from entities import query as data_query
import os
import time
import json
from discord.ui import Button, View
import re
from config import *
from chatbot import chat_via_interaction,chat_via_mention
import asyncio


### LOGGING ###

logging.basicConfig(
    level=logging.INFO,  # 設定最低記錄等級
    format=' [%(asctime)s] [%(filename)s / %(funcName)s] [%(levelname)s] %(message)s ',  # 記錄格式
    filename='latest.log',  # 輸出到檔案（可省略則輸出到 console）
    filemode='a'  # 'w' 表示覆寫，'a' 表示追加,
)
# logging.debug("這是除錯訊息")
# logging.info("這是一般訊息")
# logging.warning("這是警告")
# logging.error("這是錯誤")
# logging.critical("這是嚴重錯誤")



### ON READY ###
@bot.event
async def on_ready():
    logging.info(f"Bot is online as {bot.user}")
    try:
        owner = await owner_user()
        await owner.send(embed=Embed(title="機器人啟動成功",description="各指令已就緒"))
    except Exception as e:
        logging.exception(e)
        

### ON MESSAGE ###
@bot.event
async def on_message(message:Message):
    if message.author.id==bot.user.id:
        return
    if message.author.bot:
        logging.info("Message from bot, ignored")
        return
    
    if message.guild:
        logging.info("Message from guild")
        if message.guild.id==DEV_GUILD.id:
            logging.info(f"Message from dev guild: {message.guild.id}")
            if bot.user.mention in message.content:
                logging.info("Message contains bot mention")
                async with message.channel.typing():
                    code = await chat_via_mention(message)
                    if code == 1:
                        return
                if code == 2:
                    embed = Embed(
                        title="權杖餘額不足",
                        description="權杖不足100，不足最低使用需求，無法使用AI服務",
                        color=Colour.red()
                    )
                    embed.set_footer(
                        text="本訊息將會於5秒後自動刪除",
                    )
                    send = await message.reply(embed=embed)
                    await asyncio.sleep(5)
                    await sent.delete()
                if code == 3:
                    embed = Embed(
                        title="請求過於頻繁",
                        description="為避免服務阻塞，請勿頻繁請求AI服務",
                        color=Colour.red()
                    )
                    embed.set_footer(
                        text="本訊息將會於5秒後自動刪除",
                    )
                    sent = await message.reply(embed=embed)
                    await asyncio.sleep(5)
                    await sent.delete()
                    return
                else:
                    logging.info("Chat via mention failed")
                    return
            elif '!!!!' in message.content:
                logging.info("Message contains !!!!")
                embed= Embed(title="自動回覆",description=f"嘿，{message.author.mention}，何意味。\n(溫馨提醒，本訊息將在60秒後自動刪除:trollface:)",color=Colour.yellow(),timestamp=message.created_at)
                embed.set_footer(
                    text=message.author.name,
                    icon_url=message.author.display_avatar.url
                )
                sent = await message.reply(embed=embed)
                await asyncio.sleep(60)
                await sent.delete()
                return
            else:
                logging.info("Message does not contain bot mention or !!!!")
                return
        else:
            return
    else:
        return
    

### SLASH COMMANDS ###

@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@bot.tree.command(name="send_message", description="傳送訊息") 
async def send_message(interaction: Interaction,channel_id:str="0",msg:str="測試"):
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
        raise CommandException("權限不足","非管理人員請不要使用該指令")

@app_commands.checks.cooldown(1, 300, key=lambda i: i.user.id)
@app_commands.describe(player_or_uuid="玩家名稱 | UUID")
@bot.tree.command(name="link_hypixel", description="discord與Minecraft帳號驗證連結-Hypxiel驗證")
async def link_hypixel(interaction: Interaction, api_key:str,player_or_uuid:str):
    await interaction.response.defer(ephemeral=True) 
    try:
        player=Player(player_or_uuid)
        tmp = data_query("SELECT minecraft_uuid FROM discord_minecraft",do_format=False),data_query("SELECT discord_user_id FROM discord_minecraft",do_format=False)
        if all(tmp):
            uuid_list,dcuid_list= tmp[0], tmp[1]
            if interaction.user.id in dcuid_list or player.uuid in uuid_list:
                await interaction.followup.send(embed=Embed(colour=0xFFFF00,title="已驗證",description="一個Minecraft帳號只能對應到一位Discord用戶，如果你的任一方帳號有被盜、無法登入等其他情形，請聯繫開發者(Discord ID: lxtw)"),ephemeral=True)
                return
        if verify_hypixel_discord(api_key,player.uuid,interaction.user.name):
            try:
                expire_date=(datetime.date.today()+datetime.timedelta(days=45)).isoformat()
                with new_conn() as conn:
                    cursor=conn.cursor()
                    cursor.execute("INSERT INTO discord_minecraft VALUES(?,?,?,?)",(interaction.user.id,interaction.user.name,player.uuid,expire_date))
                    conn.commit()
            except Exception as e:
                raise e
            await interaction.followup.send(embed=Embed(colour=0x00FF00,title="驗證成功!",description=f"該連結有效期限至``{expire_date}`` (45天)，過期後須重新驗證"),ephemeral=True)
        else:
            await interaction.followup.send(embed=Embed(colour=0xFF0000,title="驗證失敗!"),ephemeral=True)
        return
    except Exception as e:
        await interaction.followup.send(embed=Embed(title="發生未知錯誤",description=f"已回報給開發者"),ephemeral=True)
        return
    

@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@app_commands.describe(player_or_uuid="玩家名稱 | UUID，可連結後直接執行查詢自己的tierlist")
@bot.tree.command(name="tier", description="查詢玩家資料及Tier (New)") 
async def tier(interaction: Interaction,player_or_uuid:str=""):
    # TODO [UI]: 實作下拉選單 (Select Menu) 讓玩家切換不同的顯示模式 (如只看核心積分)
    # TODO [PERF]: 異步化處理 target=Player(player_or_uuid) 的實例化過程，避免阻塞事件迴圈
    await interaction.response.defer()
    if not player_or_uuid:
        logging.info("Provide no player, try to fetch link status...")
        linked= await check_link(interaction=interaction)
        if linked:
            player_or_uuid=linked
        else:
            return
    
    try:
        target=Player(player_or_uuid)
        embed=Embed()
        
        embed.color=Colour.gold() if target.is_famous else Colour.blue()
        embed.title=target.name.replace("_","\_")  # type: ignore
        
        # embed.set_thumbnail(url=f"https://mc-heads.net/head/{target.uuid}/left")
        embed.set_image(url=f"https://starlightskins.lunareclipse.studio/render/{choice(render)}/{target.uuid}/full?borderHighlight=true&borderHighlightRadius=5&dropShadow=true&renderScale=2")
        embed.description="\n".join(target.extra_info)
        embed.add_field(name="UUID",value=f'`{target.uuid}`',inline=False)
        embed.add_field(name="暱稱",value=target.nickname,inline=False) if target.nickname else None
        if target.discord_user_id:
            player_user =await bot.fetch_user(int(target.discord_user_id))
            embed.add_field(name="Discord",value=f"{player_user.mention} / ``{player_user.name}``\n名稱: {player_user.global_name}\n(右方為Discord頭像)")
            embed.set_thumbnail(url=player_user.display_avatar.url)
        else:
            embed.set_thumbnail(url=target.head_pic_url)
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
            
        embed.add_field(name="考試紀錄已經搬家了喔!",value="使用`/test_history`即可查詢完整考試紀錄! ",inline=False)
        
        if interaction.guild_id!=990378958501584916 and rd()>0.7:
            embed.add_field(name="你是 Minecraft 高版本PVP玩家嗎?",value="快加入 [福爾摩沙 Tier List Discord Server](https://discord.gg/hamescZvtP) 證明你的實力吧!",inline=False)
            await interaction.followup.send(embed=embed,content="[᠌](https://discord.gg/hamescZvtP)")
        else:
            await interaction.followup.send(embed=embed)
    except Exception as e:
        raise e

@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@app_commands.describe(player_or_uuid="玩家名稱 | UUID",reason="原因",expire_date="結束日期",effected_date="生效日期",ban_id="指定封鎖ID")
@bot.tree.command(name="tier_ban", description="封鎖玩家") 
async def tier_ban(interaction: Interaction,player_or_uuid:str,reason:str,expire_date:str,effected_date:str="Now",ban_id:str="Default"):
    if interaction.user.id==bot.owner_id:
        await interaction.response.defer()
        player=Player(player_or_uuid)
        ban_id=None if ban_id == "Default" else ban_id
        if effected_date=="Now":
            bid,efd,exd=player.ban(reason,expired_date=expire_date,ban_id=ban_id) 
        else:
            bid,efd,exd=player.ban(reason,expired_date=expire_date,effect_date=effected_date,ban_id=ban_id) 
        await interaction.followup.send(embed=Embed(color=Colour.dark_embed(),
                                                            title=f"已封鎖玩家{player.name} ",
                                                            description=f"封鎖原因: {reason} (uuid:{player.uuid})\n封鎖期間: {efd} - {exd} \nBan ID: {bid}"))
        return
    else:
        raise CommandException("權限不足","非管理人員請勿使用該指令")

@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@app_commands.describe(player_or_uuid="玩家名稱 | UUID")
@bot.tree.command(name="tier_unban", description="解封鎖玩家") 
async def tier_unban(interaction: Interaction,player_or_uuid:str):
    await interaction.response.defer() 
    if interaction.user.id==bot.owner_id:
        player=Player(player_or_uuid)
        player.unban()
        await interaction.followup.send(embed=Embed(color=Colour.dark_embed(),
                                                            title=f"已解封鎖玩家 {player.name}",
                                                            description=f"(uuid:{player.uuid})"))
        return
    else:
        raise CommandException("權限不足","非管理人員請勿使用該指令")
        

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
# async def point_statistics(interaction: Interaction, mode:Choice[int], x_axis:Choice[str]):
#     bf,stats=stat_method.tier_list_count_by_tier(mode.value, x_axis.value)
#     embed=Embed(title=f"Tier List 統計 | 以模式分類 | {x_axis.name} | {mode.name}",)
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

@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
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
async def rank(interaction: Interaction, rang:Choice[int], page:Choice[int]):
    await interaction.response.defer() 
    if rang.value:
        rank_list=fetch_core_rank()
    else:
        rank_list=fetch_overall_rank()
    embed=Embed(title=f"Tier List 排名 | {rang.name} | # {page.name}")
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
# async def statistics(interaction: Interaction):
#     bf,stats=stat_method.overall_point_stat()
#     embed=Embed(title=f"Tier List 積分統計長條圖",)
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


@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@bot.tree.command(name="kill", description="重啟機器人 | 只有開發者可以使用") 
async def kill(interaction: Interaction): 
    if interaction.user.id==bot.owner_id:
        fallback = await interaction.response.send_message(embed=Embed(title="機器人已關閉",description="掰掰"),ephemeral=True)
        owner= await owner_user()
        await owner.send(embed=Embed(title="機器人已關閉",description="Shutdown"))
        await bot.close()
    else:
        print(f"{interaction.user.name} ({interaction.user.id}) tried to kill the bot, but he is not the owner")
        await interaction.response.send_message(embed=Embed(title="你沒有權限關閉機器人",description="只有開發者可以重啟"),ephemeral=True)


@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@bot.tree.command(name="update_tier", description="更新玩家Tier資料 | 只有開發者可以使用")
@app_commands.describe(player="玩家名稱",mode="遊戲模式",tier="Tier,表示移除",is_retired="是否退役",inform_discord_user="DC用戶通知對象",reason="原因")
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
async def update_tier(interaction: Interaction,player:str,mode:Choice[int],tier:Choice[int],is_retired:bool=False,inform_discord_user:Member=None,reason:str=None):
    await interaction.response.defer()
    if interaction.user.id==bot.owner_id:
        via_admin = False
        pass
    elif fetch_role_json(interaction.user.id) == "admin":
        via_damin = True
        pass
    else:
        print(f"{interaction.user.name} ({interaction.user.id}) tried to run update_tier command, but he is not the owner")
        await interaction.followup.send(embed=Embed(title="你沒有權限更改玩家資料",description="只有開發者可以更改"),ephemeral=True)
        return
    
    player_to_update=Player(player)
    _,orginal_tier=player_to_update.get_tier(str(mode.value))
    
    try:
        player_to_update.update_tier(mode.value,tier.value,is_retired=is_retired)
        info = embed=Embed(title="更新成功",description=f"已將 {player_to_update.name} ({player_to_update.uuid}) {mode.name} 項目的 Tier 從 {orginal_tier} 更改為 {tier.name}\n原因： {reason} [本訊息將會留存予 <@{bot.owner_id}>]")
        await interaction.followup.send(embed=info)
        dm = bot.get_partial_messageable(1410204311715315722)
        await dm.send(embed=info)
        if inform_discord_user:
            try:
                player_dm = await inform_discord_user.create_dm()
                info = embed=Embed(title="福爾摩沙 Tier List Tier 變更通知",description=f"玩家 {player_to_update.name} ({player_to_update.uuid}) 您好：\n 您 {mode.name} 項目的 Tier 已從 {orginal_tier} 變更為 {tier.name}。\n 原因： {reason if reason else "無"} \n 如有任何問題，請聯繫福爾摩沙 Tier List 管理人員\n 前往[福爾摩沙 Tier List Discord Server](https://discord.gg/hamescZvtP)")
                await player_dm.send(embed=info)
            except Exception as e:
                raise Exception("無法傳送訊息: {e}")

    except Exception as e:
        import traceback
        await interaction.followup.send(embed=Embed(title="更新失敗",description=f"發生錯誤:\n ```{traceback.format_exception(e)}```"))
    
    return


@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@bot.tree.command(name="add_test_record",description="考試成果寫入資料庫(update_tier替代方案)/考官登記成績")
@app_commands.describe(examinee="受試玩家",mode="考試項目",examiner="執試考官 | 如果為考官身分可默認選擇",examinee_score="受試玩家得分",examiner_score="執試考官得分",new_tier="受試玩家Tier評測結果",date="考試日期，預設為指令執行當下日期，格式請參照`YYYY-MM-DD`",input_test_id="自訂考試ID | 考官不可以自訂",orginal_tier="原考試tier，預設為資料庫tier，輸入後無法更新tier | 考官請勿輸入",do_update_tier="是否執行更新tier | 考官請勿更變",examinee_discord="如果在考試公布區域發送，可提及受試者Discord用戶",ps="備註")
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
        ],orginal_tier=[
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
async def add_test_record(interaction:Interaction, examinee:str, mode:Choice[int],examiner:str,examinee_score:int,examiner_score:int,new_tier:Choice[int],date:str="today",examinee_discord:Member=None,input_test_id:str="Default",orginal_tier:Choice[int]=None,do_update_tier:bool=True,ps:str=""):
    # TODO: 建立「考試確認步驗」：在寫入資料庫前，先發送一個帶有確認按鈕的 Embed 給考官
    # TODO: 自動偵測異常數據（例如：分數差過大或不合理的等級跳躍）並標記警告
    # TODO: 將複雜的「私訊通知與連結邏輯」提取成獨立的 service 函式，提高可讀性
    # 若考官手動輸入錯誤可能繞過檢查，應改用更嚴謹的按鈕 (Button) 確認互動。
    logging.info(f"{interaction.user.id=}")
    role = fetch_role_json(interaction.user.id)
    logging.info(f"{role=}")
    in_test_report_chennel=interaction.channel_id in (990383001709977651,990383035323121695,1151080742294667384,1406316354310770878)
    logging.info(f"{in_test_report_chennel=}")
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id == bot.owner_id:
        logging.info("user is owner")
        pass
    else:
        if role == "admin":
            logging.info("user is admin")
            pass
        elif role == "examiner":
            logging.info("user is examiner")
            if in_test_report_chennel:
                linked= await check_link(interaction=interaction)
                if linked:
                    logging.info("examiner is verified.")
                    examiner=linked
                    input_test_id="Default"
                    do_update_tier="True"
                    orginal_tier=None
                    ps=""
                    if in_test_report_chennel and not examinee_discord:
                        logging.info("examiner did not provide dcmember")
                        await interaction.followup.send(embed=Embed(title="請提供受試者Discord用戶",description=""),ephemeral=True)
                        return
                else:
                    logging.info("examiner is not verified")
                    return
            else:
                logging.info("in the wrong channel")
                await interaction.followup.send(embed=Embed(title="你不能在這裡使用該指令",description="請到 <#990383001709977651> <#990383035323121695> <#1151080742294667384> 使用"),ephemeral=True)
        else:
            logging.info("user is nobody")
            await interaction.followup.send(embed=Embed(title="你沒有權限更改資料",description="只有開發者可以更改"),ephemeral=True)
            return
                

    examinee=Player(examinee)
    examiner=Player(examiner)
    repeat_warning = False
    cd_warning = False
    temp=data_query("SELECT test_id,test_date FROM tests WHERE examinee=? AND mode_id =? ORDER BY test_date DESC LIMIT 1",(examinee.uuid,mode.value))
    if temp:
        check_test_id,check_date=temp
        check_date=datetime.date.fromisoformat(check_date)
        if check_date + datetime.timedelta(days=20) > datetime.date.today():
            cd_warning = True
            check_test_record = data_query("SELECT examiner,outcome_tier_id,examinee_grade,examiner_grade FROM tests WHERE test_id = ?",(check_test_id,))
            repeat_warning = all((examiner.uuid == check_test_record[0],
                                 check_test_record[1] == str(new_tier.value),
                                 examinee_score == check_test_record[2],
                                 examiner_score == check_test_record[3]))
    if date == "today":
        date=today()
    else:
        try:
            date=datetime.date.fromisoformat(date)
            date=date.isoformat()
        except Exception as e:
            raise CommandException("日期格式錯誤","日期格式應為`YYYY-MM-DD`，如 `2026-02-25`")


    examiner_id= data_query(f"SELECT examiner_id FROM examiners WHERE uuid = '{examiner.uuid}'")
    # logging.info(f"{examiner_id=} {examiner=}")
    have_old_tier=False
    if not orginal_tier:
        tier_dict=examinee.tier_dict.get('tiers')
        old_tier_name=tier_dict.get(mode.name)
        tier_table=get_tier_table()
        old_tier_id=tier_table.get(old_tier_name)
    else:
        have_old_tier=True
        old_tier_id=orginal_tier.value
        old_tier_name=orginal_tier.name
        
    date_list=date.split("-")
    ym=str(date_list[0])+str(date_list[1])
    if input_test_id == "Default" or input_test_id.startswith("COMMIT:"):
        last_id = data_query(f"SELECT test_id FROM tests WHERE test_id LIKE 'T{ym}%' ORDER BY test_id DESC LIMIT 1")
        if last_id:
            sub_id=str(int(last_id[-3:])+1)
            test_id="T"+ym+sub_id.zfill(3)
        else:
            test_id="T"+ym+"001"
    else:
        if input_test_id.startswith("COMMIT:"):
            raise CommandException("Costomized test ID is not supported in COMMIT mode",)
        else:
            test_id = input_test_id
            
    if cd_warning or repeat_warning:
        if input_test_id == "COMMIT:"+test_id:
            pass
        else:
            if repeat_warning:
                await interaction.followup.send(ephemeral=True,embed=Embed(colour=0xFFFF00,title="重複登記警告",description=f"偵測到該受試者在20天內有同一項目考試，並且成績及考官一模一樣，請確認是否已經登記，如果確認要登記，請在input_test_id欄位輸入: ``{"COMMIT:"+test_id}``"))
            else:
                await interaction.followup.send(ephemeral=True,embed=Embed(colour=0xFFFF00,title="考試冷卻警告",description=f"偵測到該受試者在20天內有同一項目考試，如果確認要登記，請在input_test_id欄位輸入: ``{"COMMIT:"+test_id}``"))
            return
        
    dm = bot.get_partial_messageable(1410204311715315722)    
    try:

        with new_conn() as conn:
            cursor=conn.cursor()
            cursor.execute("INSERT INTO tests VALUES(?,?,?,?,?,?,?,?,?)",(test_id,mode.value,examinee.uuid,examiner.uuid,examinee_score,examiner_score,old_tier_id,new_tier.value,date))
            link_infomation_message=Embed(color=Colour.blue())
            link_desc=""
            if examinee_discord:
                cursor.execute("SELECT * FROM discord_minecraft WHERE discord_user_id = ? AND minecraft_uuid = ?",(examinee_discord.id,examinee.uuid))
                expired_at=datetime.date.today()+datetime.timedelta(days=90)
                
                if cursor.fetchall():
                    try:
                        cursor.execute("UPDATE discord_minecraft SET expired_at = ?, discord_user_name=? WHERE discord_user_id = ? AND minecraft_uuid = ?",(expired_at.isoformat(),examinee_discord.name,examinee_discord.id,examinee.uuid))
                        link_desc="系統偵測到您的帳號連結狀態正常，我們已自動為您延長了帳號連結的有效期限。"
                    except Exception as e:
                        await dm.send(f"更新 Minecraft 玩家 {examinee.name} ({examinee.uuid}) 與 {examinee_discord.mention} ({examinee_discord.id}) 連結之期限時發生錯誤:\n```{e}```\n")
                else:
                    try:
                        cursor.execute("DELETE FROM discord_minecraft WHERE discord_user_id = ? OR minecraft_uuid = ?",(examinee_discord.id,examinee.uuid))
                        cursor.execute("INSERT INTO discord_minecraft VALUES(?,?,?,?)",(examinee_discord.id,examinee_discord.name,examinee.uuid,expired_at.isoformat()))
                        link_desc=f"系統已自動將您開單考試時的Discord帳戶(該帳戶)連結至玩家 {examinee.name}。"
                    except Exception as e:
                        await dm.send(f"連結 Minecraft 玩家 {examinee.name} ({examinee.uuid}) 與 {examinee_discord.mention} ({examinee_discord.id}) 時發生錯誤:\n```{e}```\n")

            conn.commit()
        if do_update_tier and not have_old_tier:
            examinee.update_tier(mode.value,new_tier.value)
        if examinee_discord:
            link_infomation_message.title="考試結果通知"
            link_infomation_message.description=f"""
親愛的 Minecraft 玩家 **{examinee.name}** 您好：

感謝您參與 **福爾摩沙 Tier List** 考試，考官/管理人員已將本次考試結果正式登記入資料庫中。{link_desc}

**【考試結果報告】**
* **受試玩家：** {examinee.name}
* **玩家 UUID：** `{examinee.uuid}`
* **考試項目：** {mode.name}
* **考官：** {examiner.name}
* **考試日期：** {date}
* **對戰比分：**
{examinee.name}  **{examinee_score} : {examiner_score}** {examiner.name}
* **Tier 變更：** {old_tier_name} → **{new_tier.name}**
* **備註：** {ps if ps != "" else "無"}

*如果以上資訊有誤，請聯繫管理人員(<@{bot.owner_id}>)或考官({examiner.name})*

{f'**【驗證連結資訊】**\n* **連結對象：** {examinee_discord.mention} ({examinee_discord.id})\n* **有效期限：** 90 天\n* **到期日期：** {expired_at.isoformat()}' if examinee_discord else ''}
""".replace("_","\_")+"""
**💡 小提醒：**
* 完成驗證後，您在使用本機器人 `/tier` 指令時可以**省略玩家名稱參數**，系統將自動帶入您的資料，請多多利用。
* 若期限屆滿需要重新驗證，您可以透過**再次參與考試**或使用 `/link_hypixel` 指令（詳情請見 `/tier` 指令說明）來完成。
* 您也可以透過 [福爾摩沙 TierList 網站](https://tierlist.formosa.network) 查詢玩家資訊，資料有30分鐘左右延遲。

祝您在高版本 PVP 領域中**百尺竿頭，更進一步！**
---
*福爾摩沙 Tier List Database 敬上*
"""
            link_infomation_message.set_author(
            name="福爾摩沙 Tier List Database", 
            icon_url=bot.user.avatar.url # 這裡可以放你們的 LOGO 網址
            )
            link_infomation_message.set_footer(
            text="自動發送訊息"
            )
            examinee_dm_channel= await examinee_discord.create_dm()
            try:
                await examinee_dm_channel.send(embed=link_infomation_message)
                link_infomation_message.title="考試結果通知 (備份留存)"
                await dm.send(embed=link_infomation_message)
            except discordForbidden:
                await dm.send("考試結果私訊時，無法發送，特此留存",embed=link_infomation_message)


        test_info=Embed(title="考試成果已收錄於資料庫中",
description=f"""
考試ID: {test_id}
受試者: {examinee.name} ({examinee_discord.mention if examinee_discord else "No discord user provided"})
uuid: {examinee.uuid}
項目: {mode.name}
考官: {examiner.name} (ID: {examiner_id})
日期: {date}
結果:
{examinee.name}   **{examinee_score} : {examiner_score}**   {examiner.name}
Tier 變化: {old_tier_name} → {new_tier.name}
{"註: TierList資料表已自動更新" if not have_old_tier else ""}
{"註: 已透過強制方式無視重複登記/考試冷卻警告" if cd_warning or repeat_warning else ""}
{"註: 本訊息將同時發送通知至開發者留存" if role == examiner else ""}""".replace("_","\_"))
        
        if in_test_report_chennel:
            in_exam_report_channel=True
            if not old_tier_name:
                cpr="考上了"
            elif str(new_tier.value)>str(old_tier_id):
                cpr="升級至"
            elif str(new_tier.value)==str(old_tier_id):
                cpr="停留在"
            else:
                cpr="降級至"
            
            await interaction.followup.send(
                content=f"""{examinee_discord.mention} ({examinee.name}) {cpr} **{new_tier.name}** {mode.name}
**{examiner.name} {examiner_score}-{examinee_score} {examinee.name}**\n -# 請將此訊息複製貼上""".replace("_","\_"))
            await interaction.followup.send(embed=test_info,ephemeral=True)
        else:
            await interaction.followup.send(embed=test_info)
        
        await dm.send(embed=test_info)
        if examiner.discord_user_id:
            examiner_dm_channel = await bot.fetch_user(examiner.discord_user_id)
            if examiner_dm_channel:
                await examiner_dm_channel.send(embed=test_info)
                await examiner_dm_channel.send(embed=Embed(title="!!請仔細核對以上成績資訊!!",colour=Colour.red(),description=f"**考官您好：**\n成績已登記入資料庫！如果以上資訊有問題，或者是後續考試成績需更改之情形，請私訊開發人員/資料庫管理人員 <@{bot.owner_id}>，感謝您的合作！"))
            
        
        return
    
    except Exception as e:
        raise e



@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@bot.tree.command(name="add_examiner", description="新增考官")
async def add_examiner(interaction: Interaction,player:str):
    await interaction.response.defer()
    if interaction.user.id==bot.owner_id:
        num=data_query("SELECT examiner_id FROM examiners ORDER by examiner_id DESC LIMIT 1")[1:]
        examier_id="E"+str(int(num)+1).zfill(4)
        player=Player(player)
        data_query(f"INSERT INTO examiners VALUES('{examier_id}','{player.uuid}')")
        await interaction.followup.send(embed=Embed(title="操作成功",description=f"已將 {player.name} ({player.uuid}) 新增至考官資料庫，ID: {examier_id}".replace("_","\_")))
        return
    else:
        await interaction.followup.send(embed=Embed(title="你沒有權限更改資料",description="只有開發者可以更改"),ephemeral=True)
        return
        

@app_commands.checks.cooldown(1, 1, key=lambda i: i.user.id)
@bot.tree.command(name="remove_examiner", description="移除考官")
async def remove_examiner(interaction: Interaction,examiner:str):
    await interaction.response.defer()
    if interaction.user.id==bot.owner_id:
        logging.info(f"{examiner=}")
        examiner=Player(examiner)
        examiner_id = data_query(f"SELECT examiner_id FROM examiners WHERE uuid = '{examiner.uuid}'")
        logging.info(f"{examiner_id=}")
        data_query(f"DELETE FROM examiners WHERE examiner_id = '{examiner_id}'",do_commit=True)
        await interaction.followup.send(embed=Embed(title="操作成功",description=f"已將 {examiner.name} 從考官資料庫移除".replace("_","\_")))
        return
    else:
        await interaction.followup.send(embed=Embed(title="你沒有權限更改資料",description="只有開發者可以更改"),ephemeral=True)
        return
    



@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.command(name="query", description="SQL查詢 (僅限SELECT) ")
@app_commands.describe(script="SQL查詢語法，僅限SELECT，切分至第一個分號為止")
async def query(interaction: Interaction,script:str):
    await interaction.response.defer() 
    db_backup()
    if bot.is_owner(interaction.user):
        pass
    else:
        # if not script.startswith("SELECT"):
        #     await interaction.followup.sends("只能輸入SELECT開頭的查詢語法",ephemeral=True)
        # script=script.split(';')[0]
        # for i in ('UPDATE',"DELETE","INSERT","DROP","CREATE","ALTER","PRAGMA","ATTACH",'DETACH','REINDEX','VACUUM','--'):
        #     if i.lower() in script.lower():
        #         await interaction.followup.send(f"偵測到非法詞彙：{i}",ephemeral=True)
        #         return
        await interaction.followup.send(embed=Embed(title="目前已不開放其他使用者使用該指令",description="只有開發者可以使用"),ephemeral=True)
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

@app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
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
async def play_server(interaction: Interaction, ping_range:Choice[str]):
    # TODO: 實作緩存機制：伺服器狀態每 5 分鐘更新一次即可，不需要每次指令都請求 API
    # TODO [UX]: 增加「點擊複製 IP」的按鈕
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
        embed=Embed()
        # if i==0:
        #     embed.title=f":fire: {j[1]} :fire: (強力推薦!!!)"
        # else:
        embed.title=j[1]+" - "+j[4]
        
        embed.add_field(name="IP",value=j[3])
        embed.add_field(name="地區",value=j[2])
        embed.set_thumbnail(url=f"https://mc-api.co/v1/icon/{j[3]}")
        embed.add_field(name="介紹",value=j[5],inline=False)
        embed.set_image(url=f'https://mcapi.us/server/image?ip={j[3]}')
        response=None
        try:
            response=requests.get(f" https://api.mcsrvstat.us/3/{j[3]}",timeout=(5,10))
        except Exception as e:
            embed.set_footer(text="目前網路發生問題，僅能從資料庫擷取資料")
        if response:
            if response.status_code==200:
                data=response.json()
                if data["online"]:
                    embed.add_field(name="狀態",value="🟢在線")
                    # embed.add_field(name="Ping (台北)",value=f"{data.get('ping')} ms")
                    embed.add_field(name="在線人數",value=data.get('players').get('online'))
                    embed.add_field(name="版本",value=data.get('version'))
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

@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
async def dashboard(interaction:Interaction,factor:Choice[int]):
    await interaction.response.defer()
    embed=Embed(title=f"Tier List 資料庫儀錶板 - {factor.name}")
    today=datetime.date.today().isoformat()
    last_month=(datetime.date.today().replace(day=1)-datetime.timedelta(days=1)).isoformat()
    embed.set_footer(text=datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"))
    if factor.value==1:
        embed.add_field(name="資料庫紀錄玩家數",value=get_players_amount())
        embed.add_field(name="封禁玩家數", value=get_banned_amount())
        embed.add_field(name="取得Tier玩家數",value=get_tier_list_amount())
        embed.add_field(name="考官數",value=data_query("SELECT COUNT(*) FROM examiners"),inline=False)
        embed.add_field(name=f"本月({datetime.date.today().strftime("%m月")})考試人次",value=data_query(f"SELECT COUNT(*) FROM tests WHERE test_date LIKE '{today[:-2]}%'"))
        embed.add_field(name="上月考試人次",value=data_query(f"SELECT COUNT(*) FROM tests WHERE test_date LIKE '{last_month[:-2]}%'"))
        embed.add_field(name=f"累計考試人次(2025年12月-)",value=data_query("SELECT COUNT(*) FROM tests"),inline=False)
        r=data_query(f"SELECT player,COUNT(*) AS x FROM tests,players WHERE players.uuid = tests.examiner AND test_date LIKE '{datetime.date.today().isoformat()[:-2]}%' GROUP BY player ORDER BY x DESC LIMIT 1")
        if r:
            embed.add_field(name="本月目前執試最多次考官",value=f"{r[0]} (共 {r[1]} 次)")
        else:
            embed.add_field(name="本月目前執試最多次考官",value="無")
            
        r=data_query(f"SELECT player,COUNT(*) AS x FROM tests,players WHERE players.uuid = tests.examiner AND test_date LIKE '{last_month[:-2]}%' GROUP BY player ORDER BY x DESC LIMIT 1")
        
        if r:
            embed.add_field(name="上月明星考官",value=f"{r[0]} (共 {r[1]} 次)")
        else:
            embed.add_field(name="上月明星考官",value="無")
            
        
    else:
        embed.add_field(name="其他儀錶板開發中",value="敬請期待")
        
    await interaction.followup.send(embed=embed)
    return
        
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.command(name="examiners_leaderboard",description="考官執試排行榜")             
async def examiners_leaderboard(interaction:Interaction):
    await interaction.response.defer()
    embed=Embed(title="考官執試排行榜")
    l_total=data_query("SELECT players.player,COUNT(*) FROM tests,players WHERE tests.examiner=players.uuid GROUP BY examiner ORDER BY COUNT(*) DESC")
    l_month=data_query(f"SELECT players.player,COUNT(*) FROM tests,players WHERE tests.examiner=players.uuid AND tests.test_date LIKE '{datetime.date.today().isoformat()[:-2]}%' GROUP BY examiner ORDER BY COUNT(*) DESC")
    last_month=(datetime.date.today().replace(day=1)-datetime.timedelta(days=1)).isoformat()
    l_lst_month=data_query(f"SELECT players.player,COUNT(*) FROM tests,players WHERE tests.examiner=players.uuid AND tests.test_date LIKE '{last_month[:-2]}%' GROUP BY examiner ORDER BY COUNT(*) DESC")

    desc=""
    rank=1
    if l_total:
        for i,j in enumerate(l_total):
            if i == 0 or j[1]!=l_total[i-1][1]:
                rank=i+1
            else:
                pass
            desc+=f"第 {rank} 名 : {j[0].replace("_","\_")} - `{j[1]}` 次\n"
        embed.add_field(name='總排行',value=desc,inline=False)
    desc=""
    if l_month:
        for i,j in enumerate(l_month):
            if i == 0 or j[1]!=l_month[i-1][1]:
                rank=i+1
            else:
                pass
            desc+=f"第 {rank} 名 : {j[0].replace("_","\_")} - `{j[1]}` 次\n"
        embed.add_field(name='本月度排行',value=desc)
    desc=""
    if l_lst_month:
        for i,j in enumerate(l_lst_month):
            if i == 0 or j[1]!=l_lst_month[i-1][1]:
                rank=i+1
            else:
                pass
            desc+=f"第 {rank} 名 : {j[0].replace("_","\_")} - `{j[1]}` 次\n"
        embed.add_field(name='上月度排行',value=desc)
    await interaction.followup.send(embed=embed)

# @play_server.autocomplete("mode")
# async def auto_complete_mode(interaction: Interaction, current: str):
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


@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.command(name="help", description="打開指令手冊，查看所有詳細指南！")
async def help_command(interaction: Interaction):
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
    
        embed = Embed(
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

@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.command(name="test_history", description="查詢測驗歷史紀錄")
@app_commands.describe(player_or_uuid="篩選受試者玩家名稱或UUID",test_id_like="模糊篩選考試ID(考試ID為一項考試之唯一辨識值)",date="篩選特定日期",examiner="篩選特定考官玩家名稱或是UUID",mode="篩選模式名稱",page="指定頁數，默認為第一頁(建議先執行一遍了解有多少頁)")
@app_commands.choices(
    mode = [
        Choice(name=y,value=int(x)) for x,y in get_modes_dict().items()
    ]
)
async def test_history(interaction: Interaction,player_or_uuid:str=None,test_id_like:str=None,date:str=None,examiner:str=None,mode:Choice[int]=None,page:int=None):
    await interaction.response.defer()
    filter_query=[]
    filter_var=[]
    thumbnail=None
    description=""
    if player_or_uuid:
        player = Player(player_or_uuid)
        filter_query.append('examinee = ?')
        filter_var.append(player.name)
        thumbnail=player.head_pic_url
        description+=f"篩選: 受試玩家 `{player.name}`\n"
    if examiner:
        examiner = Player(examiner)
        filter_query.append('examiner = ?')
        filter_var.append(examiner.name)
        thumbnail=examiner.head_pic_url
        description+=f"篩選: 考官 `{examiner.name}`\n"
    if mode:
        mode = mode.name
        filter_query.append('mode = ?')
        filter_var.append(mode)
        description+=f"篩選: 模式 `{mode}`\n"
    if date:
        try:
            datetime.date.fromisoformat(date)
        except Exception as e:
            raise CommandException("日期格式錯誤","日期格式應為`YYYY-MM-DD`，如 `2026-02-25`")
        filter_query.append('test_date = ?')
        filter_var.append(date)
        description+=f"篩選: 日期 `{date}`\n"
    if test_id_like:
        filter_query.append("test_id LIKE ?")
        filter_var.append(f'%{test_id_like}%')
        description+=f"篩選: test_id 相似 `{test_id_like}`\n"
    if filter_query and filter_var:
        filter_query_combine =" WHERE "+" AND ".join(filter_query)
    else:
        filter_query_combine = ""
    full_query=f"SELECT * FROM test_records {filter_query_combine} ORDER BY test_id DESC"
    logging.info(f"{full_query=}")
    result = data_query(full_query,tuple(filter_var),do_format=False)
    
    embed=Embed(title="歷史考試紀錄查詢結果",description=description)
    embed.set_thumbnail(url=thumbnail)
    if not result:
        embed.colour=Colour.green()
        embed.add_field(name="找不到任何紀錄",value="去[考試](https://discord.gg/jsHFxvd3)吧。")
        await interaction.followup.send(embed=embed)
        return
    max_page=(len(result)-1)//5+1
    if page:
        if page> max_page:
            raise CommandException("查詢頁數超出範圍",f"此查詢條件結果共{len(result)}筆，最多為{max_page}頁")
        if page <=0 or type(page) is not int:
            raise CommandException("無效的頁數","請輸入0以上的整數數字")
    else:
        page=1
    page_result = result[(page-1)*5:min(len(result),page*5)]
    for i,x in enumerate(page_result):
        days_ago=(datetime.date.today()-datetime.date.fromisoformat(x[1])).days
        cd= "" if days_ago > 21 else "(🛑冷卻中)" 
        embed.add_field(name=f'{i+1}. {x[0]} {cd}',value=f"**{x[1]} | {x[2]}**\n{x[3]} `{x[4]}` : `{x[5]}` {x[6]}\n{x[7]} → {x[8]}".replace("_","\_"),inline=False)
    embed.set_footer(text=f"共查詢到 {len(result)} 筆，第 {page}/{max_page} 頁")
    embed.colour=Colour.orange()
    await interaction.followup.send(embed=embed)
    
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.command(name="manual_link", description="手動連結Discord - Minecraft")
async def manual_link(interaction: Interaction,player_or_uuid:str,discord_user:Member,expiration:int):
    await interaction.response.defer()
    
    if interaction.user.id != bot.owner_id:
        raise CommandException("權限不足","請勿使用該指令")
        return
    
    player=Player(player_or_uuid)
    if expiration <=0 or type(expiration) is not int:
        raise CommandException("expiration 參數格式錯誤","格式為非0正整數")
        return
    
    dm = bot.get_partial_messageable(1410204311715315722)  
    
    with new_conn() as conn:
        link_desc=""
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM discord_minecraft WHERE discord_user_id = ? AND minecraft_uuid = ?",(discord_user.id,player.uuid))
        expired_at=datetime.date.today()+datetime.timedelta(days=expiration)
        
        if cursor.fetchall():
            try:
                cursor.execute("UPDATE discord_minecraft SET expired_at = ?, discord_user_name=? WHERE discord_user_id = ? AND minecraft_uuid = ?",(expired_at.isoformat(),discord_user.name,discord_user.id,player.uuid))
                link_desc=f"偵測到帳號連結狀態正常({player.name} (`{player.uuid}`) - {discord_user.mention})，已延長帳號連結的有效期限。".replace("_","\_")
            except Exception as e:
                await dm.send(f"更新 Minecraft 玩家 {player.name} ({player.uuid}) 與 {discord_user.mention} ({discord_user.id}) 連結之期限時發生錯誤:\n```{e}```\n")
        else:
            try:
                cursor.execute("DELETE FROM discord_minecraft WHERE discord_user_id = ? OR minecraft_uuid = ?",(discord_user.id,player.uuid))
                cursor.execute("INSERT INTO discord_minecraft VALUES(?,?,?,?)",(discord_user.id,discord_user.name,player.uuid,expired_at.isoformat()))
                link_desc=f"已將Discord帳戶({discord_user.mention})連結至玩家 {player.name} (`{player.uuid}`)。"
            except Exception as e:
                await dm.send(f"連結 Minecraft 玩家 {player.name} ({player.uuid}) 與 {discord_user.mention} ({discord_user.id}) 時發生錯誤:\n```{e}```\n")
    
    await dm.send(link_desc)
    await interaction.followup.send(content="操作成功。",ephemeral=True)
    return 
        
### GUILD LIMITED COMMAND ###


@app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
@bot.tree.command(name="ai_chat", description="與AI聊天")
@app_commands.guilds(DEV_GUILD)
async def ai_chat(interaction: Interaction,text:str):
    await interaction.response.defer()
    await chat_via_interaction(interaction,text)
    
    
       
### MENU COMMAND ###      
        
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.context_menu(name="智慧登記")
async def smart_signing(interaction: Interaction, message: Message):
    await interaction.response.defer(ephemeral=True)
    if interaction.channel.id in (990383001709977651,990383035323121695,1151080742294667384):
        text=message.content
        pattern = r"<@!?(?P<discord_id>\d+)>\s*\(?[*_~]*(?P<username>.+?)[*_~]*\)?\s*(?P<action>考上了|升級至|降級至|維持在|停留在)\s*[*_~]*(?P<mode>[HLM]T\d)[*_~]*\s*[*_~]*(?P<tier>.+?)[*_~]*$"
        matches = re.finditer(pattern, text)
        parsed_results = []
        for match in matches:
            data = match.groupdict()
            
            # 整理成你要的四個參數
            discord_id = data['discord_id']
            username = data['username']
            mode = data['mode']
            tier = data['tier'].strip()
            action = data['action'] # 雖然你沒提，但保留動作可能有助於判斷邏輯
            
            parsed_results.append(
                f"🔹 **玩家**: <@{discord_id}>\n"
                f"📛 **名稱**: {username}\n"
                f"🎮 **模式**: {mode}\n"
                f"🏆 **階級**: {tier}\n"
                f"━━━━━━━━━━━━"
            )

        if not parsed_results:
            await interaction.followup.send("❌ 找不到符合格式的玩家資訊。", ephemeral=True)
        else:
            final_report = "\n".join(parsed_results)
            await interaction.followup.send(f"✅ **解析成功！**\n\n{final_report}", ephemeral=True)
    else:
        await interaction.followup.send("非考試公布頻道，無法使用")
        




# 建立一個右鍵點擊訊息時出現的指令
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
@bot.tree.context_menu(name="撤回此訊息")
async def retract_message(interaction: Interaction, message: Message):
    if interaction.user.id==bot.owner_id:
        try:
            if message.author.id == bot.user.id:
                await message.delete()
                await interaction.response.send_message("訊息已撤回",ephemeral=True,delete_after=5)
            else:
                await interaction.response.send_message("這不是我的訊息",ephemeral=True,delete_after=3)
        except discordNotFound:
            await interaction.response.send_message("❓ 訊息可能已經被刪除了", ephemeral=True)
        except discordForbidden:
            await interaction.response.send_message("🚫 我沒有權限刪除這則訊息（請檢查頻道權限）", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"🚨 發生預期外的錯誤：{e}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 你沒有權限指使我刪除這則訊息", ephemeral=True)
        return





### AUTO COMPLETE ###
@manual_link.autocomplete("player_or_uuid")
@test_history.autocomplete("player_or_uuid")
@link_hypixel.autocomplete("player_or_uuid")
@tier_ban.autocomplete("player_or_uuid")
@add_examiner.autocomplete("player")
@tier.autocomplete("player_or_uuid")
@update_tier.autocomplete("player")
@tier_unban.autocomplete("player_or_uuid")
@add_test_record.autocomplete("examinee")
async def auto_complete_player(interaction: Interaction, current: str):
    logging.info(f"triggeer AC-player")
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

@test_history.autocomplete("examiner")
@remove_examiner.autocomplete("examiner")
@add_test_record.autocomplete("examiner")
async def auto_complete_examiner(interaction: Interaction,current: str):
    logging.info(f"triggeer AC-examiner")
    l=data_query("SELECT player,examiners.examiner_id FROM players,examiners WHERE examiners.uuid = players.uuid ")
    if current:
        match_=set([x for x in l if current.lower() in x[0].lower()])
        starts_with=set([x for x in l if [x[0].lower()][0].startswith(current.lower())])
        sec=match_-starts_with
        l=sorted(list(starts_with),key= lambda x:x[0])+sorted(list(sec),key= lambda x:x[0])
        return [app_commands.Choice(name=x[0],value=x[0]) for x in l if current.lower() in x[0].lower()][:25]
    else:
        return [app_commands.Choice(name=x[0],value=x[0]) for x in l]


       

### ERROR HANDLEING ###
@bot.tree.error
async def on_tree_error(interaction: Interaction, error: app_commands.AppCommandError):
    # TODO: 建立錯誤代碼系統 (Error Code)
    if interaction.response.is_done():
        send=interaction.followup.send
    else:
        send= interaction.response.send_message
    logging.exception(f"{error}")
    if isinstance(error, app_commands.CommandOnCooldown):
        embed=Embed(colour=Colour.yellow(),title="⏳ 指令冷卻中",description=f"請等待 `{error.retry_after:.2f}` 秒")
        await send(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await send("你沒有使用這個指令的權限", ephemeral=True)
        return
    elif isinstance(error, EntityException):
        error:EntityException
        embed=Embed(colour=Colour.red(),title="內部操作錯誤")
        embed.add_field(name=error,value=error.solution)
        await send(embed=embed,ephemeral=True)
        return
    elif isinstance(error,CommandException):
        error:CommandException
        embed=Embed(colour=Colour.red(),title="指令操作錯誤")
        embed.add_field(name=error,value=error.solution)
        await send(embed=embed,ephemeral=True)
        return
    else:
        # 預設未捕捉的錯誤，選擇丟出或回報
        dm = bot.get_partial_messageable(1410204311715315722)
        params = []
        if interaction.data:
            if "options" in interaction.data: # type: ignore
                for option in interaction.data["options"]: # type: ignore
                    params.append(f'{option["name"]}: {option["value"]}\n'.replace("_","\_")) # type: ignore
        params_str = ", ".join(params)
        if interaction.guild:
            guild_name=interaction.guild
            guild_id=interaction.guild_id
        else:
            guild_name="Private"
            guild_id=None
        if type(interaction.channel) is DMChannel:
            channel_name=f"{interaction.user.name}'s Direct Message"
        else:
            channel_name=interaction.channel.name #type:ignore
        user_embed=Embed(colour=Colour.red(),title="⚠️ 發生未知錯誤", description="錯誤報告已經回報給開發者")
        await send(embed=user_embed,ephemeral=True,delete_after=5)
        await dm.send(embed=Embed(colour=Colour.red(),title="⚠️ 錯誤報告", description="```"+str(error.with_traceback(error.__traceback__))+"```"+f"\n時間: {datetime.datetime.now().isoformat()}\n伺服器: {guild_name} ({guild_id}) \n頻道: {channel_name} ({interaction.channel_id})\n使用者: {interaction.user.name} ({interaction.user.id}) \n指令: {interaction.command.name}\n參數: \n{params_str}".replace("_","\_"))) #type:ignore
        


### Main ###
def startup():
    try:
        
        bot.setup_hook=setup_hook
        logging.info("Starting up bot...")
        bot.run(os.getenv("BOT_TOKEN")) # type: ignore
        logging.info("Bot shutdown successfully.")
        return 0
    except Exception as e:
        logging.exception(e)
        return 1


startup()