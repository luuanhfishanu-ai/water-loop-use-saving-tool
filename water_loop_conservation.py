import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

USERS_FILE = "users.csv"
DATA_FILE = "water_usage.csv"

# ----------------- Safe rerun -----------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.warning("⚠️ Phiên bản Streamlit của bạn không hỗ trợ rerun tự động.")

# ----------------- Gradient Background -----------------
def set_background():
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(120deg, #eff6ff, #dbeafe); }
        .stButton>button { background-color: #2563EB; color: white; border-radius: 10px; padding: 0.6em 1.2em; }
        </style>
        """, unsafe_allow_html=True
    )

# ----------------- Login & Register -----------------
def login_register():
    set_background()
    st.markdown("<h1 style='text-align:center;color:#05595b;'>💧 WATER LOOP 💧 </h1>", unsafe_allow_html=True)
    if not hasattr(st.session_state, "logged_in"):
        st.session_state.logged_in = False

    mode = st.radio("Chọn chế độ:", ["Đăng nhập", "Đăng ký"], horizontal=True)
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔒 Mật khẩu", type="password")

    # --- Load users ---
    try:
        users = pd.read_csv(USERS_FILE)
        if "address" not in users.columns:
            users["address"] = ""
    except FileNotFoundError:
        users = pd.DataFrame(columns=[
            "username","password","house_type","location","address","daily_limit","entries_per_day","reminder_times"
        ])

    if mode=="Đăng ký":
        default_house_types = ["Chung cư","Nhà riêng","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"]
        house_type = st.selectbox("🏠 Loại hộ gia đình", default_house_types + ["➕ Khác"])
        if house_type == "➕ Khác":
            house_type = st.text_input("Nhập loại nhà của bạn:")

        location = st.selectbox("📍 Khu vực", [
            "Tỉnh Tuyên Quang","Tỉnh Lào Cai","Tỉnh Thái Nguyên","Tỉnh Phú Thọ","Tỉnh Bắc Ninh","Tỉnh Hưng Yên",
            "Thành phố Hải Phòng","Tỉnh Ninh Bình","Tỉnh Quảng Trị","Thành phố Đà Nẵng","Tỉnh Quảng Ngãi",
            "Tỉnh Gia Lai","Tỉnh Khánh Hoà","Tỉnh Lâm Đồng","Tỉnh Đắk Lắk","Thành phố Hồ Chí Minh","Tỉnh Đồng Nai",
            "Tỉnh Tây Ninh","Thành phố Cần Thơ","Tỉnh Vĩnh Long","Tỉnh Đồng Tháp","Tỉnh Cà Mau","Tỉnh An Giang",
            "Thành phố Hà Nội","Thành phố Huế","Tỉnh Lai Châu","Tỉnh Điện Biên","Tỉnh Sơn La","Tỉnh Lạng Sơn",
            "Tỉnh Quảng Ninh","Tỉnh Thanh Hoá","Tỉnh Nghệ An","Tỉnh Hà Tĩnh","Tỉnh Cao Bằng"
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

    elif mode=="Đăng nhập":
        if st.button("Đăng nhập", use_container_width=True):
            user_row = users[(users["username"]==username)&(users["password"]==password)]
            if user_row.empty:
                st.error("❌ Sai tên đăng nhập hoặc mật khẩu.")
            else:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.daily_limit = user_row.iloc[0]["daily_limit"]
                st.session_state.entries_per_day = user_row.iloc[0]["entries_per_day"]
                st.session_state.reminder_times = user_row.iloc[0]["reminder_times"].split(",") if pd.notna(user_row.iloc[0]["reminder_times"]) else []
                st.session_state.address = user_row.iloc[0]["address"] if "address" in user_row.columns else ""
                st.success("✅ Đăng nhập thành công!")
                safe_rerun()

# ----------------- Dashboard -----------------
DEFAULT_ACTIVITIES = {
    "🚿 Tắm":50,"🧺 Giặt quần áo":70,"🍳 Nấu ăn":20,"🌱 Tưới cây":15,
    "🧹 Lau nhà":25,"🛵 Rửa xe máy":40,"🚗 Rửa ô tô":150,"🚲 Rửa xe đạp":10
}

# Hỗ trợ: chia đều số lượng cho nhiều hoạt động trong cùng 1 lần nhập
def explode_and_allocate(df, activity_col='activity', amount_col='amount'):
    df = df.copy()
    df['activity_list'] = df[activity_col].fillna('Không xác định').astype(str).str.split(', ')
    df = df.explode('activity_list')
    # mỗi dòng ban đầu có n hoạt động -> chia đều lượng nước cho mỗi hoạt động
    counts = df.groupby(df.index)['activity_list'].transform('count')
    df['alloc_amount'] = df[amount_col] / counts
    return df

# Lưu hoặc gộp vào nhóm nhập trong 30 phút
def save_or_merge_entry(data, username, house_type, location, addr_input, activity, amount, note_text, date_input):
    now = datetime.now()
    # đảm bảo có cột date/time
    if data.empty:
        data = pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount","note"]) 

    # chuẩn hóa một vài cột
    if 'note' not in data.columns:
        data['note'] = ""

    # tìm entry gần nhất của user
    user_entries = data[data['username']==username].copy()
    if not user_entries.empty:
        user_entries['datetime'] = pd.to_datetime(user_entries['date'].astype(str) + ' ' + user_entries['time'].astype(str))
        user_entries = user_entries.sort_values('datetime', ascending=False)
        last_idx = user_entries.index[0]
        last_dt = user_entries.loc[last_idx, 'datetime']
        if (now - last_dt) <= timedelta(minutes=30):
            # gộp
            existing_acts = str(data.at[last_idx, 'activity']) if pd.notna(data.at[last_idx, 'activity']) else ''
            existing_list = [a for a in existing_acts.split(', ') if a]
            if activity not in existing_list:
                existing_list.append(activity)
            data.at[last_idx, 'activity'] = ', '.join(existing_list)
            data.at[last_idx, 'amount'] = float(data.at[last_idx, 'amount']) + float(amount)
            data.at[last_idx, 'time'] = now.strftime("%H:%M:%S")
            data.at[last_idx, 'date'] = now.strftime("%Y-%m-%d")
            # note: nối nếu có
            existing_note = str(data.at[last_idx, 'note']) if pd.notna(data.at[last_idx, 'note']) else ''
            if note_text:
                if existing_note:
                    if note_text not in existing_note:
                        data.at[last_idx, 'note'] = existing_note + ' || ' + note_text
                else:
                    data.at[last_idx, 'note'] = note_text
            # cập nhật địa chỉ nếu khác
            if addr_input and addr_input != data.at[last_idx, 'address']:
                data.at[last_idx, 'address'] = addr_input
            return data, True

    # nếu không có entry gần hoặc user chưa có entry -> tạo mới
    new_entry = {
        "username": username,
        "house_type": house_type,
        "location": location,
        "address": addr_input,
        "date": date_input.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "activity": activity,
        "amount": float(amount),
        "note": note_text if note_text else ""
    }
    data = pd.concat([data, pd.DataFrame([new_entry])], ignore_index=True)
    return data, False


def water_dashboard():
    set_background()
    st.markdown("<h2 style='color:#05595b;'>💧 Nhập dữ liệu về sử dụng nước</h2>", unsafe_allow_html=True)

    # --- Load dữ liệu ---
    try:
        data = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        data = pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount","note"]) 

    username = st.session_state.username
    users = pd.read_csv(USERS_FILE)
    if "address" not in users.columns:
        users["address"] = ""
    user_info = users[users["username"]==username].iloc[0]

    house_type = user_info["house_type"]
    location = user_info["location"]
    address = user_info["address"] if "address" in user_info.index else ""
    daily_limit = float(st.session_state.daily_limit)
    reminder_times = st.session_state.reminder_times

    # --- Reminder ---
    now = datetime.now()
    for t in reminder_times:
        try:
            h,m = map(int, t.split(":"))
        except:
            continue
        reminder_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta_minutes = abs((now - reminder_time).total_seconds()/60)
        if delta_minutes <=5:
            st.info(f"⏰ Nhắc nhở: Đã đến giờ nhập dữ liệu nước! (Khoảng {t})")

    # --- Layout: trái (nhập + chart) | phải (ghi chú + bảng) ---
    left, right = st.columns([2,1])

    with left:
        st.subheader("📝 Ghi nhận hoạt động")
        col1, col2 = st.columns([3,1])
        with col1:
            activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys())+["➕ Khác"])        
            if activity=="➕ Khác":
                custom_act = st.text_input("Nhập tên hoạt động:")
                if custom_act:
                    activity = custom_act
        with col2:
            amount = st.number_input("Lượng nước (Lít)", min_value=1, value=DEFAULT_ACTIVITIES.get(activity,10))

        date_input = st.date_input("📅 Ngày sử dụng", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())
        addr_input = st.text_input("🏠 Địa chỉ", value=address)

        st.markdown("---")
        st.info("Ghi chú: Nếu trong vòng 30 phút bạn nhập nhiều lần, các hoạt động sẽ được gộp vào 1 lần nhập chung.")

        note_quick = st.text_area("Ghi chú nhanh cho lần nhập này (tùy chọn):", height=80)

        if st.button("💾 Lưu hoạt động", use_container_width=True):
            if not activity:
                st.warning("Vui lòng chọn hoặc nhập hoạt động.")
            else:
                data, merged = save_or_merge_entry(data, username, house_type, location, addr_input, activity, amount, note_quick, date_input)
                data.to_csv(DATA_FILE, index=False)
                if merged:
                    st.success("✅ Đã gộp vào lần nhập trước trong vòng 30 phút (cập nhật).")
                else:
                    st.success("✅ Đã lưu hoạt động mới!")
                safe_rerun()

        st.markdown("---")
        # --- Bộ lọc phân tích ---
        st.subheader("🔍 Bộ lọc & Biểu đồ")
        user_data_all = data[data['username']==username].copy()
        if not user_data_all.empty:
            user_data_all['datetime'] = pd.to_datetime(user_data_all['date'].astype(str) + ' ' + user_data_all['time'].astype(str))
            all_addresses = user_data_all['address'].fillna('').unique().tolist()
            selected_addresses = st.multiselect("Chọn địa chỉ để phân tích", options=all_addresses, default=all_addresses)
            filtered_data = user_data_all[user_data_all['address'].isin(selected_addresses)].copy()

            # Timeframe for totals chart
            time_frame = st.radio("Khoảng thời gian tổng kết", ["Tuần","Tháng"], horizontal=True)

            # --- Activity bar chart (phân bổ đều lượng nước khi 1 dòng có nhiều hoạt động) ---
            st.markdown("**📊 Biểu đồ theo hoạt động (tổng Lít)**")
            if not filtered_data.empty:
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
            # --- Tổng kết tuần/tháng (bar chart) ---
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

        else:
            st.info("Chưa có dữ liệu để hiển thị biểu đồ. Hãy nhập hoạt động trước.")

    with right:
        st.subheader("📝 Ghi chú nhanh & Nhật ký")
        # Quick note: gán cho lần nhập gần nhất
        note_for_last = st.text_area("Ghi chú cho lần nhập gần nhất (nhóm 30 phút):", height=120)
        if st.button("💾 Lưu ghi chú cho lần gần nhất", use_container_width=True):
            # cập nhật ghi chú cho entry gần nhất
            try:
                df_user = data[data['username']==username].copy()
                if df_user.empty:
                    st.warning("Chưa có hoạt động để gắn ghi chú.")
                else:
                    df_user['datetime'] = pd.to_datetime(df_user['date'].astype(str) + ' ' + df_user['time'].astype(str))
                    last_idx = df_user.sort_values('datetime', ascending=False).index[0]
                    old_note = str(data.at[last_idx, 'note']) if pd.notna(data.at[last_idx, 'note']) else ''
                    if note_for_last:
                        if old_note:
                            if note_for_last not in old_note:
                                data.at[last_idx, 'note'] = old_note + ' || ' + note_for_last
                        else:
                            data.at[last_idx, 'note'] = note_for_last
                        data.to_csv(DATA_FILE, index=False)
                        st.success('✅ Đã lưu ghi chú cho lần nhập gần nhất.')
                        safe_rerun()
                    else:
                        st.warning('⚠️ Ghi chú rỗng, vui lòng nhập nội dung.')
            except Exception as e:
                st.error('Có lỗi khi lưu ghi chú: ' + str(e))

        st.markdown('---')
        # --- Nhật ký / Data Editor ---
        st.subheader('📋 Nhật ký hoạt động')
        user_data = data[data['username']==username].copy()
        if not user_data.empty:
            user_data['datetime'] = pd.to_datetime(user_data['date'].astype(str) + ' ' + user_data['time'].astype(str))
            user_data = user_data.sort_values('datetime', ascending=False).reset_index()
            # user_data's reset_index added original index as "index" column
            # Tính tổng theo ngày
            daily_sum = user_data.groupby('date')['amount'].sum().to_dict()
            user_data['Tổng Lượng Ngày (L)'] = user_data['date'].map(daily_sum)

            def warning_label(amount):
                if amount < 0.8*daily_limit: return "💚 Ổn"
                elif amount <= 1.1*daily_limit: return "🟠 Gần ngưỡng"
                else: return "🔴 Vượt ngưỡng"
            user_data['Cảnh báo'] = user_data['Tổng Lượng Ngày (L)'].apply(warning_label)
            user_data['Xóa'] = False

            display_df = user_data[['date','time','activity','amount','Tổng Lượng Ngày (L)','Cảnh báo','note','address','index']].copy()
            display_df = display_df.rename(columns={'index':'_orig_index'})
            # ẩn cột _orig_index khi hiển thị nhưng giữ để map khi lưu/xóa
            edited = st.data_editor(
                display_df.drop(columns=['_orig_index']),
                use_container_width=True,
                num_rows='dynamic',
                hide_index=True
            )

            cols_editable = ['activity','amount','note','address','Xóa']
            # Nút lưu thay đổi
            if st.button('💾 Lưu thay đổi trong nhật ký'):
                try:
                    # lấy cột _orig_index để biết mapping; vì st.data_editor trả về dataframe reorder index 0..n-1,
                    # chúng ta sẽ lấy lại _orig_index từ display_df theo vị trí
                    orig_indices = display_df['_orig_index'].tolist()
                    for i, orig_idx in enumerate(orig_indices):
                        for col in cols_editable:
                            if col in edited.columns:
                                data.at[orig_idx, col] = edited.iloc[i][col]
                    data.to_csv(DATA_FILE, index=False)
                    st.success('✅ Lưu thay đổi thành công.')
                    safe_rerun()
                except Exception as e:
                    st.error('Lưu thay đổi thất bại: ' + str(e))

            if st.button('❌ Xóa các hoạt động đã chọn'):
                try:
                    orig_indices = display_df['_orig_index'].tolist()
                    # tìm hàng có Xóa True trong edited
                    to_delete_positions = [i for i,row in edited.iterrows() if ('Xóa' in edited.columns and row['Xóa']==True)]
                    if not to_delete_positions:
                        st.warning('⚠️ Bạn chưa chọn hoạt động nào để xóa.')
                    else:
                        indices_to_drop = [orig_indices[pos] for pos in to_delete_positions]
                        data = data.drop(indices_to_drop).reset_index(drop=True)
                        data.to_csv(DATA_FILE, index=False)
                        st.success(f'✅ Đã xóa {len(indices_to_drop)} hoạt động.')
                        safe_rerun()
                except Exception as e:
                    st.error('Xóa thất bại: ' + str(e))

            # Download filtered user data
            if st.button('📥 Tải toàn bộ nhật ký (CSV)'):
                st.download_button('Tải CSV', data[data['username']==username].to_csv(index=False), 'water_usage.csv', 'text/csv')

        else:
            st.info('Chưa có dữ liệu. Hãy nhập hoạt động để tạo nhật ký.')

        st.markdown('---')
        # --- Pet ảo ---
        st.subheader('🌱 Trồng cây ảo')
        today_data = data[(data['username']==username) & (pd.to_datetime(data['date']).dt.date == datetime.now().date())]
        today_usage = today_data['amount'].sum() if not today_data.empty else 0
        if today_usage < 0.8*daily_limit:
            pet_emoji, pet_color, pet_msg = "🌳","#3B82F6","Cây đang phát triển tươi tốt! 💚"
        elif today_usage <= 1.1*daily_limit:
            pet_emoji, pet_color, pet_msg = "🌿","#FACC15","Cây hơi héo, hãy tiết kiệm thêm ⚠️"
        else:
            pet_emoji, pet_color, pet_msg = "🥀","#EF4444","Cây đang héo 😢"
        st.markdown(f"<div style='font-size:60px;text-align:center'>{pet_emoji}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='padding:14px;border-radius:12px;background:{pet_color};color:white;font-weight:bold;text-align:center;font-size:18px;'>{pet_msg}</div>", unsafe_allow_html=True)

        # Logout
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.logged_in=False
            st.session_state.username=None
            safe_rerun()

# ----------------- Main -----------------
def main():
    st.set_page_config(page_title="Water Loop App", page_icon="💧", layout="centered")
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_register()
    else:
        water_dashboard()

if __name__=="__main__":
    main()


