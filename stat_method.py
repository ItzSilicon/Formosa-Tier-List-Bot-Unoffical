import pandas as pd
import sqlite3
import seaborn as sb
import matplotlib.pyplot as plt
import io
import statistics
plt.rcParams['font.sans-serif']=['Taipei Sans TC Beta']

tier_point_table={
    "HT1":60,
    "LT1":45,
    "HT2":30,
    "LT2":20,
    "HT3":10,
    "MT3":8,
    "LT3":6,
    "HT4":4,
    "LT4":3,
    "HT5":2,
    "LT5":1
}
def tier_list_count_by_tier(mode_id,x_axis):
    modes={0:"Overall",
    1:"Sword",
    2:"UHC",
    3:"Axe",
    4:"NPot",
    5:"DPot",
    6:"CPVP",
    7:"SMP",
    8:"Cart"}
    conn=sqlite3.connect("tier_list_latest.db")
    cursor=conn.cursor()
    if mode_id:
        sql=f"""
        SELECT player,mode.short,tier_table.tier, tier_table.class_id ,tier_table.short FROM tier_list
        JOIN players ON tier_list.uuid=players.uuid
        JOIN mode ON tier_list.mode_id=mode.mode_id
        JOIN tier_table ON tier_list.tier_id=tier_table.tier_id
        WHERE mode.mode_id = {mode_id}
        ORDER BY tier_list.tier_id
        """
    else:
        sql=f"""
        SELECT player,mode.short,tier_table.tier, tier_table.class_id ,tier_table.short FROM tier_list
        JOIN players ON tier_list.uuid=players.uuid
        JOIN mode ON tier_list.mode_id=mode.mode_id
        JOIN tier_table ON tier_list.tier_id=tier_table.tier_id
        WHERE tier_list.mode_id<8
        ORDER BY tier_list.tier_id
        """
    cursor.execute(sql)
    tier_list_sql=cursor.fetchall()
    conn.close()
    data=[]
    for i in range(len(tier_list_sql)):
        tier_list_sql[i] = list(tier_list_sql[i])
        base=5-tier_list_sql[i][2]
        mult=0.33 if tier_list_sql[i][2]==3 else 0.5
        point=tier_point_table.get(tier_list_sql[i][4])
        n_tier=round(5-base+mult*(tier_list_sql[i][3]-1),2)
        tier_list_sql[i].append(point)
        tier_list_sql[i].append(n_tier)
        if x_axis=="正規化點數":
            data.append(point)
        elif x_axis=="正規化Tier":
            data.append(n_tier)
    
    if data:
        total=len(data)
        player_count=len(set([x[0] for x in tier_list_sql]))
        mean=statistics.mean(data)
        median=statistics.median(data)
        mode=statistics.mode(data)
        stdev=statistics.stdev(data)

        
    tier_list=pd.DataFrame(tier_list_sql)
    tier_list.columns=["玩家","模式","MTier","STier","Tier","正規化點數","正規化Tier"]
    plt.figure(figsize=(16,9),dpi=600)
    if x_axis=="正規化點數" or x_axis=="正規化Tier":
        fig, (ax, ax2) = plt.subplots(2, 1, figsize=(16, 16))
    else:
        ax=None
    ax=sb.countplot(data=tier_list, x=x_axis, hue='模式', y=None,saturation=1,ax=ax)
    ax.set_ylabel("人數",fontsize=12)
    ax.set_title("Tier List 人數統計長條圖 | 以Tier分類 | "+x_axis+" | "+modes[mode_id],fontsize=16)
    if x_axis=="正規化點數" or x_axis=="正規化Tier":
        ax2=sb.boxenplot(data=tier_list, x=x_axis,y='模式', hue='模式',saturation=1,ax=ax2,k_depth='full')
        ax2.set_title("Tier List 人數統計高階箱型圖 | 以Tier分類 | "+x_axis+" | "+modes[mode_id],fontsize=16)
        plt.tight_layout()
    bf=io.BytesIO()
    plt.savefig(bf)
    plt.close()
    if data:
        stats=[total,player_count,mean,median,mode,stdev]
        for i in range(len(stats)):
            if type(stats[i]) is int:
                continue
            stats[i]=round(stats[i],4) # type: ignore
    else:
        stats=None
    return bf,stats

def fetch_overall_rank(player=None):
    conn=sqlite3.connect("tier_list_latest.db")
    cursor=conn.cursor()
    sql=f"""
    SELECT player,mode.short,tier_table.tier, tier_table.class_id ,tier_table.short FROM tier_list
    JOIN players ON tier_list.uuid=players.uuid
    JOIN mode ON tier_list.mode_id=mode.mode_id
    JOIN tier_table ON tier_list.tier_id=tier_table.tier_id
    WHERE tier_list.mode_id<8
    ORDER BY tier_list.tier_id
    """
    cursor.execute(sql)
    tier_list_sql=cursor.fetchall()
    conn.close()
    data={x[0]:0 for x in tier_list_sql}
    for i,j in enumerate(tier_list_sql):
        base=5-j[2]
        mult=0.33 if j[2]==3 else 0.5
        point=round(base+mult*(j[3]),2)
        data[j[0]]+=point
    data_tmp=sorted(data.items(),key=lambda x:x[1],reverse=True)
    data_dict={}
    ptr=1
    for i,j in enumerate(data_tmp):
        if data_tmp[i-1][1]!=j[1]:
            rank=i+1
            ptr=rank
        else:
            rank=ptr
        data_dict[j[0]]=rank
    if player:
        return data_dict.get(player)
    else:
        return data_dict
    
    
def fetch_core_rank(player=None):
    conn=sqlite3.connect("tier_list_latest.db")
    cursor=conn.cursor()
    sql=f"""
    SELECT player,mode.short,tier_table.tier, tier_table.class_id ,tier_table.short FROM tier_list
    JOIN players ON tier_list.uuid=players.uuid
    JOIN mode ON tier_list.mode_id=mode.mode_id
    JOIN tier_table ON tier_list.tier_id=tier_table.tier_id
    WHERE tier_list.mode_id<5 OR tier_list.mode_id=6
    ORDER BY tier_list.tier_id
    """
    cursor.execute(sql)
    tier_list_sql=cursor.fetchall()
    conn.close()
    data={x[0]:0 for x in tier_list_sql}
    for i,j in enumerate(tier_list_sql):
        base=5-j[2]
        mult=0.33 if j[2]==3 else 0.5
        point=tier_point_table.get(j[4])
        if not point:
            continue
        data[j[0]]+=point
    data_tmp=sorted(data.items(),key=lambda x:x[1],reverse=True)
    data_dict={}
    ptr=1
    for i,j in enumerate(data_tmp):
        if data_tmp[i-1][1]!=j[1]:
            rank=i+1
            ptr=rank
        else:
            rank=ptr
        data_dict[j[0]]=rank
    if player:
        return data_dict.get(player)
    else:
        return data_dict

def get_player_amount_in_list():
    conn=sqlite3.connect("tier_list_latest.db")
    cursor=conn.cursor()
    cursor.execute("SELECT uuid FROM tier_list")
    l=[x[0] for x in cursor.fetchall()]
    conn.close()
    return len(set(l))




def overall_point_stat():
    conn=sqlite3.connect("tier_list_latest.db")
    cursor=conn.cursor()
    sql=f"""
        SELECT player,tier_table.short FROM tier_list
        JOIN players ON tier_list.uuid=players.uuid
        JOIN mode ON tier_list.mode_id=mode.mode_id
        JOIN tier_table ON tier_list.tier_id=tier_table.tier_id
        WHERE tier_list.mode_id<8
        ORDER BY tier_list.tier_id
        """
    cursor.execute(sql)
    tier_list_sql=cursor.fetchall()
    conn.close()

    data={x[0]:0 for x in tier_list_sql}
    for i,j in enumerate(tier_list_sql):
        point=tier_point_table.get(j[1])
        if not point:
            continue
        data[j[0]]+=point
    point_data=[(x,data[x]) for x in data]
    data=[x[1] for x in point_data]
    player_count=len(set([x[0] for x in tier_list_sql]))
    mean=statistics.mean(data)
    median=statistics.median(data)
    mode=statistics.mode(data)
    stdev=statistics.stdev(data)

        
    pointdf=pd.DataFrame(point_data)
    pointdf.columns=["玩家","積分"]
    plt.figure(figsize=(32,9),dpi=200)
    ax2=sb.histplot(data=pointdf, x='積分',kde=True)
    ax2.set_title("Tier List 積分統計長條圖",fontsize=16)
    bf=io.BytesIO()
    plt.savefig(bf)
    plt.close()
    if data:
        stats=[player_count,mean,median,mode,stdev]
        for i in range(len(stats)):
            if type(stats[i]) is int:
                continue
            stats[i]=round(stats[i],4) # type: ignore
    else:
        stats=None
    return bf,stats
