import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector 

# ==========================================
# 0. 全局配置
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False # 解决负号显示问题
# ==========================================
st.set_page_config(
    page_title="Python 历史战略实验室",
    layout="wide",
    page_icon="⚓"
)


# ... (后面接侧边栏代码 st.sidebar...) ...
# ==========================================
# 1. 核心模型逻辑 (Mesa Backend)
# ==========================================
# ... (NationAgent 和 SeaPowerModel 类代码保持不变，为了节省篇幅，这里直接使用您上一版修正好的逻辑) ...
# ... (请保留您上一步修正过的 NationAgent 和 SeaPowerModel 类) ...

class NationAgent(Agent):
    def __init__(self, unique_id, model, name, strategy, color, land_security_burden):
        super().__init__(unique_id, model)
        self.name = name
        self.strategy = strategy
        self.color = color
        self.land_security_burden = land_security_burden
        self.wealth = 500
        self.industry = 120 
        self.merchant_fleet = 50
        self.navy = 20
        self.has_sea_control = False
        self.is_blockaded = False

    @property
    def total_power(self):
        ship_value = 2.0
        if self.is_blockaded: ship_value = 0.2
        asset_value = (self.industry * 5) + (self.navy * 15) + (self.merchant_fleet * ship_value)
        return self.wealth + asset_value

    def step(self):
        self.economic_cycle()
        self.invest()
        self.pay_maintenance()

    def economic_cycle(self):
        if self.color == '#8B4513': ind_multiplier = 4.0 
        else: ind_multiplier = 0.2 if self.is_blockaded else 1.5
        base_income = self.industry * ind_multiplier
        
        if self.has_sea_control: trade_eff = 2.0 
        elif self.is_blockaded: trade_eff = 0.05 
        else: trade_eff = 0.8
        
        trade_income = self.merchant_fleet * 2.0 * trade_eff
        self.wealth += base_income + trade_income
            
    def invest(self):
        if self.wealth <= 10: return
        budget = self.wealth * 0.4 
        self.wealth -= budget
        net_budget = budget * (1 - self.land_security_burden)
        self.industry += (net_budget * self.strategy['industry']) // 40
        self.merchant_fleet += (net_budget * self.strategy['merchant']) // 8
        self.navy += (net_budget * self.strategy['navy']) // 15

    def pay_maintenance(self):
        cost = (self.navy * 0.8) + (self.merchant_fleet * 0.2)
        self.wealth -= cost
        if self.wealth < 0: self.wealth = 0

class SeaPowerModel(Model):
    def __init__(self, land_burden_ger, land_burden_uk):
        self.grid = MultiGrid(10, 10, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        self.current_sea_state = "Contested"
        self.status_message = "" 
        
        uk = NationAgent(1, self, "UK (Sea)", {'navy':0.6, 'merchant':0.3, 'industry':0.1}, 'blue', land_burden_uk)
        self.grid.place_agent(uk, (1, 8))
        self.schedule.add(uk)
        
        ger_strat = {'navy': 0.3, 'merchant': 0.2, 'industry': 0.5}
        ger = NationAgent(2, self, "Germany (Land)", ger_strat, '#8B4513', land_burden_ger)
        self.grid.place_agent(ger, (8, 2))
        self.schedule.add(ger)
        
        ned = NationAgent(3, self, "Netherlands", {'navy':0.1, 'merchant':0.8, 'industry':0.1}, 'orange', 0.1)
        self.grid.place_agent(ned, (5, 5))
        self.schedule.add(ned)

        self.datacollector = DataCollector(agent_reporters={"TotalPower": "total_power", "Navy": "navy"})

    def step(self):
        if self.schedule.steps == 15:
            ger = next(a for a in self.schedule.agents if a.unique_id == 2)
            if ger.land_security_burden < 0.1:
                ger.strategy = {'navy': 0.8, 'merchant': 0.0, 'industry': 0.2}
                ger.name = "Germany (Total War)"
                self.status_message = "⚠️ 警告：德国启动《提尔皮茨计划》！(Total War Econ)"
        
        self.determine_sea_control()
        self.schedule.step()
        self.datacollector.collect(self)

    def determine_sea_control(self):
        agents = self.schedule.agents
        sorted_agents = sorted(agents, key=lambda x: x.navy, reverse=True)
        strongest = sorted_agents[0]
        runner_up = sorted_agents[1]
        ratio = strongest.navy / max(1, runner_up.navy)
        
        for a in agents: a.has_sea_control, a.is_blockaded = False, False
        
        if ratio > 1.2:
            strongest.has_sea_control = True
            if strongest.color == 'blue': self.current_sea_state = "blue_domination"
            elif strongest.color == '#8B4513': self.current_sea_state = "red_domination"
            elif strongest.color == 'orange': self.current_sea_state = "orange_domination"
            for a in agents: 
                if a != strongest: a.is_blockaded = True
        else:
            self.current_sea_state = "Contested"
            strongest.navy *= 0.95
            runner_up.navy *= 0.95

# ==========================================
# 2. Streamlit 前端界面
# ==========================================

# --- 侧边栏 ---
st.sidebar.markdown("### [🐍 Python 历史战略实验室](https://www.pystrategylab.com)")
logo_url = "https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=768,fit=crop,q=95/1evUiS818YahKfZE/pythonlogo2-AfiMET3ydIQjjfId.png" 
st.sidebar.image(logo_url, width=100) 

st.sidebar.header("⚙️ 战略参数调整")

st.sidebar.info("💡 **操作指南**：通过调整'陆防负担'，模拟国家在陆军上消耗的国力。数值越低，代表该国地缘环境越安全，可投入更多资源造舰。")

st.sidebar.subheader("陆权国的抉择")
land_burden_ger = st.sidebar.slider(
    "德国的陆军防御负担", 
    min_value=0.0, max_value=0.8, value=0.5, step=0.05,
    help="如果低于 0.1，德国将认为陆地安全，启动疯狂造舰计划挑战英国。"
)

st.sidebar.subheader("海权国的优势")
land_burden_uk = st.sidebar.slider(
    "英国的陆军防御负担", 
    min_value=0.0, max_value=0.5, value=0.05, step=0.05,
    help="作为岛国，英国天然不需要维持庞大陆军。"
)

simulation_years = st.sidebar.slider("模拟时长 (年)", 20, 100, 60)
run_btn = st.sidebar.button("🚀 开始推演", type="primary")

# --- 主界面 ---
# ... (st.set_page_config 代码之后) ...

# --- 封面图与介绍模块 ---

# 封面图 URL (这里用了您之前生成的那个“算法眼中的帝国”图)
cover_url = "https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=1920,h=1152,fit=crop/1evUiS818YahKfZE/aeu-aee-r-o-KMkansqXeywRDmdU.jpg"  # 示例链接，建议换成您真实上传后的图片链接

# 使用 st.image 展示封面，use_column_width=True 让它自动撑满宽度
st.image(cover_url, use_container_width=True, caption="Project 002: Algorithm of The Empire")
# 项目标题
st.title("⚓ 马汉海权论：大国兴衰推演")

# 核心介绍 (MBA 视角卖点)
st.markdown("""
> **“谁控制了海洋，谁就控制了全球贸易；谁控制了贸易，谁就控制了世界的财富。”** —— A.T. 马汉

本模拟器基于 **Agent-Based Modeling (ABM)** 技术，重构了 1914 年前后的英德海权博弈。
不仅复盘历史，更旨在通过算法推演，为现代商业决策提供**量化洞见**：

* **平台战略 vs 全产业链**：英国代表的“贸易垄断”如何对抗德国代表的“工业内循环”？
* **战略透支**：模拟德国如何在**“陆地安全”与“海洋霸权”**的资源拉锯中走向破产。给盲目扩张企业的警示录。
* **数字风洞**：通过调整**【陆防负担】**等关键参数，在虚拟沙盘中预演企业转型的风险与收益。

👉 **请在左侧侧边栏调整参数，点击“开始模拟”启动推演。**
""")

st.markdown("---")

# 【新增模块 1】理论情报简报
with st.expander("📚 理论情报：马汉海权论的三个核心支柱 (点击展开)"):
    st.markdown("""
    本模型基于阿尔弗雷德·赛耶·马汉 (Alfred Thayer Mahan) 的《海权对历史的影响》，模拟了三个核心论点：
    1.  **生产与贸易 (Production & Trade)**：海权不仅仅是军舰，更是通过海洋贸易积累的财富。
        * *对应代码*：商船队 (Merchant Fleet) 带来的巨额收入。
    2.  **封锁与窒息 (Blockade)**：丧失制海权的国家将被切断贸易，经济链条崩溃。
        * *对应代码*：被封锁国资产贬值，收入锐减（商业国死得最快）。
    3.  **决战与制海权 (Command of the Sea)**：海权不能共享，必须通过集中兵力决战获得，赢家通吃。
        * *对应代码*：只要海军实力比 > 1.2，霸主即确立，对手即被封锁。
    """)

st.markdown("---")
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🌍 地缘政治态势图")
    map_placeholder = st.empty()

with col2:
    st.subheader("📈 综合国力演变 (Total Power)")
    chart_placeholder = st.empty()
    st.subheader("🚢 海军吨位对比 (Naval Strength)")
    navy_chart_placeholder = st.empty()

# 绘图函数
def plot_grid(model, year):
    fig, ax = plt.subplots(figsize=(6, 6))
    
    bg_color = '#f0f0f0'
    title_text = "Status: Contested (消耗战)"
    
    if model.status_message and year >= 15:
        title_text = f"{model.status_message}"
        if "blue_domination" in model.current_sea_state:
            title_text += "\n(But UK still holds Sea)"
    else:
        if "blue_domination" in model.current_sea_state:
            bg_color = '#d0eaff'
            title_text = "Status: Pax Britannica (英国治世)"
        elif "red_domination" in model.current_sea_state:
            bg_color = '#ffcccb'
            title_text = "Status: German Hegemony (德国霸权)"
    
    ax.set_facecolor(bg_color)
    ax.set_xlim(-1, 10)
    ax.set_ylim(-1, 10)
    ax.set_title(f"Year: {year} | {title_text}", fontsize=11, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)
    
    for agent in model.schedule.agents:
        size = agent.total_power / 10
        ax.scatter(agent.pos[0], agent.pos[1], s=size, c=agent.color, 
                   label=agent.name, edgecolors='black', alpha=0.8, zorder=10)
        
        if agent.is_blockaded:
            circle = plt.Circle((agent.pos[0], agent.pos[1]), 0.8, 
                                color='red', fill=False, linewidth=2, linestyle='--')
            ax.add_patch(circle)
            ax.text(agent.pos[0], agent.pos[1], "❌", 
                    ha='center', va='center', fontsize=12, color='red', weight='bold')
        
        ax.text(agent.pos[0], agent.pos[1] + 0.8, agent.name.split(' ')[0], 
                ha='center', fontsize=10, weight='bold')
        
    return fig

# --- 模拟运行逻辑 ---
if run_btn:
    model = SeaPowerModel(land_burden_ger, land_burden_uk)
    
    for i in range(simulation_years):
        model.step()
        fig_map = plot_grid(model, i)
        map_placeholder.pyplot(fig_map)
        plt.close(fig_map)
        
        data = model.datacollector.get_agent_vars_dataframe().reset_index()
        power_data = data.pivot(index='Step', columns='AgentID', values='TotalPower')
        power_data.columns = ["UK", "Germany", "Netherlands"]
        chart_placeholder.line_chart(power_data)
        
        navy_data = data.pivot(index='Step', columns='AgentID', values='Navy')
        navy_data.columns = ["UK", "Germany", "Netherlands"]
        navy_chart_placeholder.line_chart(navy_data)

    # --- 【新增模块 2】战略复盘报告 ---
    st.success("✅ 模拟结束！")
    
    winner = max(model.schedule.agents, key=lambda a: a.total_power)
    ger = next(a for a in model.schedule.agents if a.unique_id == 2)
    
    st.markdown("## 📝 深度复盘报告 (Deep Dive Debrief)")
    
    # 使用 Tabs 分两个维度解读
    tab1, tab2 = st.tabs(["🏛️ 历史战略视角", "💼 MBA 商业视角"])
    
    # --- Tab 1: 传统的历史解读 ---
    with tab1:
        if winner.color == 'blue':
            st.info(f"""
            **胜者：大英帝国 (Sea Power)**
            
            * **历史复盘**：
                英国成功维持了“双强标准”，利用制海权切断了德国的贸易生命线。
                德国虽然工业强大，但因**陆防负担过高**（两线作战），无法将足够的资源转化为海军存量。
            * **理论验证**：马汉《海权论》—— 贸易垄断产生的复利，最终压倒了单纯的工业产出。
            """)
        elif winner.color == '#8B4513':
            st.warning(f"""
            **胜者：得意志帝国 (Land Power)**
            
            * **历史复盘**：
                这是一个“反事实”的历史剧本。德国通过外交手段将陆防负担降至极低，成功触发**《提尔皮茨计划》**。
                德国利用**工业内循环 (Industry Multiplier)** 抵抗了封锁，并用 80% 的预算堆出了世界第一舰队。
            * **理论验证**：麦金德《陆权论》—— 大陆心脏地带的资源整合能力，一旦突破临界点，将终结海洋霸权。
            """)
        else:
            st.error(f"**胜者：{winner.name}**\n\n和平发展模式获胜。")

    # --- Tab 2: 新增的 MBA 商业解读 ---
    with tab2:
        st.markdown("#### 📊 从大国博弈看商业竞争")
        
        if winner.color == 'blue':
            st.info(f"""
            **商业案例：平台型企业的胜利 (Platform Strategy Win)**
            
            * **原型**：苹果 (Apple) / 亚马逊 (Amazon)
            * **胜因分析**：
                英国代表了**“轻资产、重生态”**的平台模式。它通过控制**核心渠道**（海权/AppStore）向全球收税。
                尽管德国（制造型企业）产能惊人，但因为缺乏**渠道控制权**（被封锁），产品卖不出去，现金流断裂。
            * **MBA 启示**：
                * **护城河 (Moat)**：控制连接用户的通道（贸易线）比拥有工厂更重要。
                * **现金流 (Cash Flow)**：贸易复利带来的现金流优势，可以拖垮重资产的竞争对手。
            """)
        elif winner.color == '#8B4513':
            st.warning(f"""
            **商业案例：全产业链企业的逆袭 (Vertical Integration Win)**
            
            * **原型**：华为 (Huawei) / 比亚迪 (BYD) / 早期福特
            * **胜因分析**：
                德国代表了**“重研发、全产业链”**的硬核模式。当它解决了**管理内耗**（降低陆防负担）后，
                利用**垂直整合**（工业内循环）带来的成本优势和抗风险能力，硬扛住了平台的封锁，最终实现了技术/产能的**暴力突围**。
            * **MBA 启示**：
                * **反脆弱 (Antifragility)**：在“去全球化”或“被制裁”的环境下，拥有核心制造能力的企业比平台型企业更具生存力。
                * **饱和式投入**：当在一个单一赛道（海军/新能源）投入 80% 资源时，规模效应将击穿对手的壁垒。
            """)
        else:
             st.markdown("商业环境平稳，专注于细分市场的**隐形冠军**（商业国）获得了最大收益。")

    # --- 底部增加通用的 MBA 理论映射 ---
    with st.expander("📚 知识卡片：海权论中的 MBA 隐喻"):
        st.markdown("""
        | 军事概念 | MBA 商业映射 | 
        | :--- | :--- |
        | **海洋 (The Sea)** | **全球市场 (Global Market)** |
        | **海军 (Navy)** | **核心竞争力/研发投入 (R&D & Capital)** |
        | **商船队 (Merchant Fleet)** | **供应链与物流体系 (Supply Chain)** |
        | **封锁 (Blockade)** | **技术制裁 / 专利壁垒 / 渠道封杀** |
        | **陆防负担 (Land Burden)** | **企业管理内耗 / 合规成本 / 非核心业务拖累** |
        """)