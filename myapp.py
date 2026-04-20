import pandas as pd
import plotly.express as px
import streamlit as st
import sqlite3
import hashlib
from sklearn.linear_model import LinearRegression

# ------------------ PAGE SETUP ------------------
st.set_page_config(page_title="SMART DATA INSIGHTS", page_icon="📈", layout="wide")

# ------------------ DATABASE ------------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# ------------------ TABLES ------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    username TEXT,
    action TEXT
)
""")
conn.commit()

# ------------------ FUNCTIONS ------------------
def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def log_action(user, action):
    cursor.execute("INSERT INTO logs VALUES (?, ?)", (user, action))
    conn.commit()

def add_user(username, password, role):
    cursor.execute("INSERT INTO users VALUES (?, ?, ?)", 
                   (username, make_hash(password), role))
    conn.commit()

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", 
                   (username, make_hash(password)))
    return cursor.fetchone()

def clean_column(col):
    col = col.strip()
    col = col.replace(" ", "_")
    col = col.replace("%", "percent")
    col = col.replace("(", "")
    col = col.replace(")", "")
    col = col.replace("-", "_")
    return col

def create_table(table_name, columns):
    clean_cols = [clean_column(col) for col in columns]
    cols = ", ".join([f'"{col}" TEXT' for col in clean_cols])
    cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols})')
    conn.commit()

def get_tables():
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [table[0] for table in cursor.fetchall()]

# ------------------ SESSION ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ------------------ SIDEBAR AUTH ------------------
st.sidebar.title("🔐 Authentication")
menu = st.sidebar.selectbox("Menu", ["Login", "Signup"])

if menu == "Signup":
    st.subheader("Create Account")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type='password')
    role = st.selectbox("Role", ["user", "admin"])

    if st.button("Signup"):
        try:
            add_user(new_user, new_pass, role)
            st.success("Account created ✅")
        except:
            st.error("User already exists")

elif menu == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user[0]
            st.session_state.role = user[2]
            st.success(f"Welcome {user[0]} 👋")
        else:
            st.error("Invalid Credentials")

# ------------------ LOGOUT ------------------
if st.session_state.logged_in:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        #st.experimental_rerun()
        st.session_state.clear()
        st.rerun()

# ================== MAIN APP ==================
if st.session_state.logged_in:

    st.title("📊 SMART DATA INSIGHTS")

    # ------------------ ADMIN PANEL ------------------
    if st.session_state.role == "admin":
        st.sidebar.subheader("🛠 Admin Panel")

        if st.sidebar.button("View Users"):
            users = pd.read_sql("SELECT username, role FROM users", conn)
            st.dataframe(users)

        del_user = st.sidebar.text_input("Delete User")
        if st.sidebar.button("Delete"):
            cursor.execute("DELETE FROM users WHERE username=?", (del_user,))
            conn.commit()
            st.success("User Deleted")

    # ------------------ FILE UPLOAD ------------------
    file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

    data = None

    if file is not None:
        if file.name.endswith("csv"):
            data = pd.read_csv(file)
        else:
            data = pd.read_excel(file)

        log_action(st.session_state.username, "Uploaded File")
        data.columns = [clean_column(col) for col in data.columns]

        st.dataframe(data)

        # ------------------ METRICS ------------------
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", data.shape[0])
        c2.metric("Columns", data.shape[1])
        c3.metric("Missing", data.isnull().sum().sum())

        # ------------------ CLEANING ------------------
        st.subheader("🧹 Data Cleaning")

        if st.checkbox("Remove Missing"):
            data = data.dropna()

        if st.checkbox("Remove Duplicates"):
            data = data.drop_duplicates()

        # ------------------ FILTER ------------------
        st.subheader("🔍 Filter Data")

        col = st.selectbox("Column", data.columns)
        val = st.text_input("Value")

        if st.button("Apply Filter"):
            data = data[data[col].astype(str).str.contains(val)]
            st.dataframe(data)

        # ------------------ SAVE ------------------
        st.subheader("💾 Save to Database")

        table_name = st.text_input("Table Name")

        if st.button("Save"):
            create_table(table_name, data.columns)

            for _, row in data.iterrows():
                placeholders = ", ".join(["?"] * len(row))
                cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", tuple(row.astype(str)))

            conn.commit()
            st.success("Saved to DB")

    # ------------------ LOAD DB ------------------
    st.subheader("📂 Load Data")

    tables = get_tables()

    if tables:
        selected = st.selectbox("Select Table", tables)

        if st.button("Load"):
            data = pd.read_sql(f"SELECT * FROM {selected}", conn)
            st.dataframe(data)

        if st.button("Delete Table"):
            cursor.execute(f"DROP TABLE {selected}")
            conn.commit()
            st.warning("Deleted")

    # ------------------ ANALYSIS ------------------
    if data is not None:

        st.subheader("📊 Analysis")

        st.dataframe(data.describe())

        # ------------------ KPIs ------------------
        st.subheader("📈 KPIs")

        num_cols = data.select_dtypes(include='number').columns

        if len(num_cols) > 0:
            kpi_col = st.selectbox("Select Column", num_cols)

            c1, c2, c3 = st.columns(3)
            c1.metric("Mean", round(data[kpi_col].mean(),2))
            c2.metric("Max", data[kpi_col].max())
            c3.metric("Min", data[kpi_col].min())

        # ------------------ GROUPBY ------------------
        st.subheader("📊 Groupby")

        g_cols = st.multiselect("Group Columns", data.columns)
        op_col = st.selectbox("Operation Column", data.columns)
        op = st.selectbox("Operation", ["sum","mean","max","min"])

        if g_cols:
            result = data.groupby(g_cols).agg({op_col:op}).reset_index()
            st.dataframe(result)
        else:
            result = data

        # ------------------ VISUALIZATION ------------------
        st.subheader("📊 Visualization")

        chart = st.selectbox("Chart", ["line","bar","scatter","pie"])

        x = st.selectbox("X Axis", result.columns)
        y = st.selectbox("Y Axis", result.columns)

        if chart == "line":
            st.plotly_chart(px.line(result, x=x, y=y))

        elif chart == "bar":
            st.plotly_chart(px.bar(result, x=x, y=y))

        elif chart == "scatter":
            st.plotly_chart(px.scatter(result, x=x, y=y))

        elif chart == "pie":
            st.plotly_chart(px.pie(result, names=x, values=y))

        # ------------------ ML MODEL ------------------
        st.subheader("🤖 Prediction")

        if len(num_cols) > 1:
            target = st.selectbox("Target", num_cols)

            if st.button("Train Model"):
                df = data[num_cols].dropna()
                X = df.drop(columns=[target])
                y = df[target]

                model = LinearRegression()
                model.fit(X, y)

                st.success("Model Trained ✅")

        # ------------------ EXPORT ------------------
        st.subheader("📥 Export")

        st.download_button("Download CSV", data.to_csv(index=False), "data.csv")

else:
    st.warning("🔒 Please login")
