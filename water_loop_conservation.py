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
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(120deg, #a1c4fd, #c2e9fb); }
        .stButton>button { background-color: #70c1b3; color: white; border-radius: 8px; padding: 0.5em 1em; }
        </style>
        """, unsafe_allow_html=True)

# ----------------- Login & Register -----------------
def login_register():
    set_background()
    st.markdown("<h1 style='text-align:center;color:#05595b;'>💧 WATER LOOP 💧 </h1>", unsafe_allow_html=True)
    if not hasattr(st.session_state, "logged_in"):
        st.session_state.logged_in = False

    mode = st.radio("Chọn chế độ:", ["Đăng nhập", "Đăng ký"], horizontal=True)
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔒 Mật khẩu", type="password")

    # --- Đọc file users.csv, nếu thiếu cột address thì tạo mặc định ---
    try:
        users = pd.read_csv(USERS_FILE)
        if "address" not in users.columns:
            users["address"] = ""  # thêm cột trống nếu chưa có
    except FileNotFoundError:
        users = pd.DataFrame(columns=[
            "username","password","house_type","location","address","daily_limit","entries_per_day","reminder_times"
        ])

    if mode=="Đăng ký":
        default_house_types = ["Chung cư","Nhà riêng","Khác","Biệt thự","Nhà trọ","Khu tập thể","Kí túc xá"]
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

def water_dashboard():
    set_background()
    st.markdown("<h2 style='color:#05595b;'>💧 Dashboard sử dụng nước</h2>", unsafe_allow_html=True)

    # --- Load dữ liệu ---
    try:
        data = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        data = pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount"])

    username = st.session_state.username
    users = pd.read_csv(USERS_FILE)
    user_info = users[users["username"]==username].iloc[0]
    house_type = user_info["house_type"]
    location = user_info["location"]
    address = user_info["address"]
    daily_limit = st.session_state.daily_limit
    entries_per_day = st.session_state.entries_per_day
    reminder_times = st.session_state.reminder_times

    # --- Nhắc nhở giờ ±5 phút ---
    now = datetime.now()
    for t in reminder_times:
        h, m = map(int, t.split(":"))
        reminder_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta_minutes = abs((now - reminder_time).total_seconds()/60)
        if delta_minutes <= 5:
            st.info(f"⏰ Nhắc nhở: Đã đến giờ nhập dữ liệu nước! (Khoảng {t})")

    # --- Ghi nhận hoạt động ---
    st.subheader("📝 Ghi nhận hoạt động")
    col1, col2 = st.columns(2)
    with col1:
        activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys())+["➕ Khác"])
    with col2:
        if activity=="➕ Khác":
            custom_act = st.text_input("Nhập tên hoạt động:")
            if custom_act:
                activity = custom_act

    amount = st.number_input("Lượng nước đã dùng (Lít)", min_value=1, value=DEFAULT_ACTIVITIES.get(activity,10))
    date_input = st.date_input("📅 Ngày sử dụng", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())
    addr_input = st.text_input("🏠 Nhập địa chỉ (sửa nếu khác địa chỉ đăng ký)", value=address)

    if st.button("💾 Lưu hoạt động", use_container_width=True):
        new_entry = pd.DataFrame([{
            "username": username,
            "house_type": house_type,
            "location": location,
            "address": addr_input,
            "date": date_input.strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "activity": activity,
            "amount": amount
        }])
        data = pd.concat([data,new_entry], ignore_index=True)
        data.to_csv(DATA_FILE,index=False)
        st.success("✅ Đã lưu hoạt động!")
        safe_rerun()

    # --- Quản lý & xóa hoạt động ---
    st.subheader("🗑️ Quản lý hoạt động")
    user_data = data[data["username"]==username].copy()
    if not user_data.empty:
        user_data["datetime"] = pd.to_datetime(user_data["date"] + " " + user_data["time"])
        user_data = user_data.sort_values("datetime", ascending=False).reset_index(drop=True)

        # Tính tổng lượng nước mỗi ngày
        daily_sum = user_data.groupby("date")["amount"].sum().to_dict()
        user_data["Tổng Lượng Ngày (L)"] = user_data["date"].map(daily_sum)

        def warning_label(amount):
            if amount < 0.8*daily_limit: return "💚 Ổn"
            elif amount <= 1.1*daily_limit: return "🟠 Gần ngưỡng"
            else: return "🔴 Vượt ngưỡng"
        user_data["Cảnh báo"] = user_data["Tổng Lượng Ngày (L)"].apply(warning_label)
        user_data["Xóa"] = False

        # --- Data editor để xóa hoặc sửa ---
        def row_color(row):
            if "💚" in row["Cảnh báo"]: return ["#d4f4dd"]*9
            elif "🟠" in row["Cảnh báo"]: return ["#ffe5b4"]*9
            else: return ["#ffcccc"]*9
        row_colors = [row_color(r) for _, r in user_data.iterrows()]

        edited_df = st.data_editor(
            user_data[["date","time","activity","amount","Tổng Lượng Ngày (L)","Cảnh báo","Xóa","address"]],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            row_colors=row_colors
        )

        if st.button("❌ Xóa các hoạt động đã chọn"):
            to_delete = edited_df[edited_df["Xóa"]==True]
            if not to_delete.empty:
                indices_to_delete = user_data.loc[to_delete.index].index
                data = data.drop(indices_to_delete)
                data.to_csv(DATA_FILE, index=False)
                st.success(f"✅ Đã xóa {len(to_delete)} hoạt động!")
                safe_rerun()
            else:
                st.warning("⚠️ Bạn chưa chọn hoạt động nào để xóa.")

        # --- Bộ lọc địa chỉ và thời gian ---
        st.subheader("🔍 Bộ lọc phân tích")
        all_addresses = user_data["address"].unique().tolist()
        selected_addresses = st.multiselect("Chọn địa chỉ", options=all_addresses, default=all_addresses)
        filtered_data = user_data[user_data["address"].isin(selected_addresses)]

        # Chọn khoảng thời gian: tuần/tháng
        time_frame = st.radio("Chọn khoảng thời gian", ["Tuần", "Tháng"], horizontal=True)

        if time_frame=="Tuần":
            filtered_data["year"] = filtered_data["datetime"].dt.isocalendar().year
            filtered_data["week"] = filtered_data["datetime"].dt.isocalendar().week
            week_sum = filtered_data.groupby(["address","year","week"])["amount"].sum().reset_index()
            week_sum["year_week"] = week_sum["year"].astype(str) + "-W" + week_sum["week"].astype(str)
            chart_week = alt.Chart(week_sum).mark_line(point=True).encode(
                x="year_week",
                y="amount",
                color="address:N",
                tooltip=["address","year_week","amount"]
            ).properties(width=700, height=350)
            st.altair_chart(chart_week, use_container_width=True)
        else:  # Tháng
            filtered_data["month"] = filtered_data["datetime"].dt.to_period("M").astype(str)
            month_sum = filtered_data.groupby(["address","month"])["amount"].sum().reset_index()
            chart_month = alt.Chart(month_sum).mark_line(point=True).encode(
                x="month",
                y="amount",
                color="address:N",
                tooltip=["address","month","amount"]
            ).properties(width=700, height=350)
            st.altair_chart(chart_month, use_container_width=True)

        # --- Pet ảo ---
        st.subheader("🌱 Trồng cây ảo")
        today_data = user_data[user_data["datetime"].dt.date==datetime.now().date()]
        today_usage = today_data["amount"].sum() if not today_data.empty else 0
        if today_usage < 0.8*daily_limit:
            pet_emoji, pet_color, pet_msg = "🌳", "#d4f4dd", "Cây đang phát triển tươi tốt! 💚"
        elif today_usage <= 1.1*daily_limit:
            pet_emoji, pet_color, pet_msg = "🌿", "#ffe5b4", "Cây hơi héo, hãy tiết kiệm thêm ⚠️"
        else:
            pet_emoji, pet_color, pet_msg = "🥀", "#ffcccc", "Cây đang héo 😢"

        st.markdown(f"<div style='font-size:60px;text-align:center'>{pet_emoji}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='padding:14px;border-radius:12px;background:{pet_color};color:white;font-weight:bold;text-align:center;font-size:18px;'>{pet_msg}</div>", unsafe_allow_html=True)

        # --- Download CSV ---
        st.download_button("📥 Tải dữ liệu CSV", filtered_data.to_csv(index=False), "water_usage.csv", "text/csv")

    # --- Logout ---
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

