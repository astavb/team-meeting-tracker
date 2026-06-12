
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Team Meeting Tracker V4", page_icon="📋", layout="wide")

# ---------- DB ----------
conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY AUTOINCREMENT,
employee_name TEXT,
task_name TEXT,
assigned_date TEXT,
status TEXT,
completed_date TEXT
)
""")
conn.commit()

def get_employees():
    cursor.execute("SELECT name FROM employees ORDER BY name")
    return [x[0] for x in cursor.fetchall()]

def get_tasks():
    return pd.read_sql_query("SELECT * FROM tasks", conn)

# ---------- STYLE ----------
st.markdown("""
<style>
.main-title{text-align:center;font-size:42px;font-weight:700;}
.metric-box{
padding:15px;border-radius:10px;border:1px solid #333;text-align:center;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📋 Team Meeting Tracker V4</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navigation",
    ["📋 Meeting Report","📊 Dashboard","⚙️ Task Management","📥 Reports"]
)

# ---------- MEETING REPORT ----------
if menu == "📋 Meeting Report":
    st.header("Daily Meeting Report")

    rows = []

    for emp in get_employees():

        cursor.execute("""
        SELECT task_name
        FROM tasks
        WHERE employee_name=? AND status='Assigned'
        """,(emp,))
        assigned = [x[0] for x in cursor.fetchall()]

        cursor.execute("""
        SELECT task_name,assigned_date
        FROM tasks
        WHERE employee_name=? AND status='Pending'
        """,(emp,))

        pending_items = []
        for task_name,assigned_date in cursor.fetchall():
            days = (
                datetime.today().date() -
                datetime.strptime(
                    assigned_date,"%Y-%m-%d"
                ).date()
            ).days

            pending_items.append(
                f"{task_name} ({days} Days)"
            )

        rows.append({
            "Employee":emp,
            "Assigned Tasks":"\n".join(assigned),
            "Pending Tasks":"\n".join(pending_items)
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        height=600
    )

# ---------- DASHBOARD ----------
elif menu == "📊 Dashboard":

    df = get_tasks()

    total = len(df)
    assigned = len(df[df["status"]=="Assigned"]) if not df.empty else 0
    pending = len(df[df["status"]=="Pending"]) if not df.empty else 0
    completed = len(df[df["status"]=="Completed"]) if not df.empty else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Tasks", total)
    c2.metric("Assigned", assigned)
    c3.metric("Pending", pending)
    c4.metric("Completed", completed)

    st.divider()

    st.subheader("👨‍💼 Employee Performance")

    employees = get_employees()

    if employees:

        selected_emp = st.selectbox(
            "Select Employee",
            employees
        )

        emp_df = df[
            df["employee_name"] == selected_emp
        ].copy()

        completed_count = len(
            emp_df[emp_df["status"] == "Completed"]
        )

        pending_count = len(
            emp_df[emp_df["status"] == "Pending"]
        )

        assigned_count = len(
            emp_df[emp_df["status"] == "Assigned"]
        )

        a1, a2, a3 = st.columns(3)

        a1.metric("Completed", completed_count)
        a2.metric("Pending", pending_count)
        a3.metric("Assigned", assigned_count)

        display_rows = []

        for _, row in emp_df.iterrows():

            assigned_date = datetime.strptime(
                row["assigned_date"],
                "%Y-%m-%d"
            ).date()

            completed_date = row["completed_date"]

            if completed_date:

                completed_dt = datetime.strptime(
                    completed_date,
                    "%Y-%m-%d"
                ).date()

                days_taken = (
                    completed_dt - assigned_date
                ).days

            else:

                days_taken = (
                    datetime.today().date()
                    - assigned_date
                ).days

            display_rows.append({
                "Task": row["task_name"],
                "Status": row["status"],
                "Assigned Date": row["assigned_date"],
                "Completed Date": completed_date if completed_date else "-",
                "Days": days_taken
            })

        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True
        )

# ---------- TASK MANAGEMENT ----------
elif menu == "⚙️ Task Management":

    left,right = st.columns([1,2])

    with left:
        st.subheader("Add Employee")

        emp = st.text_input("Employee Name")

        if st.button("Add Employee"):
            try:
                cursor.execute(
                    "INSERT INTO employees(name) VALUES(?)",
                    (emp.strip(),)
                )
                conn.commit()
                st.success("Added")
                st.rerun()
            except:
                st.warning("Already exists")

        st.divider()

        st.subheader("Assign Task")

        employees = get_employees()

        if employees:
            employee = st.selectbox("Employee", employees)
            task = st.text_input("Task Name")
            adate = st.date_input("Assigned Date")

            if st.button("Assign Task"):
                cursor.execute("""
                INSERT INTO tasks(
                employee_name,task_name,
                assigned_date,status,completed_date
                )
                VALUES(?,?,?,?,?)
                """,(
                    employee,
                    task,
                    adate.strftime("%Y-%m-%d"),
                    "Assigned",
                    None
                ))
                conn.commit()
                st.success("Task Added")
                st.rerun()

    with right:

        st.subheader("Current Tasks")

        df = get_tasks()

        if not df.empty:

            for _,row in df.iterrows():

                task_id = int(row["id"])

                cols = st.columns([2,4,2,2,2])

                cols[0].write(row["employee_name"])
                cols[1].write(row["task_name"])
                cols[2].write(row["status"])

                days = (
                    datetime.today().date()
                    - datetime.strptime(
                        row["assigned_date"],
                        "%Y-%m-%d"
                    ).date()
                ).days

                cols[3].write(f"{days} Days")

                if row["status"] == "Assigned":
                    if cols[4].button("Pending", key=f"p{task_id}"):
                        cursor.execute(
                            "UPDATE tasks SET status='Pending' WHERE id=?",
                            (task_id,)
                        )
                        conn.commit()
                        st.rerun()

                elif row["status"] == "Pending":
                    if cols[4].button("Complete", key=f"c{task_id}"):
                        cursor.execute("""
                        UPDATE tasks
                        SET status='Completed',
                        completed_date=?
                        WHERE id=?
                        """,(
                            datetime.today().strftime("%Y-%m-%d"),
                            task_id
                        ))
                        conn.commit()
                        st.rerun()

# ---------- REPORTS ----------
elif menu == "📥 Reports":

    st.subheader("Meeting Reports")

    df = get_tasks()

    csv = df.to_csv(index=False)

    st.download_button(
        "📄 Download CSV",
        csv,
        "tasks.csv",
        "text/csv"
    )

    report_rows = []

    for emp in get_employees():

        cursor.execute("""
        SELECT task_name
        FROM tasks
        WHERE employee_name=? AND status='Assigned'
        """,(emp,))

        assigned = ", ".join([x[0] for x in cursor.fetchall()])

        cursor.execute("""
        SELECT task_name,assigned_date
        FROM tasks
        WHERE employee_name=? AND status='Pending'
        """,(emp,))

        pending = []

        for t,d in cursor.fetchall():
            days = (
                datetime.today().date() -
                datetime.strptime(d,"%Y-%m-%d").date()
            ).days
            pending.append(f"{t} ({days} Days)")

        report_rows.append({
            "Employee":emp,
            "Assigned Tasks":assigned,
            "Pending Tasks":", ".join(pending)
        })

    report_df = pd.DataFrame(report_rows)

    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        report_df.to_excel(writer, index=False, sheet_name="Meeting Report")

    st.download_button(
        "📊 Download Excel Report",
        buffer.getvalue(),
        "meeting_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
