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
        .stApp {
            background: linear-gradient(120deg, #a1c4fd, #c2e9fb);
        }
        .stButton>button {
            background-color: #70c1b3;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1em;
        }
        </style>
        """, unsafe_allow_html=True
    )

# ----------------- Login & Register -----------------
def login_register():
    set_background()
    st.markdown("<h1 style='text-align:center;color:#05595b;'>💧 Ứng dụng tiết kiệm nước</h1>", unsafe_allow_html=True)
    if not hasattr(st.session_state, "logged_in"):
        st.session_state.logged_in = False

    mode = st.radio("Chọn chế độ:", ["Đăng nhập", "Đăng ký"], horizontal=True)
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔒 Mật khẩu", type="password")

    try:
        users = pd.read_csv(USERS_FILE)
    except FileNotFoundError:
        users = pd.DataFrame(columns=["username","password","house_type","location","daily_limit","entries_per_day"])

    if mode=="Đăng ký":
        house_type = st.selectbox("🏠 Loại hộ gia đình", ["Chung cư","Nhà riêng","Khác"])
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
                    "entries_per_day": entries_per_day
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
                st.success("✅ Đăng nhập thành công!")
                safe_rerun()

# ----------------- Dashboard -----------------
DEFAULT_ACTIVITIES = {"🚿 Tắm":50,"🧺 Giặt quần áo":70,"🍳 Nấu ăn":20,"🌱 Tưới cây":15,"🧹 Lau nhà":25,"🛵 Rửa xe máy":40,"🚗 Rửa ô tô":150,"🚲 Rửa xe đạp":10}

def water_dashboard():
    set_background()
    st.markdown("<h2 style='color:#05595b;'>💧 Dashboard sử dụng nước</h2>", unsafe_allow_html=True)

    try:
        data = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        data = pd.DataFrame(columns=["username","house_type","location","date","activity","amount"])

    username = st.session_state.username
    users = pd.read_csv(USERS_FILE)
    user_info = users[users["username"]==username].iloc[0]
    house_type = user_info["house_type"]
    location = user_info["location"]
    daily_limit = st.session_state.daily_limit
    entries_per_day = st.session_state.entries_per_day

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

    if st.button("💾 Lưu hoạt động", use_container_width=True):
        new_entry = pd.DataFrame([{"username": username,"house_type": house_type,"location": location,"date": date_input.strftime("%Y-%m-%d"),"activity": activity,"amount": amount}])
        data = pd.concat([data,new_entry], ignore_index=True)
        data.to_csv(DATA_FILE,index=False)
        st.success("✅ Đã lưu hoạt động!")

    st.subheader("📊 Thống kê sử dụng nước")
    user_data = data[data["username"]==username]
    today = datetime.now().strftime("%Y-%m-%d")
    today_entries = user_data[user_data["date"]==today].shape[0]

    # Nhắc nhở nhập đủ số lần
    if today_entries < entries_per_day:
        st.warning(f"⚠️ Bạn chưa nhập đủ {entries_per_day} lần hôm nay ({today_entries}/{entries_per_day}).")
    else:
        st.success(f"✅ Bạn đã nhập đủ {entries_per_day} lần hôm nay.")

    if not user_data.empty:
        today_usage = user_data[user_data["date"]==today]["amount"].sum()

        # Card màu gradient theo ngưỡng 80-110%
        if today_usage < 0.8*daily_limit:
            color, msg, pet = "lightgreen", "Rất tiết kiệm 👏", "🌳"
        elif today_usage <= 1.1*daily_limit:
            color, msg, pet = "orange", "Cần chú ý ⚠️", "🌿"
        else:
            color, msg, pet = "red", "Đã vượt ngưỡng ❌", "🥀"

        st.markdown(
            f"<div style='padding:14px;border-radius:12px;background:{color};color:white;font-weight:bold;text-align:center;font-size:18px;'>💧 Hôm nay: {today_usage} L - {msg} {pet}</div>",
            unsafe_allow_html=True
        )

        # Progress bar
        st.write("### 🚰 Tiến độ sử dụng hôm nay")
        st.progress(min(today_usage/daily_limit,1.0))
        st.write(f"💧 {today_usage}/{daily_limit} L")

        # Bar chart hoạt động
        act_sum = user_data.groupby("activity")["amount"].sum().reset_index()
        bar_chart = alt.Chart(act_sum).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("activity", sort=None),
            y="amount",
            color=alt.Color("activity", scale=alt.Scale(scheme="pastel1"), legend=None),
            tooltip=["activity","amount"]
        ).properties(width=700, height=350)
        st.altair_chart(bar_chart,use_container_width=True)

        # Line chart theo ngày
        day_sum = user_data.groupby("date")["amount"].sum().reset_index()
        line_chart = alt.Chart(day_sum).mark_line(point=True, color="#05595b").encode(
            x="date",
            y="amount",
            tooltip=["date","amount"]
        ).properties(width=700, height=350)
        st.altair_chart(line_chart,use_container_width=True)

        # Pet ảo animation đơn giản
        st.subheader("🐟 Pet ảo")
        st.markdown(f"<div style='font-size:60px;text-align:center'>{pet}</div>", unsafe_allow_html=True)
        if today_usage < 0.8*daily_limit:
            st.success("Cây đang phát triển tươi tốt!")
        elif today_usage <= 1.1*daily_limit:
            st.warning("Cây hơi héo, hãy tiết kiệm thêm nhé.")
        else:
            st.error("Cây đang héo / Cá buồn 😢")

        st.download_button("📥 Tải dữ liệu CSV", user_data.to_csv(index=False),"water_usage.csv","text/csv")

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
