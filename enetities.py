import sqlite3
import requests
import os
import datetime
from stat_method import fetch_core_rank,fetch_overall_rank
from discord.app_commands import AppCommandError
db_path="./tier_list_latest.db"

class EntityException(AppCommandError):
    def __init__(self,message,solution=None):
        super().__init__(message)
        self.solution = solution


def query(script,param=None,do_format=True,do_commit=False):
    with new_conn() as conn:
        cursor=conn.cursor()
        if param:
            cursor.execute(script,param)
        else:
            cursor.execute(script)
        r=cursor.fetchall()
        if do_commit:
            conn.commit()
            return
    if r:
        if len(r)>1:
            if do_format:
                for i in r:
                    if not len(i)==1:
                        break
                else:
                    return [x[0] for x in r]
            else:
                return r
            
            return r
        else:
            if do_format:
                if len(r[0])>1:
                    return r[0]
                else:
                    return r[0][0]
            else:
                return r
    else:
        return None


def get_modes_dict() -> dict:
    with sqlite3.connect(db_path) as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM mode")
        modes_list=cursor.fetchall()
        modes={x[0]:x[2] for x in modes_list}
    return modes
        
def new_conn(db_path=db_path):
    conn=sqlite3.connect(db_path)
    return conn


def db_backup():
    
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.system(f"cp ./tier_list_latest.db ./database_backup/tier_list_{now_str}.db")
    return 

def get_examiner_dict():
    with new_conn() as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT player,examiners.examiner_id FROM players,examiners WHERE players.uuid = examiners.uuid")
        examiners_list=cursor.fetchall()
        examiners={x[0]:x[1] for x in examiners_list}
    return examiners
        
        
def get_tier_table():
    with new_conn() as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT tier_id,short FROM tier_table")
        tier_table_list=cursor.fetchall()
        tier_table_dict={x[1]:x[0] for x in tier_table_list}
    return tier_table_dict


def get_players_amount():
    with new_conn() as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT COUNT(player) FROM players")
    return cursor.fetchone()[0]
    
def get_banned_amount():
    with new_conn() as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT COUNT(player) FROM players WHERE ban_id !=''")
    return cursor.fetchone()[0]
    
def get_tier_list_amount():
    with new_conn() as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT COUNT(uuid) FROM (SELECT DISTINCT uuid FROM tier_list)")
    return cursor.fetchone()[0]

class Player:
    def __init__(self,input:str):
        self.conn=new_conn()
        self.cursor=self.conn.cursor()
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
                    raise EntityException("Bad name format | 錯誤的玩家名稱格式","請確認輸入欄位是否為正確的玩家名稱")
            self.uuid,self.name=Player.get_uuid(input)
        
        else:
            raise EntityException("Bad input, uuid or player name is required. | 錯誤的參數，必須為uuid或玩家名稱","請輸入正確格式的玩家名稱或uuid")
        
        if self.uuid.startswith("#unknown"):
            self.extra_info.append("The infomation about this player is not traceable. |  該玩家的資料已經不可考")

        if self.db_name is None:
            db_backup()
            self.cursor.execute("INSERT INTO players(player,uuid,ban_id,is_famous,nickname,intro,examiner_id) VALUES(?,?,NULL,0,NULL,NULL,NULL)",(self.name,self.uuid))
            self.extra_info.append("New player | 新計入資料庫的玩家")
        elif self.db_name != self.name:
            self.extra_info.append(f"Name changed | 玩家名稱變動：{self.db_name} → {self.name}")
            db_backup()
            self.cursor.execute("UPDATE players SET player=? WHERE uuid=?",(self.name,self.uuid))
        self.conn.commit()
        
        self.ban_id,self.ban_reason,self.ban_effective,self.ban_expired=self.check_ban()
        print(f"DEBUG: ban_id is '{self.ban_id}' type: {type(self.ban_id)}")
        self.intro,is_famous,self.nickname,self.examiner_id=self.cursor.execute("SELECT intro,is_famous,nickname,examiner_id FROM players WHERE uuid=?",(self.uuid,)).fetchone()
        
        self.is_banned = bool(self.ban_id and str(self.ban_id).strip())
        self.is_famous = bool(is_famous)
        self.is_examiner=True if self.examiner_id else False
        
        if self.is_banned:
            eff = self.ban_effective if self.ban_effective != "0" else "未知"
            exp = self.ban_expired if self.ban_expired != "0" else "永久"
            self.extra_info.append(f"This player has been banned. | 該玩家已經被封鎖，ID:`{self.ban_id}`，原因:{self.ban_reason}，生效於`{eff}`持續至`{exp}`")
        
        for i in range(len(self.extra_info)):
            self.extra_info[i]="ⓘ "+self.extra_info[i]
            
        self.info_dict={
            "uuid":self.uuid,
            "name":self.name,
            "is_banned":self.is_banned,
            "is_famous":self.is_famous,
            "nickname":self.nickname,
            "intro":self.intro,
            "extra_info":self.extra_info,
            "tier_data":self.tier_dict
        }
        
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
        self.cursor.execute("""
        SELECT mode.short AS MODE ,tier_table.short as TIER, tier_list.is_retired , tier_table.points , mode.range FROM tier_list
        JOIN mode ON tier_list.mode_id=mode.mode_id
        JOIN tier_table ON tier_list.tier_id = tier_table.tier_id
        JOIN players ON tier_list.uuid = players.uuid
        WHERE players.uuid= ? ORDER BY tier_list.mode_id""",(self.uuid,))
        data=self.cursor.fetchall()
        k=lambda x: "R" if x else ""
        return {"tiers":{x[0]:f'{k(x[2])}{x[1]}' for x in data if x[4]},
                "other_tiers":{x[0]:f'{k(x[2])}{x[1]}' for x in data if not x[4]},
                "overall_points":sum([y[3] for y in data if y[4]]),
                "core_points":sum([z[3] for z in data if z[4] == "core"]),
                "overall_rank":fetch_overall_rank(self.name),
                "core_rank":fetch_core_rank(self.name)}
    @property
    def test_records(self,limit=5):
        self.cursor.execute("SELECT      tests.test_id ,mode.short, tests.test_date,     players.player,     tests.examinee_grade,     tests.examiner_grade,     tt1.short AS original_short,     tt2.short AS outcome_short FROM tests JOIN players ON players.uuid = tests.examiner JOIN mode ON tests.mode_id = mode.mode_id LEFT JOIN tier_table AS tt1 ON tt1.tier_id = tests.orginal_tier_id LEFT JOIN tier_table AS tt2 ON tt2.tier_id = tests.outcome_tier_id WHERE tests.examinee = ? ORDER BY tests.test_date DESC LIMIT ?;",(self.uuid,limit))
        record_list=self.cursor.fetchall()
        records_dict={x[0]:f"{x[0]} / {x[2]} *({(datetime.date.today()-datetime.date.fromisoformat(x[2])).days} 天前)* / {x[1]}\n**{self.name}** `{x[4]}` : `{x[5]}` {x[3]} | {x[6]} → {x[7]}".replace("_","\_") for x in record_list}
        return records_dict
    
    @property
    def test_records_list(self):
        self.cursor.execute("SELECT      tests.test_id ,mode.short AS mode, tests.test_date,     players.player,     tests.examinee_grade,     tests.examiner_grade,     tt1.short AS original_tier,     tt2.short AS outcome_tier FROM tests JOIN players ON players.uuid = tests.examiner JOIN mode ON tests.mode_id = mode.mode_id LEFT JOIN tier_table AS tt1 ON tt1.tier_id = tests.orginal_tier_id LEFT JOIN tier_table AS tt2 ON tt2.tier_id = tests.outcome_tier_id WHERE tests.examinee = ? ORDER BY tests.test_date DESC;",(self.uuid,))
        record_list=self.cursor.fetchall()
        title = [x[0] for x in self.cursor.description]
        record_dict={x[0]:{title[y]:x[y] for y in range(1,len(x))} for x in record_list }
        return record_dict
        
    
    @property
    def head_pic_url(self):
        return f"https://starlightskins.lunareclipse.studio/render/ultimate/{self.uuid}/face?borderHighlight=true&borderHighlightRadius=5&dropShadow=true"
    
    def ban(self,reason:str,expired_date:str,effect_date=datetime.date.today().isoformat(),ban_id=None):
        # raise Exception("指令未完善")
        db_backup()
        try:
            expired_date=datetime.date.fromisoformat(expired_date).isoformat() if expired_date != "0" else "0"
            effect_date=datetime.date.fromisoformat(effect_date).isoformat() if effect_date != "0" else "0"
        except Exception as e:
            raise EntityException("日期格式輸入錯誤","日期應該為'YYYY-MM-DD'格式")

        if not ban_id:
            last_id = query(f"SELECT ban_id FROM ban_list WHERE ban_id LIKE 'B{str(datetime.date.today().year)[2:]}%' ORDER BY ban_id DESC LIMIT 1")
            if last_id:
                sub_id = int(last_id[3:])+1
            else:
                sub_id = 1
            ban_id = "B"+datetime.date.today().strftime("%y")+str(sub_id).zfill(3)
        else:
            ban_id = "B"+ban_id


        try:
            self.cursor.execute("INSERT INTO ban_list (ban_id,banned_player_uuid,reason,effect_date,expired_date) VALUES(?,?,?,?,?)",(ban_id,self.uuid,reason,effect_date,expired_date))
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            raise EntityException("This Ban ID already exists.","請不要輸入重複的Ban ID")
        self.cursor.execute("UPDATE players SET ban_id = ? WHERE uuid = ?",(ban_id,self.uuid))
        self.conn.commit()
        eff = effect_date if effect_date != "0" else "未知"
        exp = expired_date if expired_date != "0" else "永久"
        return ban_id,eff,exp
        
    def unban(self):
        # raise Exception("指令未完善")
        db_backup()
        self.cursor.execute("DELETE FROM ban_list WHERE banned_player_uuid = ? ", (self.uuid,))
        self.cursor.execute("UPDATE players SET ban_id=? WHERE uuid=?",('',self.uuid))
        self.conn.commit()
        return
    
    def check_ban(self):
        banned_uuid = query("SELECT banned_player_uuid FROM ban_list")
        if not banned_uuid:
            return None,None,None,None
        if self.uuid in banned_uuid:
            ban_id,_,ban_reason,ban_effective,ban_expire=query("SELECT * FROM ban_list WHERE banned_player_uuid = ?",(self.uuid,))
            ban_expire_date=datetime.date.fromisoformat(ban_expire)
            if datetime.date.today()>ban_expire_date:
                self.unban()
            else:
                return ban_id,ban_reason,ban_effective,ban_expire
        else:
            return None,None,None,None
        
    def update_tier(self,mode_id,tier_id,is_retired=False):
        if is_retired:
            is_retired=1
        else:
            is_retired=0
        try:
            self.cursor.execute(f"DELETE FROM tier_list WHERE uuid = ? AND mode_id= ?",(self.uuid,mode_id))
            self.cursor.execute(f"INSERT INTO tier_list VALUES('{self.uuid}','{tier_id}','{mode_id}',{is_retired})")
        except Exception as e:
            raise e
        self.conn.commit()
        return 
    
    def get_tier(self,mode_id_or_name:str):
        if mode_id_or_name.isnumeric:
            if mode_id_or_name in query("SELECT mode_id FROM mode"):
                tmp=query("SELECT tier_id,tier FROM tier_list_data WHERE uuid = ? AND mode_id = ?",(self.uuid,mode_id_or_name))
            else:
                tmp=None
        elif mode_id_or_name in query("SELECT short FROM mode"):
            tmp=query("SELECT tier_id,tier FROM tier_list_data WHERE uuid = ? AND mode = ?",(self.uuid,mode_id_or_name))
        else:
            raise ValueError(mode_id_or_name)
        if tmp:
            return tmp
        else:
            return None,None
    
    @staticmethod
    def get_name(uuid):
        try:
            response=requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}",timeout=(5,10))
        except requests.exceptions.Timeout:
            raise EntityException("Request timed out. | 與 Minecraft Services API 請求逾時","請聯繫開發者(lxtw)了解詳情")
        if response.status_code == 200:
            name=response.json()["name"]
            return name
        elif response.status_code == 404:
            raise EntityException("Player is not found. | 找無此玩家","請確認uuid是否完全正確")
        else:
            raise Exception(f"Unexcepted error occurs. | 未預期的錯誤 : {response.status_code}")

    @staticmethod
    def get_uuid(name):
        try:
            response=requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}",timeout=(5,10))
        except requests.exceptions.Timeout:
            raise EntityException("Request timed out. | 與 Minecraft Services API 請求逾時","請聯繫開發者(lxtw)了解詳情")
        if response.status_code == 200:
            uuid=response.json()["id"]
            real_name=response.json()["name"]
            return uuid.strip("-"),real_name
        elif response.status_code == 404:
            with sqlite3.connect(db_path) as conn:
                cursor=conn.cursor()
                cursor.execute("SELECT uuid FROM players WHERE player = ?",(name,))
                queuy=cursor.fetchall()
            if len(queuy) == 1:
                uuid_temp=queuy[0][0]
                return uuid_temp,Player.get_name(uuid_temp)
            elif len(queuy) > 1:
                raise EntityException("Too many players to determined. | 無法確認玩家身分：太多結果","請聯繫開發者(lxtw)")
            else:
                raise EntityException("Player is not found. | 找無此玩家","請確認玩家名稱是否正確並存在")
        else:
            raise Exception(f"Unexcepted error occurs. | 未預期的錯誤 : {response.status_code}")

    @staticmethod
    def get_db_name(uuid):
        with sqlite3.connect(db_path) as conn:
            cursor=conn.cursor()
            cursor.execute("SELECT player FROM players WHERE uuid=?",(uuid,))
            name=cursor.fetchone()
            if name:
                return name[0]
            else:
                return None


    # player = Player("59ce4c88ee4b43bd9c75761a8785483f")
        



        
        
