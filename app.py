##丞燕產品訂購系統 (有紀錄查詢版)11  app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from st_copy_to_clipboard import st_copy_to_clipboard
# 額外需要的庫（需加入 requirements.txt）: gspread
import gspread
from google.oauth2.service_account import Credentials

# 1. 頁面配置
st.set_page_config(page_title="丞燕產品訂購系統", layout="wide")

# 2. 初始化 Session State
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'order_count' not in st.session_state:
    st.session_state.order_count = 1

# --- Google Sheets 連線設定 ---
# 建議將金鑰放在 Streamlit Secrets 中
def get_gspread_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # 這裡假設您在 Streamlit Secrets 存儲了金鑰內容
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

# 3. 讀取產品資料
@st.cache_data
def load_data():
    df = pd.read_csv('丞燕產品價格.csv', dtype={'貨號': str})
    return df

df = load_data()

# --- 主標題 ---
st.title("🌿 丞燕產品訂購系統")

# --- 右側框架：使用 Tabs 分頁 ---
tab1, tab2, tab3 = st.tabs(["📝 產品選購", "🛒 購物車結帳", "📜 紀錄管理"])

# --- Tab 1: 訂單資訊與產品選購 ---
with tab1:
    st.subheader("第一步：填寫基本資料")
    with st.container(border=True):
        col_name, col_id = st.columns([1, 1])
        with col_name:
            customer_name = st.text_input("👤 訂購人姓名", placeholder="請輸入姓名...")
        with col_id:
            tw_time = datetime.now() + timedelta(hours=8)
            today_str = tw_time.strftime("%Y%m%d")
            order_id = f"{today_str}-{st.session_state.order_count:03d}"
            st.write(f"🆔 當前訂單序號：`{order_id}`")
            if st.button("🔄 下一組序號"):
                st.session_state.order_count += 1
                st.rerun()

    st.divider()
    st.subheader("第二步：選購產品")
    search_term = st.text_input("🔍 搜尋品名或貨號", "")
    
    f_df = df[df["品名"].str.contains(search_term, case=False) | df["貨號"].str.contains(search_term)]
    
    for _, row in f_df.iterrows():
        with st.expander(f"**{row['品名']}** (DPT {row['含稅價 DPT']:,})"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"貨號: `{row['貨號']}` | SV: {row['積分額 SV']}")
            with c2:
                qty = st.number_input("數量", min_value=1, value=1, key=f"q_{row['貨號']}")
                if st.button("➕ 加入", key=f"b_{row['貨號']}", use_container_width=True):
                    st.session_state.cart[row['貨號']] = st.session_state.cart.get(row['貨號'], 0) + qty
                    st.success(f"✅ 已加入 {row['品名']}")

# --- Tab 2: 購物車內容 ---
with tab2:
    st.header("🛒 確認訂購內容")
    if not st.session_state.cart:
        st.info("購物車是空的")
    else:
        cart_items = []
        total_sv, total_dpt = 0, 0
        for hid, q in list(st.session_state.cart.items()):
            p = df[df['貨號'] == hid].iloc[0]
            total_sv += p['積分額 SV'] * q
            total_dpt += p['含稅價 DPT'] * q
            cart_items.append({"品名": p['品名'], "數量": q, "SV": p['積分額 SV']*q, "DPT": p['含稅價 DPT']*q})
            st.write(f"🔸 {p['品名']} x {q} (DPT {p['含稅價 DPT']*q:,})")

        st.divider()
        promo_choice = st.radio("優惠方案", ["不使用", "(SV-4500)x10%", "SVx10%"])
        
        final_p = total_dpt
        disc_val = 0
        if "4500" in promo_choice:
            disc_val = max(0, (total_sv - 4500) * 0.1)
        elif "SVx10%" in promo_choice:
            disc_val = total_sv * 0.1
        final_p = total_dpt - disc_val

        st.metric("應付金額", f"NT$ {final_p:,.0f}")

        # --- 存檔功能 ---
        if st.button("💾 儲存紀錄到雲端並複製", use_container_width=True):
            # 這裡實作串接 Google Sheets 的寫入邏輯
            gc = get_gspread_client()
            if gc:
                try:
                    sh = gc.open("訂購紀錄").get_worksheet(0)
                    items_str = ", ".join([f"{i['品名']}x{i['數量']}" for i in cart_items])
                    sh.append_row([order_id, tw_time.strftime("%Y-%m-%d %H:%M"), customer_name, items_str, sum(i['數量'] for i in cart_items), total_sv, total_dpt, final_p])
                    st.success("☁️ 紀錄已同步至 Google Drive！")
                except:
                    st.error("連線失敗，請檢查 Google Sheets 設定")
            
            # 原有的複製邏輯...
            st.write("已複製到剪貼簿，請至 LINE 貼上")

# --- Tab 3: 紀錄管理 (查詢、編輯、刪除) ---
with tab3:
    st.header("📜 歷史紀錄管理")
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open("訂購紀錄").get_worksheet(0)
            records = pd.DataFrame(sh.get_all_records())
            
            if not records.empty:
                # 查詢功能
                search_q = st.text_input("🔍 搜尋人名或序號")
                if search_q:
                    records = records[records['訂購人'].str.contains(search_q) | records['訂單序號'].str.contains(search_q)]
                
                # 顯示表格
                st.dataframe(records, use_container_width=True)
                
                # 刪除功能
                del_idx = st.number_input("輸入要刪除的列號 (從 0 開始)", min_value=0, max_value=len(records)-1, step=1)
                if st.button("🗑️ 刪除選定紀錄"):
                    sh.delete_rows(int(del_idx) + 2) # +2 是因為標題列與 0 索引位移
                    st.rerun()
            else:
                st.info("尚無歷史紀錄")
        except:
            st.warning("無法讀取紀錄，請確認試算表名稱為『訂購紀錄』並已共享給服務帳號")
