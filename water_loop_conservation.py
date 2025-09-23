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
        .stApp { background: linear-gradient(120deg, #a1c4fd, #c2e9fb); }
        .stButton>button { background-color: #70c1b3; color: white; border-radius: 8px; padding: 0.5em 1em; }
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

    try:
        users = pd.read_csv(USERS_FILE)
    except FileNotFoundError:
        users = pd.DataFrame(columns=[
            "username","password","house_type","location","daily_limit","entries_per_day","reminder_times"
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
        daily_limit = st.number_input("⚖️ Ngưỡng nước hàng ngày (Lít)", min_value=50, value=200)
        entries_per_day = st.slider("🔔 Số lần nhập dữ liệu/ngày", 1, 5, 3)

        reminder_times = st.multiselect(
            "⏰ Chọn giờ nhắc nhở trong ngày",
            options=[f"{h:02d}:00" for h in range(0,24)],
            default=["08:00","12:00","18:00"]
        )

        if st.button("Đăng ký", use_container_width=True):
            if username in users["username"].values:
                st.error("❌ Tên đăng nhập đã tồn tại.")
            else:
                new_user = pd.DataFrame([{
                    "username": username,
                    "password": password,
                    "house_type": house_type,
                    "location": location,
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
        data = pd.DataFrame(columns=["username","house_type","location","date","time","activity","amount"])

    username = st.session_state.username
    users = pd.read_csv(USERS_FILE)
    user_info = users[users["username"]==username].iloc[0]
    house_type = user_info["house_type"]
    location = user_info["location"]
    daily_limit = st.session_state.daily_limit
    entries_per_day = st.session_state.entries_per_day
    reminder_times = st.session_state.reminder_times

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

    if st.button("💾 Lưu hoạt động", use_container_width=True):
        new_entry = pd.DataFrame([{
            "username": username,
            "house_type": house_type,
            "location": location,
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
        daily_sum = user_data.groupby("date")["amount"].sum().to_dict()
        user_data["Tổng Lượng Ngày (L)"] = user_data["date"].map(daily_sum)
        def warning_label(amount):
            if amount < 0.8*daily_limit: return "💚 Ổn"
            elif amount <= 1.1*daily_limit: return "🟠 Gần ngưỡng"
            else: return "🔴 Vượt ngưỡng"
        user_data["Cảnh báo"] = user_data["Tổng Lượng Ngày (L)"].apply(warning_label)
        user_data["Xóa"] = False
        def row_color(row):
            if "💚" in row["Cảnh báo"]: return ["#d4f4dd"]*len(row)
            elif "🟠" in row["Cảnh báo"]: return ["#ffe5b4"]*len(row)
            else: return ["#ffcccc"]*len(row)
        row_colors = user_data.apply(row_color, axis=1)
        edited_df = st.data_editor(
            user_data[["date","time","activity","amount","Tổng Lượng Ngày (L)","Cảnh báo","Xóa"]],
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
    else:
        st.info("Chưa có dữ liệu nào để xóa.")

    # --- Thống kê ---
    st.subheader("📊 Thống kê sử dụng nước")
    if user_data.empty:
        st.info("Chưa có dữ liệu nào. Hãy nhập hoạt động để bắt đầu theo dõi!")
        return

    user_data["datetime"] = pd.to_datetime(user_data["date"] + " " + user_data["time"])
    today = datetime.now().date()
    today_data = user_data[user_data["datetime"].dt.date==today].copy()
    today_data = today_data.sort_values("datetime")
    today_data["entry_group"] = (today_data["datetime"].diff().dt.total_seconds().fillna(999)/60 > 30).cumsum()
    today_entries = today_data["entry_group"].nunique()
    today_usage = today_data["amount"].sum()
    if today_entries < entries_per_day:
        st.warning(f"⚠️ Bạn chưa nhập đủ {entries_per_day} lần hôm nay ({today_entries}/{entries_per_day}).")
    else:
        st.success(f"✅ Bạn đã nhập đủ {entries_per_day} lần hôm nay.")

    # --- Pet ảo trực quan ---
    st.subheader("🌱 Trồng cây ảo (Trực quan)")
    if today_usage < 0.8*daily_limit:
        pet_emoji, pet_color, pet_msg = "🌳", "#d4f4dd", "Cây đang phát triển tươi tốt! 💚"
    elif today_usage <= 1.1*daily_limit:
        pet_emoji, pet_color, pet_msg = "🌿", "#ffe5b4", "Cây hơi héo, hãy tiết kiệm thêm nhé. 🟠"
    else:
        pet_emoji, pet_color, pet_msg = "🥀", "#ffcccc", "Cây đang héo! 🔴 Hãy chú ý sử dụng nước."
    st.markdown(
        f"<div style='padding:20px;border-radius:12px;background:{pet_color};text-align:center;font-size:80px'>{pet_emoji}</div>",
        unsafe_allow_html=True
    )
    st.markdown(f"<div style='text-align:center;font-size:18px;font-weight:bold'>{pet_msg}</div>", unsafe_allow_html=True)

    # --- Biểu đồ bar/pie trực quan ---
    act_today_sum = today_data.groupby("activity")["amount"].sum().reset_index()
    act_today_sum = act_today_sum.sort_values("amount", ascending=False)
    if today_usage < 0.8*daily_limit: bar_color_value = "#77dd77"
    elif today_usage <= 1.1*daily_limit: bar_color_value = "#ffb347"
    else: bar_color_value = "#ff6961"
    bar_chart = alt.Chart(act_today_sum).mark_bar(color=bar_color_value).encode(
        x=alt.X("amount:Q", title="Lượng nước (Lít)"),
        y=alt.Y("activity:N", sort="-x", title="Hoạt động"),
        tooltip=["activity","amount"]
    ).properties(height=300)
    st.altair_chart(bar_chart, use_container_width=True)

    week_start = today - timedelta(days=6)
    week_data = user_data[(user_data["datetime"].dt.date >= week_start) & (user_data["datetime"].dt.date <= today)]
    week_sum = week_data.groupby("date")["amount"].sum().reset_index()
    def week_status_color(x):
        if x <= daily_limit*0.8: return "#77dd77"
        elif x <= daily_limit*1.1: return "#ffb347"
        else: return "#ff6961"
    week_sum["color"] = week_sum["amount"].apply(week_status_color)
    week_sum["status"] = week_sum["amount"].apply(lambda x: "Cây xanh" if x <= daily_limit else "Cây héo")
    pie_week = alt.Chart(week_sum).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("amount", type="quantitative"),
        color=alt.Color("color:N", scale=None),
        tooltip=["date","amount","status"]
    )
    st.altair_chart(pie_week, use_container_width=True)

    user_data["year"] = user_data["datetime"].dt.isocalendar().year
    user_data["week"] = user_data["datetime"].dt.isocalendar().week
    week_line = user_data.groupby(["year","week"])["amount"].sum().reset_index()
    week_line["year_week"] = week_line["year"].astype(str) + "-W" + week_line["week"].astype(str)
    line_chart = alt.Chart(week_line).mark_line(point=True, color="#05595b").encode(
        x="year_week", y="amount", tooltip=["year_week","amount"]
    ).properties(width=700, height=350)
    st.altair_chart(line_chart,use_container_width=True)

    # --- Download CSV ---
    st.download_button("📥 Tải dữ liệu CSV", user_data.to_csv(index=False), "water_usage.csv", "text/csv")

    # --- Nhắc nhở popup nếu vượt ngưỡng ---
    if today_usage > daily_limit:
        st.warning(f"⚠️ Hôm nay bạn đã vượt ngưỡng {daily_limit} L! ({today_usage} L) Hãy tiết kiệm nước nhé!")
    elif today_usage >= 0.8*daily_limit:
        st.info(f"ℹ️ Bạn đã dùng gần ngưỡng hôm nay: {today_usage} L / {daily_limit} L")

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
