# app.py - Water Loop (full, includes name/address + grouped logs + charts + pet)
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import uuid
import os

# ---------------- Config ----------------
USERS_FILE = "users.csv"
DATA_FILE  = "water_usage.csv"

st.set_page_config(page_title="Water Loop", page_icon="💧", layout="wide")

# Default activities
DEFAULT_ACTIVITIES = {
    "🚿 Tắm":50, "🧺 Giặt quần áo":70, "🍳 Nấu ăn":20, "🌱 Tưới cây":15,
    "🧹 Lau nhà":25, "🛵 Rửa xe máy":40, "🚗 Rửa ô tô":150, "🚲 Rửa xe đạp":10
}

# Pet thresholds
PET_LEVELS = [
    (0, "Seedling", "🌱"),
    (50, "Sprout", "🌿"),
    (150, "Young Tree", "🌳"),
    (350, "Mature Tree", "🌲"),
    (700, "Forest Guardian", "🌳🌟")
]

PROVINCES = [
    "Tỉnh Tuyên Quang","Tỉnh Lào Cai","Tỉnh Thái Nguyên","Tỉnh Phú Thọ","Tỉnh Bắc Ninh",
    "Tỉnh Hưng Yên","Thành phố Hải Phòng","Tỉnh Ninh Bình","Tỉnh Quảng Trị","Thành phố Đà Nẵng",
    "Tỉnh Quảng Ngãi","Tỉnh Gia Lai","Tỉnh Khánh Hoà","Tỉnh Lâm Đồng","Tỉnh Đắk Lắk",
    "Thành phố Hồ Chí Minh","Tỉnh Đồng Nai","Tỉnh Tây Ninh","Thành phố Cần Thơ","Tỉnh Vĩnh Long",
    "Tỉnh Đồng Tháp","Tỉnh Cà Mau","Tỉnh An Giang","Thành phố Hà Nội","Thành phố Huế",
    "Tỉnh Lai Châu","Tỉnh Điện Biên","Tỉnh Sơn La","Tỉnh Lạng Sơn","Tỉnh Quảng Ninh",
    "Tỉnh Thanh Hoá","Tỉnh Nghệ An","Tỉnh Hà Tĩnh","Tỉnh Cao Bằng"
]

# ---------------- Utilities ----------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.warning("⚠️ Phiên bản Streamlit của bạn không hỗ trợ rerun tự động.")

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
            "username","full_name","house_type","location","address",
            "date","time","activity","amount","note","group_id"
        ])
        df.to_csv(DATA_FILE, index=False)

def load_users():
    ensure_users_file()
    df = pd.read_csv(USERS_FILE, dtype=str).fillna("")
    if "points" not in df.columns:
        df["points"] = 0.0
    else:
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
    # ensure numeric amount
    if "amount" in df.columns:
        try:
            df["amount"] = df["amount"].astype(float)
        except:
            df["amount"] = df["amount"].replace("", 0).astype(float)
    else:
        df["amount"] = 0.0
    for c in ["group_id","note","full_name","house_type","location","address"]:
        if c not in df.columns:
            df[c] = ""
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def gen_group_id():
    return str(uuid.uuid4())

def pet_level_for_points(points):
    lvl, emo = PET_LEVELS[0][1], PET_LEVELS[0][2]
    for thr, name, emoji in PET_LEVELS:
        if points >= thr:
            lvl, emo = name, emoji
    return lvl, emo

# ---------------- Theme (simple) ----------------
def set_background():
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(120deg,#eff6ff,#dbeafe); }
        .stButton>button { background-color:#2563EB;color:white;border-radius:8px;padding:0.5em 1em; }
        </style>
    """, unsafe_allow_html=True)

# ---------------- Auth / Register ----------------
def login_register():
    set_background()
    st.markdown("<h1 style='text-align:center;color:#05595b;'>💧 WATER LOOP 💧</h1>", unsafe_allow_html=True)
    users = load_users()

    mode = st.radio("Chọn chế độ:", ["Đăng nhập","Đăng ký"], horizontal=True)
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔒 Mật khẩu", type="password")

    if mode == "Đăng ký":
        full_name = st.text_input("Họ & tên")
        default_house_types = ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"]
        house_type = st.selectbox("🏠 Loại hộ gia đình", default_house_types + ["➕ Khác"])
        if house_type == "➕ Khác":
            house_type = st.text_input("Nhập loại nhà của bạn:")
        location = st.selectbox("📍 Khu vực", PROVINCES)
        address = st.text_input("🏠 Địa chỉ cụ thể (số nhà, đường...)")
        daily_limit = st.number_input("⚖️ Ngưỡng nước hàng ngày (Lít)", min_value=50, value=200)
        entries_per_day = st.slider("🔔 Số lần nhập dữ liệu/ngày", 1, 5, 3)
        reminder_times = st.multiselect(
            "⏰ Chọn giờ nhắc nhở trong ngày (tối đa 5 lần)",
            options=[f"{h:02d}:00" for h in range(24)],
            default=["08:00","12:00","18:00"]
        )
        if len(reminder_times) > 5:
            st.warning("⚠️ Chỉ chọn tối đa 5 giờ nhắc nhở. Mặc định giữ 5 giờ đầu.")
            reminder_times = reminder_times[:5]

        if st.button("Đăng ký", use_container_width=True):
            if username in users['username'].values:
                st.error("❌ Tên đăng nhập đã tồn tại.")
            else:
                new = pd.DataFrame([{
                    "username": username, "password": password, "full_name": full_name,
                    "role":"user", "house_type": house_type, "location": location, "address": address,
                    "daily_limit": daily_limit, "entries_per_day": entries_per_day, "reminder_times": ",".join(reminder_times),
                    "points": 0.0, "pet_state":""
                }])
                users = pd.concat([users, new], ignore_index=True)
                save_users(users)
                st.success("✅ Đăng ký thành công, vui lòng đăng nhập.")

    else:  # login
        if st.button("Đăng nhập", use_container_width=True):
            user_row = users[(users["username"]==username)&(users["password"]==password)]
            if user_row.empty:
                st.error("❌ Sai tên đăng nhập hoặc mật khẩu.")
            else:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.full_name = user_row.iloc[0].get("full_name","")
                st.session_state.daily_limit = float(user_row.iloc[0].get("daily_limit",200))
                st.session_state.entries_per_day = int(user_row.iloc[0].get("entries_per_day",3))
                st.session_state.reminder_times = user_row.iloc[0].get("reminder_times","").split(",") if pd.notna(user_row.iloc[0].get("reminder_times","")) else []
                st.session_state.address = user_row.iloc[0].get("address","")
                st.success("✅ Đăng nhập thành công!")
                safe_rerun()

# ---------------- Data add (per-activity row) ----------------
def add_activity(data, username, full_name, house_type, location, addr_input, activity, amount, note_text, date_input):
    now = datetime.now()
    # ensure columns
    for c in ["username","full_name","house_type","location","address","date","time","activity","amount","note","group_id"]:
        if c not in data.columns:
            data[c] = "" if c in ["username","full_name","house_type","location","address","activity","note","group_id"] else 0.0
    data = data.reset_index(drop=True)

    # find user's last entry and reuse group_id if within 30 minutes
    user_entries = data[data["username"]==username].copy()
    group_id = gen_group_id()
    if not user_entries.empty:
        user_entries['datetime'] = pd.to_datetime(user_entries['date'].astype(str) + " " + user_entries['time'].astype(str), errors='coerce')
        user_entries = user_entries.sort_values('datetime', ascending=False)
        last_idx = user_entries.index[0]
        last_dt = user_entries.loc[last_idx, 'datetime']
        last_group = user_entries.loc[last_idx, 'group_id'] if pd.notna(user_entries.loc[last_idx, 'group_id']) and user_entries.loc[last_idx, 'group_id']!="" else None
        if pd.notna(last_dt) and (now - last_dt) <= timedelta(minutes=30):
            group_id = last_group if last_group else gen_group_id()

    new_row = {
        "username": username,
        "full_name": full_name,
        "house_type": house_type,
        "location": location,
        "address": addr_input,
        "date": date_input.strftime("%Y-%m-%d") if isinstance(date_input, datetime) else str(date_input),
        "time": now.strftime("%H:%M:%S"),
        "activity": activity,
        "amount": float(amount),
        "note": note_text if note_text else "",
        "group_id": group_id
    }
    data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
    save_data(data)
    return data

# ---------------- Grouped log UI ----------------
def grouped_summary_for_user(data, username):
    df = data[data['username']==username].copy()
    if df.empty:
        return pd.DataFrame()
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + " " + df['time'].astype(str), errors='coerce')
    grouped = df.groupby('group_id').agg({
        'date':'min','time':'min','address': lambda x: x.dropna().astype(str).iloc[0] if len(x.dropna())>0 else "",
        'amount':'sum','activity': lambda x: ", ".join(x.astype(str))
    }).reset_index().rename(columns={'amount':'total_amount','activity':'activities'}).sort_values(['date','time'], ascending=False)
    return grouped

def show_grouped_log_for_user(data, username):
    st.subheader("📒 Nhật ký (tóm tắt theo nhóm)")
    grouped = grouped_summary_for_user(data, username)
    if grouped.empty:
        st.info("Chưa có dữ liệu.")
        return data
    st.dataframe(grouped[['group_id','date','time','address','total_amount','activities']].rename(columns={'total_amount':'Tổng Lít','activities':'Hoạt động'}), use_container_width=True)

    sel = st.selectbox("🔎 Chọn nhóm để xem chi tiết / chỉnh sửa:", options=grouped['group_id'])
    if sel:
        st.write(f"### Chi tiết nhóm: {sel}")
        details = data[(data['username']==username) & (data['group_id']==sel)].sort_values(['date','time'], ascending=False).reset_index()
        # details has column 'index' (original index in data)
        if 'index' not in details.columns:
            st.error("Lỗi nội bộ: không tìm thấy mapping index.")
            return data
        display_df = details[['index','date','time','activity','amount','note','address']].copy().rename(columns={'index':'_orig_index'})
        orig_indices = display_df['_orig_index'].tolist()
        editor_df = display_df.drop(columns=['_orig_index']).reset_index(drop=True)
        edited = st.data_editor(editor_df, num_rows="dynamic", use_container_width=True, hide_index=True)

        if st.button("💾 Lưu thay đổi chi tiết nhóm"):
            try:
                for pos, orig_idx in enumerate(orig_indices):
                    row = edited.iloc[pos]
                    data.at[orig_idx, 'date'] = row['date']
                    data.at[orig_idx, 'time'] = row['time']
                    data.at[orig_idx, 'activity'] = row['activity']
                    try:
                        data.at[orig_idx, 'amount'] = float(row['amount'])
                    except:
                        pass
                    data.at[orig_idx, 'note'] = row.get('note', data.at[orig_idx,'note'])
                    data.at[orig_idx, 'address'] = row.get('address', data.at[orig_idx,'address'])
                save_data(data)
                st.success("✅ Lưu thay đổi thành công.")
                safe_rerun()
            except Exception as e:
                st.error("Lưu thay đổi thất bại: " + str(e))

        # Delete selection
        choices = [f"{i+1}. {details.loc[i,'activity']} ({details.loc[i,'amount']} L) - {details.loc[i,'date']} {details.loc[i,'time']}" for i in range(len(details))]
        to_delete = st.multiselect("🗑️ Chọn các hoạt động để xóa (chỉ tác động tới hoạt động được chọn):", options=list(range(len(details))), format_func=lambda i: choices[i])
        if st.button("❌ Xóa hoạt động đã chọn"):
            if not to_delete:
                st.warning("Bạn chưa chọn hoạt động nào để xóa.")
            else:
                indices_to_drop = [orig_indices[pos] for pos in to_delete]
                data = data.drop(indices_to_drop).reset_index(drop=True)
                save_data(data)
                st.success(f"✅ Đã xóa {len(indices_to_drop)} hoạt động.")
                safe_rerun()

        if st.button("🗑️ Xóa toàn bộ nhóm này"):
            data = data[data['group_id'] != sel].reset_index(drop=True)
            save_data(data)
            st.success("✅ Đã xóa toàn bộ nhóm.")
            safe_rerun()

    return data

# ---------------- Charts ----------------
def plot_activity_bar(df):
    if df.empty:
        st.info("Chưa có dữ liệu để vẽ biểu đồ hoạt động.")
        return
    tmp = df.copy()
    tmp['activity_list'] = tmp['activity'].astype(str).str.split(', ')
    tmp = tmp.explode('activity_list').reset_index(drop=True)
    counts = tmp.groupby(tmp.index)['activity_list'].transform('count')
    tmp['alloc_amount'] = tmp['amount'].astype(float) / counts.replace(0,1)
    agg = tmp.groupby('activity_list')['alloc_amount'].sum().reset_index().rename(columns={'activity_list':'activity','alloc_amount':'total_lit'}).sort_values('total_lit', ascending=False)
    chart = alt.Chart(agg).mark_bar().encode(
        x=alt.X('activity:N', sort='-y', title='Hoạt động'),
        y=alt.Y('total_lit:Q', title='Tổng Lít'),
        tooltip=['activity','total_lit'],
        color='activity:N'
    ).properties(height=320)
    st.altair_chart(chart, use_container_width=True)

def plot_week_month_totals(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    d = df.copy()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    d = d.dropna(subset=['datetime'])
    d['year'] = d['datetime'].dt.isocalendar().year
    d['week'] = d['datetime'].dt.isocalendar().week
    week_sum = d.groupby(['year','week'])['amount'].sum().reset_index()
    week_sum['label'] = week_sum['year'].astype(str) + '-W' + week_sum['week'].astype(str)
    chart = alt.Chart(week_sum).mark_bar().encode(x=alt.X('label:N', sort='-y', title='Tuần'), y=alt.Y('amount:Q', title='Tổng Lít'), tooltip=['label','amount']).properties(height=240)
    st.altair_chart(chart, use_container_width=True)
    d['month'] = d['datetime'].dt.to_period('M').astype(str)
    month_sum = d.groupby('month')['amount'].sum().reset_index()
    chart2 = alt.Chart(month_sum).mark_bar().encode(x=alt.X('month:N', sort='-y', title='Tháng'), y=alt.Y('amount:Q', title='Tổng Lít'), tooltip=['month','amount']).properties(height=240)
    st.altair_chart(chart2, use_container_width=True)

def plot_cumulative(df):
    if df.empty:
        st.info("Chưa có dữ liệu để vẽ biểu đồ tích lũy.")
        return
    d = df.copy()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    d = d.dropna(subset=['datetime'])
    daily = d.groupby(d['datetime'].dt.date)['amount'].sum().reset_index().rename(columns={'datetime':'date','amount':'total'})
    daily['date'] = pd.to_datetime(daily['datetime'].astype(str), errors='coerce') if 'datetime' in daily.columns else pd.to_datetime(daily['date'])
    # to be safe: create a date column of type datetime
    daily['date_only'] = pd.to_datetime(daily['date'])
    daily = daily.sort_values('date_only')
    daily['cum'] = daily['total'].cumsum()
    chart = alt.Chart(daily).mark_line(point=True).encode(
        x=alt.X('date_only:T', title='Ngày'),
        y=alt.Y('cum:Q', title='Tích lũy (L)'),
        tooltip=[alt.Tooltip('date_only:T', title='Ngày'), alt.Tooltip('cum:Q', title='Tích lũy (L)')]
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

def plot_hour_heatmap(df):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    d = df.copy()
    d['datetime'] = pd.to_datetime(d['date'].astype(str) + " " + d['time'].astype(str), errors='coerce')
    d = d.dropna(subset=['datetime'])
    d['hour'] = d['datetime'].dt.hour
    heat = d.groupby('hour')['amount'].sum().reset_index()
    chart = alt.Chart(heat).mark_bar().encode(
        x=alt.X('hour:O', title='Giờ trong ngày'),
        y=alt.Y('amount:Q', title='Tổng Lít'),
        tooltip=['hour','amount']
    ).properties(height=240)
    st.altair_chart(chart, use_container_width=True)

# ---------------- Dashboard (input + charts + log) ----------------
def water_dashboard():
    set_background()
    st.markdown("<h2 style='color:#05595b;'>💧 Nhập dữ liệu về sử dụng nước</h2>", unsafe_allow_html=True)

    users = load_users()
    data = load_data()
    data = ensure_group_ids(data)

    username = st.session_state.username
    user_row = users[users['username']==username].iloc[0] if username in users['username'].values else {}
    house_type = user_row.get('house_type','') if isinstance(user_row, dict) or user_row.empty else user_row.get('house_type','')
    location = user_row.get('location','') if isinstance(user_row, dict) or user_row.empty else user_row.get('location','')
    full_name = user_row.get('full_name','') if isinstance(user_row, dict) or user_row.empty else user_row.get('full_name','')
    daily_limit = float(st.session_state.get('daily_limit', user_row.get('daily_limit',200) if not user_row.empty else 200))
    reminder_times = st.session_state.get('reminder_times', user_row.get('reminder_times',"").split(",") if not user_row.empty else [])

    # reminders
    now = datetime.now()
    for t in reminder_times:
        try:
            h,m = map(int, (t or "00:00").split(":"))
            reminder_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if abs((now - reminder_time).total_seconds()/60) <= 5:
                st.info(f"⏰ Nhắc nhở: Đến giờ nhập dữ liệu nước! ({t})")
        except:
            pass

    # Input
    st.subheader("📝 Ghi nhận hoạt động")
    left, right = st.columns([3,1])
    with left:
        activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys()) + ["➕ Khác"])
        if activity == "➕ Khác":
            custom_act = st.text_input("Nhập tên hoạt động:")
            if custom_act:
                activity = custom_act
        amount = st.number_input("Lượng nước (Lít)", min_value=1, value=int(DEFAULT_ACTIVITIES.get(activity,10)))
        date_input = st.date_input("📅 Ngày sử dụng", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())
        addr_input = st.text_input("🏠 Địa chỉ", value=st.session_state.get('address', user_row.get('address','') if not isinstance(user_row, dict) else ''))
        note_quick = st.text_area("Ghi chú nhanh cho lần nhập này (tùy chọn):", height=80)

        if st.button("💾 Lưu hoạt động", use_container_width=True):
            if not activity:
                st.warning("Vui lòng chọn hoặc nhập hoạt động.")
            else:
                data = add_activity(data, username, full_name, house_type, location, addr_input, activity, amount, note_quick, date_input)
                # award points simple
                try:
                    users = load_users()
                    users.loc[users['username']==username,'points'] = users.loc[users['username']==username,'points'].astype(float) + (1 if amount>=0 else 0)
                    save_users(users)
                except:
                    pass
                st.success("✅ Đã lưu hoạt động!")
                safe_rerun()

    with right:
        st.markdown("**Tóm tắt hôm nay**")
        df_user = data[data['username']==username].copy()
        if not df_user.empty:
            df_user['datetime'] = pd.to_datetime(df_user['date'].astype(str) + " " + df_user['time'].astype(str), errors='coerce')
            today_sum = df_user[df_user['datetime'].dt.date == datetime.now().date()]['amount'].sum()
            st.metric("Tổng (L) hôm nay", f"{int(today_sum)} L")
        else:
            st.write("Chưa có dữ liệu")

    st.markdown("---")

    # Filters & charts
    st.subheader("🔍 Bộ lọc & Biểu đồ")
    user_data_all = data[data['username']==username].copy()
    if not user_data_all.empty:
        user_data_all['datetime'] = pd.to_datetime(user_data_all['date'].astype(str) + " " + user_data_all['time'].astype(str), errors='coerce')
        all_addresses = user_data_all['address'].fillna('').unique().tolist()
        selected_addresses = st.multiselect("Chọn địa chỉ để phân tích", options=all_addresses, default=all_addresses)
        filtered_data = user_data_all[user_data_all['address'].isin(selected_addresses)].copy()

        time_frame = st.radio("Khoảng thời gian tổng kết", ["Tuần","Tháng"], horizontal=True)

        st.markdown("**📊 Biểu đồ theo hoạt động (tổng Lít)**")
        try:
            plot_activity_bar(filtered_data)
        except Exception as e:
            st.error("Lỗi vẽ biểu đồ hoạt động: " + str(e))

        st.markdown("---")
        st.markdown("**📈 Tổng lượng theo khoảng (Tuần/Tháng)**")
        try:
            plot_week_month_totals(filtered_data)
        except Exception as e:
            st.error("Lỗi vẽ tổng tuần/tháng: " + str(e))

        st.markdown("---")
        st.markdown("**📈 Biểu đồ tích lũy (hàng ngày)**")
        try:
            plot_cumulative(filtered_data)
        except Exception as e:
            st.error("Lỗi vẽ biểu đồ tích lũy: " + str(e))

        st.markdown("---")
        st.markdown("**🕒 Heatmap giờ sử dụng**")
        try:
            plot_hour_heatmap(filtered_data)
        except Exception as e:
            st.error("Lỗi vẽ heatmap: " + str(e))

        st.download_button("📥 Tải dữ liệu phân tích (CSV)", filtered_data.to_csv(index=False), "water_usage_filtered.csv", "text/csv")
    else:
        st.info("Chưa có dữ liệu để hiển thị biểu đồ. Hãy nhập hoạt động trước.")

    st.markdown("---")
    # grouped log editor
    data = show_grouped_log_for_user(data, username)

    st.markdown("---")
    # Pet
    st.subheader("🌱 Trồng cây nàooo")
    user_row = load_users()[load_users()['username']==username].iloc[0] if username in load_users()['username'].values else None
    pts = int(user_row['points']) if user_row is not None else 0
    lvl, emo = pet_level_for_points(pts)
    # show pet: compute today usage and warn message
    df_user = data[data['username']==username].copy()
    today_df = df_user[pd.to_datetime(df_user['date']).dt.date == datetime.now().date()] if not df_user.empty else pd.DataFrame()
    today_usage = today_df['amount'].sum() if not today_df.empty else 0
    if today_usage < 0.8 * daily_limit:
        pet_emoji, pet_color, pet_msg = emo, "#d4f4dd", "Cây đang phát triển tươi tốt! 💚"
    elif today_usage <= 1.1 * daily_limit:
        pet_emoji, pet_color, pet_msg = "🌿", "#ffe5b4", "Cây hơi héo, hãy tiết kiệm thêm ⚠️"
    else:
        pet_emoji, pet_color, pet_msg = "🥀", "#ffcccc", "Cây đang héo 😢"
    st.markdown(f"<div style='font-size:60px;text-align:center'>{pet_emoji}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='padding:14px;border-radius:12px;background:{pet_color};color:black;font-weight:bold;text-align:center;font-size:18px;'>{pet_msg}</div>", unsafe_allow_html=True)

    # Logout
    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.logged_in=False
        st.session_state.username=None
        safe_rerun()

# ---------------- Main ----------------
def main():
    st.set_page_config(page_title="Water Loop App", page_icon="💧", layout="centered")
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_register()
    else:
        water_dashboard()

if __name__=="__main__":
    main()
