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

# ----------------- Login & Register -----------------
def login_register():
    st.title("🔑 Đăng nhập / Đăng ký")
    if not hasattr(st.session_state, "logged_in"):
        st.session_state.logged_in = False

    mode = st.radio("Chọn chế độ:", ["Đăng nhập", "Đăng ký"])
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔒 Mật khẩu", type="password")

    try:
        users = pd.read_csv(USERS_FILE)
    except FileNotFoundError:
        users = pd.DataFrame(columns=["username", "password", "house_type", "location"])

    if mode == "Đăng ký":
        house_type = st.selectbox("🏠 Loại hộ gia đình", ["Chung cư", "Nhà riêng", "Khác"])
        location = st.selectbox("📍 Khu vực", ["Tỉnh Tuyên Quang","Tỉnh Lào Cai","Tỉnh Thái Nguyên","Tỉnh Phú Thọ","Tỉnh Bắc Ninh","Tỉnh Hưng Yên","Thành phố Hải Phòng","Tỉnh Ninh Bình","Tỉnh Quảng Trị","Thành phố Đà Nẵng","Tỉnh Quảng Ngãi","Tỉnh Gia Lai","Tỉnh Khánh Hoà","Tỉnh Lâm Đồng","Tỉnh Đắk Lắk","Thành phố Hồ Chí Minh","Tỉnh Đồng Nai","Tỉnh Tây Ninh","Thành phố Cần Thơ","Tỉnh Vĩnh Long","Tỉnh Đồng Tháp","Tỉnh Cà Mau","Tỉnh An Giang","Thành phố Hà Nội","Thành phố Huế","Tỉnh Lai Châu","Tỉnh Điện Biên","Tỉnh Sơn La","Tỉnh Lạng Sơn","Tỉnh Quảng Ninh","Tỉnh Thanh Hoá","Tỉnh Nghệ An","Tỉnh Hà Tĩnh","Tỉnh Cao Bằng"])
        if st.button("Đăng ký"):
            if username in users["username"].values:
                st.error("❌ Tên đăng nhập đã tồn tại.")
            else:
                new_user = pd.DataFrame([{"username": username,"password": password,"house_type": house_type,"location": location}])
                users = pd.concat([users, new_user], ignore_index=True)
                users.to_csv(USERS_FILE, index=False)
                st.success("✅ Đăng ký thành công, vui lòng đăng nhập.")

    elif mode == "Đăng nhập":
        if st.button("Đăng nhập"):
            if users[(users["username"]==username)&(users["password"]==password)].empty:
                st.error("❌ Sai tên đăng nhập hoặc mật khẩu.")
            else:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ Đăng nhập thành công!")
                safe_rerun()

# ----------------- Dashboard -----------------
DEFAULT_ACTIVITIES = {"🚿 Tắm":50,"🧺 Giặt quần áo":70,"🍳 Nấu ăn":20,"🌱 Tưới cây":15,"🧹 Lau nhà":25,"🛵 Rửa xe máy":40,"🚗 Rửa ô tô":150,"🚲 Rửa xe đạp":10}

def water_dashboard():
    st.title("💧 Ứng dụng tiết kiệm nước")
    st.write("Theo dõi và cải thiện thói quen sử dụng nước của bạn.")

    try:
        data = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        data = pd.DataFrame(columns=["username","house_type","location","date","activity","amount"])

    username = st.session_state.username
    users = pd.read_csv(USERS_FILE)
    user_info = users[users["username"]==username].iloc[0]
    house_type = user_info["house_type"]
    location = user_info["location"]

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
    date_input = st.date_input("📅 Ngày sử dụng", value=datetime.now().date(), min_value=datetime(2020,1,1).date(), max_value=datetime.now().date())

    if st.button("💾 Lưu"):
        new_entry = pd.DataFrame([{"username": username,"house_type": house_type,"location": location,"date": date_input.strftime("%Y-%m-%d"),"activity": activity,"amount": amount}])
        data = pd.concat([data,new_entry], ignore_index=True)
        data.to_csv(DATA_FILE,index=False)
        st.success("✅ Đã lưu hoạt động!")

    st.subheader("📊 Thống kê sử dụng nước")
    user_data = data[data["username"]==username]

    if not user_data.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        today_usage = user_data[user_data["date"]==today]["amount"].sum()

        if today_usage<100: color,msg="green","Rất tiết kiệm 👏"
        elif today_usage<200: color,msg="orange","Cần chú ý ⚠️"
        else: color,msg="red","Đã vượt ngưỡng ❌"

        st.markdown(f"<div style='padding:10px;border-radius:10px;background:{color};color:white'>💧 Hôm nay: {today_usage} L - {msg}</div>",unsafe_allow_html=True)

        daily_limit = 200
        st.write("### 🚰 Tiến độ sử dụng hôm nay")
        st.progress(min(today_usage/daily_limit,1.0))
        st.write(f"💧 {today_usage}/{daily_limit} L")

        # Biểu đồ màu sắc theo hoạt động
        st.write("### 📌 Tỷ lệ theo hoạt động")
        act_sum = user_data.groupby("activity")["amount"].sum().reset_index()
        bar_chart = alt.Chart(act_sum).mark_bar().encode(
            x=alt.X("activity", sort=None),
            y="amount",
            color=alt.Color("activity", legend=None)
        ).properties(width=700)
        st.altair_chart(bar_chart,use_container_width=True)

        # Biểu đồ theo ngày
        st.write("### 📅 So sánh theo ngày")
        day_sum = user_data.groupby("date")["amount"].sum().reset_index()
        line_chart = alt.Chart(day_sum).mark_line(point=True).encode(
            x="date",
            y="amount",
            color=alt.value("blue")
        ).properties(width=700)
        st.altair_chart(line_chart,use_container_width=True)

        st.subheader("🐟 Pet ảo")
        if today_usage<100: st.success("🌳 Cây đang phát triển tươi tốt!")
        elif today_usage<200: st.warning("🌿 Cây hơi héo, hãy tiết kiệm thêm nhé.")
        else: st.error("🥀 Cây đang héo / Cá buồn 😢")

        st.download_button("📥 Tải dữ liệu CSV", user_data.to_csv(index=False),"water_usage.csv","text/csv")
    else:
        st.info("Chưa có dữ liệu nào. Hãy nhập hoạt động trước.")

    if st.button("🚪 Đăng xuất"):
        st.session_state.logged_in=False
        st.session_state.username=None
        safe_rerun()

def main():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_register()
    else:
        water_dashboard()

if __name__=="__main__":
    main()
