# app.py - Full Water Loop App (fixed DEFAULT_ACTIVITIES and complete)
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import uuid
from datetime import datetime, timedelta
import os

# -----------------------------
# Config / Constants
# -----------------------------
USERS_FILE = "users.csv"
DATA_FILE = "water_usage.csv"

THEME = {
    "bg_gradient": ("#eff6ff", "#dbeafe"),
    "primary": "#2563EB",
    "text": "#0f172a"
}

# DEFAULT activities (must be defined before UI uses it)
DEFAULT_ACTIVITIES = {
    "🚿 Tắm": 50,
    "🧺 Giặt quần áo": 70,
    "🍳 Nấu ăn": 20,
    "🌱 Tưới cây": 15,
    "🧹 Lau nhà": 25,
    "🛵 Rửa xe máy": 40,
    "🚗 Rửa ô tô": 150,
    "🚲 Rửa xe đạp": 10
}

PROVINCES = [
    "Tỉnh Tuyên Quang","Tỉnh Lào Cai","Tỉnh Thái Nguyên","Tỉnh Phú Thọ","Tỉnh Bắc Ninh",
    "Tỉnh Hưng Yên","Thành phố Hải Phòng","Tỉnh Ninh Bình","Tỉnh Quảng Trị","Thành phố Đà Nẵng",
    "Tỉnh Quảng Ngãi","Tỉnh Gia Lai","Tỉnh Khánh Hoà","Tỉnh Lâm Đồng","Tỉnh Đắk Lắk",
    "Thành phố Hồ Chí Minh","Tỉnh Đồng Nai","Tỉnh Tây Ninh","Thành phố Cần Thơ","Tỉnh Vĩnh Long",
    "Tỉnh Đồng Tháp","Tỉnh Cà Mau","Tỉnh An Giang","Thành phố Hà Nội","Thành phố Huế",
    "Tỉnh Lai Châu","Tỉnh Điện Biên","Tỉnh Sơn La","Tỉnh Lạng Sơn","Tỉnh Quảng Ninh",
    "Tỉnh Thanh Hoá","Tỉnh Nghệ An","Tỉnh Hà Tĩnh","Tỉnh Cao Bằng"
]

# Pet levels config (points thresholds)
PET_LEVELS = [
    (0, "Seedling", "🌱"),
    (50, "Sprout", "🌿"),
    (150, "Young Tree", "🌳"),
    (350, "Mature Tree", "🌲"),
    (700, "Forest Guardian", "🌳🌟"),
]

# -----------------------------
# File utilities
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
    if "points" not in df.columns:
        df["points"] = 0.0
    else:
        # coerce numeric
        try:
            df["points"] = df["points"].astype(float)
        except:
            df["points"] = 0.0
    if "pet_state" not in df.columns:
        df["pet_state"] = ""
    return df

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def load_data():
    ensure_data_file()
    df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    # ensure amount numeric
    if "amount" in df.columns:
        try:
            df["amount"] = df["amount"].astype(float)
        except:
            df["amount"] = df["amount"].replace("", 0).astype(float)
    else:
        df["amount"] = 0.0
    # ensure group_id exists
    if "group_id" not in df.columns:
        df["group_id"] = ""
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# -----------------------------
# Theme CSS
# -----------------------------
def set_background():
    a,b = THEME["bg_gradient"]
    primary = THEME["primary"]
    text = THEME["text"]
    st.markdown(f"""
    <style>
    .stApp {{ background: linear-gradient(120deg, {a}, {b}); color: {text}; }}
    .stButton>button {{ background-color: {primary}; color: white; border-radius: 10px; padding: 0.5em 1em; font-weight:600; }}
    .stDataFrame table td, .stDataFrame table th {{ color: {text}; }}
    </style>
    """, unsafe_allow_html=True)

# -----------------------------
# Utilities
# -----------------------------
def gen_group_id():
    return str(uuid.uuid4())

def pet_level_for_points(points):
    lvl_name, emoji = PET_LEVELS[0][1], PET_LEVELS[0][2]
    for threshold, name, emo in PET_LEVELS:
        if points >= threshold:
            lvl_name, emoji = name, emo
    return lvl_name, emoji

# -----------------------------
# Data helpers
# -----------------------------
def ensure_group_ids(df):
    # Backfill group_id if missing per username using 30-min rule
    if df.empty:
        return df
    if 'group_id' not in df.columns or df['group_id'].isnull().all() or (df['group_id']=="" ).all():
        df = df.sort_values(['username','date','time']).reset_index(drop=True)
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + " " + df['time'].astype(str), errors='coerce')
        df['group_id'] = ""
        for user in df['username'].unique():
            mask = df['username']==user
            user_idx = df[mask].index.tolist()
            last_dt = None
            current_group = None
            for idx in user_idx:
                dt = df.at[idx, 'datetime']
                if pd.isna(dt) or last_dt is None or (dt - last_dt) > timedelta(minutes=30):
                    current_group = gen_group_id()
                df.at[idx, 'group_id'] = current_group
                last_dt = dt
        df = df.drop(columns=['datetime'])
    return df

def explode_and_allocate(df, activity_col='activity', amount_col='amount'):
    # split comma-separated activities and allocate amount equally
    if df.empty:
        return df
    tmp = df.copy()
    tmp['activity_list'] = tmp[activity_col].astype(str).str.split(', ')
    tmp = tmp.explode('activity_list').reset_index(drop=True)
    counts = tmp.groupby(tmp.index)['activity_list'].transform('count')
    tmp['alloc_amount'] = tmp[amount_col].astype(float) / counts.replace(0,1)
    return tmp

# -----------------------------
# Auth & Profile UI
# -----------------------------
def register_user(users_df):
    st.subheader("Tạo tài khoản")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Tên đăng nhập (username)")
        password = st.text_input("Mật khẩu", type="password")
    with col2:
        full_name = st.text_input("Họ & tên")
        role = st.selectbox("Vai trò", ["user","admin"])
    house_type = st.selectbox("Loại hộ", ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"])
    location = st.selectbox("Tỉnh/Thành", PROVINCES)
    address = st.text_input("Địa chỉ (số nhà, đường...)")
    daily_limit = st.number_input("Ngưỡng nước hàng ngày (Lít)", min_value=50, value=200)
    entries_day = st.slider("Số lần nhập/ngày", 1, 10, 3)
    reminders = st.multiselect("Giờ nhắc nhở (tối đa 5)", options=[f"{h:02d}:00" for h in range(24)], default=["08:00","12:00","18:00"])
    if len(reminders) > 5:
        reminders = reminders[:5]
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
    col1, col2 = st.columns(2)
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
    full = st.text_input("Họ & tên", value=user_row.get('full_name',''))
    try:
        idx = ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"].index(user_row.get('house_type','Chung cư'))
    except:
        idx = 0
    house_type = st.selectbox("Loại hộ", ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"], index=idx)
    try:
        loc_idx = PROVINCES.index(user_row.get('location','Thành phố Hà Nội'))
    except:
        loc_idx = 0
    location = st.selectbox("Tỉnh/Thành", PROVINCES, index=loc_idx)
    address = st.text_input("Địa chỉ", value=user_row.get('address',''))
    daily_limit = st.number_input("Ngưỡng nước hàng ngày (Lít)", min_value=50, value=float(user_row.get('daily_limit',200)))
    entries_day = st.slider("Số lần nhập/ngày", 1, 10, int(user_row.get('entries_per_day') or 3))
    reminders = st.multiselect("Giờ nhắc nhở (tối đa 5)", options=[f"{h:02d}:00" for h in range(24)],
                               default=(user_row.get('reminder_times','').split(",") if user_row.get('reminder_times') else ["08:00","12:00","18:00"]))
    if len(reminders)>5:
        reminders = reminders[:5]
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
# Data add / grouped editor
# -----------------------------
def add_activity(data_df, username, house_type, location, addr_input, activity, amount, note_text, date_input):
    now = datetime.now()
    if data_df.empty:
        data_df = pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount","note","group_id"])
    user_rows = data_df[data_df['username']==username]
    group_id = gen_group_id()
    if not user_rows.empty:
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
def plot_activity_bar(df):
    if df.empty:
        st.info("Chưa có dữ liệu để vẽ biểu đồ hoạt động.")
        return
    exploded = explode_and_allocate(df)
    agg = exploded.groupby('activity_list')['alloc_amount'].sum().reset_index().rename(columns={'activity_list':'activity','alloc_amount':'total_lit'}).sort_values('total_lit', ascending=False)
    chart = alt.Chart(agg).mark_bar().encode(
        x=alt.X('activity:N', sort='-y', title='Hoạt động'),
        y=alt.Y('total_lit:Q', title='Tổng Lít'),
        tooltip=['activity','total_lit'],
        color='activity:N'
    ).properties(height=320)
    st.altair_chart(chart, use_container_width=True)

def plot_week_month(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    d = df.copy()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    d['week'] = d['datetime'].dt.isocalendar().week
    d['year'] = d['datetime'].dt.isocalendar().year
    week_sum = d.groupby(['year','week'])['amount'].sum().reset_index()
    week_sum['label'] = week_sum['year'].astype(str) + "-W" + week_sum['week'].astype(str)
    chart = alt.Chart(week_sum).mark_bar().encode(x='label:N', y='amount:Q', tooltip=['label','amount']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)
    d['month'] = d['datetime'].dt.to_period('M').astype(str)
    month_sum = d.groupby('month')['amount'].sum().reset_index()
    chart2 = alt.Chart(month_sum).mark_bar().encode(x='month:N', y='amount:Q', tooltip=['month','amount']).properties(height=240)
    st.altair_chart(chart2, use_container_width=True)

def plot_hour_heatmap(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    d = df.copy()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    d['hour'] = d['datetime'].dt.hour
    heat = d.groupby('hour')['amount'].sum().reset_index()
    chart = alt.Chart(heat).mark_bar().encode(x=alt.X('hour:O', title='Giờ'), y=alt.Y('amount:Q', title='Tổng Lít'), tooltip=['hour','amount']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)

def plot_cumulative(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    d = df.copy()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    daily = d.groupby(d['datetime'].dt.date)['amount'].sum().reset_index().rename(columns={'datetime':'date'})
    daily['cum'] = daily['amount'].cumsum()
    chart = alt.Chart(daily).mark_line(point=True).encode(x=alt.X('datetime:T', title='Ngày'), y=alt.Y('cum:Q', title='Tích lũy (L)'), tooltip=['datetime','cum']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)

# -----------------------------
# Admin panel
# -----------------------------
def admin_panel(users_df, data_df):
    st.header("⚙️ Admin panel")
    st.subheader("Danh sách người dùng")
    st.dataframe(users_df[['username','full_name','role','location','address','daily_limit','points']].sort_values('username'), use_container_width=True)
    st.download_button("Tải users.csv", users_df.to_csv(index=False), "users.csv", "text/csv")
    st.markdown("---")
    st.subheader("Quản lý dữ liệu water_usage")
    uploaded = st.file_uploader("Import CSV water_usage (ghi đè dữ liệu hiện tại)", type=['csv'])
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
    st.markdown("---")
    st.subheader("Leaderboard (điểm)")
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
        score = max(0, limit - today_sum)
        scores.append({"username":u,"score":score})
    if scores:
        s_df = pd.DataFrame(scores).sort_values('score', ascending=False).reset_index(drop=True)
        st.dataframe(s_df.head(20), use_container_width=True)
    else:
        st.info("Chưa đủ dữ liệu để leaderboard.")

# -----------------------------
# Main app
# -----------------------------
def main():
    st.set_page_config(page_title="Water Loop App (Full)", page_icon="💧", layout="wide")
    set_background()
    users_df = load_users()
    data_df = load_data()
    data_df = ensure_group_ids(data_df)

    if 'username' not in st.session_state:
        st.session_state['username'] = None

    st.sidebar.title("WATER LOOP")
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

    if st.session_state['username']:
        username = st.session_state['username']
        user_row = users_df[users_df['username']==username].iloc[0] if username in users_df['username'].values else None
        tabs = st.tabs(["Nhập dữ liệu","Phân tích","Nhật ký","Hồ sơ","Admin"])
        # TAB 1: Input
        with tabs[0]:
            st.header("📝 Ghi nhận hoạt động")
            left, right = st.columns([3,1])
            with left:
                activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys()) + ["➕ Khác"])
                if activity == "➕ Khác":
                    activity = st.text_input("Nhập tên hoạt động:", "")
                amount = st.number_input("Lượng nước (Lít)", min_value=1, value=int(DEFAULT_ACTIVITIES.get(activity,10)))
                date_input = st.date_input("📅 Ngày", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())
                addr_input = st.text_input("🏠 Địa chỉ", value=user_row.get('address') if user_row is not None else "")
                note = st.text_area("Ghi chú (tuỳ chọn):", height=80)
                if st.button("💾 Lưu hoạt động"):
                    data_df, group_id = add_activity(data_df, username, user_row.get('house_type','') if user_row is not None else '', user_row.get('location','') if user_row is not None else '', addr_input, activity, amount, note, date_input)
                    st.success("Đã lưu!")
                    # award points (simple)
                    try:
                        limit = float(user_row.get('daily_limit',200))
                        add_pts = 1
                        if amount < 0.8 * limit:
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
                    pts = int(users_df.loc[users_df['username']==username,'points'].iloc[0])
                    st.write("Điểm hiện có:", pts)
                    lvl, emo = pet_level_for_points(pts)
                    st.write(f"Pet: {emo} — {lvl}")
                else:
                    st.write("Chưa có dữ liệu")
        # TAB 2: Analysis
        with tabs[1]:
            st.header("📊 Phân tích")
            all_users = data_df['username'].unique().tolist()
            if len(all_users)==0:
                all_users = [username]
            default_idx = all_users.index(username) if username in all_users else 0
            sel_user = st.selectbox("Xem dữ liệu của:", options=all_users, index=default_idx)
            df_user = data_df[data_df['username']==sel_user].copy()
            if df_user.empty:
                st.info("Người dùng này chưa có dữ liệu.")
            else:
                addrs = df_user['address'].fillna('').unique().tolist()
                selected_addrs = st.multiselect("Chọn địa chỉ để phân tích", options=addrs, default=addrs)
                df_user = df_user[df_user['address'].isin(selected_addrs)]
                st.subheader("Biểu đồ theo hoạt động")
                plot_activity_bar(df_user)
                st.markdown("---")
                st.subheader("Heatmap giờ sử dụng")
                plot_hour_heatmap(df_user)
                st.markdown("---")
                st.subheader("Tổng theo Tuần / Tháng")
                plot_week_month(df_user)
                st.markdown("---")
                st.subheader("Tích lũy theo thời gian")
                plot_cumulative(df_user)
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
        st.info("Vui lòng đăng nhập hoặc đăng ký ở sidebar để sử dụng ứng dụng.")

if __name__ == "__main__":
    main()
