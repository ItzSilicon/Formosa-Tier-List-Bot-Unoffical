import sqlite3
import requests
from stat_method import fetch_core_rank,fetch_overall_rank


class Player:
    with sqlite3.connect("./tier_list_latest.db") as conn:
        cursor=conn.cursor()

        def __init__(self,input:str):
            self.extra_info=[]
            if len(input)==32:
                self.uuid=input
                self.name=self.get_name(self.uuid)
            
            elif input.startswith("#unknown") :
                self.name=self.db_name
                
            elif len(input)<=16:
                for chr in input:
                    if (chr.isalnum or chr == "_") and chr !=" ":
                        continue
                    else:
                        raise Exception("Bad name format | 錯誤的玩家名稱格式")
                self.uuid,self.name=self.get_uuid(input)
            
            else:
                raise Exception("Bad input, uuid or player name is required. | 錯誤的參數，必須為uuid或玩家名稱")
            
            if self.uuid.startswith("#unknown"):
                self.extra_info.append("The infomation about this player is not traceable. |  該玩家的資料已經不可考")

            if self.db_name is None:
                self.cursor.execute("INSERT INTO players(player,uuid,is_banned,reason,is_famous,nickname,intro) VALUES(?,?,0,NULL,0,NULL,NULL)",(self.name,self.uuid))
                self.extra_info.append("New player | 新計入資料庫的玩家")
            elif self.db_name != self.name:
                self.extra_info.append(f"Name changed | 玩家名稱變動：{self.db_name} → {self.name}")
                self.cursor.execute("UPDATE players SET player=? WHERE uuid=?",(self.name,self.uuid))
            self.conn.commit()
            
            is_banned,self.banned_reason,self.intro,is_famous,self.nickname=self.cursor.execute("SELECT is_banned,reason,intro,is_famous,nickname FROM players WHERE uuid=?",(self.uuid,)).fetchone()
            
            self.is_banned = bool(is_banned)
            self.is_famous = bool(is_famous)
            self.info_dict={
                "uuid":self.uuid,
                "name":self.name,
                "is_banned":self.is_banned,
                "banned_reason":self.banned_reason,
                "is_famous":self.is_famous,
                "nickname":self.nickname,
                "intro":self.intro,
                "extra_info":self.extra_info
            }
            if self.is_banned:
                self.extra_info.append(f"This player has been banned. | 該玩家已經被封鎖，原因：{self.banned_reason}")
            
            for i in range(len(self.extra_info)):
                self.extra_info[i]="ⓘ "+self.extra_info[i]
            
        @property
        def overall_points(self):
            return self.tier_dict["overall_points"]
        
        @property
        def core_points(self):
            return self.tier_dict["core_points"]
            
        @property
        def db_name(self):
            return self.get_db_name(self.uuid)
        
        @property
        def overall_rank(self):
            return self.tier_dict["overall_rank"]
        
        @property
        def core_rank(self):
            return self.tier_dict["core_rank"]
            
        @property
        def tier_dict(self):
            self.cursor.execute("""SELECT mode.short AS MODE ,tier_table.short as TIER, tier_list.is_retired , tier_table.points , mode.is_core FROM tier_list
            JOIN mode ON tier_list.mode_id=mode.mode_id
            JOIN tier_table ON tier_list.tier_id = tier_table.tier_id
            JOIN players ON tier_list.uuid = players.uuid
            WHERE players.uuid= ? ORDER BY tier_list.mode_id""",(self.uuid,))
            data=self.cursor.fetchall()
            k=lambda x: "R" if x else ""
            return {"tiers":{x[0]:f'{k(x[2])}{x[1]}' for x in data},
                    "overall_points":sum([y[3] for y in data]),
                    "core_points":sum([z[3] for z in data if z[4]]),
                    "overall_rank":fetch_overall_rank(self.name),
                    "core_rank":fetch_core_rank(self.name)}
        
        @property
        def head_pic_url(self):
            return f"https://starlightskins.lunareclipse.studio/render/ultimate/{self.uuid}/face?borderHighlight=true&borderHighlightRadius=5&dropShadow=true"
        
        def ban(self,reason):
            self.cursor.execute("UPDATE players SET is_banned=1, reason=?",(reason,))
            self.conn.commit()
            return
            
        def unban(self):
            self.cursor.execute("UPDATE players SET is_banned=0, reason=?",(None,))
            self.conn.commit()
            return
            
    @staticmethod
    def get_name(uuid):
        try:
            response=requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}",timeout=(5,10))
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. | 與 Minecraft Services API 請求逾時")
        if response.status_code == 200:
            name=response.json()["name"]
            return name
        elif response.status_code == 404:
            raise Exception("Player is not found. | 找無此玩家")
        else:
            raise Exception(f"Unexcepted error occurs. | 未預期的錯誤 : {response.status_code}")
    
    @staticmethod
    def get_uuid(name):
        try:
            response=requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}",timeout=(5,10))
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. | 與 Minecraft Services API 請求逾時")
        if response.status_code == 200:
            uuid=response.json()["id"]
            real_name=response.json()["name"]
            return uuid.strip("-"),real_name
        elif response.status_code == 404:
            with sqlite3.connect("./tier_list_latest.db") as conn:
                cursor=conn.cursor()
                cursor.execute("SELECT uuid,player FROM players WHERE player = ?",(name,))
                queuy=cursor.fetchall()
            if len(queuy) == 1:
                return queuy[0]
            elif len(queuy) > 1:
                raise Exception("Too many players to determined. | 無法確認玩家身分：太多結果")
            else:
                raise Exception("Player is not found. | 找無此玩家")
        else:
            raise Exception(f"Unexcepted error occurs. | 未預期的錯誤 : {response.status_code}")
    
    @staticmethod
    def get_db_name(uuid):
        with sqlite3.connect("./tier_list_latest.db") as conn:
            cursor=conn.cursor()
            cursor.execute("SELECT player FROM players WHERE uuid=?",(uuid,))
            name=cursor.fetchone()
            if name:
                return name[0]
            else:
                return None


        


    

        
        
