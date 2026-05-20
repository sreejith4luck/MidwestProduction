import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

DB_FILE = "production_data.db"

# 1. Database Setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            emp_id TEXT,
            emp_name TEXT,
            role TEXT,
            work_type TEXT,
            production_val REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_users (
            username TEXT PRIMARY KEY,
            full_name TEXT,
            password TEXT,
            access_level TEXT,
            recovery_pin TEXT,
            is_first_login INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS targets (
            work_type TEXT PRIMARY KEY,
            target_value REAL
        )
    ''')
    
    # Setup baseline Master Administrator
    cursor.execute("SELECT COUNT(*) FROM system_users WHERE username = 'sreejith'")
    if cursor.fetchone() == 0:
        cursor.execute('''
            INSERT INTO system_users (username, full_name, password, access_level, recovery_pin, is_first_login) 
            VALUES ('sreejith', 'Sreejith (Admin)', 'admin123', 'admin', '1732', 0)
        ''')
        cursor.execute("DELETE FROM system_users WHERE username = 'admin'")
        
    # Setup baseline workflow targets
    cursor.execute("SELECT COUNT(*) FROM targets")
    if cursor.fetchone() == 0:
        default_targets = [
            ("Coding Review", 100.0),
            ("Add Hold", 300.0),
            ("Rebilling", 165.0),
            ("Other Work", 50.0)
        ]
        cursor.executemany("INSERT INTO targets (work_type, target_value) VALUES (?, ?)", default_targets)
        
    conn.commit()
    conn.close()

init_db()

def get_targets():
    conn = sqlite3.connect(DB_FILE)
    df_targets = pd.read_sql_query("SELECT work_type, target_value FROM targets", conn)
    conn.close()
    return dict(zip(df_targets['work_type'], df_targets['target_value']))

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    df_users = pd.read_sql_query("SELECT username, full_name, access_level FROM system_users", conn)
    conn.close()
    return df_users

# Core Config
st.set_page_config(page_title="Corporate Production Workspace", layout="centered")
ROLES = ["Biller", "Coder"]
WORK_TYPES = ["Coding Review", "Add Hold", "Rebilling", "Other Work"]

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'full_name' not in st.session_state:
    st.session_state['full_name'] = None
if 'force_password_change' not in st.session_state:
    st.session_state['force_password_change'] = False
if 'recovery_mode' not in st.session_state:
    st.session_state['recovery_mode'] = False

# 2. Setup Lifecycle Prompt
if st.session_state['logged_in'] and st.session_state['force_password_change']:
    st.title("🔄 First-Time Setup Workspace")
    with st.form("force_change_pwd_form"):
        new_pwd = st.text_input("Create Secure Password", type="password")
        confirm_pwd = st.text_input("Confirm Secure Password", type="password")
        new_pin = st.text_input("Choose 4-Digit PIN", max_chars=4, type="password")
        submit_change = st.form_submit_button("Lock Controls & Launch Workspace")
        
        if submit_change:
            if not new_pwd or not new_pin:
                st.error("All text fields require values.")
            elif new_pwd != confirm_pwd:
                st.error("Passwords do not match.")
            elif len(new_pin) != 4 or not new_pin.isdigit():
                st.error("Recovery PIN must be 4 digits.")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('UPDATE system_users SET password = ?, recovery_pin = ?, is_first_login = 0 WHERE username = ?', (new_pwd, new_pin, st.session_state['username']))
                conn.commit()
                conn.close()
                st.session_state['force_password_change'] = False
                st.success("Setup complete!")
                st.rerun()

# 3. Recovery Console
elif st.session_state['recovery_mode']:
    st.title("🔓 Account Recovery Console")
    with st.form("recovery_execution_form"):
        rec_user = st.text_input("Username").strip().lower()
        rec_pin = st.text_input("4-Digit PIN", max_chars=4, type="password")
        rec_new_pwd = st.text_input("New Password", type="password")
        rec_confirm_pwd = st.text_input("Confirm New Password", type="password")
        btn_run_recovery = st.form_submit_button("Apply Override")
        
        if btn_run_recovery:
            if not rec_user or not rec_pin or not rec_new_pwd:
                st.error("All processing fields require entry validation.")
            elif rec_new_pwd != rec_confirm_pwd:
                st.error("Passwords do not match.")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT recovery_pin FROM system_users WHERE username = ?", (rec_user,))
                user_pin_match = cursor.fetchone()
                conn.close()
                
                if user_pin_match and user_pin_match[0] == rec_pin:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE system_users SET password = ?, is_first_login = 0 WHERE username = ?", (rec_new_pwd, rec_user))
                    conn.commit()
                    conn.close()
                    st.success("Password updated! Return to login.")
                    st.session_state['recovery_mode'] = False
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    
    if st.button("⬅️ Return to Login"):
        st.session_state['recovery_mode'] = False
        st.rerun()

# 4. Login Screen
elif not st.session_state['logged_in']:
    st.title("🔐 Production Portal Sign In")
    with st.form("login_form"):
        input_user = st.text_input("Username").strip().lower()
        input_pass = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Sign In")
        
        if login_btn:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT username, full_name, password, access_level, is_first_login FROM system_users WHERE username = ?', (input_user,))
            user_record = cursor.fetchone()
            conn.close()
            
            if user_record:
                db_user, db_name, db_pass, db_role, db_first_login = user_record
                if input_pass == db_pass:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = db_user
                    st.session_state['full_name'] = db_name
                    st.session_state['user_role'] = db_role
                    if db_first_login == 1: 
                        st.session_state['force_password_change'] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            else:
                st.error("Invalid credentials.")
                
    if st.button("❓ Forgot Password / PIN Override Reset Link"):
        st.session_state['recovery_mode'] = True
        st.rerun()

# 5. Core Application Workspace
else:
    st.sidebar.markdown(f"### Active Identity")
    st.sidebar.markdown(f"User: **{st.session_state['full_name']}**")
    st.sidebar.markdown(f"Access: **{st.session_state['user_role'].upper()}**")
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['username'] = None
        st.session_state['full_name'] = None
        st.rerun()

    st.title("📊Midwest Production Log")

    conn = sqlite3.connect(DB_FILE)
    raw_df = pd.read_sql_query("SELECT id, date, emp_id, emp_name, role, work_type, production_val FROM production ORDER BY id ASC", conn)
    conn.close()
    targets_map = get_targets()

    if not raw_df.empty:
        report_df = pd.DataFrame()
        report_df["Database_ID"] = raw_df["id"] # Hidden mapping link kept for deletions
        report_df["SL#"] = range(1, len(raw_df) + 1)
        report_df["Date"] = raw_df["date"]
        report_df["Name"] = raw_df["emp_name"]
        report_df["Role"] = raw_df["role"]
        report_df["Type of work"] = raw_df["work_type"]
        report_df["Production #"] = raw_df["production_val"].astype(int)
        report_df["Target"] = report_df["Type of work"].map(targets_map).fillna(0).astype(int)
    else:
        report_df = pd.DataFrame()

    # Master Excel Downloader
    if st.session_state['user_role'] == "admin" and not report_df.empty:
        export_clean = report_df.drop(columns=["Database_ID"])
        st.download_button(
            label="📥 Quick Download Master Excel Spreadsheet (.CSV)",
            data=export_clean.to_csv(index=False).encode('utf-8'),
            file_name=f"Master_Production_Log_{datetime.today().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.markdown("---")

    # Core Form Entry
    with st.form("production_entry_form", clear_on_submit=True):
        st.subheader("Submit Production Record")
        selected_date = st.date_input("Processing Date", datetime.today())
        selected_role = st.selectbox("Assigned Workflow Role", ROLES)
        selected_work_type = st.selectbox("Type of Work Completed", WORK_TYPES)
        production_value = st.number_input("Production Count", min_value=0.0, step=1.0)
        submit_data = st.form_submit_button("SUBMIT DATA")
        
    if submit_data:
        if production_value <= 0:
            st.error("Production output count must be greater than 0.")
        else:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO production (date, emp_id, emp_name, role, work_type, production_val)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (selected_date.strftime("%m/%d/%Y"), st.session_state['username'], st.session_state['full_name'], selected_role, selected_work_type, production_value))
            conn.commit()
            conn.close()
            st.success("Production logged successfully!")
            st.rerun()

    # Employees Self View Module
    if st.session_state['user_role'] == "employee":
        st.markdown("---")
        st.subheader("📋 My Added Production Records")
        if not report_df.empty:
            user_history_df = report_df[raw_df['emp_id'] == st.session_state['username']].copy()
            if not user_history_df.empty:
                user_history_df["SL#"] = range(1, len(user_history_df) + 1)
                st.dataframe(user_history_df.drop(columns=["Database_ID"]), use_container_width=True, hide_index=True)
            else:
                st.info("You haven't logged any production records yet.")
        else:
            st.info("No logs present in tracking database ledger.")

    # Administrative Controls Panel Hub
    if st.session_state['user_role'] == "admin":
        st.markdown("---")
        st.subheader("⚙️ Enterprise Management Matrix (Admin Rights)")

        # ==========================================================
        # 🗑️ FIXED DIRECT LINE-ITEM LOG ERASER TOOL
        # ==========================================================
        with st.expander("❌ Quick Delete Production Rows"):
            if not report_df.empty:
                st.write("Select a row number to delete it permanently:")
                
                # Dynamic mapping select box choice items mapping dictionary
                select_options = {}
                for _, row in report_df.iterrows():
                    label = f"SL# {row['SL#']} | {row['Date']} | {row['Name']} | {row['Type of work']} ({int(row['Production #'])} units)"
                    select_options[label] = int(row['Database_ID'])
                
                target_label = st.selectbox("Select Row to Erase:", list(select_options.keys()))
                target_db_id = select_options[target_label]
                
                if st.button("🗑️ Delete This Row", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM production WHERE id = ?", (target_db_id,))
                    conn.commit()
                    conn.close()
                    st.success("Successfully deleted row from ledger database!")
                    st.rerun()
            else:
                st.info("No active production rows available to clear.")

        with st.expander("📝 Modify User Production Logs"):
            filter_date = st.date_input("Step 1: Filter by Date", datetime.today(), key="mod_date_picker")
            formatted_filter_date = filter_date.strftime("%m/%d/%Y")
            
            conn = sqlite3.connect(DB_FILE)
            active_names_on_date = pd.read_sql_query("SELECT DISTINCT emp_id, emp_name FROM production WHERE date = ?", conn, params=(formatted_filter_date,))
            conn.close()
            
            if active_names_on_date.empty:
                st.info(f"No records logged by any user on {formatted_filter_date}.")
            else:
                user_options = dict(zip(active_names_on_date['emp_id'], active_names_on_date['emp_name']))
                selected_mod_uid = st.selectbox("Step 2: Select Employee", list(user_options.keys()), format_func=lambda x: user_options[x], key="mod_user_picker")
                
                conn = sqlite3.connect(DB_FILE)
                user_logs = pd.read_sql_query("SELECT id, role, work_type, production_val FROM production WHERE date = ? AND emp_id = ?", conn, params=(formatted_filter_date, selected_mod_uid))
                conn.close()
                
                for index, row in user_logs.iterrows():
                    entry_id = int(row['id'])
                    with st.form(f"mod_form_{entry_id}"):
                        col_r, col_w, col_p = st.columns(3)
                        with col_r:
                            idx_role = ROLES.index(row['role']) if row['role'] in ROLES else 0
                            new_log_role = st.selectbox("Role", ROLES, index=idx_role, key=f"r_{entry_id}")
                        with col_w:
                            idx_wt = WORK_TYPES.index(row['work_type']) if row['work_type'] in WORK_TYPES else 0
                            new_log_wt = st.selectbox("Type of Work", WORK_TYPES, index=idx_wt, key=f"w_{entry_id}")
                        with col_p:
                            new_log_val = st.number_input("Production #", min_value=0.0, value=float(row['production_val']), step=1.0, key=f"v_{entry_id}")
                        
                        if st.form_submit_button("💾 Save Changes"):
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE production SET role = ?, work_type = ?, production_val = ? WHERE id = ?", (new_log_role, new_log_wt, new_log_val, entry_id))
                            conn.commit()
                            conn.close()
                            st.success("Record updated successfully!")
                            st.rerun()

        with st.expander("👤 User Provisioning Panel"):
            with st.form("add_user_form", clear_on_submit=True):
                new_username = st.text_input("Unique Username").strip().lower()
                new_full_name = st.text_input("Employee Full Name").strip()
                default_password = st.text_input("Temporary Password", value="Welcome123").strip()
                new_role_access = st.selectbox("Workspace Authorization Rights", ["Standard Employee", "System Admin"])
                
                if st.form_submit_button("Verify & Create Profile"):
                    if not new_username or not new_full_name:
                        st.error("All text input parameters require fields.")
                    else:
                        db_role_string = "admin" if new_role_access == "System Admin" else "employee"
                        try:
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO system_users (username, full_name, password, access_level, recovery_pin, is_first_login) VALUES (?, ?, ?, ?, '', 1)", (new_username, new_full_name, default_password, db_role_string))
                            conn.commit()
                            conn.close()
                            st.success("User provisioned successfully!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username already linked to profile mapping.")

            st.write("---")
            df_existing_users = get_all_users()
            st.dataframe(df_existing_users, use_container_width=True, hide_index=True)
            user_list = df_existing_users['username'].tolist()

            st.write("---")
            selected_reset_user = st.selectbox("Select Account to Reset Password:", user_list)
            reset_pwd_input = st.text_input("Forced Override Password Value:", value="Reset123")
            if st.button("⚡ Force Override Password Reset"):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE system_users SET password = ?, is_first_login = 1 WHERE username = ?", (reset_pwd_input, selected_reset_user))
                conn.commit()
                conn.close()
                st.success("Forced reset complete!")

            st.write("---")
            user_to_delete = st.selectbox("Select Account to Delete Permanently:", [u for u in user_list if u != 'sreejith'])
            if st.button("🗑️ Erase Account Profile", type="primary"):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM system_users WHERE username = ?", (user_to_delete,))
                conn.commit()
                conn.close()
                st.success("Profile deleted successfully!")
                st.rerun()

        with st.expander("🎯 Set Corporate Production Volume Limits"):
            current_targets = get_targets()
            with st.form("target_form"):
                updated_targets = {}
                for wt in WORK_TYPES:
                    existing_target = current_targets.get(wt, 100.0)
                    updated_targets[wt] = st.number_input(f"Target Count for '{wt}':", min_value=0.0, value=float(existing_target), step=5.0)
                
                if st.form_submit_button("💾 Save All Target Rules"):
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    for wt, val in updated_targets.items():
                        cursor.execute("INSERT OR REPLACE INTO targets (work_type, target_value) VALUES (?, ?)", (wt, val))
                    conn.commit()
                    conn.close()
                    st.success("Targets updated successfully!")
                    st.rerun()

        # Master Ledger View
        st.markdown("---")
        st.subheader("📋 Master Reports Export Center (All Active Database Data Logs)")
        if not report_df.empty:
            st.dataframe(report_df.drop(columns=["Database_ID"]), use_container_width=True, hide_index=True)
        else:
            st.info("The ledger database tracking matrix is completely empty.")
