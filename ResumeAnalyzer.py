from typing import TypedDict,List
from langgraph.graph import StateGraph,START,END
from langchain_core.messages import SystemMessage,HumanMessage
from Load_apis import load_llm, load_apis,save_graph,draw_graph
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from RankResume import rank_resume
from Db import ResumeDatabase
from RankResume import extract_json
import time
import json

start_time = time.time()
load_apis()

# Example using Python, PyMuPDF (fitz) for loading, and LangChain for chunking
import base64
files = ["Official Resume Template.pdf","software-engineer-resume-example.pdf"]
def load_pdf_as_gemini_file(path: str):
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    return {
        "mime_type": "application/pdf",
        "data": base64.b64encode(pdf_bytes).decode()
    }


def parse_resume(pdf_file:dict):
    llm=load_llm()
    system_msg=SystemMessage(content="""You are a helpful assistant. Analyze this resume PDF and extract the following information:
    - Name
    - Contact Information
    - Email Address
    - LinkedIn Profile
    - List of skills
    - List of experience
    - List of education
    - List of projects
    - List of extras (certifications, awards, publications, patents, interests,courses,etc.)
    Return the information in JSON format.
    """)
    human_msg = HumanMessage(
        content=[
            {
                "type": "media",
                "mime_type": pdf_file["mime_type"],
                "data": pdf_file["data"]
            }
        ]
    )
    response=llm.invoke([system_msg,human_msg])
    response = extract_json(response.content)
    return response

def updateUserState(newUserData:dict,userData:dict):
    userData["skills"] = {
    "skill": userData["skills"],
    "score": newUserData["skills"]["score"],
    "justification": newUserData["skills"]["justification"]}
    userData["experience"] = {
    "experience": userData["experience"],
    "score": newUserData["experience"]["score"],
    "justification": newUserData["experience"]["justification"]}
    userData["projects"] = {
    "projects": userData["projects"],
    "score": newUserData["projects"]["score"],
    "justification": newUserData["projects"]["justification"]}
    userData["extras"] = {
    "extras": userData["extras"],
    "score": newUserData["extras"]["score"],
    "justification": newUserData["extras"]["justification"]}
    return userData
print("-"*100)
user_input=input("Enter the Job Description: ")
print("-"*100)

# Initialize database with proper connection management
db = ResumeDatabase()

try:
    for file in files:
        print(f"\nProcessing: {file}")
        print("-"*50)
        
        # Load and parse resume
        pdf_file = load_pdf_as_gemini_file(file)
        resume=parse_resume(pdf_file)
        
        # Prepare user data
        userData = {}
        for key in ['name','contact_information','email_address','linkedin_profile']:
            if key in resume:
                userData[key] = resume.pop(key)
        
        # Merge resume data into userData
        userData.update(resume)
        
        # Insert resume into database
        try:
            result = db.insert_resume(userData)
            resume_id = result['id']
            print(f"✓ Resume inserted: {userData.get('name', 'Unknown')} (ID: {resume_id})")
        except Exception as e:
            print(f"✗ Error inserting resume: {e}")
            continue
        
        # Rank the resume
        try:
            Resume_rank_sheet = rank_resume(resume, user_input)
            
            # Update resume with ranking
            update_userData = updateUserState(Resume_rank_sheet, resume)
            db.update_resume(resume_id, update_userData)
            
            # Also add ranking as a separate entry
            db.add_ranking(resume_id, Resume_rank_sheet, user_input)
            
            print(f"✓ Total score: {Resume_rank_sheet['total_score']} / 100")
        except Exception as e:
            print(f"✗ Error ranking resume: {e}")
            
        print("-"*50)
        
except Exception as e:
    print(f"✗ Fatal error: {e}")
finally:
    # Always close database connection
    db.close_connection()
    end_time = time.time()
    print(f"\n{'='*50}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"{'='*50}")