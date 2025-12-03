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
# ==========================================
st.set_page_config(
    page_title="Python 历史战略室",
    layout="wide",
    page_icon="⚓"
)

# 中文支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False 

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
st.title("⚓ 马汉海权论：大国兴衰推演")

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
    
    st.markdown("## 📝 战略复盘报告 (Strategic Debrief)")
    
    # 根据结果生成不同的分析文案
    if winner.color == 'blue':
        st.info(f"""
        **胜者：大英帝国 (Sea Power)**
        
        **战局分析：**
        英国成功维持了“双强标准”，通过强大的海军封锁了大陆对手。
        * **关键因素**：德国的陆防负担 ({land_burden_ger}) 可能过高，导致其无法将足够资源转化为海军；或者德国虽然发起了挑战，但被英国深厚的存量优势压制。
        * **马汉理论验证**：证明了“封锁”对贸易型经济的毁灭性打击。
        """)
    elif winner.color == '#8B4513':
        st.warning(f"""
        **胜者：得意志帝国 (Land Power)**
        
        **战局分析：**
        这是一个典型的**“麦金德时刻”**——陆权国家利用其庞大的工业腹地，彻底压倒了海权岛国。
        * **关键转折**：在第 15 年，德国因陆防负担较低 (<0.1)，成功启动了《提尔皮茨计划》，将经济转入战时体制。
        * **胜因**：德国依靠 `工业系数 4.0` 的内循环能力抵抗了封锁，并用 80% 的预算堆出了比英国更多的军舰。
        * **历史启示**：这模拟了“如果德国在一战前不与法俄为敌，全力对付英国”的反事实历史。
        """)
    else:
        st.error(f"**胜者：{winner.name}**\n\n这通常意味着由于参数设置过于温和，世界处于长期的和平或低烈度竞争中，商业国家依靠复利赢得了胜利。")

    # --- 【新增模块 3】模型机制解释 ---
    with st.expander("🔍 揭秘：这个模型背后的数学逻辑是什么？"):
        st.markdown("""
        为了模拟真实的地缘政治，我们在后台加入了以下**修正参数**：
        1.  **陆权韧性 (The Continental Resilience)**：
            * 当英国被封锁，其工业产出系数降为 `0.2`（饥饿）。
            * 当德国被封锁，其工业产出系数保持 `4.0`（鲁尔区内循环）。这解释了为什么德国很难被“饿死”。
        2.  **资产泡沫 (Asset Bubble)**：
            * 你看到的圆圈大小代表“综合国力”。一旦被封锁，商船价值从 `2.0` 暴跌至 `0.2`，模拟战时资产贬值。
        3.  **提尔皮茨触发器 (Tirpitz Trigger)**：
            * 只有当你在侧边栏将德国陆防负担设为 `< 0.1` 时，德国才会显露野心，将海军预算从 30% 提升至 80%。
        """)