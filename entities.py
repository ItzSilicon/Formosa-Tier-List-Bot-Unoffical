import sqlite3
import requests
import os
import datetime
from stat_method import fetch_core_rank,fetch_overall_rank
from discord.app_commands import AppCommandError
from typing import Union, List, Any,Optional
import re
from functools import cached_property
from pathlib import Path
import shutil
import logging
from pandas import DataFrame
db_path="./tier_list_latest.db"



class EntityException(AppCommandError):
    def __init__(self,message,solution=None):
        super().__init__(message)
        self.message= message
        self.solution = solution
        
        
def new_conn(db_path=db_path):
    conn = sqlite3.connect(db_path, timeout=10)
    # 讓回傳結果可以透過欄位名稱存取 (解決索引問題)
    conn.row_factory = sqlite3.Row 
    return conn


def query(script: str, param: Union[tuple, dict] = None, do_format: bool = True, do_commit: bool = False):
    r = None
    retry_count = 3
    delay = 0.5

    for attempt in range(retry_count):
        try:
            # 使用 context manager 自動處理 commit/rollback
            with new_conn() as conn:
                cursor = conn.cursor()
                
                if param:
                    cursor.execute(script, param)
                else:
                    cursor.execute(script)
                
                # 如果是寫入操作且需要 commit
                if do_commit:
                    conn.commit()
                    return None
                
                # 獲取結果
                rows = cursor.fetchall()
                # 將 sqlite3.Row 轉回 tuple 以保持與原邏輯相容 (最小衝擊)
                r = [tuple(row) for row in rows]
            break # 成功則跳出重試迴圈


        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < retry_count - 1:
                time.sleep(delay * (attempt + 1)) # 指數退避
                continue
            raise e # 其他錯誤或重試耗盡則拋出
        except Exception as e:
            raise e
        finally:
            conn.close()

    # --- 以下保持你原有的回傳格式化邏輯 (Do format) ---
    if not r:
        return None

    if len(r) > 1:
        if do_format:
            # 檢查是否所有 row 都只有一個元素
            if all(len(row) == 1 for row in r):
                return [x[0] for x in r]
        return r
    else:
        if do_format:
            return r[0][0] if len(r[0]) == 1 else r[0]
        return r

def query_to_dataframe(script: str, param: Union[tuple, dict] = None, do_format: bool = True, do_commit: bool = False) -> Optional[DataFrame | dict]:
    r = None
    retry_count = 3
    delay = 0.5

    for attempt in range(retry_count):
        try:
            # 使用 context manager 自動處理 commit/rollback
            with new_conn() as conn:
                cursor = conn.cursor()
                
                if param:
                    cursor.execute(script, param)
                else:
                    cursor.execute(script)
                
                # 如果是寫入操作且需要 commit
                if do_commit:
                    conn.commit()
                    return None
                
                # 獲取結果
                rows = cursor.fetchall()
                # 將 sqlite3.Row 轉回 tuple 以保持與原邏輯相容 (最小衝擊)
                if rows:
                    # print(f"rows: {rows}")
                    col=[col[0] for col in cursor.description]
                    r = DataFrame(rows, columns=col)
                    # print(f"r: {r}")
                else:
                    return None
            break # 成功則跳出重試迴圈


        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < retry_count - 1:
                time.sleep(delay * (attempt + 1)) # 指數退避
                continue
            raise e # 其他錯誤或重試耗盡則拋出
        except Exception as e:
            raise e
        finally:
            conn.close()
    
    # print(r)
    # --- 以下保持你原有的回傳格式化邏輯 (Do format) ---
    if r.empty:
        return None

    if len(r.columns) >1:
        if do_format:
            # 檢查是否所有 row 都只有一個元素
            if len(r) == 1:
                return {x:r[x][0] for x in r.columns}
        return r
    else:
        if do_format:
            return r[r.columns[0]][0] if len(r)==1 else r[r.columns[0]]
        return r


def get_modes_dict() -> dict:
    with sqlite3.connect(db_path) as conn:
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM mode")
        modes_list=cursor.fetchall()
        modes={x[0]:x[2] for x in modes_list}
    return modes
        


def db_backup():
    try:
        source = Path('tier_list_latest.db')
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = Path('./database_backup')
        backup_folder.mkdir(parents=True,exist_ok=True)
        backups_list = list(backup_folder.iterdir())
        backup_queue_size=100
        if len(backups_list)>backup_queue_size:
            logging.info("Backup Queue is full, delete excessive files")
            backups_list.sort()
            for file in backups_list[:backup_queue_size]:
                logging.info(f"Delete {file.name}")
                file.unlink(missing_ok=True)
        else:
            logging.info(f"Backup Queue is not full, {len(backups_list)}/{backup_queue_size}")
        if source.exists():
            backup_path = backup_folder / f"tier_list_{now_str}.db"
            copies = Path(shutil.copy2(source,backup_path))
            if copies.exists():
                logging.info(f"{copies.name} have been backed up!")
            else:
                logging.warning("backup file is missing!")
        else:
            logging.critical("source file is missing!")
    except:
        raise e
            
            

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
    # TODO [SECURITY]: 在執行 INSERT/UPDATE 前，增加資料格式驗證 (Validation) 確保資料庫安全
    # TODO [REFRACTOR]: 將所有的 SQL 語句提取為類別常量或獨立的 .sql 檔案
    # TODO: 檢構化初始化邏輯：將「從 API 獲取資料」與「更新數據庫」拆分為獨立私有方法
    # TODO: 優化 _unknown 玩家的處理邏輯，目前的實作可能會在 name 為 None 時噴錯
    # TODO: 考慮使用緩存 (Cache) 機制，避免短時間內重複實例化同一個玩家時頻繁請求 API
    def __init__(self,input:str):
        try:
            self._conn=new_conn()
            self._cursor=self._conn.cursor()
            self.extra_info=[]
            self.is_famous=False
            self.is_banned=False
            self.name=None
            self.uuid=None
            ### 輸入確認 ###
            
            if len(input)==32:
                self.uuid=input
                self.name=self.get_name(self.uuid)
            elif input.startswith("#unknown") :
                self.uuid=input
                self.name=self.db_name or "Unknown Player"
            elif len(input)<=16:
                if not re.match(r"^\w{1,16}$", input):
                    raise EntityException("錯誤的玩家名稱格式","請確認輸入欄位是否為正確的玩家名稱")
                self.uuid,self.name=Player.get_uuid(input)
            else:
                raise EntityException("錯誤的參數，必須為uuid或玩家名稱","請輸入正確格式的玩家名稱或uuid")
            
            if self.uuid.startswith("#unknown"):
                self.extra_info.append("該玩家的資料已經不可考")

            
            ###更新資料###
            
            current_db_name = self.get_db_name(self.uuid)
            with self._conn:
                if current_db_name is None:
                    db_backup()
                    self._cursor.execute("INSERT INTO players(player,uuid,ban_id,is_famous,nickname,intro,examiner_id) VALUES(?,?,NULL,0,NULL,NULL,NULL)",(self.name,self.uuid))
                    self.extra_info.append("New player | 新計入資料庫的玩家")
                elif current_db_name != self.name:
                    self.extra_info.append(f"Name changed | 玩家名稱變動：{current_db_name} → {self.name}")
                    db_backup()
                    self._cursor.execute("UPDATE players SET player=? WHERE uuid=?",(self.name,self.uuid))
                
            self.ban_id,self.ban_reason,self.ban_effective,self.ban_expired=self.check_ban()
            self.is_banned = self.ban_id is not None
            
            res=self._cursor.execute("SELECT intro,is_famous,nickname,examiner_id FROM players WHERE uuid=?",(self.uuid,)).fetchone()
            
            if res:
                self.intro, is_famous, self.nickname, self.examiner_id = res
                self.is_famous = bool(is_famous)
                self.is_examiner = bool(self.examiner_id)
                
            if self.is_banned:
                eff = self.ban_effective if self.ban_effective != "0" else "未知"
                exp = self.ban_expired if self.ban_expired != "0" else "永久"
                self.extra_info.append(f"該玩家已經被列入封鎖，ID:`{self.ban_id}`，原因:{self.ban_reason}，生效於`{eff}`持續至`{exp}`")
                
            for i in range(len(self.extra_info)):
                self.extra_info[i]="ⓘ "+self.extra_info[i]
            
            # self.discord_user_id = query("SELECT discord_user_id FROM discord_minecraft WHERE minecraft_uuid = ?",(self.uuid,))

                
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
            
        except EntityException as e:
            logging.error(f"Expected Exception: {e.message}")
            raise EntityException("Minecraft Player 初始化發生錯誤",f"**{e.message}**"+"\n"+e.solution)
        except Exception as e:
            raise EntityException(f"發生未知錯誤:\n{e}")
        finally:
            self._conn.close()
        
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
        
    @cached_property
    def tier_dict(self):
        # TODO: 將複雜的 SQL 語句提取到外部定義，或使用 SQLAlchemy 等 ORM 工具簡化
        # TODO: 處理 fetch_overall_rank 失敗時的預設值，避免整個 Property 崩潰
        data=query("""
        SELECT mode.short AS MODE ,tier_table.short as TIER, tier_list.is_retired , tier_table.points , mode.range FROM tier_list
        JOIN mode ON tier_list.mode_id=mode.mode_id
        JOIN tier_table ON tier_list.tier_id = tier_table.tier_id
        JOIN players ON tier_list.uuid = players.uuid
        WHERE players.uuid= ? ORDER BY tier_list.mode_id""",(self.uuid,),do_format=False) or []
        k=lambda x: "R" if x else ""
        return {"tiers":{x[0]:f'{k(x[2])}{x[1]}' for x in data if x[4]},
                "other_tiers":{x[0]:f'{k(x[2])}{x[1]}' for x in data if not x[4]},
                "overall_points":sum([y[3] for y in data if y[4]]),
                "core_points":sum([z[3] for z in data if z[4] == "core"]),
                "overall_rank":fetch_overall_rank(self.name),
                "core_rank":fetch_core_rank(self.name)}
    @cached_property
    def test_records(self,limit=5):
        # TODO: 支援分頁功能：當玩家想查看全部紀錄時，能透過 offset 參數讀取
        record_list=query("SELECT      tests.test_id ,mode.short, tests.test_date,     players.player,     tests.examinee_grade,     tests.examiner_grade,     tt1.short AS original_short,     tt2.short AS outcome_short FROM tests JOIN players ON players.uuid = tests.examiner JOIN mode ON tests.mode_id = mode.mode_id LEFT JOIN tier_table AS tt1 ON tt1.tier_id = tests.orginal_tier_id LEFT JOIN tier_table AS tt2 ON tt2.tier_id = tests.outcome_tier_id WHERE tests.examinee = ? ORDER BY tests.test_date DESC LIMIT ?;",(self.uuid,limit),do_format=False)
        if record_list:
            records_dict={x[0]:f"{x[0]} / {x[2]} *({(datetime.date.today()-datetime.date.fromisoformat(x[2])).days} 天前)* / {x[1]}\n**{self.name}** `{x[4]}` : `{x[5]}` {x[3]} | {x[6]} → {x[7]}".replace("_","\_") for x in record_list}
            return records_dict
        else:
            return None
    
    @cached_property
    def test_records_list(self):
        self._cursor.execute("SELECT      tests.test_id ,mode.short AS mode, tests.test_date,     players.player,     tests.examinee_grade,     tests.examiner_grade,     tt1.short AS original_tier,     tt2.short AS outcome_tier FROM tests JOIN players ON players.uuid = tests.examiner JOIN mode ON tests.mode_id = mode.mode_id LEFT JOIN tier_table AS tt1 ON tt1.tier_id = tests.orginal_tier_id LEFT JOIN tier_table AS tt2 ON tt2.tier_id = tests.outcome_tier_id WHERE tests.examinee = ? ORDER BY tests.test_date DESC;",(self.uuid,))
        record_list=self._cursor.fetchall()
        title = [x[0] for x in self._cursor.description]
        record_dict={x[0]:{title[y]:x[y] for y in range(1,len(x))} for x in record_list }
        return record_dict
    
    @cached_property
    def discord_user_id(self):
        """從 __init__ 抽出來，只有用到時才查"""
        return query("SELECT discord_user_id FROM discord_minecraft WHERE minecraft_uuid = ?", (self.uuid,))
        
    
    @property
    def head_pic_url(self):
        # TODO: 考慮增加預設頭像 URL，當 API 服務 (lunareclipse) 斷線時可以備援
        return f"https://starlightskins.lunareclipse.studio/render/ultimate/{self.uuid}/face?borderHighlight=true&borderHighlightRadius=5&dropShadow=true"
    
    def ban(self,reason:str,expired_date:str,effect_date=datetime.date.today().isoformat(),ban_id=None):
        # TODO: 實作自動解除封鎖的監聽器，或在機器人啟動時跑一次清理任務
        # TODO: 驗證 expired_date 必須大於 effect_date
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
            self._cursor.execute("INSERT INTO ban_list (ban_id,banned_player_uuid,reason,effect_date,expired_date) VALUES(?,?,?,?,?)",(ban_id,self.uuid,reason,effect_date,expired_date))
            self._conn.commit()
        except sqlite3.IntegrityError as e:
            raise EntityException("This Ban ID already exists.","請不要輸入重複的Ban ID")
        self._cursor.execute("UPDATE players SET ban_id = ? WHERE uuid = ?",(ban_id,self.uuid))
        self._conn.commit()
        eff = effect_date if effect_date != "0" else "未知"
        exp = expired_date if expired_date != "0" else "永久"
        return ban_id,eff,exp
        
    def unban(self):
        db_backup()
        self._cursor.execute("DELETE FROM ban_list WHERE banned_player_uuid = ? ", (self.uuid,))
        self._cursor.execute("UPDATE players SET ban_id=? WHERE uuid=?",('',self.uuid))
        self._conn.commit()
        return
    
    def check_ban(self):
        # TODO: 效能優化：目前每次檢查都會 query 全部的 banned_uuid，改為直接查詢該玩家的 uuid 即可
        banned = query("SELECT * FROM ban_list WHERE banned_player_uuid = ?",(self.uuid,))
        if banned:
            ban_id,_,ban_reason,ban_effective,ban_expire=banned
            if ban_expire != "0":
                ban_expire_date=datetime.date.fromisoformat(ban_expire)
                if datetime.date.today()>ban_expire_date:
                    self.unban()
                    return None,None,None,None
            return ban_id,ban_reason,ban_effective,ban_expire
        else:
            return None,None,None,None
        
    def update_tier(self,mode:Union[int,str],tier:Union[int,str],is_retired=False):
        # TODO: 實作「歷史紀錄表 (tier_history)」：每次變更時自動備份舊數據，以便追蹤進度曲線
        # TODO: 變更成功後發送一個信號 (Signal)，讓 bot.py 可以捕捉並自動更新 Discord 身分組
        if type(mode) == str:
            mode_id:int=query(f"SELECT mode_id FROM mode WHERE short = ?",(mode,))
        else:
            mode_id=mode
        if type(tier) == str:
            tier_id:int=query(f"SELECT tier_id FROM tier_table WHERE short = ?",(tier,))
        else:
            tier_id=tier
        if is_retired:
            is_retired=1
        else:
            is_retired=0
        try:
            query(f"DELETE FROM tier_list WHERE uuid = ? AND mode_id= ?",(self.uuid,mode_id))
            query(f"INSERT INTO tier_list VALUES('{self.uuid}','{tier_id}','{mode_id}',{is_retired})")
            if "tier_dict" in self.__dict__:
                del self.tier_dict
                
            self._refresh_info_dict()
        except Exception as e:
            raise e
        return 
    
    
    def _refresh_info_dict(self):
        """重新封裝資訊字典"""
        self.info_dict = {
            "uuid": self.uuid,
            "name": self.name,
            "is_banned": self.is_banned,
            "extra_info": self.extra_info,
            "tier_data": self.tier_dict # 這裡會觸發新的 tier_dict 查詢並存入快取
        }
    
    
    def get_tier(self,mode_id_or_name:str,return_short=True):
        if mode_id_or_name in query("SELECT mode_id FROM mode"):
            tmp=query("SELECT tier_id,tier FROM tier_list_data WHERE uuid = ? AND mode_id = ?",(self.uuid,mode_id_or_name))
        elif mode_id_or_name in query("SELECT short FROM mode"):
            tmp=query("SELECT tier_id,tier FROM tier_list_data WHERE uuid = ? AND mode = ?",(self.uuid,mode_id_or_name))
        else:
            raise ValueError(mode_id_or_name)
        if tmp:
            if return_short:
                return tmp[1]
            else:
                return tmp[0]
        else:
            return None
    
    @staticmethod
    def get_name(uuid):
        # TODO: 增加 User-Agent 標頭，避免被 Minecraft API 判定為惡意爬蟲
        # TODO: 實作重試機制 (Retry Strategy)，處理偶發性的網路波動
        try:
            response=requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}",timeout=(5,10))
        except requests.exceptions.Timeout:
            raise EntityException("與 Minecraft Services API 請求逾時","請聯繫開發者(lxtw)了解詳情")
        if response.status_code == 200:
            name=response.json()["name"]
            return name
        elif response.status_code == 404:
            raise EntityException("找無此玩家","請確認uuid是否完全正確")
        else:
            raise Exception(f" 未預期的錯誤 : {response.status_code}")

    @staticmethod
    def get_uuid(name):
        # TODO: 針對已經在資料庫中的玩家，優先查詢本地資料庫以節省 API 配額
        # 應實作 Try-Except 並加入短暫的 time.sleep() 重試機制，避免機器人因頻繁查詢而暫時癱瘓。
        try:
            response=requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}",timeout=(5,10))
        except requests.exceptions.Timeout:
            raise EntityException("與 Minecraft Services API 請求逾時","請聯繫開發者(lxtw)了解詳情")
        if response.status_code == 200:
            uuid=response.json()["id"]
            real_name=response.json()["name"]
            logging.info(f"Find Minecraft Account : {real_name} ({uuid})")
            return uuid.strip("-"),real_name
        elif response.status_code == 404:
            logging.info("Player not found via Minecraft Services API")
            with sqlite3.connect(db_path) as conn:
                cursor=conn.cursor()
                cursor.execute("SELECT uuid FROM players WHERE player = ?",(name,))
                queuy=cursor.fetchall()
            if len(queuy) == 1:
                uuid_temp=queuy[0][0]
                logging.info("Player found via local database")
                real_name = Player.get_name(uuid_temp)
                if real_name:
                    logging.info(f"Find Minecraft Account : {real_name} ({uuid_temp})")
                    return uuid_temp,real_name
                else:
                    logging.warning(f"Player {name} is not available")
                    raise EntityException("找無此玩家","請確認玩家名稱是否正確並存在")
            elif len(queuy) > 1:
                logging.info("Too many results")
                raise EntityException("無法確認玩家身分：太多結果","請聯繫開發者(lxtw)")
            else:
                logging.warning(f"Player {name} is invalid (Not exist)")
                raise EntityException("找無此玩家","請確認玩家名稱是否正確並存在")
        elif response.status_code == 429:
            raise EntityException("太多次請求","請稍後再試")
        else:
            raise EntityException(f"未預期的錯誤 : {response.status_code}")

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
