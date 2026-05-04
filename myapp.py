import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

# Safe import for environments without streamlit
try:
    import streamlit as st
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Streamlit is not installed. Install it first using: pip install streamlit"
    )

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="SMART DATA INSIGHTS", page_icon="📈", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS logs(
    username TEXT,
    action TEXT
)
''')
conn.commit()

# ---------------- FUNCTIONS ----------------
def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def add_user(username, password, role):
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?)",
        (username, make_hash(password), role),
    )
    conn.commit()


def login_user(username, password):
    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, make_hash(password)),
    )
    return cursor.fetchone()


def log_action(username, action):
    cursor.execute("INSERT INTO logs VALUES (?, ?)", (username, action))
    conn.commit()


def clean_column(col):
    return (
        str(col)
        .strip()
        .replace(" ", "_")
        .replace("%", "percent")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
    )


# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- AUTH ----------------
st.sidebar.title("Authentication")
menu = st.sidebar.selectbox("Menu", ["Login", "Signup"])

if menu == "Signup":
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])

    if st.button("Signup"):
        try:
            add_user(username, password, role)
            st.success("Account created successfully")
        except Exception:
            st.error("User already exists")

elif menu == "Login":
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user[0]
            st.session_state.role = user[2]
            st.success(f"Welcome {user[0]}")
        else:
            st.error("Invalid credentials")

# ---------------- MAIN APP ----------------
if st.session_state.logged_in:
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.title("SMART DATA INSIGHTS")

    uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    data = None

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith("csv"):
                data = pd.read_csv(uploaded_file)
            else:
                data = pd.read_excel(uploaded_file)

            data.columns = [clean_column(col) for col in data.columns]
            log_action(st.session_state.username, "Uploaded File")
        except Exception as e:
            st.error(f"File loading error: {e}")

    if data is not None:
        st.subheader("Dataset Preview")
        st.dataframe(data)

        num_cols = data.select_dtypes(include="number").columns.tolist()

        # -------- Visualization --------
        st.subheader("Visualization")
        chart = st.selectbox("Select Chart", ["line", "bar", "scatter", "pie", "sunburst"])

        if chart != "sunburst":
            x = st.selectbox("Select X", data.columns, key="x")
            y = st.selectbox("Select Y", data.columns, key="y")

            try:
                if chart == "line":
                    fig = px.line(data, x=x, y=y)
                elif chart == "bar":
                    fig = px.bar(data, x=x, y=y)
                elif chart == "scatter":
                    fig = px.scatter(data, x=x, y=y)
                else:
                    fig = px.pie(data, names=x, values=y)

                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Chart error: {e}")

        else:
            hierarchy = st.multiselect(
                "Hierarchy Columns",
                data.columns,
                default=data.columns[:2].tolist(),
            )

            if hierarchy and num_cols:
                value_col = st.selectbox("Value Column", num_cols)
                try:
                    fig = px.sunburst(data, path=hierarchy, values=value_col)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Sunburst error: {e}")

        # -------- ML Comparison --------
        if len(num_cols) > 1:
            st.subheader("Model Comparison")
            target = st.selectbox("Target Column", num_cols)

            if st.button("Compare Models"):
                df = data[num_cols].dropna()

                X = df.drop(columns=[target])
                y = df[target]

                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )

                models = {
                    "Linear Regression": LinearRegression(),
                    "Decision Tree": DecisionTreeRegressor(random_state=42),
                    "Random Forest": RandomForestRegressor(random_state=42),
                }

                results = []

                for name, model in models.items():
                    model.fit(X_train, y_train)
                    predictions = model.predict(X_test)

                    results.append({
                        "Model": name,
                        "R2 Score": round(r2_score(y_test, predictions), 3),
                        "MAE": round(mean_absolute_error(y_test, predictions), 3),
                    })

                result_df = pd.DataFrame(results)
                st.dataframe(result_df)

                fig = px.bar(result_df, x="Model", y="R2 Score", title="R2 Score Comparison")
                st.plotly_chart(fig, use_container_width=True)

                best_model = result_df.loc[result_df["R2 Score"].idxmax()]
                st.success(f"Best Model: {best_model['Model']}")

else:
    st.warning("Please login first")

# ---------------- BASIC TESTS ----------------
def _test_clean_column():
    assert clean_column("Total Sales (%)") == "Total_Sales_percent"


_test_clean_column()
