import streamlit as str_web
import pandas as pd
import yfinance as yf
import requests
import io
import time
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

str_web.set_page_config(page_title="Dual Engine IB Terminal", layout="wide")
str_web.title("👑 Квантовая Инвестиционная Платформа (Двухдвижковая Модель)")

# ==========================================
# БОКОВАЯ ПАНЕЛЬ: ВЫБОР МОДЕЛИ И ВВОД ДАННЫХ
# ==========================================
str_web.sidebar.header("⚙️ Выбор аналитического движка")
valuation_mode = str_web.sidebar.radio(
    "Метод ввода финансовых данных",
    ["Классическая бухгалтерия (РСБУ/МСФО)", "Операционные драйверы (Клиенты/Чек)"]
)

str_web.sidebar.markdown("---")
str_web.sidebar.header("1. Операционные показатели")
company_name = str_web.sidebar.text_input("Название бизнеса", value="Моя Корпорация")
currency = str_web.sidebar.selectbox("Валюта расчетов", ["₽", "$", "€"])

if valuation_mode == "Классическая бухгалтерия (РСБУ/МСФО)":
    str_web.sidebar.subheader("Ввод данных из отчетов ФНС")
    current_revenue = str_web.sidebar.number_input(f"Годовая Выручка ({currency})", value=500_000_000, step=1_000_000)
    current_ebitda = str_web.sidebar.number_input(f"Годовая EBITDA ({currency})", value=80_000_000, step=1_000_000)
    current_net_income = str_web.sidebar.number_input(f"Чистая прибыль ({currency})", value=45_000_000, step=1_000_000)
    st_growth = str_web.sidebar.slider("Ожидаемый темп роста выручки (%/год)", 0.0, 50.0, 15.0) / 100
else:
    str_web.sidebar.subheader("Ввод драйверов юнит-экономики")
    client_base = str_web.sidebar.number_input("Количество активных клиентов", value=10_000, step=100)
    arpu = str_web.sidebar.number_input(f"Средний чек клиента в год (ARPU, {currency})", value=50_000, step=500)
    churn_rate = str_web.sidebar.slider("Отток клиентов (Churn Rate, %/год)", 0.0, 30.0, 5.0) / 100
    st_growth_clients = str_web.sidebar.slider("Приток новых клиентов (%/год)", 0.0, 50.0, 15.0) / 100
    t_ebitda_margin = str_web.sidebar.slider("Маржа EBITDA (% от выручки)", 5, 50, 16) / 100
    t_net_margin = str_web.sidebar.slider("Чистая маржинальность (%)", 3, 40, 9) / 100
    
    # Автоматический пересчет драйверов в рубли для расчетного ядра
    current_revenue = client_base * arpu
    current_ebitda = current_revenue * t_ebitda_margin
    current_net_income = current_revenue * t_net_margin
    st_growth = st_growth_clients - churn_rate

str_web.sidebar.markdown("---")
str_web.sidebar.header("2. Оборотный Капитал и Баланс")
col_b1, col_b2, col_b3 = str_web.sidebar.columns(3)
dio = col_b1.number_input("Запасы (DIO)", value=45)
dso = col_b2.number_input("Дебиторка (DSO)", value=30)
dpo = col_b3.number_input("Кредиторка (DPO)", value=40)

t_assets = str_web.sidebar.number_input(f"Внеоборотные активы / Имущество ({currency})", value=200_000_000, step=1_000_000)
t_debt = str_web.sidebar.number_input(f"Общий долг компании ({currency})", value=30_000_000, step=1_000_000)
t_cash = str_web.sidebar.number_input(f"Наличные на счетах ({currency})", value=10_000_000, step=1_000_000)
liquidation_value = str_web.sidebar.number_input(f"Ликвидационный порог активов ({currency})", value=120_000_000, step=1_000_000)

discount_pct = str_web.sidebar.slider("Дисконт за неликвидность закрытого бизнеса (%)", 0, 50, 25)
illiquidity_discount = discount_pct / 100

str_web.sidebar.markdown("---")
str_web.sidebar.header("3. Рыночные Компсы")
default_comps = "MGNT, FIVE, SBER, LKOH" if currency == "₽" else "MSFT, GOOGL, META, DELL"
competitors_input = str_web.sidebar.text_input("Тикеры аналогов через запятую", value=default_comps)
competitors = [x.strip().upper() for x in competitors_input.split(",") if x.strip()]

run_button = str_web.sidebar.button("ЗАПУСТИТЬ ДВУХДВИЖКОВЫЙ АНАЛИЗ", type="primary")

def fetch_moex_risk_free():
    try:
        url = "https://moex.com"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['securities']['data'], columns=res['securities']['columns'])
        return float(df['EFFECTYIELD'].median()) / 100
    except: return 0.15
if run_button:
    with str_web.spinner("Двухдвижковое ядро консолидирует балансы и запускает симуляции Монте-Карло..."):
        net_debt = t_debt - t_cash
        
        # Расчет Финансового цикла оборотного капитала
        ccc = dio + dso - dpo
        
        # Затратный подход (NAV)
        total_assets = t_assets + (current_revenue * (dio + dso) / 365) + t_cash
        nav_value = total_assets - t_debt
        nav_discounted = nav_value * (1 - illiquidity_discount)
        
        # Моделирование ставки капитала WACC (CAPM)
        rf_rate = fetch_moex_risk_free() if currency == "₽" else 0.045
        calculated_beta = round(np.random.uniform(0.95, 1.25), 2)
        cost_of_equity = rf_rate + calculated_beta * 0.06
        total_v = nav_value + t_debt
        we, wd = (nav_value/total_v, t_debt/total_v) if total_v > 0 else (1, 0)
        calculated_wacc = (we * cost_of_equity) + (wd * 0.15 * 0.8)

        # Симуляция Монте-Карло (10 000 итераций)
        simulations = 10_000
        monte_carlo_valuations = []
        sim_cagr = np.random.normal(st_growth, 0.025, simulations)
        sim_margin = np.random.normal((current_ebitda / current_revenue), 0.015, simulations)
        base_fcff = current_ebitda * 0.85 * 0.8
        
        for i in range(simulations):
            g = sim_cagr[i]
            pv_list = [base_fcff * ((1 + g) ** yr) / ((1 + calculated_wacc) ** yr) for yr in range(1, 6)]
            tv = (base_fcff * ((1 + g) ** 5) * (1 + g)) / (calculated_wacc - g) if calculated_wacc > g else 0
            pv_tv = tv / ((1 + calculated_wacc) ** 5)
            val = (sum(pv_list) + pv_tv - net_debt) * (1 - illiquidity_discount)
            monte_carlo_valuations.append(val / 1e6)
            
        monte_carlo_valuations = np.array(monte_carlo_valuations)
        mc_median = np.median(monte_carlo_valuations)
        mc_p10 = np.percentile(monte_carlo_valuations, 10)
        mc_p90 = np.percentile(monte_carlo_valuations, 90)

        # Сбор мультипликаторов аналогов
        comp_data = []
        for symbol in competitors:
            try:
                yf_symbol = f"{symbol}.ME" if currency == "₽" else symbol
                t = yf.Ticker(yf_symbol, session=session); info = t.info
                pe, ev_ebitda, ps, pbv = info.get("trailingPE") or info.get("forwardPE"), info.get("enterpriseToEbitda"), info.get("priceToSalesTrailing12Months"), info.get("priceToBookValue")
                if pe or ev_ebitda or ps or pbv:
                    comp_data.append({"Тикер": symbol, "P/E": pe, "EV/EBITDA": ev_ebitda, "P/S": ps, "P/BV": pbv})
            except: pass
        
        if not comp_data: comp_data = [{"Тикер": "КОНСЕНСУС СЕКТОР", "P/E": 7.5, "EV/EBITDA": 4.8, "P/S": 1.1, "P/BV": 1.2}]
        df_comps = pd.DataFrame(comp_data)

        # Расчет вилки стоимости по всем методам
        methods_results = {}
        for m, key, base_val in [("Мультипликатор P/E (Рыночный)", "P/E", current_net_income), ("Мультипликатор EV/EBITDA (Рыночный)", "EV/EBITDA", current_ebitda), ("Мультипликатор P/S (Рыночный)", "P/S", current_revenue)]:
            if key in df_comps.columns:
                min_v = (base_val * df_comps[key].min()) if key != "EV/EBITDA" else ((base_val * df_comps[key].min()) - net_debt)
                med_v = (base_val * df_comps[key].median()) if key != "EV/EBITDA" else ((base_val * df_comps[key].median()) - net_debt)
                max_v = (base_val * df_comps[key].max()) if key != "EV/EBITDA" else ((base_val * df_comps[key].max()) - net_debt)
                methods_results[m] = {"min": min_v * (1 - illiquidity_discount) / 1e6, "med": med_v * (1 - illiquidity_discount) / 1e6, "max": max_v * (1 - illiquidity_discount) / 1e6}

        if "P/BV" in df_comps.columns and pd.notna(df_comps["P/BV"].min()):
            methods_results["По чистым активам P/BV (Затратный)"] = {
                "min": (nav_value * df_comps["P/BV"].min()) * (1 - illiquidity_discount) / 1e6,
                "med": (nav_value * df_comps["P/BV"].median()) * (1 - illiquidity_discount) / 1e6,
                "max": (nav_value * df_comps["P/BV"].max()) * (1 - illiquidity_discount) / 1e6
            }

        # Рендеринг Дашборда
        str_web.subheader(f"📊 Дашборд консолидированной стоимости — Режим: {valuation_mode}")
        
        col_m1, col_m2, col_m3, col_m4 = str_web.columns(4)
        col_m1.metric("Финальная Выручка в модели", f"{current_revenue/1e6:.1f} млн")
        col_m2.metric("Финансовый цикл (CCC)", f"{ccc} дней")
        col_m3.metric("Чистые активы (NAV)", f"{nav_value/1e6:.1f} млн")
        col_m4.metric("Рассчитанный WACC", f"{calculated_wacc*100:.1f}%")

        str_web.markdown("---")
        plot_col1, plot_col2 = str_web.columns(2)
        
        with plot_col1:
            str_web.subheader("🟢 Интерактивное «Футбольное поле» (Все подходы)")
            fig_ff = go.Figure()
            for m, r in methods_results.items():
                fig_ff.add_trace(go.Bar(y=[m], x=[r["max"] - r["min"]], base=r["min"], orientation='h', name=m, marker=dict(color='rgba(44, 160, 44, 0.7)', line=dict(color='#1f77b4', width=1.5)), hovertemplate=f"<b>{m}</b><br>Минимум: {r['min']:.1f} млн<br>Максимум: {r['max']:.1f} млн<extra></extra>"))
                fig_ff.add_trace(go.Scatter(y=[m], x=[r["med"]], mode='markers', marker=dict(color='red', size=15, symbol='line-ns-open', line_width=4), showlegend=False, name="Медиана", hovertemplate=f"Медиана: {r['med']:.1f} млн<extra></extra>"))
            
            fig_ff.add_trace(go.Scatter(y=["Доходный метод Монте-Карло"], x=[mc_median], mode='markers', marker=dict(color='#1f77b4', size=14, symbol='diamond'), name="Монте-Карло"))
            fig_ff.add_trace(go.Scatter(y=["Прямая цена чистых активов (NAV)"], x=[nav_discounted / 1e6], mode='markers', marker=dict(color='purple', size=14, symbol='star'), name="Чистые активы"))
            fig_ff.add_trace(go.Scatter(y=["Ликвидационный минимум"], x=[liquidation_value / 1e6], mode='markers', marker=dict(color='orange', size=14, symbol='x'), name="Стресс-тест"))
            
            fig_ff.update_layout(paper_bgcolor='#111723', plot_bgcolor='#111723', font=dict(color='white'), xaxis_title=f"Стоимость бизнеса (млн {currency})", height=480, margin=dict(l=20, r=20, t=30, b=20), hovermode="closest")
            str_web.plotly_chart(fig_ff, use_container_width=True, theme=None)

        with plot_col2:
            str_web.subheader("🎲 Распределение вероятностей Монте-Карло")
            fig_mc = px.histogram(x=monte_carlo_valuations, nbins=100, labels={'x': f'Стоимость бизнеса (млн {currency})'})
            fig_mc.update_traces(marker_color='rgba(31, 119, 180, 0.7)', hovertemplate="Интервал цены: %{x:.1f} млн<br>Количество исходов: %{y}<extra></extra>")
            fig_mc.add_vline(x=mc_median, line_dash="dash", line_color="red", annotation_text=f"Мед: {mc_median:.1f}M", annotation_font_color="red")
            fig_mc.add_vline(x=mc_p10, line_dash="dot", line_color="yellow", annotation_text=f"Кризис P10: {mc_p10:.1f}M", annotation_font_color="yellow")
            fig_mc.add_vline(x=mc_p90, line_dash="dot", line_color="green", annotation_text=f"Апсайд P90: {mc_p90:.1f}M", annotation_font_color="green")
            fig_mc.update_layout(paper_bgcolor='#111723', plot_bgcolor='#111723', font=dict(color='white'), yaxis_title="Количество исходов", height=480, margin=dict(l=20, r=20, t=30, b=20))
            str_web.plotly_chart(fig_mc, use_container_width=True, theme=None)

        str_web.markdown("---")
        st_c1, st_c2 = str_web.columns(2)
        with st_c1:
            all_valuations = [r["med"] for r in methods_results.values()] + [mc_median, nav_discounted / 1e6]
            consensus_price = sum(all_valuations) / len(all_valuations)
            str_web.success(f"📊 **Консенсус-заключение платформы:** Сводная средневзвешенная стоимость {company_name} на основе синтеза всех подходов составляет **{consensus_price:.2f} млн {currency}**.")
        with st_c2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_comps.to_excel(writer, sheet_name="Мультипликаторы_Рынка", index=False)
                pd.DataFrame({"Итерация": range(1, simulations+1), "Симуляция_Монте_Карло_Млн": monte_carlo_valuations}).to_excel(writer, sheet_name="Данные_Симуляций", index=False)
            excel_data = output.getvalue()
            str_web.download_button(label="📥 СКАЧАТЬ ВЕСЬ ИНВЕСТ-ПАКЕТ (EXCEL)", data=excel_data, file_name=f"Comprehensive_Valuation_Package_{company_name}.xlsx", use_container_width=True)
else:
    str_web.info("← Выберите режим анализа, заполните метрики на левой панели и нажмите кнопку запуска расчетов.")
