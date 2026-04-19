import pandas as pd
import plotly.express as px
import streamlit as st
import sqlite3
import hashlib

# ------------------ PAGE SETUP ------------------
st.set_page_config(
    page_title="SMART DATA INSIGHTS",
    page_icon="📈",
    layout="wide"
)

# ------------------ DATABASE SETUP ------------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# ------------------ USER TABLE ------------------
def create_user_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    conn.commit()

create_user_table()

# ------------------ HASH FUNCTION ------------------
def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------ AUTH FUNCTIONS ------------------
def add_user(username, password):
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                   (username, make_hash(password)))
    conn.commit()

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", 
                   (username, make_hash(password)))
    return cursor.fetchone()

# ------------------ SESSION ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ------------------ SIDEBAR LOGIN ------------------
st.sidebar.title("🔐 Authentication")
menu = st.sidebar.selectbox("Menu", ["Login", "Signup"])

if menu == "Signup":
    st.subheader("Create Account")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type='password')

    if st.button("Signup"):
        try:
            add_user(new_user, new_pass)
            st.success("Account created successfully ✅")
        except:
            st.error("User already exists!")

elif menu == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome {username} 👋")
        else:
            st.error("Invalid Credentials")

# ------------------ LOGOUT ------------------
if st.session_state.logged_in:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

# ================== MAIN APP ==================
if st.session_state.logged_in:

    st.title(":rainbow[SMART DATA INSIGHTS]")
    st.header("📈 Data-Driven Insights for Smarter Decisions")
    st.subheader("Simplifying Data Analysis for Business and Research", divider='rainbow')

    # ------------------ DATA TABLE FUNCTIONS ------------------
    def create_table(table_name, columns):
        cols = ", ".join([f"{col} TEXT" for col in columns])
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols})")
        conn.commit()

    def get_tables():
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [table[0] for table in cursor.fetchall()]

    # ------------------ FILE UPLOAD ------------------
    file = st.file_uploader('Drop csv or excel file', type=['csv', 'xlsx'])

    data = None
    if file is not None:
        if file.name.endswith('csv'):
            data = pd.read_csv(file)
        else:
            data = pd.read_excel(file)

        st.download_button(
            label="Download.csv",
            data=data.to_csv(index=True),
            file_name="datawork.csv",
            mime="text/csv"
        )

        st.dataframe(data)
        st.info("File uploaded successfully ✔️")

        # ------------------ METRICS ------------------
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Records", data.shape[0])
        c2.metric("Total Columns", data.shape[1])
        c3.metric("Missing Values", data.isnull().sum().sum())

        # ------------------ DATABASE SAVE ------------------
        st.subheader("💾 Save Data to Database")
        table_name = st.text_input("Enter Table Name")

        if st.button("Save to Database"):
            create_table(table_name, data.columns)

            for _, row in data.iterrows():
                placeholders = ", ".join(["?"] * len(row))
                cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", tuple(row.astype(str)))

            conn.commit()
            st.success("Data saved to SQLite ✅")

    # ------------------ LOAD DATABASE ------------------
    st.subheader("📂 Load Data from Database")

    tables = get_tables()

    if tables:
        selected_table = st.selectbox("Select Table", tables)

        if st.button("Load Data"):
            query = f"SELECT * FROM {selected_table}"
            db_data = pd.read_sql(query, conn)
            data = db_data
            st.dataframe(data)

        if st.button("Delete Table"):
            cursor.execute(f"DROP TABLE {selected_table}")
            conn.commit()
            st.warning("Table Deleted ❌")

    # ------------------ ANALYSIS ------------------
    if data is not None:

        result = data.copy()

        st.subheader(':rainbow[BASIC information of dataset]', divider='rainbow')
        tab1, tab2, tab3, tab4 = st.tabs(['Summary', 'Top & Bottom', 'Data types', 'Columns'])

        with tab1:
            st.write(f"There are {data.shape[0]} rows & {data.shape[1]} columns")
            st.dataframe(data.describe())

        with tab2:
            st.subheader(":green[Top Rows]")
            toprows = st.slider("No of Rows", 1, data.shape[0])
            st.dataframe(data.head(toprows))

            st.subheader(":green[Bottom Rows]")
            bottomrows = st.slider("Bottom Rows", 1, data.shape[0])
            st.dataframe(data.tail(bottomrows))

        with tab3:
            st.dataframe(data.dtypes)

        with tab4:
            st.write("Columns:", data.shape[1])
            st.write("Column Names:", list(data.columns))

        # ------------------ VALUE COUNT ------------------
        st.subheader(":rainbow[Columns Value Count]", divider="rainbow")

        with st.expander("Value Count"):
            col1, col2 = st.columns(2)
            with col1:
                Columns = st.selectbox("Choose column", list(data.columns))
            with col2:
                num = st.number_input('Top Rows', min_value=1, step=1)

            if st.button("Count"):
                result = data[Columns].value_counts().reset_index().head(num)
                st.dataframe(result)

        # ------------------ GROUPBY ------------------
        with st.expander("Groupby"):
            col1, col2, col3 = st.columns(3)

            with col1:
                groupby_cols = st.multiselect('Groupby Columns', list(data.columns))
            with col2:
                operation_cols = st.selectbox('Operation Column', list(data.columns))
            with col3:
                operation = st.selectbox('Operation', ['sum', 'max', 'min', 'mean', 'median'])

            if groupby_cols:
                result = data.groupby(groupby_cols).agg(newcol=(operation_cols, operation)).reset_index()
                st.dataframe(result)

        # ------------------ VISUALIZATION ------------------
        st.subheader("📊 Data Visualization", divider='gray')

        graphs = st.selectbox('Choose Graph', ['line', 'bar', 'scatter', 'pie', 'sunburst'])

        if graphs == 'line':
            x = st.selectbox('X Axis', result.columns)
            y = st.selectbox('Y Axis', result.columns)
            fig = px.line(result, x=x, y=y)
            st.plotly_chart(fig)

        elif graphs == 'bar':
            x = st.selectbox('X Axis', result.columns)
            y = st.selectbox('Y Axis', result.columns)
            fig = px.bar(result, x=x, y=y)
            st.plotly_chart(fig)

        elif graphs == 'scatter':
            x = st.selectbox('X Axis', result.columns)
            y = st.selectbox('Y Axis', result.columns)
            fig = px.scatter(result, x=x, y=y)
            st.plotly_chart(fig)

        elif graphs == 'pie':
            values = st.selectbox('Values', result.columns)
            names = st.selectbox('Labels', result.columns)
            fig = px.pie(result, values=values, names=names)
            st.plotly_chart(fig)

        elif graphs == 'sunburst':
            path = st.multiselect('Path', result.columns)
            fig = px.sunburst(result, path=path, values='newcol' if 'newcol' in result.columns else None)
            st.plotly_chart(fig)

else:
    st.warning("🔒 Please login to access the app")
