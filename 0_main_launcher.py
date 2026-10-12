import sys
import importlib
try:
    import questionary
except ImportError:
    print("請先在終端機執行: pip install questionary")
    sys.exit(1)
from nba_api.stats.static import teams

sys.path.append('.')

def main():
    print("\n" + "="*60)
    print(" 🏀 歡迎來到 NBA 馬可夫鏈預期球權價值 (EPV) 與圖論分析系統 🏀 ")
    print("="*60 + "\n")
    
    # 動態載入我們寫好的三大模組
    try:
        pipeline = importlib.import_module('1_data_pipeline')
        epv_model = importlib.import_module('2_epv_model')
        network = importlib.import_module('4_network_analysis')
    except ImportError as e:
        print(f"載入模組失敗: {e}")
        return

    # 1. 抓取所有球隊清單，製作互動式選單
    print("正在載入 NBA 球隊資料庫...")
    nba_teams = teams.get_teams()
    
    # 按照字母排序讓使用者比較好找
    nba_teams = sorted(nba_teams, key=lambda x: x['full_name'])
    team_choices = [f"{t['full_name']} ({t['abbreviation']})" for t in nba_teams]
    
    # 使用 Questionary 產生滾輪選單
    selected_team_str = questionary.select(
        "請選擇你想分析的球隊 (可使用鍵盤上下鍵與 Enter 選擇):",
        choices=team_choices,
        use_indicator=True
    ).ask()
    
    if not selected_team_str:
        print("取消操作。")
        return
        
    abbr = selected_team_str.split('(')[-1].replace(')', '')
    team_info = [t for t in nba_teams if t['abbreviation'] == abbr][0]
    team_id = team_info['id']
    team_name = team_info['nickname'].lower().replace(" ", "_")
    
    # 2. 選擇賽季
    season_choices = [
        "2023-24 賽季",
        "2022-23 賽季",
        "2021-22 賽季",
        "2020-21 賽季",
        "2019-20 賽季",
        "2018-19 賽季"
    ]
    selected_season_str = questionary.select(
        "請選擇你想分析的賽季:",
        choices=season_choices,
        use_indicator=True
    ).ask()
    
    if not selected_season_str:
        print("取消操作。")
        return
        
    season_str_api = selected_season_str.split(' ')[0]
    start_year = season_str_api.split('-')[0]
    season_id_api = f"2{start_year}"
    
    print(f"\n🚀 系統設定完成！ 目標球隊: {team_info['full_name']} | 賽季: {season_str_api}")
    print("==========================================================")
    
    config = {
        'team_id': team_id,
        'team_name': team_name,
        'season_id_api': season_id_api,
        'season_str_api': season_str_api
    }
    
    # 3. 勾選要執行的步驟
    actions = questionary.checkbox(
        "請選擇你要執行的分析步驟 (可按空白鍵取消/勾選，Enter確認):",
        choices=[
            questionary.Choice("1. [爬蟲] 尋找 Game IDs", checked=True),
            questionary.Choice("2. [爬蟲] 下載整季 82 場比賽數據 (需時數分鐘)", checked=True),
            questionary.Choice("3. [清理] 幾何空間特徵離散化 (14區)", checked=True),
            questionary.Choice("4. [清理] PBP 文本 NLP 解析與雙表合併", checked=True),
            questionary.Choice("5. [建模] 建構馬可夫轉移矩陣 (Q-Matrix)", checked=True),
            questionary.Choice("6. [建模] 空間期望值 (EV) 引擎", checked=True),
            questionary.Choice("7. [運算] 馬可夫 EPV 核心解算器", checked=True),
            questionary.Choice("8. [分析] 雙人化學效應分析與最佳五人", checked=True),
            questionary.Choice("9. [圖論] 戰術網路拓撲圖與 PageRank 中心性", checked=True)
        ]
    ).ask()

    if not actions:
        print("未選擇任何步驟，程式結束。")
        return

    # 開始依照勾選執行對應的模組
    if any("1. [爬蟲]" in a for a in actions):
        pipeline.run_find_game_id(config)
    if any("2. [爬蟲]" in a for a in actions):
        pipeline.run_fetch_82_games(config)
    if any("3. [清理]" in a for a in actions):
        pipeline.run_zone_classifier(config)
    if any("4. [清理]" in a for a in actions):
        pipeline.run_pbp_parser(config)
        
    if any("5. [建模]" in a for a in actions):
        epv_model.run_transition_matrix(config)
    if any("6. [建模]" in a for a in actions):
        epv_model.run_ev_calculator(config)
    if any("7. [運算]" in a for a in actions):
        epv_model.run_markov_epv_engine(config)
    if any("8. [分析]" in a for a in actions):
        epv_model.run_synergy_analyzer(config)
        
    if any("9. [圖論]" in a for a in actions):
        network.run_network_analysis(config)

    print("\n🎉 分析管線已全數執行完畢！所有成果已儲存至目前資料夾。")

if __name__ == '__main__':
    main()
