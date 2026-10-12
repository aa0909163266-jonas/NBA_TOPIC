# Quantitative Analysis of NBA Offensive Systems: 
## Markov Reward Processes and PageRank Centrality in Tactical Networks

**Author:** [Your Name]  
**Target:** Data Science M.S. Application Portfolio  

---

### 1. Introduction & Architecture (系統架構與 API 介接)
本研究旨在將現代籃球的進攻戰術，轉化為可量化的數學模型。傳統數據分析多仰賴靜態的終結數據（如得分、命中率），忽略了「球權流動 (Ball Movement)」的拓撲結構。本專案透過建立自動化 ETL (Extract, Transform, Load) 資料管線，結合機率論與圖論，精準還原球隊的戰術大腦與最佳陣容。

#### 1.1 Data Pipeline Flowchart (資料管線流程圖)
(可在此處插入流程圖)
* **API Endpoints:** 呼叫 NBA 官方 `playbyplayv3` 與 `shotchartdetail` 獲取原始文本與空間座標。
* **NLP Processing:** 運用正規表達式 (Regular Expression) 萃取非結構化文本中的隱藏特徵（助攻者）。
* **Relational Algebra:** 利用複合鍵 (Game ID + Event ID) 執行 Inner Join，解決異質資料庫融合的問題。

---

### 2. Spatial Discretization (連續空間特徵離散化)
NBA 官方紀錄的投籃座標為二維歐幾里得空間 (2D Euclidean Space)。為了建立馬可夫矩陣的有限狀態空間 (Finite State Space)，必須將連續座標降維、離散化為 14 個標準戰術區域。

#### 2.1 Mathematical Transformation (幾何轉換公式)
針對輸入之直角座標 (x, y)，透過極座標轉換 (Polar Coordinate Transformation) 取得半徑 r 與夾角 θ：
* $r = \sqrt{x^2 + y^2}$
* $\theta = \arctan(y/x)$

藉此將球場精準切割為 Restricted Area, Corner 3, Mid-range 等 14 區。

#### 2.2 Expected Value by Law of Large Numbers (大數法則期望值)
根據大數法則 (Law of Large Numbers)，當樣本數 N 趨近於無限大時，實證命中率 (Empirical FG%) 收斂於真實機率。
* $EV = P(Make | Zone) * Points$

此步驟自動排除了低效的中距離與半場投籃，賦予禁區與三分線最高的權重 (Reward)。

---

### 3. Markov Reward Process, MRP (馬可夫獎勵過程)
本研究的核心創新在於使用吸收馬可夫鏈 (Absorbing Markov Chain) 來量化「預期球權價值 (Expected Possession Value, EPV)」。

#### 3.1 矩陣定義 (Matrix Definitions)
* **狀態空間 (State Space):** 場上 15 名球員 (Transient States) + 14 個投籃區域 (Absorbing States)。
* **轉移矩陣 (Transition Matrix, Q):** 球員 A 傳球給球員 B 的條件機率矩陣。
* **獎勵向量 (Reward Vector, R):** 球員自身選擇投籃時的平均期望值 (EV)。

#### 3.2 基礎矩陣解法 (The Fundamental Matrix Equation)
在無窮期的球權流動中，預期價值的總和為一個無限矩陣等比級數。
透過線性代數 (Linear Algebra) 推導，該級數收斂於反矩陣公式：
* $EPV = (I - Q)^{-1} R$

(其中 I 為單位矩陣 Identity Matrix)。此公式計算出當球在特定球員手中時，該次進攻回合最終能為球隊創造的極限分數。

---

### 4. Graph Theory & PageRank Centrality (圖論與戰術網路)
**【學術洞察 (Academic Insight)】: The "Star-Feeding" Bias**
單純的 EPV 模型在小樣本下存在缺陷：邊緣球員 (Role Players) 若將球權 100% 交給超級球星 (如 Nikola Jokić)，其 EPV 會產生虛高 (Inflation)。

為了解決此「籃球黑洞 (Sink Node)」問題，本專案引入圖論 (Graph Theory)，將球隊重構為有向權重圖 (Directed Weighted Graph)，並採用 Google 的 PageRank 演算法。

#### 4.1 PageRank Formula (隨機跳躍與阻尼因子)
透過引入阻尼因子 (Damping Factor, alpha = 0.85) 模擬球權的隨機重置 (Teleportation)，完美解決了轉移矩陣不收斂的報錯問題，並精準定位出真正的球隊大腦 (Tactical Hub)。

#### 4.2 Network Topology Visualization (網路拓撲視覺化)
(請在此處貼上 nuggets_22023_passing_network.png)
*比較與觀察：* 使用力導向排版 (Force-directed Layout)，節點半徑映射為 PageRank 指數。可清晰觀察到 Nikola Jokić 為金塊隊的絕對核心 (Hub)，而邊緣球員被推斥至外圍。

---

### 5. Data-Driven Lineup Optimization (數據驅動陣容最佳化)
本專案不仰賴主觀球探報告，而是透過跨模型融合 (Cross-Model Fusion) 產出最佳先發五人 (Starting 5)：
1. **The Tactical Hubs (主力大腦):** 直接提取 PageRank 中心性最高的前三名球員作為 Big 3。
2. **The 3-and-D Wings (頂級綠葉):** 對 EPV 化學效應矩陣 (Synergy Matrix) 進行條件篩選 (Boolean Indexing)，找出「接收 Big 3 傳球」且「產生最高總期望值」的兩名非核心球員。

融合拓撲學的『中樞定位』與機率論的『效率最大化』，給出最科學的陣容解答。

---

### 6. Future Work (未來展望)
在未來的研究中，本系統具備兩大擴充方向：
1. **2nd-Order Markov Chains (二階馬可夫鏈):** 突破一階無記憶性 (Memoryless) 的限制，將狀態定義擴充為 P(X_t+1 | X_t, X_t-1)，以精準擬合 Give-and-Go (撞牆配合) 等動態戰術。
2. **Reinforcement Learning (強化學習):** 若能取得 NBA 光學追蹤極密資料，可將目前的馬可夫獎勵過程 (MRP) 升級為馬可夫決策過程 (MDP)，透過 AI 為持球者計算投籃與傳球的數學最佳解 (Optimal Policy)。
