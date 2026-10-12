import pandas as pd
import numpy as np
import time
import re
import math
import sqlite3
from nba_api.stats.endpoints import leaguegamefinder, playbyplayv3, shotchartdetail

DB_NAME = "nba_master.db"

# =====================================================================
# [學術解析] run_find_game_id: 比賽識別碼 (Game ID) 獲取模組
# =====================================================================
def run_find_game_id(config):
    team_id = config['team_id']
    team_name = config['team_name']
    season_id_api = config['season_id_api']
    
    print("==========================================================")
    print(f"正在從 NBA 官方伺服器調閱 {season_id_api} 賽季 {team_name} 的所有比賽...")
    print("==========================================================")
    
    try:
        finder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
        all_games = finder.get_data_frames()[0]
        
        regular_season = all_games[all_games['SEASON_ID'] == season_id_api].copy()
        
        if regular_season.empty:
            print("❌ 找不到該賽季的數據，請確認網路連線或稍後再試。")
            return
            
        regular_season['GAME_DATE'] = pd.to_datetime(regular_season['GAME_DATE'])
        df_sorted = regular_season[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'GAME_ID']].sort_values(by='GAME_DATE')
        df_sorted['GAME_DATE'] = df_sorted['GAME_DATE'].dt.strftime('%Y-%m-%d')
        
        # [資料庫存寫] 將資料表存入 SQLite，避免產生大量 CSV
        table_name = f"{team_name}_{season_id_api}_game_ids"
        with sqlite3.connect(DB_NAME) as conn:
            df_sorted.to_sql(table_name, conn, if_exists='replace', index=False)
            
        print(f"\n✅ 成功！已經將 {len(df_sorted)} 場比賽的清單存入資料庫 ({table_name})")
            
    except Exception as e:
        print(f"\n❌ 抓取失敗，錯誤訊息：{e}")

# =====================================================================
# [學術解析] run_fetch_82_games: 巨量賽事資料批次爬蟲模組
# =====================================================================
def run_fetch_82_games(config):
    team_id = config['team_id']
    team_name = config['team_name']
    season_id_api = config['season_id_api']
    season_str_api = config['season_str_api']
    
    print("🚀 啟動自動化抓取引擎...")
    table_name = f"{team_name}_{season_id_api}_game_ids"
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            game_ids_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        game_ids = game_ids_df['GAME_ID'].astype(str).str.zfill(10).tolist()
    except Exception:
        print(f"❌ 找不到資料表 {table_name}，請先執行尋找 Game IDs 步驟！")
        return

    all_pbp_data = []
    all_shot_data = []
    
    for i, game_id in enumerate(game_ids): 
        print(f"[{i+1}/{len(game_ids)}] 正在下載比賽 {game_id} 數據...")
        try:
            pbp = playbyplayv3.PlayByPlayV3(game_id=game_id)
            pbp_df = pbp.get_data_frames()[0]
            all_pbp_data.append(pbp_df)
            
            shot_chart = shotchartdetail.ShotChartDetail(
                team_id=team_id,
                player_id=0, 
                game_id_nullable=game_id,
                season_nullable=season_str_api,
                context_measure_simple='FGA'
            )
            shot_df = shot_chart.get_data_frames()[0]
            all_shot_data.append(shot_df)
            
            time.sleep(0.8) # Rate limiting
        except Exception as e:
            print(f"❌ 抓取比賽 {game_id} 時發生錯誤: {e}")
            time.sleep(3)

    if all_pbp_data and all_shot_data:
        final_pbp_df = pd.concat(all_pbp_data, ignore_index=True)
        final_shot_df = pd.concat(all_shot_data, ignore_index=True)
        
        pbp_table = f"{team_name}_{season_id_api}_pbp"
        shots_table = f"{team_name}_{season_id_api}_shots"
        
        with sqlite3.connect(DB_NAME) as conn:
            final_pbp_df.to_sql(pbp_table, conn, if_exists='replace', index=False)
            final_shot_df.to_sql(shots_table, conn, if_exists='replace', index=False)
            
        print(f"🎉 巨量資料合併完成！已儲存至資料庫的 {pbp_table} 與 {shots_table} 資料表。")

# =====================================================================
# [學術解析] run_zone_classifier: 連續空間特徵離散化模組
# =====================================================================
def run_zone_classifier(config):
    team_name = config['team_name']
    season_id_api = config['season_id_api']
    
    def get_nba_standard_zone(x, y):
        r = math.sqrt(x**2 + y**2)
        angle = math.degrees(math.atan2(y, x))
        if angle < 0: angle += 360
    
        if y >= 430: return "01. Backcourt (後場超遠)"
        if r <= 40: return "02. Restricted Area (合理衝撞區)"        
        if y <= 150 and abs(x) <= 80: return "03. In The Paint (非衝撞區禁區)"
        if y <= 140:
            if x >= 220: return "04. Right Corner 3 (右底角三分)"
            elif x <= -220: return "05. Left Corner 3 (左底角三分)"
        if r >= 237.5:
            if 45 <= angle < 75: return "06. ATB 3 - Right Wing (右側翼三分)"
            elif 75 <= angle < 105: return "07. ATB 3 - Top of Key (正面弧頂三分)"
            elif 105 <= angle < 135: return "08. ATB 3 - Left Wing (左側翼三分)"
            else: return "09. ATB 3 - Deep (超大號外線)"
            
        if 0 <= angle < 30 or 270 <= angle <= 360: return "10. Mid - Right Baseline (右底線中距)"
        elif 30 <= angle < 75: return "11. Mid - Right Wing (右側中距)"
        elif 75 <= angle < 105: return "12. Mid - Center (正面中距)"
        elif 105 <= angle < 150: return "13. Mid - Left Wing (左側中距)"
        else: return "14. Mid - Left Baseline (左底線中距)"
    
    input_table = f"{team_name}_{season_id_api}_shots"
    output_table = f"{team_name}_{season_id_api}_shots_with_zones"
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql(f"SELECT * FROM {input_table}", conn)
            df['SHOT_ZONE'] = df.apply(lambda row: get_nba_standard_zone(row['LOC_X'], row['LOC_Y']), axis=1)
            df.to_sql(output_table, conn, if_exists='replace', index=False)
            
        print(f"✨ 離散狀態特徵集已成功建立並存入資料庫表 {output_table}")
    except Exception:
        print(f"❌ 找不到資料表 {input_table}")

# =====================================================================
# [學術解析] run_pbp_parser: 自然語言處理與關聯式資料庫聯集模組
# =====================================================================
def run_pbp_parser(config):
    team_name = config['team_name']
    season_id_api = config['season_id_api']
    
    pbp_table = f"{team_name}_{season_id_api}_pbp"
    shots_table = f"{team_name}_{season_id_api}_shots_with_zones"
    out_table = f"{team_name}_{season_id_api}_tactics_merged"
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            pbp_df = pd.read_sql(f"SELECT * FROM {pbp_table}", conn)
            shots_df = pd.read_sql(f"SELECT * FROM {shots_table}", conn)
    except Exception:
        print(f"❌ 找不到必要資料表。")
        return
    
    def extract_passer(desc):
        desc = str(desc)
        if 'AST' in desc:
            match = re.search(r'\(\s*([^()]+?)\s+\d+\s+AST\s*\)', desc)
            if match:
                return match.group(1).strip()
        return None
    
    pbp_df['Raw_Passer'] = pbp_df['description'].apply(extract_passer)
    
    import unicodedata
    def strip_accents(text):
        if not text: return ""
        return ''.join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c))

    official_names = shots_df['PLAYER_NAME'].dropna().unique()
    def standardize_name(short_name):
        if not short_name: return None
        clean_short = strip_accents(short_name).strip().lower()
        for full_name in official_names:
            clean_full = strip_accents(full_name).strip().lower()
            if clean_short == clean_full:
                return full_name
        for full_name in official_names:
            clean_full = strip_accents(full_name).strip().lower()
            last_name = clean_full.split()[-1] if clean_full else ""
            if clean_short == last_name or clean_short in clean_full:
                return full_name
        return short_name 
    
    pbp_df['Passer'] = pbp_df['Raw_Passer'].apply(standardize_name)
    
    assists_df = pbp_df[pbp_df['Passer'].notnull()].copy()
    assists_df['gameId'] = assists_df['gameId'].astype(int)
    assists_df['actionNumber'] = assists_df['actionNumber'].astype(int)
    shots_df['GAME_ID'] = shots_df['GAME_ID'].astype(int)
    shots_df['GAME_EVENT_ID'] = shots_df['GAME_EVENT_ID'].astype(int)
    
    merged_df = pd.merge(
        left=assists_df, right=shots_df, 
        left_on=['gameId', 'actionNumber'], right_on=['GAME_ID', 'GAME_EVENT_ID'], how='inner'
    )
    
    final_tactics = merged_df[['Passer', 'PLAYER_NAME', 'SHOT_ZONE', 'SHOT_MADE_FLAG']].copy()
    final_tactics.columns = ['傳球者 (Passer)', '終結者 (Shooter)', '14區出手點 (Shot Zone)', '是否進球 (Made)']
    
    with sqlite3.connect(DB_NAME) as conn:
        final_tactics.to_sql(out_table, conn, if_exists='replace', index=False)
        
    print(f"✅ NLP 萃取與雙表合併完成，戰術連線矩陣已生成至表 {out_table}。")

if __name__ == '__main__':
    print("請使用 0_main_launcher.py 來執行此程式！")
