import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io


def load_apis():
    load_dotenv()
    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

    if "LANGSMITH_API_KEY" not in os.environ:
        os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
        os.environ["LANGSMITH_TRACING"] = "true"

def load_llm():
    llm= ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2)

    return llm


def save_graph(png_bytes: bytes, filename: str):
    """Save the LangGraph PNG bytes using matplotlib & io."""
    img = mpimg.imread(io.BytesIO(png_bytes), format='PNG')
    plt.figure(figsize=(10, 10))
    plt.imshow(img)
    plt.axis("off")
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()

def draw_graph(app):
    png_bytes = app.get_graph().draw_mermaid_png()
    save_graph(png_bytes, "ContentGenerationAgentgraph.png")
    print("Graph saved to ContentGenerationAgentgraph.png")
