import re
import streamlit as st
from snowflake.snowpark import Session
from langchain_community.llms import Ollama
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from chatbot.prompt_template import snowflake_analysis_prompt

# Initialize Ollama LLM with DeepSeek coder model
llm = Ollama(model="deepseek-coder:6.7b")

# Setup conversation memory for context continuity
memory = ConversationBufferMemory(
    memory_key="chat_history",
    input_key="question",
    return_messages=True
)

# LangChain LLMChain for Snowflake analysis code generation
analysis_chain = LLMChain(
    llm=llm,
    prompt=snowflake_analysis_prompt,
    memory=memory,
    verbose=True
)

@st.cache_resource
def get_snowflake_session():
    connection_parameters = {
        "account": st.secrets["snowflake"]["account"],
        "user": st.secrets["snowflake"]["user"],
        "password": st.secrets["snowflake"]["password"],
        "role": st.secrets["snowflake"]["role"],
        "warehouse": st.secrets["snowflake"]["warehouse"],
        "database": st.secrets["snowflake"]["database"],
        "schema": st.secrets["snowflake"]["schema"],
    }
    return Session.builder.configs(connection_parameters).create()

def generate_code(session: Session, table_name: str, user_question: str) -> str:
    """
    Generate Snowflake Snowpark code from user question using LangChain Ollama,
    fallback to simple rules if LangChain fails.
    """
    try:
        # Get dataframe preview and columns to provide context for LLM
        df = session.table(table_name)
        preview = df.limit(5).to_pandas().to_csv(index=False)
        columns = ", ".join(df.columns)

        # Run LangChain LLMChain with context
        result = analysis_chain.invoke({
            "question": user_question,
            "columns": columns,
            "preview": preview
        })

        return result["text"]

    except Exception as e:
        # Fallback to basic manual code generation
        if "total sales" in user_question.lower():
            code = f'''
from snowflake.snowpark import functions as F

df = session.table("{table_name}")
result = df.select(F.sum("SALES")).collect()[0][0]
'''
            return code

        # Default fallback: select top 5 rows
        code = f'''
df = session.table("{table_name}")
result = df.limit(5).to_pandas()
'''
        return code


def extract_clean_code(llm_response: str) -> str:
    """
    Extract Python code block from LLM response.
    If no code block found, return entire text.
    """
    code_blocks = re.findall(r"```(?:python)?\n([\s\S]*?)```", llm_response, re.IGNORECASE)
    return code_blocks[0].strip() if code_blocks else llm_response.strip()
