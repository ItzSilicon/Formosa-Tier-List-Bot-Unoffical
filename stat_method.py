import pandas as pd
import sqlite3
import seaborn as sb
import matplotlib.pyplot as plt
import io
import statistics
plt.rcParams['font.sans-serif']=['Taipei Sans TC Beta']
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
        point=round(base+mult*(tier_list_sql[i][3]),2)
        n_tier=round(5-base+mult*(tier_list_sql[i][3]-1),2)
        tier_list_sql[i].append(point)
        tier_list_sql[i].append(n_tier)
        if x_axis=="正規化點數":
            data.append(point)
        elif x_axis=="正規化Tier":
            data.append(n_tier)
    
    if data:
        mean=statistics.mean(data)
        median=statistics.median(data)
        mode=statistics.mode(data)
        stdev=statistics.stdev(data)

        
    tier_list=pd.DataFrame(tier_list_sql)
    print(tier_list)
    tier_list.columns=["玩家","模式","MTier","STier","Tier","正規化點數","正規化Tier"]
    plt.figure(figsize=(10, 5),dpi=300,)
    ax=sb.countplot(data=tier_list, x=x_axis, hue='模式', y=None,saturation=1)
    ax.set_ylabel("人數",fontsize=12)
    bf=io.BytesIO()
    plt.savefig(bf)
    plt.close()
    if data:
        stats=[mean,median,mode,stdev]
        for i in range(len(stats)):
            stats[i]=round(stats[i],2) # type: ignore
    else:
        stats=None
    return bf,stats

