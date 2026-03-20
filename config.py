from discord.app_commands import AppCommandError
from discord import File,Embed,Interaction,Intents,User,Colour
from discord import Object as DiscordObject
from dotenv import load_dotenv
from discord.ext import commands
from entities import query as data_query
import logging
import requests
import datetime
import json
# --- 全局配置與初始化 ---
# TODO: 將 render 列表與 constants 配置移動到獨立的 config.py，避免主程式過長
# TODO: 實作 logging 的自動轉檔 (RotatingFileHandler)，防止 latest.log 檔案過大


class CommandException(AppCommandError):
    def __init__(self,message,solution=None):
        super().__init__(message)
        self.solution = solution

def get_error_code(code:int):
    with open("error_codes","r",encoding='utf-8') as f:
        data=f.read()
    error_code_list={int(x.split("=")[0]):x.split("=")[1] for x in data.split("\n")}
    return f"```{error_code_list.get(code)}```"

def get_link_help_embeds():
    # 1. 定義圖片檔案 (假設檔案在同級目錄下)
    # 這裡先宣告 File 物件，稍後在 send 時使用
    files = [
        File("images/A.png", filename="A.png"),
        File("images/B.png", filename="B.png")
    ]

    embeds = []
    e7=Embed(
        title="Minecraft - Discord 連結驗證教學",
        description="為了確保你是玩家本人，請利用以下方法進行 Minecraft 與 Discord 帳號驗證",
        color=Colour.purple()
    )
    embeds.append(e7)
    e6 = Embed(
        title="[方法一] 在福爾摩沙 Tier List 考試",
        description="如果您在Tier List參與考試(指派之高階考試除外)，系統登記成績時會綁定您在伺服器開單考試時的Discord用戶，效期為`90`天",
        color=Colour.dark_blue()
    )
    embeds.append(e6)

    # --- Embed 0: 標題 ---
    e0 = Embed(
        title="[方法二] Hypixel 帳號驗證教學",
        description="請按照以下步驟完成 API Key 取得與 Discord 連結。效期為`45`天",
        color=Colour.blue()
    )
    embeds.append(e0)

    # --- Embed 1: 預備 ---
    e1 = Embed(
        title="📋 預先準備",
        description="1. 開啟 **Minecraft**\n2. 準備 **瀏覽器**",
        color=Colour.blue()
    )
    embeds.append(e1)

    # --- Embed 2: 第一步 ---
    e2 = Embed(
        title="Step 1：取得 API Key",
        description=(
            "1. 前往 [Hypixel Developer Dashboard](https://developer.hypixel.net/)\n"
            "2. 使用你的 Hypixel 論壇帳號登入。\n"
            "3. **若未連結帳號**，請先透過以下方式：\n"
            "   - 方法 1: 伺服器內輸入 `/linkaccount` 並點選連結\n"
            "   - 方法 2: 加入 `forums.hypixel.net` 取得驗證碼後至 [此處](https://hypixel.net/link-minecraft/) 輸入\n"
            "4. 點選 **'CREATE API KEY'** 並複製產生的 **API-Key**。"
        ),
        color=Colour.gold()
    )
    e2.set_image(url="attachment://A.png")
    embeds.append(e2)

    # --- Embed 3: 第二步 ---
    e3 = Embed(
        title="Step 2：在遊戲內綁定 Discord",
        description=(
            "1. 進入 Hypixel 伺服器 (`mc.hypixel.net`)。\n"
            "2. 輸入 `/profile` 打開個人選單。\n"
            "3. 點擊 **'Social Media'** (頭像圖示)。\n"
            "4. 點擊 **'Discord'** 並貼上你的 **Discord 使用者名稱**。\n"
            "5. 點擊書本圖示確認存檔。"
        ),
        color=Colour.gold()
    )
    e3.set_image(url="attachment://B.png")
    embeds.append(e3)

    # --- Embed 4: 第三步 ---
    e4 = Embed(
        title="Step 3：執行驗證指令",
        description="最後回到這裡輸入：\n`/link_hypixel api_key:你的KEY player_or_uuid:你的ID`",
        color=Colour.green()
    )
    embeds.append(e4)

    # --- Embed 5: 注意事項 ---
    e5 = Embed(
        title="⚠️ 注意事項",
        description=(
            "• **被封鎖者**：若先前未綁定，將無法透過此方式驗證。\n"
            "• **名稱一致**：請確保遊戲內填寫的名稱與目前 Discord 帳號完全相同。\n"
            "• **同步延遲**：設定後 API 可能需要 1-2 分鐘生效。"
        ),
        color=Colour.red()
    )
    e5.set_footer(text="提示：API Key 是私密資訊，請勿隨意分享給他人。")
    embeds.append(e5)

    return embeds, files

def fetch_role_json(dcuid:int):
    with open("role.json",'r',encoding='utf-8') as fd:
        fd=json.load(fd)
    for i in fd:
        if dcuid in fd[i]:
            return i
    return None


def verify_hypixel_discord(api_key, uuid, discord_tag):
    # 調用 Hypixel 官方 API
    url = f"https://api.hypixel.net/v2/player?key={api_key}&uuid={uuid}"
    response = requests.get(url).json()
    
    if response.get("success") and response.get("player"):
        # 抓取玩家在遊戲內設定的 Discord 連結
        social_media = response["player"].get("socialMedia", {})
        links = social_media.get("links", {})
        hypixel_discord = links.get("DISCORD") # 這是玩家在遊戲內填的內容
        
        # 比對 Discord Tag (例如: username 或 user#1234)
        if hypixel_discord == discord_tag:
            return True
    return False

def today() -> str:
    return datetime.date.today().isoformat()

async def check_ephemeral(interaction: Interaction):
    # 取得剛才發出的回應訊息
    return False

async def check_link(interaction:Interaction) -> str:
    link_info=None
    link_info=Embed()
    tmp=data_query("SELECT discord_user_name,minecraft_uuid,expired_at FROM discord_minecraft WHERE discord_user_id = ?",(interaction.user.id,))
    if tmp:
        dcusr,mcuuid,exp_date=tmp
    else:
        logging.info("This player is not linked.")
        link_info.title="未驗證"
        link_info.description="請參考連結驗證教學，如果想查詢特定的玩家請填`player_or_uuid`欄位。"
        await interaction.followup.send(embed=link_info)
        embed_list, file_list = get_link_help_embeds()
        await interaction.followup.send(embeds=embed_list,ephemeral=True,files=file_list)
        return
    logging.info("This player is linked, try to verify...")
    exp_date=datetime.date.fromisoformat(exp_date)
    is_expired = exp_date<datetime.date.today()
    logging.info(f"{exp_date=}, {is_expired=}, {exp_date<datetime.date.today()=}")
    logging.info(f"{interaction.user.name==dcusr=}")
    username_changed = dcusr != interaction.user.name
    if is_expired or username_changed:
        logging.info("This player's verification is invaild, ask to reverify.")
        data_query("DELETE FROM discord_minecraft WHERE discord_user_id = ?",(interaction.user.id,),do_commit=True)
        if is_expired:
            link_info.title="連結驗證已過期"
        else:
            # WTF, hypixel take discord user name to link making me no sense
            link_info.title="偵測到使用者名稱已變更，為確認驗證有效，請重新驗證"
        link_info.description="請使用``/link_hypixel``重新驗證"
        await interaction.followup.send(embed=link_info)
        return
    else:
        logging.info("Verify successfully.")
        logging.debug(f"{mcuuid=}")
        return mcuuid
    
    
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


intents = Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents,owner_id=1110595121591898132)
intents.message_content = True # 必須明確開啟
intents.members = True

def get_bot_user() -> User:
    return bot.user

async def owner_user() -> User:
    if bot.owner_id:
        owner:User = await bot.fetch_user(bot.owner_id)
    return owner


DEV_GUILD= DiscordObject(id=990378958501584916)
# DEV_GUILD2= DiscordObject(id=1208000802946416640)

async def setup_hook():
    try:
        synced = await bot.tree.sync()
        guild_synced = await bot.tree.sync(guild=DEV_GUILD)
        # guild_synced2 = await bot.tree.sync(guild=DEV_GUILD2)
        logging.info(f"🔄 已同步 {len(synced)} 個斜線指令")
        logging.info(f"🔄 A伺服器已同步 {len(guild_synced)} 個斜線指令")
        # logging.info(f"🔄 B伺服器已同步 {len(guild_synced2)} 個斜線指令")
    except Exception as e:
        logging.error(f"❌ 同步指令失敗: {e}")
        
        
def command_execute_log_warpper(func,local: dict):
    logging.info(f"\nCommand {func.name} is executed by {local['interaction'].user.mention} ({local['interaction'].user.global_name})\nFull parameters:\n{"\n".join([f"{x} = {y}" for x,y in local.items()])}")
    

ticket_cate={
    1150356770129190972:1,
    1150357639071539241:3,
    1150357441125560380:4,
    1150357731493023775:7,
    1176825057151033405:9,
    1150357335617835038:5
}