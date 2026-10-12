import sys
import time
import importlib

def process_team(team_id, team_name, season_id='22023', season_str='2023-24', delay=0.8):
    config = {
        'team_id': team_id,
        'team_name': team_name,
        'season_id_api': season_id,
        'season_str_api': season_str
    }
    print(f"\n==========================================")
    print(f"🚀 開始執行 {team_name.upper()} ({season_str}) 分析管線")
    print(f"==========================================")
    
    p1 = importlib.import_module('1_data_pipeline')
    p2 = importlib.import_module('2_epv_model')
    p4 = importlib.import_module('4_network_analysis')
    
    print("1. 取得 Game IDs...")
    p1.run_find_game_id(config)
    
    print("2. 批次下載賽事 Play-by-Play 與 ShotChart...")
    p1.run_fetch_82_games(config)
    
    print("3. 連續空間離散化 (14區)...")
    p1.run_zone_classifier(config)
    
    print("4. NLP 文本清洗與雙表合併...")
    p1.run_pbp_parser(config)
    
    print("5. 轉移矩陣 (Q Matrix)...")
    p2.run_transition_matrix(config)
    
    print("6. 空間期望值 (Zone EV)...")
    p2.run_ev_calculator(config)
    
    print("7. 馬可夫 EPV 核心解算器...")
    p2.run_markov_epv_engine(config)
    
    print("8. 雙人化學效應分析 (Duo Synergy)...")
    p2.run_synergy_analyzer(config)
    
    print("9. 戰術拓撲網絡分析 (PageRank)...")
    p4.run_network_analysis(config)
    
    print(f"✅ {team_name.upper()} 分析全部完成！\n")

if __name__ == '__main__':
    # 支援命令列指定球隊: python run_pipeline_for_team.py celtics 1610612738
    if len(sys.argv) >= 3:
        t_name = sys.argv[1]
        t_id = int(sys.argv[2])
        process_team(t_id, t_name)
    else:
        # 預設執行塞爾提克 Celtics (2023-24 總冠軍)
        process_team(1610612738, 'celtics')
