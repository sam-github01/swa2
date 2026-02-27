#產品查詢網頁程式碼
import streamlit as st
import pandas as pd

# 設定頁面資訊
st.set_page_config(page_title="丞燕產品價格查詢系統", layout="wide")

# 讀取 CSV 資料
@st.cache_data
def load_data():
    # 讀取檔案，確保貨號被視為字串以防格式跑掉
    df = pd.read_csv('丞燕產品價格.csv', dtype={'貨號': str})
    return df

try:
    df = load_data()

    # --- 側邊欄：搜尋與篩選 ---
    st.sidebar.header("🔍 查詢條件")

    # 1. 關鍵字搜尋 (品名或貨號)
    search_term = st.sidebar.text_input("輸入產品名稱或貨號", "")

    # 2. 類別篩選
    all_categories = ["全部"] + sorted(df["類別"].unique().tolist())
    selected_category = st.sidebar.selectbox("選擇產品類別", all_categories)

    # 3. 價格範圍篩選 (根據 含稅價 DPT)
    min_price = int(df["含稅價 DPT"].min())
    max_price = int(df["含稅價 DPT"].max())
    price_range = st.sidebar.slider(
        "含稅價範圍 (DPT)", 
        min_price, max_price, (min_price, max_price)
    )

    # --- 資料過濾邏輯 ---
    filtered_df = df.copy()

    # 關鍵字過濾
    if search_term:
        filtered_df = filtered_df[
            filtered_df["品名"].str.contains(search_term, case=False, na=False) |
            filtered_df["貨號"].str.contains(search_term, na=False)
        ]

    # 類別過濾
    if selected_category != "全部":
        filtered_df = filtered_df[filtered_df["類別"] == selected_category]

    # 價格過濾
    filtered_df = filtered_df[
        (filtered_df["含稅價 DPT"] >= price_range[0]) & 
        (filtered_df["含稅價 DPT"] <= price_range[1])
    ]

    # --- 主頁面顯示 ---
    st.title("🌿 丞燕產品價格查詢系統")
    st.info(f"💡 目前符合條件的產品共 **{len(filtered_df)}** 項")

    # 分頁顯示或呈現主要表格
    if not filtered_df.empty:
        # 顯示互動式表格
        st.subheader("📋 產品清單")
        st.dataframe(
            filtered_df, 
            width='stretch' , 
            hide_index=True,
            column_config={
                "含稅價 DPT": st.column_config.NumberColumn("含稅價 (NT$)", format="$ %d"),
                "積分額 SV": st.column_config.NumberColumn("積分 (SV)")
            }
        )

        # 顯示卡片式視圖 (適合手機查看)
        st.markdown("---")
        st.subheader("📱 快速預覽")
        cols = st.columns(3)
        for i, (_, row) in enumerate(filtered_df.iterrows()):
            with cols[i % 3]:
                with st.expander(f"**{row['品名']}**", expanded=True):
                    st.write(f"🏷️ **類別**: {row['類別']}")
                    st.write(f"🔢 **貨號**: {row['貨號']}")
                    st.write(f"💰 **含稅價**: NT$ {row['含稅價 DPT']:,}")
                    st.write(f"⭐ **積分額**: {row['積分額 SV']} SV")

    else:
        st.warning("⚠️ 找不到符合條件的產品，請嘗試調整搜尋字眼或篩選器。")

except FileNotFoundError:
    st.error("找不到 '丞燕產品價格.csv' 檔案，請確保檔案與 app.py 放在同一個資料夾中。")
