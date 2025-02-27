import streamlit as st
from dotenv import load_dotenv
import os
import datetime
import re
import time
import logging
from pdfminer.high_level import extract_text
import firecrawl
print(dir(firecrawl))
import agno

# Load environment variables
load_dotenv()
os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Set up logging
logging.basicConfig(filename="job_agent.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)

def clean_text(text):
    """Cleans up extracted job description text."""
    return re.sub(r'\s+', ' ', text).strip()

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
        return extract_text(resume_file)
    except Exception as e:
        logging.exception(f"Error extracting text from resume: {e}")
        return None

def search_jobs(job_title, job_location, num_results=5):
    """Uses Firecrawl to search for job listings."""
    search_query = f"{job_title} {job_location} site:linkedin.com/jobs"
    crawler = Crawler()
    results = firecrawl.scrape(search_query)
    
    job_data = []
    for result in results:
        job_data.append({
            "title": result.get('title', 'Unknown Job Title'),
            "link": result.get('url', '#')
        })
    return job_data

def get_job_description(job_link):
    """Uses Firecrawl to extract job description from a job posting."""
    try:
        crawler = Crawler()
        content = crawler.scrape(job_link)
        return clean_text(content.get('text', ''))
    except Exception as e:
        logging.exception(f"Error retrieving job description: {e}")
        return None

def assess_job_fit(resume_text, job_description, job_title):
    """Uses Agno to assess job fit."""
    client = agno.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""
    You are an expert recruiter. Analyze the following:
    
    Job Title: {job_title}
    Job Description: {job_description}
    Applicant Resume: {resume_text}
    
    Provide a summary of how well the resume matches the job. Give a score (1-10) and suggest improvements.
    """
    return client.generate(prompt)

def generate_cover_letter(resume_text, job_description, job_title, company_name):
    """Uses Agno to generate a customized cover letter."""
    client = agno.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""
    Write a compelling cover letter for the following applicant:
    
    Job Title: {job_title}
    Company: {company_name}
    Job Description: {job_description}
    Resume: {resume_text}
    
    The cover letter should be professional, tailored, and engaging.
    """
    return client.generate(prompt)

def apply_for_jobs(resume_file, job_title, job_location, applications_per_day):
    """Main function to orchestrate job applications."""
    st.write(f"Applying for: {job_title} in {job_location}")
    resume_text = extract_resume_text(resume_file)
    if not resume_text:
        st.error("Failed to extract text from resume.")
        return
    
    job_data = search_jobs(job_title, job_location, applications_per_day)
    
    for job in job_data:
        job_description = get_job_description(job["link"])
        if job_description:
            assessment = assess_job_fit(resume_text, job_description, job["title"])
            st.write(f"Assessment for {job['title']}: {assessment}")
            cover_letter = generate_cover_letter(resume_text, job_description, job["title"], "Unknown")
            st.write(f"Cover Letter for {job['title']}: {cover_letter}")
        time.sleep(15)  # Prevent rapid requests

# Streamlit UI
st.title("AI Job Application Agent")
st.sidebar.header("Configuration")

job_title = st.sidebar.text_input("Job Title:", "Software Engineer")
job_location = st.sidebar.text_input("Job Location:", "Remote")
applications_per_day = st.sidebar.slider("Applications per Day:", 1, 20, 5)
resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if resume_file and st.button("Start Applying!"):
    if validate_inputs(resume_file, job_title, job_location):
        apply_for_jobs(resume_file, job_title, job_location, applications_per_day)