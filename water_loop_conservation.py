import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

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

        location = st.text_input("📍 Khu vực (tỉnh/thành phố)")
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
    st.markdown("<h2 style='color:#05595b;'>💧 Nhập dữ liệu về sử dụng nước</h2>", unsafe_allow_html=True)

    # --- Load dữ liệu ---
    try:
        data = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        data = pd.DataFrame(columns=["username","house_type","location","address","date","time","activity","amount"])

    username = st.session_state.username
    users = pd.read_csv(USERS_FILE)
    if "address" not in users.columns:
        users["address"] = ""
    user_info = users[users["username"]==username].iloc[0]

    house_type = user_info["house_type"]
    location = user_info["location"]
    address = user_info["address"] if "address" in user_info.index else ""
    daily_limit = st.session_state.daily_limit
    reminder_times = st.session_state.reminder_times

    # --- Reminder ---
    now = datetime.now()
    for t in reminder_times:
        h,m = map(int, t.split(":"))
        reminder_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta_minutes = abs((now - reminder_time).total_seconds()/60)
        if delta_minutes <=5:
            st.info(f"⏰ Nhắc nhở: Đã đến giờ nhập dữ liệu nước! (Khoảng {t})")

    # --- Nhập dữ liệu ---
    st.subheader("📝 Ghi nhận hoạt động")
    col1,col2 = st.columns(2)
    with col1:
        activity = st.selectbox("Chọn hoạt động:", list(DEFAULT_ACTIVITIES.keys())+["➕ Khác"])
    with col2:
        if activity=="➕ Khác":
            custom_act = st.text_input("Nhập tên hoạt động:")
            if custom_act:
                activity = custom_act

    amount = st.number_input("Lượng nước đã dùng (Lít)", min_value=1, value=DEFAULT_ACTIVITIES.get(activity,10))
    date_input = st.date_input("📅 Ngày sử dụng", value=datetime.now().date())
    addr_input = st.text_input("🏠 Nhập địa chỉ", value=address)

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

    # --- Quản lý hoạt động ---
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

        # Editor
        edited_df = st.data_editor(
            user_data[["date","time","activity","amount","Tổng Lượng Ngày (L)","Cảnh báo","Xóa","address"]],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

        if st.button("❌ Xóa các hoạt động đã chọn"):
            to_delete = edited_df[edited_df["Xóa"]==True]
            if not to_delete.empty:
                indices_to_delete = user_data.loc[to_delete.index].index
                data = data.drop(indices_to_delete)
                data.to_csv(DATA_FILE,index=False)
                st.success(f"✅ Đã xóa {len(to_delete)} hoạt động!")
                safe_rerun()
            else:
                st.warning("⚠️ Bạn chưa chọn hoạt động nào để xóa.")

        # --- Biểu đồ theo hoạt động ---
        st.subheader("📊 Thống kê hoạt động")
        act_sum = user_data.groupby("activity")["amount"].sum().reset_index()
        chart = alt.Chart(act_sum).mark_bar().encode(
            x="activity", y="amount", tooltip=["activity","amount"],
            color="activity"
        ).properties(width=700,height=350)
        st.altair_chart(chart,use_container_width=True)

        # --- Pet ảo ---
        st.subheader("🌱 Trồng cây ảo")
        today_data = user_data[user_data["datetime"].dt.date==datetime.now().date()]
        today_usage = today_data["amount"].sum() if not today_data.empty else 0
        if today_usage < 0.8*daily_limit:
            pet_emoji, pet_color, pet_msg = "🌳","#d4f4dd","Cây đang phát triển tươi tốt! 💚"
        elif today_usage <= 1.1*daily_limit:
            pet_emoji, pet_color, pet_msg = "🌿","#ffe5b4","Cây hơi héo, hãy tiết kiệm thêm ⚠️"
        else:
            pet_emoji, pet_color, pet_msg = "🥀","#ffcccc","Cây đang héo 😢"
        st.markdown(f"<div style='font-size:60px;text-align:center'>{pet_emoji}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='padding:14px;border-radius:12px;background:{pet_color};color:white;font-weight:bold;text-align:center;font-size:18px;'>{pet_msg}</div>", unsafe_allow_html=True)

        # Download CSV
        st.download_button("📥 Tải dữ liệu CSV", user_data.to_csv(index=False),"water_usage.csv","text/csv")

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
