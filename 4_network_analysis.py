import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import sqlite3

DB_NAME = "nba_master.db"

def run_network_analysis(config):
    team_name = config['team_name']
    season_id = config['season_id_api']
    input_table = f"{team_name}_{season_id}_tactics_merged"
    
    print(f"🕸️ 啟動 {team_name.capitalize()} 戰術網路與圖論中心性分析...")
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql(f"SELECT * FROM {input_table}", conn)
    except Exception:
        print(f"找不到資料表 {input_table}")
        return
        
    df = df[df['傳球者 (Passer)'] != df['終結者 (Shooter)']]
    pass_counts = df.groupby(['傳球者 (Passer)', '終結者 (Shooter)']).size().reset_index(name='Pass_Count')
    
    pass_counts = pass_counts[pass_counts['Pass_Count'] >= 15]
    
    G = nx.DiGraph()
    for _, row in pass_counts.iterrows():
        G.add_edge(row['傳球者 (Passer)'], row['終結者 (Shooter)'], weight=row['Pass_Count'])
        
    try:
        centrality = nx.pagerank(G, weight='weight')
    except Exception as e:
        print(f"計算中心性時發生錯誤: {e}")
        return
        
    centrality_df = pd.DataFrame(list(centrality.items()), columns=['球員 (Player)', '戰術樞紐指數 (Centrality)'])
    centrality_df = centrality_df.sort_values(by='戰術樞紐指數 (Centrality)', ascending=False)
    
    print("\n🏆 --- 球隊戰術樞紐 (PageRank Centrality) 排行榜 ---")
    print(centrality_df.head(10).to_string(index=False))
    
    # =====================================================================
    # [學術解析] 陣容最佳化 (Lineup Optimization)：基於 PageRank 的先發五人
    # 邏輯：
    # 1. 核心 (Big 3)：這次我們不再使用容易受樣本數影響的 EPV，而是使用圖論算出的 
    #    PageRank 戰術樞紐指數前三名，作為真正的球隊大腦。
    # 2. 綠葉 (Role Players)：去資料庫調閱 EPV 化學效應表 (Synergy)，找出最能把
    #    這三顆大腦傳出來的球，轉化為高期望值得分的頂級綠葉。
    # =====================================================================
    big_3 = centrality_df['球員 (Player)'].head(3).tolist()
    synergy_table = f"{team_name}_{season_id}_duo_synergy"
    try:
        with sqlite3.connect(DB_NAME) as conn:
            synergy_df = pd.read_sql(f"SELECT * FROM {synergy_table}", conn)
            
        cond_passer = synergy_df['傳球者 (Passer)'].isin(big_3)
        cond_shooter = ~synergy_df['終結者 (Shooter)'].isin(big_3)
        role_players_df = synergy_df[cond_passer & cond_shooter]
        best_role_players = role_players_df.groupby('終結者 (Shooter)')['總創造期望值'].sum().sort_values(ascending=False).head(2).index.tolist()
        
        print(f"\n👑 【PageRank 判定 {team_name.capitalize()} 戰術核心 Big 3】:", ", ".join(big_3))
        print("🛡️  【最佳綠葉推薦 (適配核心三人組)】:", ", ".join(best_role_players))
        print("🚀 【數據驅動推薦：期望值最大化先發五人陣容】")
        print("   主力大腦 (PageRank):", ", ".join(big_3))
        print("   頂級綠葉 (EPV Synergy):", ", ".join(best_role_players))
    except Exception:
        print("\n⚠️ 無法計算先發五人，資料庫缺少 synergy 資料表，請先確認步驟 8 已執行。")
    
    
    plt.figure(figsize=(14, 12))
    
    node_sizes = [centrality[node] * 6000 for node in G.nodes()]
    edges = G.edges()
    weights = [G[u][v]['weight'] / 15 for u, v in edges]
    
    pos = nx.spring_layout(G, k=1.2, seed=42)
    
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='gold', alpha=0.9, edgecolors='darkblue', linewidths=2)
    nx.draw_networkx_edges(G, pos, width=weights, edge_color='gray', alpha=0.5, arrowsize=20, connectionstyle="arc3,rad=0.15")
    nx.draw_networkx_labels(G, pos, font_size=11, font_family='sans-serif', font_weight='bold')
    
    plt.title(f"NBA {config['season_str_api']} {team_name.capitalize()} Passing Network & Tactical Hubs", fontsize=20, fontweight='bold')
    plt.axis('off')
    
    output_img = f"{team_name}_{season_id}_passing_network.png"
    plt.savefig(output_img, dpi=300, bbox_inches='tight')
    print(f"🖼️ 拓撲圖已儲存為 {output_img}")

if __name__ == "__main__":
    print("請使用 0_main_launcher.py 來執行此程式！")
