# app.py — Full Water Loop App (complete)
# Features:
# - user register/login/profile (users.csv)
# - group_id for 30-min grouping; each activity is one row (water_usage.csv)
# - grouped summary + expand to edit/delete activities
# - charts: activity bar, week/month totals, cumulative, hourly heatmap
# - import/export CSV, admin panel, leaderboard, pet/gamification (points)
# - theme CSS customisable in set_background()
#
# Note: no background scheduling; reminders are shown when user opens app and current time
# is within +/- 5 minutes of a reminder time registered in users.csv.

import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import uuid
from datetime import datetime, timedelta, time
import io
import os

# -----------------------------
# Config — change these if needed
# -----------------------------
USERS_FILE = "users.csv"
DATA_FILE = "water_usage.csv"
THEME = {
    "bg_gradient": ("#eff6ff", "#dbeafe"),
    "primary": "#2563EB",
    "text": "#0f172a"
}
# Pet levels config (points thresholds)
PET_LEVELS = [
    (0, "Seedling", "🌱"),
    (50, "Sprout", "🌿"),
    (150, "Young Tree", "🌳"),
    (350, "Mature Tree", "🌲"),
    (700, "Forest Guardian", "🌳🌟")
]
# -----------------------------

# -----------------------------
# Helpers: file load/save
# -----------------------------
def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=[
            "username","password","full_name","role","house_type","location","address",
            "daily_limit","entries_per_day","reminder_times","points","pet_state"
        ])
        df.to_csv(USERS_FILE, index=False)

def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "username","house_type","location","address","date","time","activity","amount","note","group_id"
        ])
        df.to_csv(DATA_FILE, index=False)

def load_users():
    ensure_users_file()
    df = pd.read_csv(USERS_FILE, dtype=str).fillna("")
    # types
    if "points" not in df.columns:
        df["points"] = "0"
    if "pet_state" not in df.columns:
        df["pet_state"] = ""
    df["points"] = df["points"].astype(float)
    return df

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def load_data():
    ensure_data_file()
    df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    # ensure columns
    for c in ["amount"]:
        if c in df.columns:
            try:
                df[c] = df[c].astype(float)
            except:
                df[c] = 0.0
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# -----------------------------
# UI theme CSS
# -----------------------------
def set_background():
    a,b = THEME["bg_gradient"]
    primary = THEME["primary"]
    text = THEME["text"]
    st.markdown(f"""
    <style>
    .stApp {{ background: linear-gradient(120deg, {a}, {b}); color: {text}; }}
    .stButton>button {{ background-color: {primary}; color: white; border-radius: 10px; padding: 0.5em 1em; font-weight:600; }}
    .css-1aumxhk .st-cb {{ color: {text}; }}
    .stDataFrame table td, .stDataFrame table th {{ color: {text}; }}
    </style>
    """, unsafe_allow_html=True)

# -----------------------------
# Utilities
# -----------------------------
def gen_group_id():
    return str(uuid.uuid4())

def ensure_group_ids(df):
    # Backfill group_id if missing per username using 30-min rule
    if df.empty: return df
    if 'group_id' not in df.columns or df['group_id'].isnull().all() or (df['group_id']=="" ).all():
        df = df.sort_values(['username','date','time']).reset_index(drop=True)
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + " " + df['time'].astype(str), errors='coerce')
        df['group_id'] = ""
        for user in df['username'].unique():
            mask = df['username']==user
            idxs = df[mask].index.tolist()
            last_dt = None
            cur_group = None
            for i in idxs:
                dt = df.at[i,'datetime']
                if pd.isna(dt) or last_dt is None or (dt - last_dt) > timedelta(minutes=30):
                    cur_group = gen_group_id()
                df.at[i,'group_id'] = cur_group
                last_dt = dt
        df = df.drop(columns=['datetime'])
    return df

def pet_level_for_points(points):
    # Return (level_name, emoji)
    lvl_name, emo = PET_LEVELS[0][1], PET_LEVELS[0][2]
    for threshold, name, emoji in PET_LEVELS:
        if points >= threshold:
            lvl_name, emo = name, emoji
    return lvl_name, emo

# -----------------------------
# Auth: register/login/logout/profile
# -----------------------------
def register_user(users_df):
    st.subheader("Tạo tài khoản mới")
    col1,col2 = st.columns(2)
    with col1:
        username = st.text_input("Tên đăng nhập (username)")
        password = st.text_input("Mật khẩu", type="password")
    with col2:
        full_name = st.text_input("Họ & tên")
        role = st.selectbox("Vai trò", ["user","admin"])
    # profile defaults
    house_type = st.selectbox("Loại hộ", ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"])
    location = st.selectbox("Tỉnh/Thành", PROVINCES)
    address = st.text_input("Địa chỉ (số nhà, đường...)")
    daily_limit = st.number_input("Ngưỡng nước hàng ngày (Lít)", min_value=50, value=200)
    entries_day = st.slider("Số lần nhập/ngày", 1, 10, 3)
    reminders = st.multiselect("Giờ nhắc nhở (tối đa 5)", options=[f"{h:02d}:00" for h in range(24)], default=["08:00","12:00","18:00"])
    if len(reminders)>5: reminders = reminders[:5]
    if st.button("Đăng ký"):
        if username.strip()=="" or password.strip()=="":
            st.error("Vui lòng nhập username và password.")
            return users_df
        if username in users_df['username'].values:
            st.error("Tên đăng nhập đã tồn tại.")
            return users_df
        new = {
            "username": username, "password": password, "full_name": full_name,
            "role": role, "house_type": house_type, "location": location, "address": address,
            "daily_limit": daily_limit, "entries_per_day": entries_day, "reminder_times": ",".join(reminders),
            "points": 0.0, "pet_state": ""
        }
        users_df = pd.concat([users_df, pd.DataFrame([new])], ignore_index=True)
        save_users(users_df)
        st.success("Đăng ký thành công — hãy đăng nhập.")
    return users_df

def login_user(users_df):
    st.subheader("Đăng nhập")
    col1,col2 = st.columns(2)
    with col1:
        username = st.text_input("Tên đăng nhập (username)")
    with col2:
        password = st.text_input("Mật khẩu", type="password")
    if st.button("Đăng nhập"):
        if username.strip()=="" or password.strip()=="":
            st.error("Nhập đủ thông tin.")
            return None
        row = users_df[(users_df['username']==username) & (users_df['password']==password)]
        if row.empty:
            st.error("Sai tên đăng nhập hoặc mật khẩu.")
            return None
        st.success(f"Chào {row.iloc[0].get('full_name') or username}!")
        return username
    return None

def edit_profile(users_df, current_user):
    st.subheader("Chỉnh sửa hồ sơ")
    user_row = users_df[users_df['username']==current_user].iloc[0]
    col1,col2 = st.columns(2)
    with col1:
        full = st.text_input("Họ & tên", value=user_row.get('full_name',''))
        house_type = st.selectbox("Loại hộ", ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"], index=0)
        # try to set index to existing house_type if present
        try:
            house_type = st.selectbox("Loại hộ", ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"], index=["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"].index(user_row.get('house_type','Chung cư')))
        except:
            house_type = st.selectbox("Loại hộ", ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"])
    with col2:
        location = st.selectbox("Tỉnh/Thành", PROVINCES, index=(PROVINCES.index(user_row.get('location')) if user_row.get('location') in PROVINCES else 0))
        address = st.text_input("Địa chỉ", value=user_row.get('address',''))
    daily_limit = st.number_input("Ngưỡng nước hàng ngày (Lít)", min_value=50, value=float(user_row.get('daily_limit',200)))
    entries_day = st.slider("Số lần nhập/ngày", 1, 10, int(user_row.get('entries_per_day') or 3))
    reminders = st.multiselect("Giờ nhắc nhở (tối đa 5)", options=[f"{h:02d}:00" for h in range(24)],
                               default=(user_row.get('reminder_times','').split(",") if user_row.get('reminder_times') else ["08:00","12:00","18:00"]))
    if len(reminders)>5: reminders=reminders[:5]
    if st.button("Lưu hồ sơ"):
        users_df.loc[users_df['username']==current_user, ['full_name','house_type','location','address','daily_limit','entries_per_day','reminder_times']] = [
            full, house_type, location, address, daily_limit, entries_day, ",".join(reminders)
        ]
        save_users(users_df)
        st.success("Đã lưu hồ sơ.")
    if st.button("Đổi mật khẩu"):
        newpw = st.text_input("Mật khẩu mới", type="password", key="newpw")
        if newpw:
            users_df.loc[users_df['username']==current_user, 'password'] = newpw
            save_users(users_df)
            st.success("Đổi mật khẩu thành công.")
    return users_df

# -----------------------------
# Data operations & UI
# -----------------------------
def add_activity(data_df, username, house_type, location, addr_input, activity, amount, note_text, date_input):
    # create new row for activity, assign group_id by looking up last entry for user within 30 min
    now = datetime.now()
    # ensure types
    if data_df.empty:
        data_df = pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount","note","group_id"])
    # find last for user
    user_rows = data_df[data_df['username']==username]
    group_id = gen_group_id()
    if not user_rows.empty:
        # parse last datetime
        last_row = user_rows.sort_values(['date','time']).iloc[-1]
        try:
            last_dt = datetime.strptime(f"{last_row['date']} {last_row['time']}", "%Y-%m-%d %H:%M:%S")
        except:
            last_dt = None
        if last_dt and (now - last_dt) <= timedelta(minutes=30):
            group_id = last_row.get('group_id') or gen_group_id()
    row = {
        "username": username, "house_type": house_type, "location": location, "address": addr_input,
        "date": date_input.strftime("%Y-%m-%d") if isinstance(date_input, datetime) else str(date_input),
        "time": now.strftime("%H:%M:%S"),
        "activity": activity, "amount": float(amount), "note": note_text if note_text else "", "group_id": group_id
    }
    data_df = pd.concat([data_df, pd.DataFrame([row])], ignore_index=True)
    save_data(data_df)
    return data_df, group_id

def grouped_summary_for_user(data_df, username):
    d = data_df[data_df['username']==username].copy()
    if d.empty:
        return pd.DataFrame()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    grouped = d.groupby('group_id').agg({
        'date':'min','time':'min','address':lambda x: x.dropna().astype(str).iloc[0] if len(x.dropna())>0 else "",
        'amount':'sum','activity': lambda x: ", ".join(x.astype(str))
    }).reset_index().rename(columns={'amount':'total_amount','activity':'activities'}).sort_values(['date','time'], ascending=False)
    return grouped

def show_grouped_editor(data_df, username):
    st.subheader("📒 Nhật ký (tóm tắt theo nhóm)")
    grouped = grouped_summary_for_user(data_df, username)
    if grouped.empty:
        st.info("Chưa có dữ liệu.")
        return data_df
    st.dataframe(grouped[['group_id','date','time','address','total_amount','activities']].rename(columns={'total_amount':'Tổng Lít','activities':'Hoạt động'}), use_container_width=True)
    sel = st.selectbox("Chọn nhóm để xem/ sửa chi tiết:", options=grouped['group_id'])
    if sel:
        st.write(f"### Chi tiết nhóm: {sel}")
        details = data_df[(data_df['username']==username) & (data_df['group_id']==sel)].sort_values(['date','time'], ascending=False).reset_index()
        # 'index' column is original index in data_df before reset_index
        display = details[['index','date','time','activity','amount','note','address']].rename(columns={'index':'_orig_index'})
        orig_indices = display['_orig_index'].tolist()
        editor_df = display.drop(columns=['_orig_index']).reset_index(drop=True)
        edited = st.data_editor(editor_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 Lưu thay đổi chi tiết nhóm"):
            for pos, orig in enumerate(orig_indices):
                row = edited.iloc[pos]
                data_df.at[orig, 'date'] = row['date']
                data_df.at[orig, 'time'] = row['time']
                data_df.at[orig, 'activity'] = row['activity']
                try:
                    data_df.at[orig, 'amount'] = float(row['amount'])
                except:
                    pass
                data_df.at[orig, 'note'] = row.get('note', data_df.at[orig,'note'])
                data_df.at[orig, 'address'] = row.get('address', data_df.at[orig,'address'])
            save_data(data_df)
            st.success("Đã lưu thay đổi.")
            st.experimental_rerun()
        # delete items
        choices = [f"{i+1}. {details.loc[i,'activity']} ({details.loc[i,'amount']} L) - {details.loc[i,'date']} {details.loc[i,'time']}" for i in range(len(details))]
        to_delete = st.multiselect("Chọn hoạt động để xóa:", options=list(range(len(details))), format_func=lambda i: choices[i])
        if st.button("❌ Xóa hoạt động đã chọn"):
            if to_delete:
                idxs = [orig_indices[pos] for pos in to_delete]
                data_df = data_df.drop(idxs).reset_index(drop=True)
                save_data(data_df)
                st.success("Đã xóa hoạt động.")
                st.experimental_rerun()
        if st.button("🗑️ Xóa toàn bộ nhóm này"):
            data_df = data_df[data_df['group_id'] != sel].reset_index(drop=True)
            save_data(data_df)
            st.success("Đã xóa nhóm.")
            st.experimental_rerun()
    return data_df

# -----------------------------
# Charts
# -----------------------------
def plot_activity_bar(data_df):
    if data_df.empty:
        st.info("Chưa có dữ liệu để vẽ biểu đồ hoạt động.")
        return
    exploded = explode_allocate(data_df)
    agg = exploded.groupby('activity_list')['alloc_amount'].sum().reset_index().rename(columns={'activity_list':'activity','alloc_amount':'total_lit'}).sort_values('total_lit', ascending=False)
    chart = alt.Chart(agg).mark_bar().encode(
        x=alt.X('activity:N', sort='-y', title='Hoạt động'),
        y=alt.Y('total_lit:Q', title='Tổng Lít'),
        tooltip=['activity','total_lit'],
        color='activity:N'
    ).properties(height=320)
    st.altair_chart(chart, use_container_width=True)

def explode_allocate(df):
    # similar to earlier: if any row has comma-separated activities, allocate equally
    if df.empty:
        return df
    tmp = df.copy()
    tmp['activity_list'] = tmp['activity'].fillna('Không xác định').astype(str).str.split(', ')
    tmp = tmp.explode('activity_list').reset_index(drop=True)
    counts = tmp.groupby(tmp.index)['activity_list'].transform('count')
    tmp['alloc_amount'] = tmp['amount'].astype(float) / counts.replace(0,1)
    return tmp

def plot_week_month_totals(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + " " + df['time'].astype(str), errors='coerce')
    df['week'] = df['datetime'].dt.isocalendar().week
    df['year'] = df['datetime'].dt.isocalendar().year
    week_sum = df.groupby(['year','week'])['amount'].sum().reset_index()
    week_sum['label'] = week_sum['year'].astype(str) + "-W" + week_sum['week'].astype(str)
    chart = alt.Chart(week_sum).mark_line(point=True).encode(x='label:N', y='amount:Q', tooltip=['label','amount']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)
    df['month'] = df['datetime'].dt.to_period('M').astype(str)
    month_sum = df.groupby('month')['amount'].sum().reset_index()
    chart2 = alt.Chart(month_sum).mark_bar().encode(x='month:N', y='amount:Q', tooltip=['month','amount']).properties(height=240)
    st.altair_chart(chart2, use_container_width=True)

def plot_cumulative(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + " " + df['time'].astype(str), errors='coerce')
    daily = df.groupby(df['datetime'].dt.date)['amount'].sum().reset_index().rename(columns={'datetime':'date'})
    daily['cum'] = daily['amount'].cumsum()
    chart = alt.Chart(daily).mark_line(point=True).encode(x='datetime:T', y='cum:Q', tooltip=['datetime','cum']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)

def plot_hour_heatmap(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + " " + df['time'].astype(str), errors='coerce')
    df['hour'] = df['datetime'].dt.hour
    heat = df.groupby('hour')['amount'].sum().reset_index()
    chart = alt.Chart(heat).mark_bar().encode(x='hour:O', y='amount:Q', tooltip=['hour','amount']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)

# -----------------------------
# Admin panel
# -----------------------------
def admin_panel(users_df, data_df):
    st.header("⚙️ Admin panel")
    # users table
    st.subheader("Người dùng")
    st.dataframe(users_df[['username','full_name','role','location','address','daily_limit','points']].sort_values('username'), use_container_width=True)
    # download users
    st.download_button("Tải users.csv", users_df.to_csv(index=False), "users.csv", "text/csv")
    # upload sample data
    st.subheader("Quản lý dữ liệu")
    uploaded = st.file_uploader("Import CSV water_usage (thay thế dữ liệu hiện có)", type=['csv'])
    if uploaded is not None:
        try:
            df_new = pd.read_csv(uploaded)
            save_data(df_new)
            st.success("Đã import dữ liệu (ghi đè).")
        except Exception as e:
            st.error("Import thất bại: " + str(e))
    if st.button("Xóa toàn bộ dữ liệu water_usage"):
        save_data(pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount","note","group_id"]))
        st.success("Đã xóa dữ liệu.")
    # leaderboards
    st.subheader("Leaderboard (tiết kiệm điểm)")
    # compute points: lower usage relative to limit yields more points for that day
    scores = []
    for _, row in users_df.iterrows():
        u = row['username']
        limit = float(row.get('daily_limit',200))
        user_df = data_df[data_df['username']==u].copy()
        if user_df.empty:
            continue
        user_df['datetime'] = pd.to_datetime(user_df['date'].astype(str) + " " + user_df['time'].astype(str), errors='coerce')
        today = datetime.now().date()
        today_sum = user_df[user_df['datetime'].dt.date==today]['amount'].sum()
        # simple scoring: points = max(0, limit - today_sum)
        score = max(0, limit - today_sum)
        scores.append({"username":u,"score":score})
    if scores:
        s_df = pd.DataFrame(scores).sort_values('score', ascending=False).reset_index(drop=True)
        st.dataframe(s_df.head(10), use_container_width=True)
    else:
        st.info("Chưa đủ dữ liệu để leaderboard.")

# -----------------------------
# Full app: Tabs and flow
# -----------------------------
# Provinces list used earlier
PROVINCES = [
    "Tỉnh Tuyên Quang","Tỉnh Lào Cai","Tỉnh Thái Nguyên","Tỉnh Phú Thọ","Tỉnh Bắc Ninh",
    "Tỉnh Hưng Yên","Thành phố Hải Phòng","Tỉnh Ninh Bình","Tỉnh Quảng Trị","Thành phố Đà Nẵng",
    "Tỉnh Quảng Ngãi","Tỉnh Gia Lai","Tỉnh Khánh Hoà","Tỉnh Lâm Đồng","Tỉnh Đắk Lắk",
    "Thành phố Hồ Chí Minh","Tỉnh Đồng Nai","Tỉnh Tây Ninh","Thành phố Cần Thơ","Tỉnh Vĩnh Long",
    "Tỉnh Đồng Tháp","Tỉnh Cà Mau","Tỉnh An Giang","Thành phố Hà Nội","Thành phố Huế",
    "Tỉnh Lai Châu","Tỉnh Điện Biên","Tỉnh Sơn La","Tỉnh Lạng Sơn","Tỉnh Quảng Ninh",
    "Tỉnh Thanh Hoá","Tỉnh Nghệ An","Tỉnh Hà Tĩnh","Tỉnh Cao Bằng"
]

def main():
    st.set_page_config(page_title="Water Loop App (Full)", page_icon="💧", layout="wide")
    set_background()
    # load
    users_df = load_users()
    data_df = load_data()
    data_df = ensure_group_ids(data_df)

    st.sidebar.title("WATER LOOP")
    if 'username' not in st.session_state:
        st.session_state['username'] = None

    # Auth UI in sidebar
    if st.session_state['username'] is None:
        auth_mode = st.sidebar.radio("Bạn muốn:", ["Đăng nhập","Đăng ký"])
        if auth_mode == "Đăng ký":
            users_df = register_user(users_df)
        else:
            user = login_user(users_df)
            if user:
                st.session_state['username'] = user
    else:
        st.sidebar.success(f"Đã đăng nhập: {st.session_state['username']}")
        if st.sidebar.button("🚪 Đăng xuất"):
            st.session_state['username'] = None
            st.experimental_rerun()

    # If logged in, show main tabs
    if st.session_state['username']:
        username = st.session_state['username']
        # find user row
        user_row = users_df[users_df['username']==username].iloc[0] if username in users_df['username'].values else None
        # create tabs
        tabs = st.tabs(["Nhập dữ liệu","Phân tích","Nhật ký","Hồ sơ","Admin (nếu có)"])
        # TAB 1: Input
        with tabs[0]:
            st.header("📝 Ghi nhận hoạt động")
            left, right = st.columns([3,1])
            with left:
                activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys())+["➕ Khác"])
                if activity=="➕ Khác":
                    activity = st.text_input("Nhập tên hoạt động:", "")
                amount = st.number_input("Lượng nước (Lít)", min_value=1, value=int(DEFAULT_ACTIVITIES.get(activity,10)))
                date_input = st.date_input("📅 Ngày", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())
                addr_input = st.text_input("🏠 Địa chỉ", value=user_row.get('address') if user_row is not None else "")
                note = st.text_area("Ghi chú (tuỳ chọn):", height=80)
                if st.button("💾 Lưu hoạt động"):
                    data_df, group_id = add_activity(data_df, username, user_row.get('house_type','') if user_row is not None else '', user_row.get('location','') if user_row is not None else '', addr_input, activity, amount, note, date_input)
                    st.success("Đã lưu!")
                    # award small points for entering data + bonus if amount < 0.8*limit
                    try:
                        limit = float(user_row.get('daily_limit',200))
                        add_pts = 1
                        # if saving low usage relative to default, bonus
                        if amount < 0.8*limit:
                            add_pts += 2
                        users_df.loc[users_df['username']==username, 'points'] = users_df.loc[users_df['username']==username, 'points'].astype(float) + add_pts
                        save_users(users_df)
                    except:
                        pass
                    st.experimental_rerun()
            with right:
                st.subheader("Tóm tắt nhanh hôm nay")
                udata = data_df[data_df['username']==username].copy()
                if not udata.empty:
                    udata['dt'] = pd.to_datetime(udata['date'].astype(str) + " " + udata['time'].astype(str), errors='coerce')
                    today_sum = udata[udata['dt'].dt.date==datetime.now().date()]['amount'].sum()
                    st.metric("Tổng (L) hôm nay", f"{int(today_sum)} L")
                    st.write("Điểm hiện có:", int(users_df.loc[users_df['username']==username,'points'].iloc[0]))
                    lvl, emo = pet_level_for_points(int(users_df.loc[users_df['username']==username,'points'].iloc[0]))
                    st.write(f"Pet: {emo} — {lvl}")
                else:
                    st.write("Chưa có dữ liệu")
        # TAB 2: Analysis
        with tabs[1]:
            st.header("📊 Phân tích")
            # user filter control — admin may view others
            all_users = data_df['username'].unique().tolist()
            default_sel = username
            sel_user = st.selectbox("Xem dữ liệu của:", options=all_users if len(all_users)>0 else [username], index=(all_users.index(default_sel) if default_sel in all_users else 0))
            df_user = data_df[data_df['username']==sel_user].copy()
            if df_user.empty:
                st.info("Người dùng này chưa có dữ liệu.")
            else:
                # filters
                addrs = df_user['address'].fillna('').unique().tolist()
                addr_sel = st.multiselect("Địa chỉ", options=addrs, default=addrs)
                df_user = df_user[df_user['address'].isin(addr_sel)]
                # charts
                st.subheader("Biểu đồ theo hoạt động")
                exploded = explode_allocate(df_user)
                agg = exploded.groupby('activity_list')['alloc_amount'].sum().reset_index().rename(columns={'activity_list':'activity','alloc_amount':'total_lit'}).sort_values('total_lit', ascending=False)
                c1, c2 = st.columns(2)
                with c1:
                    chart = alt.Chart(agg).mark_bar().encode(x=alt.X('activity:N',sort='-y'), y='total_lit:Q', tooltip=['activity','total_lit'], color='activity:N').properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                with c2:
                    plot_hour_heatmap(df_user)
                st.markdown("---")
                st.subheader("Tổng theo Tuần / Tháng")
                plot_week_month_totals(df_user)
                st.markdown("---")
                st.subheader("Tích lũy")
                plot_cumulative(df_user)
                st.markdown("---")
                st.download_button("Tải CSV phân tích", df_user.to_csv(index=False), f"{sel_user}_water_usage.csv", "text/csv")
        # TAB 3: Log
        with tabs[2]:
            st.header("📚 Nhật ký & chỉnh sửa")
            data_df = show_grouped_editor(data_df, username)
        # TAB 4: Profile
        with tabs[3]:
            st.header("👤 Hồ sơ của bạn")
            users_df = edit_profile(users_df, username)
        # TAB 5: Admin
        with tabs[4]:
            if user_row is not None and user_row.get('role','user') == 'admin':
                admin_panel(users_df, data_df)
            else:
                st.info("Bạn không phải admin. Yêu cầu admin đăng nhập để xem trang này.")
    else:
        st.info("Vui lòng đăng nhập hoặc đăng ký (ở sidebar) để tiếp tục.")

# Run
if __name__ == "__main__":
    main()
