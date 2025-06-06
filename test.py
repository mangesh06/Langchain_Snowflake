import streamlit as st
import pandas as pd
import traceback
from chatbot.snowflake_agent import generate_code, extract_clean_code, get_snowflake_session
from chatbot.langchain_handler import get_general_response

# Setup page
st.set_page_config(page_title="Snowflake Chatbot", layout="wide")
st.title("❄️ Snowflake Data Analyst Bot")
st.markdown("Ask general questions or analyze Snowflake data using natural language.")

# Initialize session state
for key in ["chat_history", "session", "last_output"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "chat_history" else None

# Connect to Snowflake session (cached)
if not st.session_state.session:
    st.session_state.session = get_snowflake_session()

session = st.session_state.session

# Sidebar – Table selection (Commented out for now)
# st.sidebar.title("📂 Snowflake Table")
# table_name = st.sidebar.text_input("Enter full table name (e.g., MY_DB.MY_SCHEMA.MY_TABLE)")

# ✅ Hardcoded table name
table_name = 'SALES_DATA.SALES.LATEST_SALES'

# Display chat history
for role, content in st.session_state.chat_history:
    with st.chat_message(role):
        if role == "assistant" and isinstance(content, dict):
            st.markdown("**🧠 Thought Process (Generated Code):**")
            st.code(content.get("code", ""), language="python")
            output = content.get("output")
            if output is not None:
                with st.expander("📊 Output:"):
                    if isinstance(output, pd.DataFrame):
                        st.dataframe(output)
                    else:
                        st.write(output)
        else:
            st.markdown(content)

# Chat input box
user_input = st.chat_input("Ask anything like 'top products by revenue' or 'average sales in 2024'...")

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    if table_name:
        with st.chat_message("assistant"):
            try:
                raw_code = generate_code(session, table_name, user_input)
                code = extract_clean_code(raw_code)
                code = code.strip().replace("```python", "").replace("```", "")

                if not code.strip():
                    msg = "⚠️ Sorry, I couldn't generate any code for that question."
                    st.markdown(msg)
                    st.session_state.chat_history.append(("assistant", msg))
                else:
                    st.markdown("**🧠 Thought Process (Generated Code):**")
                    st.code(code, language="python")

                    local_vars = {"session": session}
                    local_vars["df"] = session.table(table_name)  # define df before exec
                    exec(code, {}, local_vars)
                    result = local_vars.get("result")

                    if result is not None:
                        if hasattr(result, "to_pandas"):
                            result = result.to_pandas()

                        st.markdown("**📊 Output:**")
                        if isinstance(result, pd.DataFrame):
                            st.dataframe(result)
                        else:
                            st.write(result)

                        st.session_state.chat_history.append(("assistant", {
                            "code": code,
                            "output": result
                        }))
                        st.session_state.last_output = result
                    else:
                        msg = "⚠️ Code ran but no 'result' variable was found."
                        st.warning(msg)
                        st.session_state.chat_history.append(("assistant", msg))

            except Exception as e:
                error_msg = f"❌ Error:\n{str(e)}\n\n{traceback.format_exc()}"
                st.error(error_msg)
                st.session_state.chat_history.append(("assistant", error_msg))

    else:
        # Fallback to general chat
        response = get_general_response(user_input)
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.chat_history.append(("assistant", response))
