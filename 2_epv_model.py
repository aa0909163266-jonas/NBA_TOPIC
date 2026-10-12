import pandas as pd
import numpy as np
import sqlite3

DB_NAME = "nba_master.db"

def run_transition_matrix(config):
    team_name = config['team_name']
    season_id = config['season_id_api']
    input_table = f"{team_name}_{season_id}_tactics_merged"
    output_table = f"{team_name}_{season_id}_q_matrix"
    
    print("啟動線性代數引擎：建構傳球機率轉移矩陣...")
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql(f"SELECT * FROM {input_table}", conn)
    except Exception:
        print(f"找不到資料表 {input_table}")
        return

    transition_counts = pd.crosstab(df['傳球者 (Passer)'], df['14區出手點 (Shot Zone)'])
    probability_matrix = transition_counts.div(transition_counts.sum(axis=1), axis=0)
    
    reliable_cooperators = transition_counts[transition_counts.sum(axis=1) > 50].index
    final_q_matrix = probability_matrix.loc[reliable_cooperators]
    
    # 為了方便儲存矩陣，重置索引
    q_matrix_flat = final_q_matrix.reset_index()
    with sqlite3.connect(DB_NAME) as conn:
        q_matrix_flat.to_sql(output_table, conn, if_exists='replace', index=False)
        
    print(f"✅ 轉移機率矩陣已建立並儲存為表 {output_table}。")

def run_ev_calculator(config):
    team_name = config['team_name']
    season_id = config['season_id_api']
    input_table = f"{team_name}_{season_id}_shots_with_zones"
    output_table = f"{team_name}_{season_id}_zone_ev"
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql(f"SELECT * FROM {input_table}", conn)
    except Exception:
        print(f"找不到資料表 {input_table}")
        return
        
    zone_stats = df.groupby('SHOT_ZONE').agg(
        Total_Shots=('SHOT_MADE_FLAG', 'count'),
        Made_Shots=('SHOT_MADE_FLAG', 'sum')
    )
    
    zone_stats['Points_Value'] = np.where(zone_stats.index.str.contains('3'), 3, 2)
    zone_stats['FG%'] = zone_stats['Made_Shots'] / zone_stats['Total_Shots']
    zone_stats['EV (期望得分)'] = zone_stats['FG%'] * zone_stats['Points_Value']
    
    zone_stats = zone_stats.round(3).sort_values(by='EV (期望得分)', ascending=False)
    
    with sqlite3.connect(DB_NAME) as conn:
        zone_stats.reset_index().to_sql(output_table, conn, if_exists='replace', index=False)
        
    print(f"✨ 完美 R 矩陣基礎 (EV) 已儲存為表 {output_table}。")


def run_markov_epv_engine(config):
    team_name = config['team_name']
    season_id = config['season_id_api']
    tactics_table = f"{team_name}_{season_id}_tactics_merged"
    ev_table = f"{team_name}_{season_id}_zone_ev"
    output_table = f"{team_name}_{season_id}_final_epv"
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql(f"SELECT * FROM {tactics_table}", conn)
            zone_ev = pd.read_sql(f"SELECT * FROM {ev_table}", conn)
    except Exception:
        print(f"找不到所需資料表。")
        return
        
    zone_ev_dict = dict(zip(zone_ev['SHOT_ZONE'], zone_ev['EV (期望得分)']))
    
    Q_counts = pd.crosstab(df['傳球者 (Passer)'], df['終結者 (Shooter)'])
    players = list(set(Q_counts.index).union(set(Q_counts.columns)))
    Q_counts = Q_counts.reindex(index=players, columns=players, fill_value=0)
    
    Q_prob = Q_counts.div(Q_counts.sum(axis=1), axis=0).fillna(0)
    pass_probability = 0.7 
    Q_matrix = Q_prob.values * pass_probability
    
    df['Shot_EV'] = df['14區出手點 (Shot Zone)'].map(zone_ev_dict)
    player_R = df.groupby('終結者 (Shooter)')['Shot_EV'].mean().reindex(players).fillna(0)
    R_vector = player_R.values * (1 - pass_probability) 
    
    I = np.eye(len(players))
    N_matrix = np.linalg.inv(I - Q_matrix)
    EPV_vector = np.dot(N_matrix, R_vector)
    
    epv_df = pd.DataFrame({'球員 (Player)': players, '戰術樞紐期望值 (EPV)': EPV_vector})
    valid_players = Q_counts[Q_counts.sum(axis=1) > 50].index
    epv_df = epv_df[epv_df['球員 (Player)'].isin(valid_players)].sort_values(by='戰術樞紐期望值 (EPV)', ascending=False)
    
    # 除了存入資料庫，最終排行榜還是產生一份 CSV，方便直接用 Excel 查看
    csv_output = f"{team_name}_{season_id}_final_epv.csv"
    with sqlite3.connect(DB_NAME) as conn:
        epv_df.to_sql(output_table, conn, if_exists='replace', index=False)
    epv_df.to_csv(csv_output, index=False)
    
    print(f"🏆 馬可夫 EPV 最終排行榜已生成至表 {output_table} (同步匯出實體檔案 {csv_output})。")


def run_synergy_analyzer(config):
    team_name = config['team_name']
    season_id = config['season_id_api']
    tactics_table = f"{team_name}_{season_id}_tactics_merged"
    ev_table = f"{team_name}_{season_id}_zone_ev"
    epv_table = f"{team_name}_{season_id}_final_epv"
    output_table = f"{team_name}_{season_id}_duo_synergy"
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql(f"SELECT * FROM {tactics_table}", conn)
            zone_ev = pd.read_sql(f"SELECT * FROM {ev_table}", conn)
    except Exception:
        print(f"找不到所需資料表。")
        return
        
    zone_ev_dict = dict(zip(zone_ev['SHOT_ZONE'], zone_ev['EV (期望得分)']))
    df['Shot_EV'] = df['14區出手點 (Shot Zone)'].map(zone_ev_dict)
    
    synergy_df = df.groupby(['傳球者 (Passer)', '終結者 (Shooter)']).agg(
        連線次數=('Shot_EV', 'count'),
        總創造期望值=('Shot_EV', 'sum')
    ).reset_index()
    
    synergy_df = synergy_df[synergy_df['傳球者 (Passer)'] != synergy_df['終結者 (Shooter)']]
    synergy_df = synergy_df[synergy_df['連線次數'] >= 15].sort_values(by='總創造期望值', ascending=False)
    
    csv_output = f"{team_name}_{season_id}_duo_synergy.csv"
    with sqlite3.connect(DB_NAME) as conn:
        synergy_df.to_sql(output_table, conn, if_exists='replace', index=False)
    synergy_df.to_csv(csv_output, index=False)
    
    print(f"\n✨ 黃金雙人組連線排行已產出至表 {output_table} (同步匯出實體檔案 {csv_output})。")

if __name__ == '__main__':
    print("請使用 0_main_launcher.py 來執行此程式！")
