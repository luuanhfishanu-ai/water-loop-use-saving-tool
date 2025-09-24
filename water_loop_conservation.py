import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import uuid

USERS_FILE = "users.csv"
DATA_FILE = "water_usage.csv"

# ----------------- Safe rerun -----------------


def about_tab():
    """Giới thiệu & Hướng dẫn ngắn gọn về sản phẩm Water Loop App"""
    st.title("💧 Về Water Loop App 💧")

    st.markdown("""
    Water Loop App là ứng dụng gamification giúp người dùng theo dõi và giảm tiêu thụ nước.  
    Mỗi ngày bạn nhập lượng nước sử dụng, một **cây ảo** sẽ phản ánh mức tiêu thụ:

    - 🌱 **Tươi:** dùng hợp lý  
    - 🍂 **Hơi héo:** cần giảm  
    - 🔴 **Héo đỏ:** vượt ngưỡng khuyến nghị  

    Dữ liệu được tổng hợp hàng ngày, hàng tuần và hàng tháng để bạn theo dõi và duy trì thói quen tiết kiệm.
    """)

    st.subheader("Hướng dẫn nhanh")
    st.markdown("""
    1️ **Đăng ký** tài khoản mới.  
    2️ **Đăng nhập** vào ứng dụng.  
    3️ **Nhập** lượng nước đã dùng mỗi ngày (lít hoặc m³).  
    4️ **Theo dõi cây ảo** và báo cáo để điều chỉnh thói quen.
    """)

    st.subheader("Nhóm phát triển")
    st.markdown("""
    Ý tưởng được thực hiện bởi nhóm sinh viên **Khoa Quốc tế học – Đại học Hà Nội (HANU)**  
    trong khuôn khổ cuộc thi Đại sứ Gen G.

    Thành viên nhóm:
    - Đặng Lưu Anh  
    - Nguyễn Việt Anh  
    - Đàm Thiên Hương  
    - Nguyễn Thị Thư
    """)

def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.warning("⚠️ Phiên bản Streamlit của bạn không hỗ trợ rerun tự động.")

# ----------------- Gradient & Theme -----------------
def set_background():
     st.markdown(
        """
        <style>
        /* Nền toàn bộ app */
        .stApp {
            background: linear-gradient(
                120deg,
                #d8f3dc,   /* xanh lá pastel nhạt */
                #cce5ff    /* xanh dương pastel rất nhạt */
            );
            color: #374151; /* xám đậm cân bằng */
        }

        /* Tiêu đề, heading */
        h1, h2, h3, h4, h5, h6 {
            color: #1F2937; /* xám than – đậm hơn body text */
            font-weight: 700;
        }

        /* Đoạn văn, list… */
        p, li, span, label, .markdown-text-container {
            color: #374151;
        }

        /* Thanh menu chính (nếu dùng st.tabs / sidebar) */
        .css-1v3fvcr, .css-18ni7ap {
            color: #374151;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ----------------- Utils -----------------
def load_users():
    try:
        users = pd.read_csv(USERS_FILE)
        if "address" not in users.columns:
            users["address"] = ""
        # ensure reminder_times and entries_per_day exist
        if "reminder_times" not in users.columns:
            users["reminder_times"] = ""
        if "entries_per_day" not in users.columns:
            users["entries_per_day"] = 3
        return users
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "username","password","house_type","location","address","daily_limit","entries_per_day","reminder_times"
        ])

def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        # make sure required cols exist
        for c in ["username","house_type","location","address","date","time","activity","amount","note","group_id"]:
            if c not in df.columns:
                df[c] = "" if c in ["username","house_type","location","address","activity","note","group_id"] else 0
        # normalize types
        df = df.reset_index(drop=True)
        return df
    except FileNotFoundError:
        cols = ["username","house_type","location","address","date","time","activity","amount","note","group_id"]
        return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def generate_group_id():
    return str(uuid.uuid4())

# If historical data missing group_id, fill group ids per user using 30-min rule
def ensure_group_ids(df):
    if df.empty: 
        return df
    if 'group_id' not in df.columns or df['group_id'].isnull().all() or (df['group_id']=="" ).all():
        # fill per user
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
                if pd.isna(dt):
                    # if datetime missing, create new group
                    current_group = generate_group_id()
                else:
                    if last_dt is None or (dt - last_dt) > timedelta(minutes=30):
                        current_group = generate_group_id()
                df.at[idx, 'group_id'] = current_group
                last_dt = dt
        df = df.drop(columns=['datetime'])
    return df

# ----------------- Login & Register -----------------
def login_register():
    set_background()
    st.markdown("<h1 style='text-align:center;color:#05595b;'>💧 WATER LOOP 💧 </h1>", unsafe_allow_html=True)
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    users = load_users()

    mode = st.radio("Chọn chế độ:", ["Đăng nhập", "Đăng ký"], horizontal=True)
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔒 Mật khẩu", type="password")

    if mode == "Đăng ký":
        default_house_types = ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"]
        house_type = st.selectbox("🏠 Loại hộ gia đình", default_house_types + ["➕ Khác"])
        if house_type == "➕ Khác":
            house_type = st.text_input("Nhập loại nhà của bạn:")

        location = st.selectbox("📍 Khu vực", [
            "Tỉnh Tuyên Quang","Tỉnh Lào Cai","Tỉnh Thái Nguyên","Tỉnh Phú Thọ","Tỉnh Bắc Ninh",
            "Tỉnh Hưng Yên","Thành phố Hải Phòng","Tỉnh Ninh Bình","Tỉnh Quảng Trị","Thành phố Đà Nẵng",
            "Tỉnh Quảng Ngãi","Tỉnh Gia Lai","Tỉnh Khánh Hoà","Tỉnh Lâm Đồng","Tỉnh Đắk Lắk",
            "Thành phố Hồ Chí Minh","Tỉnh Đồng Nai","Tỉnh Tây Ninh","Thành phố Cần Thơ","Tỉnh Vĩnh Long",
            "Tỉnh Đồng Tháp","Tỉnh Cà Mau","Tỉnh An Giang","Thành phố Hà Nội","Thành phố Huế",
            "Tỉnh Lai Châu","Tỉnh Điện Biên","Tỉnh Sơn La","Tỉnh Lạng Sơn","Tỉnh Quảng Ninh",
            "Tỉnh Thanh Hoá","Tỉnh Nghệ An","Tỉnh Hà Tĩnh","Tỉnh Cao Bằng"
        ])
        address = st.text_input("🏠 Địa chỉ cụ thể (số nhà, đường...)")

        daily_limit = st.number_input("⚖️ Ngưỡng nước hàng ngày (Lít)", min_value=50, value=200)
        entries_per_day = st.slider("🔔 Số lần nhập dữ liệu/ngày", 1, 5, 3)

        reminder_times = st.multiselect(
            "⏰ Chọn giờ nhắc nhở trong ngày (tối đa 5 lần)",
            options=[f"{h:02d}:00" for h in range(0,24)],
            default=["08:00","12:00","18:00"]
        )
        if len(reminder_times) > 5:
            st.warning("⚠️ Chỉ chọn tối đa 5 giờ nhắc nhở. Mặc định giữ 5 giờ đầu.")
            reminder_times = reminder_times[:5]

        if st.button("Đăng ký", use_container_width=True):
            if username in users["username"].values:
                st.error("❌ Tên đăng nhập đã tồn tại.")
            else:
                new_user = pd.DataFrame([{
                    "username": username,
                    "password": password,
                    "house_type": house_type,
                    "location": location,
                    "address": address,
                    "daily_limit": daily_limit,
                    "entries_per_day": entries_per_day,
                    "reminder_times": ",".join(reminder_times)
                }])
                users = pd.concat([users,new_user], ignore_index=True)
                users.to_csv(USERS_FILE,index=False)
                st.success("✅ Đăng ký thành công, vui lòng đăng nhập.")

    else:  # Đăng nhập
        if st.button("Đăng nhập", use_container_width=True):
            user_row = users[(users["username"]==username)&(users["password"]==password)]
            if user_row.empty:
                st.error("❌ Sai tên đăng nhập hoặc mật khẩu.")
            else:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.daily_limit = float(user_row.iloc[0].get("daily_limit",200))
                st.session_state.entries_per_day = float(user_row.iloc[0].get("entries_per_day",3))
                st.session_state.reminder_times = user_row.iloc[0].get("reminder_times","").split(",") if pd.notna(user_row.iloc[0].get("reminder_times","")) else []
                st.session_state.address = user_row.iloc[0].get("address","") if "address" in user_row.columns else ""
                st.success("✅ Đăng nhập thành công!")
                safe_rerun()

# ----------------- Data operations -----------------
def explode_and_allocate(df, activity_col='activity', amount_col='amount'):
    """
    Backward-compatible: if any row stores multiple activities in a single string
    (e.g. 'A, B, C'), split and allocate amount equally.
    """
    if df.empty:
        return df
    df = df.copy()
    df['activity_list'] = df[activity_col].fillna('Không xác định').astype(str).str.split(', ')
    df = df.explode('activity_list').reset_index(drop=True)
    counts = df.groupby(df.index)['activity_list'].transform('count')
    # protect division by zero
    df['alloc_amount'] = df[amount_col].astype(float) / counts.replace(0,1)
    return df

def save_or_merge_entry(data, username, house_type, location, addr_input, activity, amount, note_text, date_input):
    """
    Save 1 activity as a separate row. If the user's last activity is within 30 minutes,
    reuse that last row's group_id (so activities share the same group).
    """
    now = datetime.now()
    # ensure columns
    for c in ["username","house_type","location","address","date","time","activity","amount","note","group_id"]:
        if c not in data.columns:
            data[c] = "" if c in ["username","house_type","location","address","activity","note","group_id"] else 0

    # reset index to keep mapping consistent
    data = data.reset_index(drop=True)

    # find last entry for this user
    user_entries = data[data['username']==username].copy()
    if not user_entries.empty:
        user_entries['datetime'] = pd.to_datetime(user_entries['date'].astype(str) + ' ' + user_entries['time'].astype(str), errors='coerce')
        user_entries = user_entries.sort_values('datetime', ascending=False)
        last_idx = user_entries.index[0]
        last_dt = user_entries.loc[last_idx, 'datetime']
        last_group = user_entries.loc[last_idx, 'group_id'] if pd.notna(user_entries.loc[last_idx, 'group_id']) and user_entries.loc[last_idx, 'group_id']!="" else None
        if pd.notna(last_dt) and (now - last_dt) <= timedelta(minutes=30):
            group_id = last_group if last_group else generate_group_id()
        else:
            group_id = generate_group_id()
    else:
        group_id = generate_group_id()

    # create new row for this activity
    new_entry = {
        "username": username,
        "house_type": house_type if house_type else "",
        "location": location if location else "",
        "address": addr_input if addr_input else "",
        "date": date_input.strftime("%Y-%m-%d") if isinstance(date_input, (datetime,)) else str(date_input),
        "time": now.strftime("%H:%M:%S"),
        "activity": activity,
        "amount": float(amount),
        "note": note_text if note_text else "",
        "group_id": group_id
    }
    data = pd.concat([data, pd.DataFrame([new_entry])], ignore_index=True)
    return data

# ----------------- UI: Grouped log view -----------------
def show_grouped_log_for_user(data, username):
    """
    data: full dataframe (with group_id)
    show grouped summary then allow user to expand to details and edit/delete individual activities
    """
    st.subheader("📒 Nhật ký (tóm tắt theo nhóm)")
    user_data = data[data['username']==username].copy()
    if user_data.empty:
        st.info("Chưa có dữ liệu. Hãy nhập hoạt động để tạo nhật ký.")
        return data  # nothing to do

    # compute datetime column for sorting
    user_data['datetime'] = pd.to_datetime(user_data['date'].astype(str) + " " + user_data['time'].astype(str), errors='coerce')
    # group summary
    grouped = user_data.groupby('group_id').agg({
        'date': 'min',
        'time': 'min',
        'address': lambda x: x.dropna().astype(str).iloc[0] if len(x.dropna())>0 else "",
        'amount': 'sum',
        'activity': lambda x: ", ".join(x.astype(str))
    }).reset_index().rename(columns={'amount':'total_amount','activity':'activities'})

    # sort by date/time descending
    grouped = grouped.sort_values(['date','time'], ascending=[False,False]).reset_index(drop=True)

    # show grouped summary table (user-friendly columns)
    st.dataframe(grouped[['group_id','date','time','address','total_amount','activities']].rename(
        columns={'total_amount':'Tổng Lít','activities':'Hoạt động'}), use_container_width=True)

    # allow selecting group
    sel = None
    if not grouped.empty:
        sel = st.selectbox("🔎 Chọn nhóm để xem chi tiết / chỉnh sửa:", options=grouped['group_id'])
    else:
        st.info("Không có nhóm nào để hiển thị.")

    if sel:
        st.write(f"### Chi tiết nhóm: {sel}")
        details = user_data[user_data['group_id']==sel].sort_values('datetime', ascending=False).reset_index()
        # keep original indices mapping to 'data'
        # details['index'] is original index in 'data' prior to reset; we kept that in reset_index()
        if 'index' not in details.columns:
            st.error("Không tìm thấy mapping index (lỗi nội bộ).")
            return data

        # prepare display df and keep orig indices list
        display_df = details[['index','date','time','activity','amount','note','address']].copy()
        display_df = display_df.rename(columns={'index':'_orig_index'})
        orig_indices = display_df['_orig_index'].tolist()
        # drop _orig_index for editor view
        editor_df = display_df.drop(columns=['_orig_index']).reset_index(drop=True)

        edited = st.data_editor(editor_df, num_rows="dynamic", use_container_width=True, hide_index=True)

        # Save edits back to main data
        if st.button("💾 Lưu thay đổi chi tiết nhóm"):
            try:
                for pos, orig_idx in enumerate(orig_indices):
                    # edited rows align by position
                    row = edited.iloc[pos]
                    # update fields: date, time, activity, amount, note, address
                    data.at[orig_idx, 'date'] = row['date']
                    data.at[orig_idx, 'time'] = row['time']
                    data.at[orig_idx, 'activity'] = row['activity']
                    # coerce amount to float
                    try:
                        data.at[orig_idx, 'amount'] = float(row['amount'])
                    except:
                        data.at[orig_idx, 'amount'] = data.at[orig_idx, 'amount']
                    data.at[orig_idx, 'note'] = row.get('note', data.at[orig_idx, 'note'])
                    data.at[orig_idx, 'address'] = row.get('address', data.at[orig_idx, 'address'])
                save_data(data)
                st.success("✅ Lưu thay đổi thành công.")
                safe_rerun()
            except Exception as e:
                st.error("Lưu thay đổi thất bại: " + str(e))

        # Delete specific activities in this group
        # present choices with friendly labels
        choices = [f"{i+1}. {details.loc[i,'activity']} ({details.loc[i,'amount']} L) - {details.loc[i,'date']} {details.loc[i,'time']}" for i in range(len(details))]
        to_delete = st.multiselect("🗑️ Chọn các hoạt động để xóa (chỉ tác động tới hoạt động được chọn):", options=list(range(len(details))), format_func=lambda i: choices[i])
        if st.button("❌ Xóa hoạt động đã chọn"):
            if not to_delete:
                st.warning("Bạn chưa chọn hoạt động nào để xóa.")
            else:
                # map positions to orig indices
                indices_to_drop = [orig_indices[pos] for pos in to_delete]
                data = data.drop(indices_to_drop).reset_index(drop=True)
                save_data(data)
                st.success(f"✅ Đã xóa {len(indices_to_drop)} hoạt động.")
                safe_rerun()

        # Delete entire group
        if st.button("🗑️ Xóa toàn bộ nhóm này"):
            data = data[data['group_id'] != sel].reset_index(drop=True)
            save_data(data)
            st.success("✅ Đã xóa toàn bộ nhóm.")
            safe_rerun()

    return data

# ----------------- Dashboard -----------------
DEFAULT_ACTIVITIES = {
    "🚿 Tắm":50,"🧺 Giặt quần áo":70,"🍳 Nấu ăn":20,"🌱 Tưới cây":15,
    "🧹 Lau nhà":25,"🛵 Rửa xe máy":40,"🚗 Rửa ô tô":150,"🚲 Rửa xe đạp":10
}

def water_dashboard():
    set_background()
    st.markdown("<h2 style='color:#05595b;'>💧 Nhập dữ liệu về sử dụng nước</h2>", unsafe_allow_html=True)

    # load users & data
    users = load_users()
    data = load_data()
    data = ensure_group_ids(data)  # backfill group ids if missing

    username = st.session_state.username
    # get user info row if exists
    user_row = users[users['username']==username]
    if not user_row.empty:
        user_row = user_row.iloc[0]
    house_type = user_row.get('house_type', "") if not user_row.empty else ""
    location = user_row.get('location', "") if not user_row.empty else ""
    address_default = st.session_state.get('address', user_row.get('address',"") if not user_row.empty else "")
    daily_limit = float(st.session_state.get('daily_limit', user_row.get('daily_limit',200) if not user_row.empty else 200))
    reminder_times = st.session_state.get('reminder_times', user_row.get('reminder_times',"").split(",") if not user_row.empty else [])

    # reminders near time
    now = datetime.now()
    for t in reminder_times:
        try:
            h,m = map(int, (t or "00:00").split(":"))
            reminder_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            delta_minutes = abs((now - reminder_time).total_seconds()/60)
            if delta_minutes <=5:
                st.info(f"⏰ Nhắc nhở: Đến giờ nhập dữ liệu nước! (Khoảng {t})")
        except:
            continue

    # Input area
    st.subheader("📝 Ghi nhận hoạt động")
    left, right = st.columns([3,1])
    with left:
        activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys())+["➕ Khác"])
        if activity == "➕ Khác":
            custom = st.text_input("Nhập tên hoạt động:")
            if custom:
                activity = custom
        if "amount" not in st.session_state:
                st.session_state.amount = float(DEFAULT_ACTIVITIES.get(activity, 10))

        amount = st.number_input("Lượng nước (Lít)", min_value=0.000000001, step=0.00001, format="%.8f", value=st.session_state.amount, key="amount")
        date_input = st.date_input("📅 Ngày sử dụng", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())
        addr_input = st.text_input("🏠 Địa chỉ", value=address_default)

        note_quick = st.text_area("Ghi chú nhanh cho lần nhập này (tùy chọn):", height=80)

        if st.button("💾 Lưu hoạt động", use_container_width=True):
            if not activity:
                st.warning("Vui lòng chọn hoặc nhập hoạt động.")
            else:
                data = save_or_merge_entry(data, username, house_type, location, addr_input, activity, amount, note_quick, date_input)
                save_data(data)
                st.success("✅ Đã lưu hoạt động!")
                safe_rerun()

    with right:
        # quick summary
        st.markdown("**Tóm tắt hôm nay**")
        df_user = data[data['username']==username].copy()
        if not df_user.empty:
            df_user['datetime'] = pd.to_datetime(df_user['date'].astype(str) + " " + df_user['time'].astype(str), errors='coerce')
            today_sum = df_user[df_user['datetime'].dt.date == datetime.now().date()]['amount'].sum()
            st.metric("Tổng (L) hôm nay", f"{float(today_sum)} L")
        else:
            st.write("Chưa có dữ liệu")

    st.markdown("---")

    # Filters and Charts
    st.subheader("🔍 Bộ lọc & Biểu đồ")
    user_data_all = data[data['username']==username].copy()
    if not user_data_all.empty:
        user_data_all['datetime'] = pd.to_datetime(user_data_all['date'].astype(str) + " " + user_data_all['time'].astype(str), errors='coerce')
        all_addresses = user_data_all['address'].fillna('').unique().tolist()
        selected_addresses = st.multiselect("Chọn địa chỉ để phân tích", options=all_addresses, default=all_addresses)
        filtered_data = user_data_all[user_data_all['address'].isin(selected_addresses)].copy()

        time_frame = st.radio("Khoảng thời gian tổng kết", ["Tuần","Tháng"], horizontal=True)

        # Activity bar chart (no need to allocate since each row is single activity)
        st.markdown("**📊 Biểu đồ theo hoạt động (tổng Lít)**")
        if not filtered_data.empty:
            # backward-compatible: handle possible comma-separated activities
            exploded = explode_and_allocate(filtered_data, activity_col='activity', amount_col='amount')
            act_sum = exploded.groupby('activity_list')['alloc_amount'].sum().reset_index().rename(columns={'activity_list':'activity','alloc_amount':'total_lit'})
            act_sum = act_sum.sort_values('total_lit', ascending=False)
            chart1 = alt.Chart(act_sum).mark_bar().encode(
                x=alt.X('activity:N', sort='-y', title='Hoạt động'),
                y=alt.Y('total_lit:Q', title='Tổng Lít'),
                tooltip=['activity','total_lit'],
                color='activity:N'
            ).properties(height=320)
            st.altair_chart(chart1, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu cho bộ lọc hiện tại.")

        st.markdown("---")
        # Week/Month totals
        st.markdown("**📈 Tổng lượng theo khoảng (Tuần/Tháng)**")
        if not filtered_data.empty:
            if time_frame == 'Tuần':
                filtered_data['year'] = filtered_data['datetime'].dt.isocalendar().year
                filtered_data['week'] = filtered_data['datetime'].dt.isocalendar().week
                week_sum = filtered_data.groupby(['year','week'])['amount'].sum().reset_index()
                week_sum['label'] = week_sum['year'].astype(str) + '-W' + week_sum['week'].astype(str)
                chart2 = alt.Chart(week_sum).mark_bar().encode(
                    x=alt.X('label:N', sort='-y', title='Tuần'),
                    y=alt.Y('amount:Q', title='Tổng Lít'),
                    tooltip=['label','amount']
                ).properties(height=240)
                st.altair_chart(chart2, use_container_width=True)
            else:
                filtered_data['month'] = filtered_data['datetime'].dt.to_period('M').astype(str)
                month_sum = filtered_data.groupby('month')['amount'].sum().reset_index()
                chart2 = alt.Chart(month_sum).mark_bar().encode(
                    x=alt.X('month:N', sort='-y', title='Tháng'),
                    y=alt.Y('amount:Q', title='Tổng Lít'),
                    tooltip=['month','amount']
                ).properties(height=240)
                st.altair_chart(chart2, use_container_width=True)

        # download filtered csv
        st.download_button("📥 Tải dữ liệu phân tích (CSV)", filtered_data.to_csv(index=False), "water_usage_filtered.csv", "text/csv")
    else:
        st.info("Chưa có dữ liệu để hiển thị biểu đồ. Hãy nhập hoạt động trước.")

    st.markdown("---")

    # Grouped log & detail editor
    data = show_grouped_log_for_user(data, username)

    st.markdown("---")
    # Pet ảo
    st.subheader("🌱 Trạng thái cây ảo")
    user_data = data[data['username']==username].copy()
    today_data = user_data[pd.to_datetime(user_data['date']).dt.date == datetime.now().date()] if not user_data.empty else pd.DataFrame()
    today_usage = today_data['amount'].sum() if not today_data.empty else 0
    if today_usage < 0.8*daily_limit:
        pet_emoji, pet_color, pet_msg = "🌳","#3B82F6","Cây đang phát triển tươi tốt nha! 💚"
    elif today_usage <= 1.1*daily_limit:
        pet_emoji, pet_color, pet_msg = "🌿","#FACC15","Cây hơi héo mất rồi, hãy tiết kiệm thêm ⚠️"
    else:
        pet_emoji, pet_color, pet_msg = "🥀","#EF4444","Cây đang héo rồi, mai bạn trồng cây khác tươi tốt hơn nhé 😢"
    st.markdown(f"<div style='font-size:60px;text-align:center'>{pet_emoji}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='padding:14px;border-radius:12px;background:{pet_color};color:white;font-weight:bold;text-align:center;font-size:18px;'>{pet_msg}</div>", unsafe_allow_html=True)

    # Logout
    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.logged_in=False
        st.session_state.username=None
        safe_rerun()

# ----------------- Main -----------------
st.set_page_config(page_title="Water Loop App",
                   page_icon="💧",
                   layout="centered")

def main():
    # Đặt "Giới thiệu & Hướng dẫn" lên trước
    tab_intro, tab_dash = st.tabs(["Giới thiệu & Hướng dẫn", "Water Loop"])

    with tab_intro:
        about_tab()

    with tab_dash:
        if "logged_in" not in st.session_state or not st.session_state.logged_in:
            login_register()
        else:
            water_dashboard()

if __name__ == "__main__":
    main()
























