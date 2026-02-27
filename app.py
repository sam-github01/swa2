##丞燕產品訂購助手05 app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard

# 1. 頁面配置
st.set_page_config(page_title="丞燕產品訂購助手", layout="wide")

# 2. 初始化 Session State
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'order_count' not in st.session_state:
    st.session_state.order_count = 1

# 3. 讀取資料
@st.cache_data
def load_data():
    # 讀取 CSV，確保貨號維持字串格式
    df = pd.read_csv('丞燕產品價格.csv', dtype={'貨號': str})
    return df

df = load_data()

# --- 側邊欄：搜尋篩選 (保留在側邊欄，節省空間) ---
st.sidebar.header("🔍 快速過濾產品")
search_term = st.sidebar.text_input("搜尋品名或貨號", "")
all_categories = ["全部"] + sorted(df["類別"].unique().tolist())
selected_category = st.sidebar.selectbox("篩選類別", all_categories)

# 過濾邏輯
filtered_df = df.copy()
if search_term:
    filtered_df = filtered_df[
        filtered_df["品名"].str.contains(search_term, case=False, na=False) |
        filtered_df["貨號"].str.contains(search_term, na=False)
    ]
if selected_category != "全部":
    filtered_df = filtered_df[filtered_df["類別"] == selected_category]

# --- 主介面佈局：左側訂單資訊 | 右側產品選擇 ---
col_order, col_products = st.columns([1.2, 1.8])

# --- 左側：訂購單與購物車管理 (現在移到這裡) ---
with col_order:
    st.subheader("📋 1. 填寫訂單資訊")
    
    # 訂購人與序號區
    with st.container(border=True):
        customer_name = st.text_input("👤 訂購人姓名", placeholder="請在此輸入姓名...")
        
        # 自動生成序號: YYYYMMDD-流水號
        today_str = datetime.now().strftime("%Y%m%d")
        order_id = f"{today_str}-{st.session_state.order_count:03d}"
        
        st.write(f"🆔 當前訂單序號: `{order_id}`")
        if st.button("🔄 切換至下一筆訂單"):
            st.session_state.order_count += 1
            st.rerun()

    st.subheader("🛒 2. 確認訂購內容")
    if not st.session_state.cart:
        st.info("尚未選購任何產品，請從右側加入。")
    else:
        cart_summary = []
        total_sv, total_dpt = 0, 0
        
        # 顯示購物車項目
        for item_id, qty in list(st.session_state.cart.items()):
            product = df[df['貨號'] == item_id].iloc[0]
            sub_sv = product['積分額 SV'] * qty
            sub_dpt = product['含稅價 DPT'] * qty
            total_sv += sub_sv
            total_dpt += sub_dpt
            cart_summary.append({"品名": product['品名'], "數量": qty, "SV": sub_sv, "DPT": sub_dpt})
            
            with st.container(border=True):
                cc1, cc2 = st.columns([5, 1])
                with cc1:
                    st.markdown(f"**{product['品名']}**")
                    st.caption(f"數量: {qty} | 金額: NT$ {sub_dpt:,} | 積分: {sub_sv:,} SV")
                with cc2:
                    if st.button("🗑️", key=f"del_{item_id}"):
                        del st.session_state.cart[item_id]
                        st.rerun()
        
        st.divider()
        st.metric("總計金額 (DPT)", f"NT$ {total_dpt:,}")
        st.metric("總計積分 (SV)", f"{total_sv:,} SV")
        
        # --- 複製按鈕 ---
        copy_text = f"📦 【丞燕產品訂購單】\n"
        copy_text += f"👤 訂購人：{customer_name if customer_name else '未填寫'}\n"
        copy_text += f"🆔 序號：{order_id}\n"
        copy_text += f"📅 日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        copy_text += "="*22 + "\n"
        for item in cart_summary:
            copy_text += f"• {item['品名']} x {item['數量']}\n"
            copy_text += f"  (NT$ {item['DPT']:,} / {item['SV']:,} SV)\n"
        copy_text += "="*22 + "\n"
        copy_text += f"💰 總計金額：NT$ {total_dpt:,}\n"
        copy_text += f"⭐ 總計積分：{total_sv:,} SV"

        st_copy_to_clipboard(
            copy_text, 
            before_copy_label="📋 點擊複製訂單明細", 
            after_copy_label="✅ 已成功複製！可直接貼到 LINE"
        )
        
        if st.button("🧹 清空購物車", use_container_width=True):
            st.session_state.cart = {}
            st.rerun()

# --- 右側：產品瀏覽與選擇 ---
with col_products:
    st.title("🌿 產品選購區")
    st.caption(f"目前顯示 {len(filtered_df)} 項產品，請先調整數量再加入購物車。")
    
    # 產品展示
    for _, row in filtered_df.iterrows():
        with st.expander(f"**{row['品名']}** (NT$ {row['含稅價 DPT']:,})", expanded=False):
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.write(f"🔢 貨號: `{row['貨號']}`")
                st.write(f"⭐ 積分: {row['積分額 SV']} SV")
            with c2:
                # 數量選擇器 (預設值為 1)
                qty = st.number_input("購買數量", min_value=1, value=1, key=f"qty_{row['貨號']}")
                if st.button("➕ 加入", key=f"btn_{row['貨號']}", use_container_width=True):
                    item_id = row['貨號']
                    st.session_state.cart[item_id] = st.session_state.cart.get(item_id, 0) + qty
                    st.toast(f"✅ 已將 {qty} 件 {row['品名']} 加入訂單")
                    st.rerun()

# --- CSS 視覺調整 ---
st.markdown("""
<style>
    /* 讓左側訂單區塊在捲動時能更明顯 */
    [data-testid="stVerticalBlock"] > div:nth-child(1) {
        background-color: transparent;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)
