import streamlit as st
from dotenv import load_dotenv
import os
import datetime
import re
import time
import logging
from pdfminer.high_level import extract_text
from duckduckgo_search import DDGS
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential  # Import tenacity

load_dotenv()

os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Set up Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# Try different model names
try:
    model = genai.GenerativeModel('gemini-2.0-flash') #Trying new model
except:
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-8b') #Trying new model
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')

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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def search_jobs(job_title, job_location, num_results=5):
    """Uses DuckDuckGoSearch to search for job listings with retry."""
    search_query = f"{job_title} in {job_location} site:linkedin.com/jobs"
    try:
        ddgs = DDGS()  # Initialize DDGS
        results = list(ddgs.text(search_query, max_results=num_results))  # Use DDGS to search

        job_data = []
        for result in results:
            job_data.append({
                "title": result['title'],
                "link": result['href']
            })
        return job_data
    except Exception as e:
        st.warning(f"Rate limit encountered during search. Retrying...")
        logging.warning(f"Rate limit encountered during search: {e}")
        raise  # Re-raise the exception for tenacity to handle

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

def generate_tailored_resume(resume_text, job_description, job_title):
    """Generates a tailored resume using the LaTeX template."""

    prompt = f"""
    You are an expert resume tailor. You will be given a job description and a resume. 
    You need to tailor the resume to match the job description. Focus on highlighting the skills and experiences 
    in the resume that are most relevant to the job description. Do not hallucinate. If the skill is not present do not include it.
    Here is the job title: {job_title}.
    Here is the job description: {job_description}.
    Here is the applicant resume: {resume_text}.

    Provide the tailored resume details, experiences and project details.

    """
    try:
        response = model.generate_content(prompt)
        tailored_content = response.text
    except Exception as e:
        st.error(f"Error generating tailored resume content: {e}")
        logging.exception(f"Tailored resume error: {e}")
        return None  # Or a default message

    # LaTeX Template (as provided)
    latex_template = r"""
\documentclass[10pt, letterpaper]{article}
\usepackage{enumitem}
\usepackage{geometry}
\geometry{left=0.75in,right=0.75in,top=0.75in,bottom=0.75in}

\begin{document}
\section*{article}
{article}

\section*{Summary}
{summary}

\section*{Experience}
{experience}

\section*{Education}
{education}

\section*{Experience_Details}
{Experience_Details}

\section*{Projects}
{projects}

\section*{Technical Skills}
{technical_skills}

\section*{Soft Skills}
{soft_skills}

\section*{Certifications}
{certifications}

\section*{Achievements}
{achievements}

\end{document}
"""

    # Use try-except blocks for each regex extraction
    article, summary, experience, education, Experience_Details, projects, technical_skills, soft_skills, certifications, achievements = "", "", "", "", "", "", "", "", "", ""
    try:
        article_match = re.search(r"Article:\s*(.*?)\s*Summary:", tailored_content, re.DOTALL)
        article = article_match.group(1).strip() if article_match else ""

        summary_match = re.search(r"Summary:\s*(.*?)\s*Experience:", tailored_content, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        experience_match = re.search(r"Experience:\s*(.*?)\s*Education:", tailored_content, re.DOTALL)
        experience = experience_match.group(1).strip() if experience_match else ""

        education_match = re.search(r"Education:\s*(.*?)\s*Experience Details:", tailored_content, re.DOTALL)
        education = education_match.group(1).strip() if education_match else ""

        Experience_Details_match = re.search(r"Experience Details:\s*(.*?)\s*Projects:", tailored_content, re.DOTALL)
        Experience_Details = Experience_Details_match.group(1).strip() if Experience_Details_match else ""

        projects_match = re.search(r"Projects:\s*(.*?)\s*Technical Skills:", tailored_content, re.DOTALL)
        projects = projects_match.group(1).strip() if projects_match else ""

        technical_skills_match = re.search(r"Technical Skills:\s*(.*?)\s*Soft Skills:", tailored_content, re.DOTALL)
        technical_skills = technical_skills_match.group(1).strip() if technical_skills_match else ""

        soft_skills_match = re.search(r"Soft Skills:\s*(.*?)\s*Certifications:", tailored_content, re.DOTALL)
        soft_skills = soft_skills_match.group(1).strip() if soft_skills_match else ""

        certifications_match = re.search(r"Certifications:\s*(.*?)\s*Achievements:", tailored_content, re.DOTALL)
        certifications = certifications_match.group(1).strip() if certifications_match else ""

        achievements_match = re.search(r"Achievements:\s*(.*)", tailored_content, re.DOTALL)
        achievements = achievements_match.group(1).strip() if achievements_match else ""
    except AttributeError as e:
        st.error(f"Error extracting content with regex: {e}")
        return None

    # Format technical skills and soft skills into LaTeX lists
    technical_skills_list = "\\\\".join(skill.strip() for skill in re.split(r",\s*", technical_skills))
    soft_skills_list = "\\\\".join(skill.strip() for skill in re.split(r",\s*", soft_skills))

    # Populate the LaTeX template
    try:
        tailored_latex = latex_template.format(
            article = article,
            summary=summary,
            experience=experience,
            education=education,
            Experience_Details = Experience_Details,
            projects=projects,
            technical_skills=technical_skills_list,
            soft_skills=soft_skills_list,
            certifications=certifications,
            achievements=achievements,
        )
    except KeyError as e:
        st.error(f"KeyError during LaTeX formatting: {e}.  Please check the output from Gemini and the LaTeX template.")
        return None

    return tailored_latex

def assess_job_fit(resume_text, job_description, job_title):
    """Uses Gemini to assess job fit."""

    prompt = f"""
    You are an expert recruiter. Analyze the following:

    Job Title: {job_title}
    Job Description: {job_description}
    Applicant Resume: {resume_text}

    Provide a summary of how well the resume matches the job. Give a score (1-10) and suggest improvements.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating assessment: {e}")
        logging.exception(f"Assessment error: {e}")
        return "Error generating assessment."

def generate_cover_letter(resume_text, job_description, job_title, company_name):
    """Uses Gemini to generate a customized cover letter."""

    prompt = f"""
    Write a compelling cover letter for the following applicant:

    Job Title: {job_title}
    Company: {company_name}
    Job Description: {job_description}
    Resume: {resume_text}

    The cover letter should be professional, tailored, and engaging.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating cover letter: {e}")
        logging.exception(f"Cover letter error: {e}")
        return "Error generating cover letter."

def apply_for_jobs(resume_file, job_title, job_location, applications_per_day):
    """Main function to orchestrate job applications."""

    st.write(f"Applying for: {job_title} in {job_location}")

    resume_text = extract_resume_text(resume_file)
    if resume_text is None:
        st.error("Failed to extract text from resume.")
        return

    job_data = []
    try:
        job_data = search_jobs(job_title, job_location, applications_per_day)
    except Exception as e:
        st.error(f"Failed to retrieve search results after multiple retries: {e}")
        return

    for job in job_data:
        job_description = get_job_description(job["link"])
        if job_description:
            # Generate the tailored resume
            tailored_resume_latex = generate_tailored_resume(resume_text, job_description, job["title"])
            if tailored_resume_latex:
                st.write("### Tailored Resume (LaTeX Code):")
                st.code(tailored_resume_latex, language="latex")  # Display LaTeX code

                assessment = assess_job_fit(resume_text, job_description, job["title"])
                st.write(f"Assessment for {job['title']}:")
                st.write(assessment)

                cover_letter = generate_cover_letter(resume_text, job_description, job["title"], "Unknown")
                st.write(f"Cover Letter for {job['title']}:")
                st.write(cover_letter)
            else:
                st.error("Failed to generate tailored resume.")

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