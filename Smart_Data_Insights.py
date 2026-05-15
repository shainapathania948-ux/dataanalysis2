import pandas as pd
import plotly.express as px
import streamlit as st
import sqlite3
import hashlib

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="SMART DATA INSIGHTS",
    page_icon="📊",
    layout="wide"
)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# ---------------- CREATE TABLES ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs(
    username TEXT,
    action TEXT
)
""")

conn.commit()

# ---------------- FUNCTIONS ----------------
def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def log_action(user, action):
    cursor.execute(
        "INSERT INTO logs VALUES (?, ?)",
        (user, action)
    )
    conn.commit()

def add_user(username, password, role):

    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?)",
        (username, make_hash(password), role)
    )

    conn.commit()

def login_user(username, password):

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, make_hash(password))
    )

    return cursor.fetchone()

def clean_column(col):

    return col.strip()\
        .replace(" ", "_")\
        .replace("%", "percent")\
        .replace("(", "")\
        .replace(")", "")\
        .replace("-", "_")

def create_table(table_name, columns):

    cols = ", ".join(
        [f'"{clean_column(col)}" TEXT' for col in columns]
    )

    cursor.execute(
        f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols})'
    )

    conn.commit()

def get_tables():

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )

    return [table[0] for table in cursor.fetchall()]

# ---------------- SMART AI ----------------
def detect_domain(df):

    cols = " ".join(df.columns).lower()

    if any(x in cols for x in ["sales", "revenue", "profit", "customer"]):
        return "Sales"

    elif any(x in cols for x in ["student", "marks", "school", "attendance"]):
        return "Education"

    return "General"

def generate_insights(df):

    insights = []

    num_cols = df.select_dtypes(include='number').columns

    for col in num_cols:

        insights.append(
            f"{col} → Avg: {round(df[col].mean(),2)} | "
            f"Max: {df[col].max()} | "
            f"Min: {df[col].min()}"
        )

    return insights

def generate_recommendations(domain):

    if domain == "Sales":

        return [
            "Increase focus on high revenue products",
            "Improve low performing regions",
            "Target repeat customers",
            "Run marketing campaigns"
        ]

    elif domain == "Education":

        return [
            "Improve weak students performance",
            "Analyze attendance vs marks",
            "Provide scholarships",
            "Improve teaching quality"
        ]

    return [
        "Focus on important data segments",
        "Improve low performing areas",
        "Use trends for decision making"
    ]

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- SIDEBAR ----------------
st.sidebar.title("🔐 Authentication")

menu = st.sidebar.selectbox(
    "Menu",
    ["Login", "Signup"]
)

# ---------------- SIGNUP ----------------
if menu == "Signup":

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    r = st.selectbox(
        "Role",
        ["user", "admin"]
    )

    if st.button("Signup"):

        try:

            add_user(u, p, r)

            st.success("Account Created Successfully ✅")

        except:

            st.error("User Already Exists")

# ---------------- LOGIN ----------------
elif menu == "Login":

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):

        user = login_user(u, p)

        if user:

            st.session_state.logged_in = True
            st.session_state.username = user[0]
            st.session_state.role = user[2]

            st.success(f"Welcome {user[0]} 👋")

        else:

            st.error("Invalid Credentials")

# ---------------- LOGOUT ----------------
if st.session_state.logged_in:

    if st.sidebar.button("Logout"):

        st.session_state.clear()
        st.rerun()

# ================= MAIN APP =================
if st.session_state.logged_in:

    st.title("📊 SMART DATA INSIGHTS")

    # ---------------- ADMIN PANEL ----------------
    if st.session_state.role == "admin":

        st.sidebar.subheader("🛠 Admin Panel")

        if st.sidebar.button("View Users"):

            users = pd.read_sql(
                "SELECT username, role FROM users",
                conn
            )

            st.dataframe(users)

        del_user = st.sidebar.text_input("Delete User")

        if st.sidebar.button("Delete"):

            cursor.execute(
                "DELETE FROM users WHERE username=?",
                (del_user,)
            )

            conn.commit()

            st.success("User Deleted Successfully")

    # ---------------- FILE UPLOAD ----------------
    file = st.file_uploader(
        "Upload CSV or Excel File",
        type=["csv", "xlsx"]
    )

    data = None

    if file:

        # READ FILE
        if file.name.endswith("csv"):
            data = pd.read_csv(file)
        else:
            data = pd.read_excel(file)

        # CLEAN COLUMN NAMES
        data.columns = [
            clean_column(c) for c in data.columns
        ]

        # FIX NUMERIC CONVERSION
        for col in data.columns:

            try:
                data[col] = pd.to_numeric(data[col])
            except:
                pass

        # LOG ACTION
        log_action(
            st.session_state.username,
            "Uploaded File"
        )

        # SHOW DATA
        st.subheader("📄 Uploaded Data")

        st.dataframe(
            data,
            use_container_width=True
        )

        # ---------------- METRICS ----------------
        c1, c2, c3 = st.columns(3)

        c1.metric("Rows", data.shape[0])
        c2.metric("Columns", data.shape[1])
        c3.metric("Missing Values", data.isnull().sum().sum())

        # ---------------- CLEANING ----------------
        st.subheader("🧹 Data Cleaning")

        if st.checkbox("Remove Missing Values"):
            data = data.dropna()

        if st.checkbox("Remove Duplicate Rows"):
            data = data.drop_duplicates()
 
       # ---------------- FILTER ----------------
        st.subheader("🔍 Advanced Data Filter")
        filtered_data = data.copy()
        filter_columns = st.multiselect("Select Columns for Filtering", data.columns)

        for col in filter_columns:
            if pd.api.types.is_numeric_dtype(filtered_data[col]):
                min_val = float(filtered_data[col].min())
                max_val = float(filtered_data[col].max())
                selected_range = st.slider(
                    f"{col} Range",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val)
                )
                filtered_data = filtered_data[
                    filtered_data[col].between(selected_range[0], selected_range[1])
                ]
            else:
                options = filtered_data[col].astype(str).unique()
                selected_values = st.multiselect(f"Select {col}", options)
                if selected_values:
                    filtered_data = filtered_data[
                        filtered_data[col].astype(str).isin(selected_values)
                    ]

        data = filtered_data.copy()
        st.dataframe(data, use_container_width=True)


        # ---------------- SAVE TO DATABASE ----------------
        st.subheader("💾 Save Data")

        table_name = st.text_input("Table Name")

        if st.button("Save to Database"):

            create_table(
                table_name,
                data.columns
            )

            for _, row in data.iterrows():

                cursor.execute(
                    f"INSERT INTO {table_name} VALUES ({','.join(['?']*len(row))})",
                    tuple(row.astype(str))
                )

            conn.commit()

            st.success("Data Saved Successfully ✅")

    # ---------------- LOAD SAVED DATA ----------------
    st.subheader("📂 Load Saved Data")

    tables = get_tables()

    if tables:

        selected_table = st.selectbox(
            "Select Table",
            tables
        )

        if st.button("Load Data"):

            data = pd.read_sql(
                f"SELECT * FROM {selected_table}",
                conn
            )

            st.dataframe(
                data,
                use_container_width=True
            )

    # ================= ANALYSIS =================
    if data is not None:

        st.subheader("📊 Data Analysis")

        st.dataframe(
            data.describe(include='all'),
            use_container_width=True
        )

        # NUMERIC COLUMNS
        num_cols = data.select_dtypes(include='number').columns

        # ---------------- KPI ----------------
        st.subheader("📈 KPIs")

        if len(num_cols) > 0:

            kpi_col = st.selectbox(
                "Select KPI Column",
                num_cols
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Mean",
                round(data[kpi_col].mean(), 2)
            )

            c2.metric(
                "Maximum",
                data[kpi_col].max()
            )

            c3.metric(
                "Minimum",
                data[kpi_col].min()
            )

        # ---------------- GROUP ANALYSIS ----------------
        st.subheader("📈 Group Analysis")

        group_cols = st.multiselect(
            "Group By Columns",
            data.columns
        )

        operation_col = st.selectbox(
            "Operation Column",
            data.columns
        )

        operation = st.selectbox(
            "Operation",
            ["sum", "mean", "max", "min"]
        )

        if group_cols:

            result = data.groupby(group_cols).agg(
                {operation_col: operation}
            ).reset_index()

        else:

            result = data

        # ---------------- VISUALIZATION ----------------
        st.subheader("📉 Visualization")

        chart_type = st.selectbox(
            "Chart Type",
            ["line", "bar", "scatter", "pie"]
        )

        x = st.selectbox("X Axis", result.columns)
        y = st.selectbox("Y Axis", result.columns)

        if chart_type == "line":
            fig = px.line(result, x=x, y=y)

        elif chart_type == "bar":
            fig = px.bar(result, x=x, y=y)

        elif chart_type == "scatter":
            fig = px.scatter(result, x=x, y=y)

        elif chart_type == "pie":
            fig = px.pie(result, names=x, values=y)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ================= MACHINE LEARNING =================
        if len(num_cols) > 1:

            st.subheader("🤖 Model Comparison")

            target = st.selectbox(
                "Select Target Column",
                num_cols
            )

            if st.button("Compare Models"):

                ml_data = data[num_cols].dropna()

                X = ml_data.drop(columns=[target])
                y = ml_data[target]

                X_train, X_test, y_train, y_test = train_test_split(
                    X,
                    y,
                    test_size=0.2,
                    random_state=42
                )

                models = {
                    "Linear Regression": LinearRegression(),
                    "Decision Tree": DecisionTreeRegressor(random_state=42),
                    "Random Forest": RandomForestRegressor(random_state=42)
                }

                results = []

                for name, model in models.items():

                    model.fit(X_train, y_train)

                    preds = model.predict(X_test)

                    r2 = r2_score(y_test, preds)

                    mae = mean_absolute_error(y_test, preds)

                    results.append({
                        "Model": name,
                        "R2 Score": round(r2, 3),
                        "MAE": round(mae, 3)
                    })

                result_df = pd.DataFrame(results)

                # BEST MODEL
                best_model = result_df.sort_values(
                    by="R2 Score",
                    ascending=False
                ).iloc[0]

                st.success(
                    f"🏆 Best Model is: {best_model['Model']} "
                    f"| R2 Score: {best_model['R2 Score']}"
                )

                # RESULTS TABLE
                st.write("### 📊 Model Results")

                st.dataframe(
                    result_df,
                    use_container_width=True
                )

                # R2 CHART
                st.write("### 📈 R2 Score Comparison")

                fig1 = px.bar(
                    result_df,
                    x="Model",
                    y="R2 Score",
                    text="R2 Score"
                )

                fig1.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig1,
                    use_container_width=True
                )

                # MAE CHART
                st.write("### 📉 MAE Comparison")

                fig2 = px.bar(
                    result_df,
                    x="Model",
                    y="MAE",
                    text="MAE"
                )

                fig2.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig2,
                    use_container_width=True
                )

        # ================= SMART INSIGHTS =================
        st.subheader("🧠 Smart Insights")

        domain = detect_domain(data)

        st.write(f"### Dataset Type: {domain}")

        st.write("### Insights")

        for insight in generate_insights(data):

            st.write(f"✔ {insight}")

        st.write("### Recommendations")

        for rec in generate_recommendations(domain):

            st.write(f"✔ {rec}")

        # ---------------- DOWNLOAD ----------------
        st.download_button(
            "⬇ Download CSV",
            data.to_csv(index=False),
            "data.csv",
            "text/csv"
        )

# ---------------- LOGIN MESSAGE ----------------
else:

    st.warning("🔒 Please Signup First")
