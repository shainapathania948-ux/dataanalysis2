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
    return col.strip().replace(" ", "_").replace("%","percent").replace("(","").replace(")","").replace("-","_")

def create_table(table_name, columns):
    cols = ", ".join([f'"{clean_column(col)}" TEXT' for col in columns])
    cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols})')
    conn.commit()

def get_tables():
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [table[0] for table in cursor.fetchall()]

# ------------------ SMART AI ------------------
def detect_domain(df):
    cols = " ".join(df.columns).lower()
    if any(x in cols for x in ["sales","revenue","profit","customer"]):
        return "Sales"
    elif any(x in cols for x in ["student","marks","school","attendance"]):
        return "Education"
    return "General"

def generate_steps(df):
    steps = ["✔ Data Loaded"]
    if df.isnull().sum().sum()>0:
        steps.append("✔ Missing values handled")
    if df.duplicated().sum()>0:
        steps.append("✔ Duplicates removed")
    steps += ["✔ Data Filtered","✔ Visualization Created","✔ Model Applied"]
    return steps

def generate_insights(df):
    insights = []
    num_cols = df.select_dtypes(include='number').columns
    for col in num_cols:
        insights.append(f"{col} → Avg:{round(df[col].mean(),2)}, Max:{df[col].max()}, Min:{df[col].min()}")
    return insights

def generate_recommendations(domain):
    if domain=="Sales":
        return [
            "Increase focus on high revenue products",
            "Target repeat customers",
            "Improve low-performing regions",
            "Run marketing campaigns"
        ]
    elif domain=="Education":
        return [
            "Improve weak students performance",
            "Analyze attendance vs marks",
            "Introduce scholarships",
            "Improve teaching quality"
        ]
    return [
        "Focus on high-value data segments",
        "Improve low-performing areas",
        "Use trends for decisions"
    ]

def prediction_tips():
    return [
        "Use more features",
        "Remove outliers",
        "Try advanced ML models",
        "Increase dataset size"
    ]

# ------------------ SESSION ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ------------------ AUTH ------------------
st.sidebar.title("🔐 Authentication")
menu = st.sidebar.selectbox("Menu", ["Login", "Signup"])

if menu == "Signup":
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    r = st.selectbox("Role", ["user","admin"])

    if st.button("Signup"):
        try:
            add_user(u,p,r)
            st.success("Account created ✅")
        except:
            st.error("User already exists")

elif menu == "Login":
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(u,p)
        if user:
            st.session_state.logged_in=True
            st.session_state.username=user[0]
            st.session_state.role=user[2]
            st.success(f"Welcome {user[0]} 👋")
        else:
            st.error("Invalid credentials")

# ------------------ LOGOUT ------------------
if st.session_state.logged_in:
    if st.sidebar.button("Logout"):
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
    file = st.file_uploader("Upload CSV/Excel", type=["csv","xlsx"])
    data = None

    if file:
        data = pd.read_csv(file) if file.name.endswith("csv") else pd.read_excel(file)
        data.columns=[clean_column(c) for c in data.columns]

        log_action(st.session_state.username, "Uploaded File")

        st.dataframe(data)

        # METRICS
        c1,c2,c3 = st.columns(3)
        c1.metric("Rows",data.shape[0])
        c2.metric("Columns",data.shape[1])
        c3.metric("Missing",data.isnull().sum().sum())

        # CLEAN
        if st.checkbox("Remove Missing"): data=data.dropna()
        if st.checkbox("Remove Duplicates"): data=data.drop_duplicates()

        # FILTER
        col = st.selectbox("Filter Column", data.columns)
        val = st.text_input("Value")
        if st.button("Apply Filter"):
            data = data[data[col].astype(str).str.contains(val)]
            st.dataframe(data)

        # SAVE
        table_name = st.text_input("Table Name")
        if st.button("Save to DB"):
            create_table(table_name, data.columns)
            for _, row in data.iterrows():
                cursor.execute(f"INSERT INTO {table_name} VALUES ({','.join(['?']*len(row))})", tuple(row.astype(str)))
            conn.commit()
            st.success("Saved to DB")

    # LOAD DB
    st.subheader("📂 Load Data")
    tables = get_tables()

    if tables:
        selected = st.selectbox("Select Table", tables)
        if st.button("Load"):
            data = pd.read_sql(f"SELECT * FROM {selected}", conn)
            st.dataframe(data)

    # ANALYSIS
    if data is not None:

        st.subheader("📊 Analysis")
        st.dataframe(data.describe())

        num_cols = data.select_dtypes(include='number').columns

        # KPI
        if len(num_cols)>0:
            col = st.selectbox("KPI Column",num_cols)
            c1,c2,c3 = st.columns(3)
            c1.metric("Mean",round(data[col].mean(),2))
            c2.metric("Max",data[col].max())
            c3.metric("Min",data[col].min())

        # GROUPBY
        g_cols = st.multiselect("Group Columns", data.columns)
        op_col = st.selectbox("Operation Column", data.columns)
        op = st.selectbox("Operation", ["sum","mean","max","min"])

        result = data.groupby(g_cols).agg({op_col:op}).reset_index() if g_cols else data

        # VISUAL
        chart = st.selectbox("Chart",["line","bar","scatter","pie"])
        x = st.selectbox("X",result.columns)
        y = st.selectbox("Y",result.columns)

        if chart=="line": st.plotly_chart(px.line(result,x=x,y=y))
        elif chart=="bar": st.plotly_chart(px.bar(result,x=x,y=y))
        elif chart=="scatter": st.plotly_chart(px.scatter(result,x=x,y=y))
        elif chart=="pie": st.plotly_chart(px.pie(result,names=x,values=y))

        # ML
       if len(num_cols) > 1:
    st.subheader("🤖 Model Comparison")

    target = st.selectbox("Select Target Column", num_cols)

    if st.button("Compare Models"):

        df = data[num_cols].dropna()

        X = df.drop(columns=[target])
        y = df[target]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        models = {
            "Linear Regression": LinearRegression(),
            "Decision Tree": DecisionTreeRegressor(),
            "Random Forest": RandomForestRegressor()
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

        # loop ke baad dataframe banao
        result_df = pd.DataFrame(results)

        st.write("### 📊 Model Results")
        st.dataframe(result_df)

        st.write("### 📈 Performance Comparison")

        fig1 = px.bar(result_df, x="Model", y="R2 Score",
                      title="R2 Score Comparison")
        st.plotly_chart(fig1)

        fig2 = px.bar(result_df, x="Model", y="MAE",
                      title="MAE Comparison")
        st.plotly_chart(fig2)

        best_model = result_df.loc[result_df["R2 Score"].idxmax()]
        st.success(f"🏆 Best Model: {best_model['Model']}")
        # AI INSIGHTS
        st.subheader("🧠 Smart Insights")

        domain=detect_domain(data)
        st.write(f"Dataset Type: **{domain}**")

        #st.write("### Steps")
        # for s in generate_steps(data): st.write(s)

        st.write("### Insights")
        for i in generate_insights(data): st.write(i)

        st.write("### Recommendations")
        for r in generate_recommendations(domain): st.write(r)

        #st.write("### Improve Prediction")
        #for t in prediction_tips(): st.write(t)

        # EXPORT
        st.download_button("Download CSV",data.to_csv(index=False),"data.csv")

else:
    st.warning("🔒 Please login")
