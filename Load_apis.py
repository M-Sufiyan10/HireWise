import io
import os

from dotenv import load_dotenv

DEFAULT_MODEL = "gemini-2.5-flash-lite"


def load_apis():
    """Load environment variables and validate the keys the app needs.

    Raises:
        RuntimeError: if GOOGLE_API_KEY is not configured.
    """
    load_dotenv()

    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to your .env file or export it "
            "in your shell before running HireWise."
        )

    # Only enable LangSmith tracing when a key is actually configured, and
    # never override an explicit LANGSMITH_TRACING choice made by the user.
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")


def load_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )


def save_graph(png_bytes: bytes, filename: str):
    """Save the LangGraph PNG bytes using matplotlib & io."""
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    img = mpimg.imread(io.BytesIO(png_bytes), format="PNG")
    plt.figure(figsize=(10, 10))
    plt.imshow(img)
    plt.axis("off")
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()


def draw_graph(app, filename: str = "ContentGenerationAgentgraph.png"):
    png_bytes = app.get_graph().draw_mermaid_png()
    save_graph(png_bytes, filename)
    print(f"Graph saved to {filename}")
