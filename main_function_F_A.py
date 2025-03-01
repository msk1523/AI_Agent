import streamlit as st
from dotenv import load_dotenv
import os
import datetime
import re
import time
import logging
from pdfminer.high_level import extract_text
#import firecrawl #Removed since it's not working
#print(dir(firecrawl))
import agno
from duckduckgo_search import ddg

load_dotenv()

os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Set up logging
logging.basicConfig(filename="job_agent.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)

def clean_text(text):
    """Cleans up extracted job description text."""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def validate_inputs(resume_file, job_title, job_location):
    """Validates user inputs."""
    if not resume_file:
        st.error("Please upload a resume.")
        return False
    if not job_title:
        st.error("Please enter a job title.")
        return False
    if not job_location:
        st.error("Please enter a job location.")
        return False
    return True

def extract_resume_text(resume_file):
    """Extracts text from a PDF resume."""
    try:
        resume_text = extract_text(resume_file)
        logging.info("Successfully extracted text from resume.")
        return resume_text
    except Exception as e:
        st.error(f"Error extracting text from resume: {e}")
        logging.exception(f"Error extracting text from resume: {e}")
        return None

def search_jobs(job_title, job_location, num_results=5):
    """Uses DuckDuckGoSearch to search for job listings."""
    search_query = f"{job_title} in {job_location} site:linkedin.com/jobs"
    try:
        results = ddg(search_query, max_results=num_results)

        job_data = []
        for result in results:
            job_data.append({
                "title": result['title'],
                "link": result['href']
            })
        return job_data
    except Exception as e:
        st.error(f"Error during search: {e}")
        logging.exception(f"Search error: {e}")
        return []  # Return an empty list in case of an error


def get_job_description(job_link):
    """Placeholder for job description extraction.  Needs to be implemented with a scraping library if desired"""
    #st.write(f"Attempting to get job description from: {job_link}") #Debug
    #return "This is a placeholder job description. Implement scraping to get actual content."

    #------------------Previous Code------------------
    """Uses Firecrawl to extract job description from a job posting."""
    try:
        #The following code cannot be run because the firecrawl library is not working as intended
        #content = firecrawl.scrape(job_link)
        #cleaned_description = clean_text(content['text'])
        #return cleaned_description
        return "This is a placeholder job description. Implement scraping to get actual content." #Temporary return to run the code, since firecrawl cannot be used
    except Exception as e:
        st.error(f"Error retrieving job description: {e}")
        return None

def assess_job_fit(resume_text, job_description, job_title):
    """Uses Agno to assess job fit."""
    client = agno.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    prompt = f"""
    You are an expert recruiter. Analyze the following:
    
    Job Title: {job_title}
    Job Description: {job_description}
    Applicant Resume: {resume_text}
    
    Provide a summary of how well the resume matches the job. Give a score (1-10) and suggest improvements.
    """
    
    response = client.generate(prompt)
    return response

def generate_cover_letter(resume_text, job_description, job_title, company_name):
    """Uses Agno to generate a customized cover letter."""
    client = agno.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    prompt = f"""
    Write a compelling cover letter for the following applicant:
    
    Job Title: {job_title}
    Company: {company_name}
    Job Description: {job_description}
    Resume: {resume_text}
    
    The cover letter should be professional, tailored, and engaging.
    """
    
    response = client.generate(prompt)
    return response

def apply_for_jobs(resume_file, job_title, job_location, applications_per_day):
    """Main function to orchestrate job applications."""
    
    st.write(f"Applying for: {job_title} in {job_location}")
    
    resume_text = extract_resume_text(resume_file)
    if resume_text is None:
        st.error("Failed to extract text from resume.")
        return
    
    job_data = search_jobs(job_title, job_location, applications_per_day)
    
    for job in job_data:
        job_description = get_job_description(job["link"])
        if job_description:
            assessment = assess_job_fit(resume_text, job_description, job["title"])
            st.write(f"Assessment for {job['title']}:")
            st.write(assessment)
            
            cover_letter = generate_cover_letter(resume_text, job_description, job["title"], "Unknown")
            st.write(f"Cover Letter for {job['title']}:")
            st.write(cover_letter)
            
        time.sleep(15)  # Prevent rapid requests

# ------------------- User Interface (Streamlit) -------------------
st.title("AI Job Application Agent")

st.sidebar.header("Configuration")

job_title = st.sidebar.text_input("Job Title:", "Software Engineer")
job_location = st.sidebar.text_input("Job Location:", "Remote")
applications_per_day = st.sidebar.slider("Applications per Day:", 1, 20, 5)
resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if resume_file and st.button("Start Applying!"):
    if validate_inputs(resume_file, job_title, job_location):
        st.write("Starting the job application process...")
        apply_for_jobs(resume_file, job_title, job_location, applications_per_day)