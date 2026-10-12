import pandas as pd
import numpy as np
from nba_api.stats.endpoints import leaguegamefinder, playbyplayv3, shotchartdetail
from nba_api.stats.static import teams

# =====================================================================
# [學術解析] run_check: 資料型別與綱要 (Schema) 檢查模組
# 目的：使用 Pandas 的 DataFrame.columns 屬性，列印出結構化表格的特徵欄位，
#       用於除錯 (Debugging) 確保資料清理步驟沒有遺失關鍵變數。
# =====================================================================
def run_check():
    print("文字直播欄位：", pd.read_csv("warriors_game_test.csv").columns.tolist())
    print("幾何空間欄位：", pd.read_csv("warriors_shots_with_zones.csv").columns.tolist())

# =====================================================================
# [學術解析] run_test_nba_api: RESTful API 端點連通性測試 (文字轉播)
# 目的：透過向遠端伺服器發送單次 HTTP 請求，驗證網路連通性與 API 接口穩定度。
# 邏輯：展示了 List Comprehension (串列生成式) 以及 Try-Except 例外處理的高級語法。
# =====================================================================
def run_test_nba_api():
    print("正在尋找金州勇士隊的 Team ID...")
    
    # [靜態資料庫調用] 從本地靜態函式庫中取得 NBA 30 支球隊的雜湊表 (Hash Table)
    nba_teams = teams.get_teams()
    
    # [串列生成式 (List Comprehension)]
    # 這是 Python 語言中極具表達力的函數式程式設計 (Functional Programming) 語法。
    # 它的等價數學集合表示法為： { team ∈ nba_teams | team['abbreviation'] == 'GSW' }
    # 最後的 [0] 提取該單元素集合中的唯一解。
    warriors = [team for team in nba_teams if team['abbreviation'] == 'GSW'][0]
    warriors_id = warriors['id']
    print(f"成功找到！勇士隊的 Team ID 是: {warriors_id}\n")
    
    # [例外處理機制 (Exception Handling)]
    # 使用 try-catch 結構。在分散式系統或爬蟲應用中，網路斷線與 403 Forbidden 是常態。
    # 此結構能確保在遇到 OSError 或 JSONDecodeError 時，程式流程 (Control Flow) 得以優雅地(gracefully)跳出，而非直接崩潰 (Crash)。
    try:
        pbp = playbyplayv3.PlayByPlayV3(game_id='0022100414')
        pbp_df = pbp.get_data_frames()[0]
    
        print("\n--- 成功抓取數據！以下為前 10 筆事件試閱 ---")
        # [多維度切片 (Multi-dimensional Slicing)] 只選取特定的特徵子集 (Feature Subset) 並顯示前 10 筆觀測值
        print(pbp_df[['period', 'clock', 'actionType', 'description']].head(10))
        pbp_df.to_csv("warriors_game_test.csv", index=False)
    
    except Exception as e:
        print(f"抓取失敗，錯誤訊息：{e}")

# =====================================================================
# [學術解析] run_test_shot_chart: RESTful API 端點連通性測試 (投籃空間)
# 目的：測試 ShotChartDetail 端點，確保能獲取帶有 (LOC_X, LOC_Y) 歐幾里得座標的連續幾何數據。
# =====================================================================
def run_test_shot_chart():
    print("正在抓取勇士隊的投籃幾何坐標數據...")
    try:
        # [API 參數化設計 (Parameterization)]
        # 透過指定 context_measure_simple='FGA'，指示伺服器過濾掉罰球 (FTA) 或失誤，
        # 只回傳 Field Goal Attempts (包含命中與未命中的所有出手事件)。
        shot_chart = shotchartdetail.ShotChartDetail(
            team_id=1610612744,
            player_id=0,  
            season_nullable='2021-22',
            season_type_all_star='Regular Season',
            context_measure_simple='FGA'  
        )
        shot_df = shot_chart.get_data_frames()[0]
        print("\n--- 成功抓取幾何數據！ ---")
        print(shot_df[['PLAYER_NAME', 'EVENT_TYPE', 'LOC_X', 'LOC_Y', 'SHOT_ZONE_AREA']].head())
        shot_df.to_csv("warriors_shots.csv", index=False)
    
    except Exception as e:
        print(f"抓取失敗：{e}")

# [主程式進入點 (Main Execution Block)]
if __name__ == '__main__':
    run_check()
    run_test_nba_api()
    run_test_shot_chart()
