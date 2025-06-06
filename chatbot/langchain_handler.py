from langchain_community.llms import Ollama
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory

# Initialize LLM
llm = Ollama(model="llama3-groq-tool-use")

# Memory setup
memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=1000)

# Conversation chain with memory
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=False
)

def get_general_response(question: str) -> str:
    try:
        return conversation.predict(input=question)
    except Exception as e:
        return f"❌ Error during conversation: {str(e)}"
