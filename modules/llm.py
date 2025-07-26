
from langchain_google_genai import ChatGoogleGenerativeAI

google_key = 'AIzaSyDcy_g83otcsIagJAXH_VjSD1AEcYiKdGM'
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    api_key=google_key,
    temperature=0.0,
    max_tokens=1000,
    top_p=1,
)

# print(llm.invoke("hi").content)