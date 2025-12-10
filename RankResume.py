from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from Load_apis import load_llm,load_apis
import json

load_apis()
llm=load_llm()

def extract_json(text: str):
    text = text.strip()

    # If wrapped in ```json ... ```
    if text.startswith("```"):
        # split on code fences
        parts = text.split("```")
        # JSON will be in parts[1]
        text = parts[1].replace("json", "", 1).strip()
    elif text.startswith("**"):
        parts = text.split("**")
        text = parts[1].replace("Resume Rank:", "", 1).strip()

    return json.loads(text)

def rank_resume(resume:dict,user_input:str):
  system_message = SystemMessage(content="""You are a helpful assistant that ranks resumes based on Job Description. You must follow the following Criteria to rank the resumes that must be relevant to Job Description.
    
    Analyze the resume and provide scores for each category. Return ONLY a valid JSON object with the following structure:
    {
        "skills": {
            "score": <number out of 40>,
            "justification": "<brief explanation>"
        },
        "experience": {
            "score": <number out of 35>,
            "justification": "<brief explanation>"
        },
        "projects": {
            "score": <number out of 10>,
            "justification": "<brief explanation>"
        },
        "other_relevant_skills": {
            "score": <number out of 10>,
            "justification": "<brief explanation>"
        },
        "extras": {
            "score": <number out of 5>,
            "justification": "<brief explanation>"
        },
        "total_score": <sum of all scores out of 100>
    }
    
    Return ONLY the JSON object, no additional text or formatting.""")
  human_message = HumanMessage(content=f"Rank the resume based on the following criteria: {resume}. Job Description: {user_input}")
  response = llm.invoke([system_message, human_message])
  response = extract_json(response.content)
  return response


