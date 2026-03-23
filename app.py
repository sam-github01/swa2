##丞燕產品訂購系統 (雲端板 有紀錄查詢版 散購)25  app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
from st_copy_to_clipboard import st_copy_to_clipboard
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

# 1. 頁面與 Icon 配置
ICON_URL = "https://i.ibb.co/9k0Rhkt5/IMG-3089.png"

st.set_page_config(
    page_title="丞燕產品訂購系統", 
    page_icon=ICON_URL,
    layout="wide"
)

# --- 針對 iPhone (iOS) 手機主畫面的「強制注入」作法 ---
components.html(
    f"""
    <script>
        try {{
            var link = window.parent.document.createElement('link');
            link.rel = 'apple-touch-icon';
            link.href = '{ICON_URL}';
            window.parent.document.head.appendChild(link);
        }} catch (e) {{
            console.log("無法寫入 Head:", e);
        }}
    </script>
    """,
    height=0, 
    width=0
)

# 2. 初始化 Session State
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = {}

# 預設的紀錄欄位
RECORD_COLUMNS = ["訂單序號", "日期", "訂購人姓名", "訂購品項", "總計金額(DPT)", "總計積分(SV)", "優惠方案紀錄", "最終應付金額"]

# --- Google Sheets 連線設定 ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open("訂購紀錄").sheet1
    except Exception as e:
        st.error(f"Google Sheets 連線失敗，請檢查金鑰或試算表名稱。錯誤: {e}")
        return None

# --- 強化的雲端紀錄讀取功能 ---
def load_records():
    ws = get_gspread_client()
    if ws:
        try:
            records = ws.get_all_records()
            if not records:
                return pd.DataFrame(columns=RECORD_COLUMNS)
            
            df = pd.DataFrame(records)
            
            for col in RECORD_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
                    
            return df
        except Exception as e:
            return pd.DataFrame(columns=RECORD_COLUMNS)
    return None

# --- 功能：取得精準的台灣時間 ---
def get_taiwan_time():
    return datetime.now(timezone.utc) + timedelta(hours=8)

# --- 功能：動態讀取歷史紀錄以產生不重複序號 ---
def get_next_order_id():
    tw_time = get_taiwan_time()
    today_str = tw_time.strftime("%Y%m%d")
    
    records_df = load_records()
    if records_df is not None and not records_df.empty:
        try:
            last_order = str(records_df.iloc[-1]["訂單序號"])
            if "-" in last_order:
                last_date, last_seq = last_order.split("-")
                if last_date == today_str:
                    return f"{today_str}-{int(last_seq) + 1:03d}"
        except Exception:
            pass 
            
    return f"{today_str}-001"

# 3. 讀取產品資料庫
@st.cache_data
def load_data():
    df = pd.read_csv('丞燕產品價格.csv', dtype={'貨號': str})
    
    # 處理「包裝」欄位，防呆機制
    if '包裝' not in df.columns:
        df['包裝'] = 1
    else:
        df['包裝'] = pd.to_numeric(df['包裝'], errors='coerce').fillna(1).astype(int)
        df['包裝'] = df['包裝'].clip(lower=1) # 確保最小為 1
        
    return df

df = load_data()

# --- 側邊欄：搜尋與過濾 ---
st.sidebar.header("🔍 產品篩選")
search_term = st.sidebar.text_input("搜尋品名或貨號", "")
all_categories = ["全部"] + sorted(df["類別"].unique().tolist())
selected_category = st.sidebar.selectbox("篩選類別", all_categories)

filtered_df = df.copy()
if search_term:
    filtered_df = filtered_df[
        filtered_df["品名"].str.contains(search_term, case=False, na=False) |
        filtered_df["貨號"].str.contains(search_term, na=False)
    ]
if selected_category != "全部":
    filtered_df = filtered_df[filtered_df["類別"] == selected_category]

# --- 主標題 ---
st.title("🌿 丞燕產品訂購系統")

# --- 右側框架：使用 Tabs 三分頁 ---
tab1, tab2, tab3 = st.tabs(["📝 訂單資訊與產品選購", "🛒 購物車明細", "📜 雲端紀錄查詢系統"])

# ==========================================
# Tab 1: 訂單資訊與產品選購
# ==========================================
with tab1:
    st.subheader("第一步：填寫基本資料")
    with st.container(border=True):
        col_name, col_id = st.columns([1, 1])
        with col_name:
            customer_name = st.text_input("👤 訂購人姓名", placeholder="請輸入姓名...")
        with col_id:
            order_id = get_next_order_id()
            st.write(f"🆔 當前訂單序號：`{order_id}`")

    st.divider()

    st.subheader("第二步：選購產品")
    st.caption(f"目前顯示 {len(filtered_df)} 項產品")
    
    if not filtered_df.empty:
        current_categories = filtered_df['類別'].unique()
        
        for i, category in enumerate(current_categories):
            st.markdown(f"#### 🏷️ -- {category} --")
            cat_df = filtered_df[filtered_df['類別'] == category]
            
            for _, row in cat_df.iterrows():
                pkg_count = int(row['包裝'])
                
                with st.expander(f"**{row['品名']}** (NT$ {row['含稅價 DPT']:,})", expanded=False):
                    col_info, col_action = st.columns([1.5, 1])
                    with col_info:
                        st.write(f"🔢 貨號: `{row['貨號']}`")
                        st.write(f"⭐ 積分: SV {row['積分額 SV']}")
                        if pkg_count > 1:
                            st.caption(f"📦 規格: 1 盒 {pkg_count} 包")
                    
                    with col_action:
                        if pkg_count > 1:
                            use_loose = st.toggle("🧩 散購模式", key=f"loose_mode_{row['貨號']}")
                        else:
                            use_loose = False
                        
                        if use_loose:
                            # 💡【修改點】：移除了一盒幾包的輸入框，直接使用背景的 pkg_count 進行運算
                            buy_pkgs = st.number_input("買幾包?", min_value=1, value=1, step=1, key=f"buy_{row['貨號']}")
                            qty = round(buy_pkgs / pkg_count, 4)
                            st.caption(f"💡 系統換算比例：{qty:g} 份")
                        else:
                            qty = st.number_input("購買數量", min_value=0.1, value=1.0, step=1.0, format="%.1f", key=f"qty_{row['貨號']}")

                        if st.button("➕ 加入購物車", key=f"btn_{row['貨號']}", width="stretch"):
                            item_id = row['貨號']
                            
                            if item_id not in st.session_state.cart or not isinstance(st.session_state.cart[item_id], dict):
                                st.session_state.cart[item_id] = {'qty': 0.0, 'is_loose': False, 'buy_pkgs': 0}
                            
                            if use_loose:
                                st.session_state.cart[item_id]['is_loose'] = True
                                st.session_state.cart[item_id]['buy_pkgs'] += buy_pkgs
                                qty_added = round(buy_pkgs / pkg_count, 4)
                                st.session_state.cart[item_id]['qty'] = round(st.session_state.cart[item_id]['qty'] + qty_added, 4)
                                st.success(f"✅ 已放入散購：{row['品名']} x {buy_pkgs} 包 ({qty_added:g} 份)")
                            else:
                                st.session_state.cart[item_id]['qty'] = round(st.session_state.cart[item_id]['qty'] + qty, 4)
                                st.session_state.cart[item_id]['buy_pkgs'] += int(qty * pkg_count)
                                st.success(f"✅ 已放入：{row['品名']} x {qty:g}")
            
            if i < len(current_categories) - 1:
                st.divider()
    else:
        st.info("沒有找到符合條件的產品。")

# ==========================================
# Tab 2: 單獨放置購物車內容
# ==========================================
with tab2:
    st.header("🛒 確認訂購內容")
    
    if 'saved_receipt' in st.session_state:
        st.success("✅ 訂單已成功寫入雲端紀錄！請點擊下方按鈕複製明細至 LINE：")
        st_copy_to_clipboard(
            st.session_state.saved_receipt, 
            before_copy_label="📋 點此複製剛儲存的訂單明細", 
            after_copy_label="✅ 已成功複製！"
        )
        if st.button("關閉此提示", width="stretch"):
            del st.session_state.saved_receipt
            st.rerun()
        st.divider()

    if not st.session_state.cart:
        if 'saved_receipt' not in st.session_state:
            st.info("目前購物車是空的，請先回到第一分頁選購。")
    else:
        cart_summary = []
        total_sv, total_dpt = 0.0, 0.0
        
        for item_id, item_data in list(st.session_state.cart.items()):
            if not isinstance(item_data, dict):
                item_data = {'qty': item_data, 'is_loose': False, 'buy_pkgs': 0}
                st.session_state.cart[item_id] = item_data
                
            qty = item_data['qty']
            is_loose = item_data.get('is_loose', False)
            buy_pkgs = item_data.get('buy_pkgs', 0)
            
            product = df[df['貨號'] == item_id].iloc[0]
            pkg_count = int(pd.to_numeric(product.get('包裝', 1), errors='coerce')) if not pd.isna(product.get('包裝', 1)) else 1
            if pkg_count <= 0: pkg_count = 1

            sub_sv = round(product['積分額 SV'] * qty, 1)
            sub_dpt = round(product['含稅價 DPT'] * qty, 1)
            total_sv += sub_sv
            total_dpt += sub_dpt
            
            cart_summary.append({
                "品名": product['品名'], 
                "數量": qty, 
                "SV": sub_sv, 
                "DPT": sub_dpt,
                "is_loose": is_loose,
                "buy_pkgs": buy_pkgs,
                "pkg_count": pkg_count
            })
            
            with st.container(border=True):
                cc1, cc2, cc3 = st.columns([3.5, 1, 1])
                with cc1:
                    st.markdown(f"**{product['品名']}**")
                    if is_loose and pkg_count > 1:
                        st.caption(f"數量: {qty:g} (散購: {buy_pkgs} 包) | 金額: NT$ {sub_dpt:,.1f} | 積分: SV {sub_sv:,.1f}")
                    else:
                        st.caption(f"數量: {qty:g} | 金額: NT$ {sub_dpt:,.1f} | 積分: SV {sub_sv:,.1f}")
                        
                with cc2:
                    if st.button("✏️ 修改", key=f"edit_{item_id}", width="stretch"):
                        st.session_state.edit_mode[item_id] = not st.session_state.edit_mode.get(item_id, False)
                        st.rerun()
                with cc3:
                    if st.button("🗑️ 刪除", key=f"del_{item_id}", width="stretch"):
                        del st.session_state.cart[item_id]
                        if item_id in st.session_state.edit_mode:
                            del st.session_state.edit_mode[item_id]
                        st.rerun()
                
                if st.session_state.edit_mode.get(item_id, False):
                    st.divider()
                    ec1, ec2 = st.columns([3, 1])
                    with ec1:
                        if pkg_count > 1:
                            edit_use_loose = st.toggle("🧩 使用散購模式修改", value=is_loose, key=f"edit_loose_{item_id}")
                            if edit_use_loose:
                                new_buy_pkgs = st.number_input("重新設定散購數量(包)：", min_value=1, value=int(buy_pkgs) if buy_pkgs > 0 else 1, step=1, key=f"newlooseqty_{item_id}")
                            else:
                                new_qty = st.number_input("重新設定數量：", min_value=0.0001, value=float(qty), step=1.0, key=f"newqty_{item_id}")
                        else:
                            edit_use_loose = False
                            new_qty = st.number_input("重新設定數量：", min_value=0.0001, value=float(qty), step=1.0, key=f"newqty_{item_id}")
                    with ec2:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("💾 確認", key=f"save_{item_id}", width="stretch", type="primary"):
                            if edit_use_loose:
                                st.session_state.cart[item_id]['is_loose'] = True
                                st.session_state.cart[item_id]['buy_pkgs'] = new_buy_pkgs
                                st.session_state.cart[item_id]['qty'] = round(new_buy_pkgs / pkg_count, 4)
                            else:
                                st.session_state.cart[item_id]['is_loose'] = False
                                st.session_state.cart[item_id]['qty'] = round(new_qty, 4)
                                st.session_state.cart[item_id]['buy_pkgs'] = int(new_qty * pkg_count)
                            
                            st.session_state.edit_mode[item_id] = False
                            st.rerun()
        
        total_dpt = round(total_dpt, 1)
        total_sv = round(total_sv, 1)
        
        st.divider()
        st.metric("總計金額 (DPT)", f"NT$ {total_dpt:,.1f}")
        st.metric("總計積分 (SV)", f"SV {total_sv:,.1f}")

        st.write("🎁 **優惠計算選項**")
        promo_choice = st.radio(
            "請選擇適用的方案：",
            ["不使用優惠", "使用優惠方案 (SV - 4500) x 10%", "使用優惠方案 SV x 10%"],
            index=0
        )

        promo_info = ""
        final_price = total_dpt

        if " (SV - 4500) x 10%" in promo_choice:
            calc_sv = max(0.0, round((total_sv - 4500) * 0.1, 1))
            final_price = round(total_dpt - calc_sv, 1)
            promo_info += f"\n💡 【優惠方案】\n分數計算: (SV {total_sv:,.1f} - 4500) x 10% = {calc_sv:,.1f} 分\n優惠價格: NT$ {total_dpt:,.1f} - {calc_sv:,.1f} = NT$ {final_price:,.1f}\n"

        elif " SV x 10%" in promo_choice:
            calc_sv_2 = round(total_sv * 0.1, 1)
            final_price = round(total_dpt - calc_sv_2, 1)
            promo_info += f"\n💡 【優惠方案】\n分數計算: SV {total_sv:,.1f} x 10% = {calc_sv_2:,.1f} 分\n優惠價格: NT$ {total_dpt:,.1f} - {calc_sv_2:,.1f} = NT$ {final_price:,.1f}\n"

        if promo_info:
            st.success(promo_info)

        tw_time = get_taiwan_time()
        order_time_str = tw_time.strftime('%Y-%m-%d %H:%M')
        
        copy_text = f"📦 【丞燕產品訂購單】\n👤 訂購人：{customer_name if customer_name else '未填寫'}\n🆔 序號：{order_id}\n📅 日期：{order_time_str}\n"
        copy_text += "="*22 + "\n"
        items_str_list = []
        
        for item in cart_summary:
            if item['is_loose'] and item['pkg_count'] > 1:
                copy_text += f"• {item['品名']} x {item['數量']:g} -- 散購：{item['buy_pkgs']} 包  (NT$ {item['DPT']:,.1f} / SV {item['SV']:,.1f})\n"
                items_str_list.append(f"{item['品名']}x{item['數量']:g}(散購{item['buy_pkgs']}包)")
            else:
                copy_text += f"• {item['品名']} x {item['數量']:g}  (NT$ {item['DPT']:,.1f} / SV {item['SV']:,.1f})\n"
                items_str_list.append(f"{item['品名']}x{item['數量']:g}")
                
        copy_text += "="*22 + "\n"
        copy_text += f"💰 總計金額：NT$ {total_dpt:,.1f}\n⭐ 總計積分：SV {total_sv:,.1f}\n"
        if promo_info:
            copy_text += promo_info + f"🔥 最終應付金額：NT$ {final_price:,.1f}\n"

        st_copy_to_clipboard(copy_text, before_copy_label="📋 點擊複製訂單明細", after_copy_label="✅ 已成功複製！")
        
        # --- 儲存至雲端資料庫按鈕 ---
        if st.button("💾 儲存訂單紀錄並清空購物車", width="stretch", type="primary"):
            ws = get_gspread_client()
            if ws:
                promo_record = promo_info.replace('\n', ' ').strip() if promo_info else "無"
                
                new_row = [
                    str(order_id),
                    str(order_time_str),
                    str(customer_name) if customer_name else "未填寫",
                    ", ".join(items_str_list), 
                    float(total_dpt),        
                    float(total_sv),         
                    str(promo_record),
                    float(final_price)       
                ]
                
                try:
                    header_vals = ws.row_values(1)
                    if not header_vals:
                        ws.append_rows([RECORD_COLUMNS, new_row])
                    else:
                        ws.append_row(new_row)
                    
                    time.sleep(1.5)
                    
                    st.session_state.cart = {}
                    st.session_state.edit_mode = {}
                    st.session_state.saved_receipt = copy_text
                    st.rerun()
                except Exception as e:
                    st.error(f"寫入過程發生錯誤: {e}")
            else:
                st.error("無法連接至 Google 雲端硬碟，儲存失敗。")

        if st.button("🧹 清空購物車", width="stretch"):
            st.session_state.cart = {}
            st.session_state.edit_mode = {}
            st.rerun()

# ==========================================
# Tab 3: 雲端訂購紀錄查詢系統
# ==========================================
with tab3:
    st.header("📜 歷史雲端紀錄管理")
    
    records_df = load_records()
    
    if records_df is not None:
        if records_df.empty:
             st.info("雲端試算表中尚無任何訂購紀錄。")
        else:
            mode = st.radio("請選擇操作模式：", ["🔍 查詢紀錄", "✏️ 編輯或刪除紀錄"], horizontal=True)
            
            if mode == "🔍 查詢紀錄":
                st.info("💡 提示：輸入關鍵字即可快速篩選訂單。")
                search_query = st.text_input("輸入「訂購人姓名」或「訂單序號」搜尋：")
                
                if search_query:
                    mask = records_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                    display_df = records_df[mask]
                    st.write(f"找到 {len(display_df)} 筆符合的紀錄：")
                    st.dataframe(display_df, width="stretch", hide_index=True)
                else:
                    st.dataframe(records_df, width="stretch", hide_index=True)
                    
            elif mode == "✏️ 編輯或刪除紀錄":
                st.warning("⚠️ **編輯模式啟用**：您可以直接雙擊表格修改，或勾選刪除。完成後務必點擊下方儲存按鈕同步至雲端。")
                
                edited_df = st.data_editor(records_df, num_rows="dynamic", width="stretch")
                
                if st.button("💾 同步更新至 Google 雲端", type="primary"):
                    ws = get_gspread_client()
                    if ws:
                        edited_df = edited_df.fillna("") 
                        ws.clear()
                        ws.update(values=[edited_df.columns.values.tolist()] + edited_df.values.tolist(), range_name='A1')
                        
                        time.sleep(1.5) 
                        st.success("✅ 雲端紀錄已成功同步更新！")
                        st.rerun()
                    else:
                        st.error("同步失敗，無法連接至 Google 雲端硬碟。")
    else:
        st.warning("尚未連線至 Google 雲端硬碟。請確認您的 Secrets 設定是否正確。")

# --- CSS 視覺調整 ---
st.markdown("""
<style>
    .stButton>button { border-radius: 5px; }
</style>
""", unsafe_allow_html=True)
