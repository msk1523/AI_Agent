import streamlit as st
from dotenv import load_dotenv
import os
import datetime
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from pdfminer.high_level import extract_text
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import google.generativeai as genai
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"] 

# Configure logging
logging.basicConfig(filename="job_agent.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)

def clean_job_description(job_description):
    # Remove HTML tags (if any)
    soup = BeautifulSoup(job_description, "html.parser")
    text = soup.get_text()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def validate_inputs(resume_file, job_title, job_location):
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
    try:
        resume_text = extract_text(resume_file)
        logging.info("Successfully extracted text from resume.")
        return resume_text
    except Exception as e:
        st.error(f"Error extracting text from resume: {e}")
        logging.exception(f"Error extracting text from resume: {e}") #log the error
        return None

def search_linkedin_jobs(job_title, job_location, experience_level="All", num_results=5):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    driver_manager = ChromeDriverManager()
    driver_path = driver_manager.install()  
    logging.debug(f"ChromeDriver path: {driver_path}")

    service = Service(driver_path)  # Use the explicit path
    driver = webdriver.Chrome(service=service, options=chrome_options) # Ensure ChromeDriver is in your PATH

    search_query = f"{job_title} at {job_location}"
    linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={job_title}&location={job_location}"

    if experience_level != "All": 

         linkedin_url += f"&f_E={experience_level}"


    try:
        driver.get(linkedin_url)
        logging.info(f"Searching LinkedIn with URL: {linkedin_url}") 

        
        WebDriverWait(driver, 30).until(
            lambda driver: len(driver.find_elements(By.CLASS_NAME, "job-card-container")) >= num_results
        )
        job_cards = driver.find_elements(By.CLASS_NAME, "job-card-container")

        job_data = []
        for card in job_cards[:num_results]: #limit the jobcards
            title = card.find_element(By.CLASS_NAME, "job-card-container__title").text
            company = card.find_element(By.CLASS_NAME, "job-card-container__company-name").text
            location = card.find_element(By.CLASS_NAME, "job-card-container__location").text
            link = card.find_element(By.TAG_NAME, 'a').get_attribute('href')
            job_data.append({"title": title, "company": company, "location": location, "link":link})

        return job_data


    except Exception as e:
        st.error(f"Error searching LinkedIn: {e}")
        logging.exception(f"Error searching LinkedIn: {e}") #log the error
        return []
    finally:
        driver.quit()

def get_job_description(job_link):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    try:
        driver.get(job_link)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "jobs-description__content"))
        )

        description_element = driver.find_element(By.CLASS_NAME, "jobs-description__content")
        job_description = description_element.text

        cleaned_description = clean_job_description(job_description)

        return cleaned_description

    except Exception as e:
        st.error(f"Error retrieving job description: {e}")
        return None
    finally:
        driver.quit()

def assess_job_fit(resume_text, job_description, job_title):

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])  # Use Gemini API key
    model = genai.GenerativeModel('gemini-pro') #initialize the model

    prompt_template = """
    You are a highly skilled recruiter. Assess the following job applicant's resume and job description
    to determine if the applicant is a good fit for the job.

    Job Title: {job_title}
    Job Description: {job_description}
    Applicant Resume: {resume_text}

    Provide a summary of the applicant's qualifications and experiences. Explain if and how their skills match up with the job requirements.
    Then give a score of 1-10 on how well this applicant fits the job (1 is not a good fit, 10 is perfect).
    Finally, suggest 3-5 areas to highlight on their cover letter to improve their application.
    """

    prompt = prompt_template.format(job_title=job_title, job_description=job_description, resume_text=resume_text)

    response = model.generate_content(prompt)
    return response.text #return the generated content

def generate_cover_letter(resume_text, job_description, job_title, company_name):

    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)  # Adjust model and temperature

    prompt_template = """
    You are a professional cover letter writer.  Write a compelling cover letter for the following job applicant,
    tailored to the specific job description and company. Use information from the resume to support your claims.

    Job Title: {job_title}
    Company Name: {company_name}
    Job Description: {job_description}
    Applicant Resume: {resume_text}

    Cover Letter:
    """

    prompt = PromptTemplate(template=prompt_template, input_variables=["job_title", "company_name", "job_description", "resume_text"])
    llm_chain = LLMChain(prompt=prompt, llm=llm)

    cover_letter = llm_chain.run(job_title=job_title, company_name=company_name, job_description=job_description, resume_text=resume_text)

    return cover_letter


def apply_for_jobs(resume_file, job_title, job_location, experience_level, applications_per_day, run_time): 

    st.write(f"Running with configuration: Title={job_title}, Location={job_location}, Experience={experience_level}, Applications/Day={applications_per_day}, Run Time={run_time}")

    resume_text = extract_resume_text(resume_file)

    if resume_text is None:
        st.error("Failed to extract text from resume.")
        return

    job_data = search_linkedin_jobs(job_title, job_location, experience_level, applications_per_day)

    if not job_data:
        st.info("No jobs found matching your criteria.")
        return

    results = []
    for job in job_data:
        job_description = get_job_description(job["link"])

        if job_description:
            # Assess job fit
            job_fit_assessment = assess_job_fit(resume_text, job_description, job["title"])


            results.append({
                "Title": job["title"],
                "Company": job["company"],
                "Location": job["location"],
                "Link": job["link"],
                "Job Fit Assessment": job_fit_assessment 
            })
        else:
            results.append({
                "Title": job["title"],
                "Company": job["company"],
                "Location": job["location"],
                "Link": job["link"],
                "Job Fit Assessment": "Could not retrieve Job description" 
            })


    st.write("## Matching Jobs")
    st.table(results)

# ------------------- User Interface (Streamlit) Code -------------------
st.title("AI Job Search Agent")

# Configuration Options
st.sidebar.header("Configuration")

job_title = st.sidebar.text_input("Desired Job Title/Keywords:", "Software Engineer, AI Developer")
job_location = st.sidebar.text_input("Desired Job Location:", "Remote, USA")
experience_level = st.sidebar.selectbox("Experience Level:", ["Entry Level", "Mid Level", "Senior Level", "All"])
applications_per_day = st.sidebar.slider("Max Jobs to Display:", 1, 20, 5)  # Changed label
run_time = st.sidebar.time_input("Time of Day to Run:", datetime.time(9, 0))  # Default 9:00 AM

resume_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

if resume_file is not None:
    st.success("Resume uploaded successfully!")
    # Button to trigger the agent
    if st.button("Search Jobs"):  # Changed button label
        if validate_inputs(resume_file, job_title, job_location):
            st.write("Agent started. Please wait...")
            apply_for_jobs(resume_file, job_title, job_location, experience_level, applications_per_day, run_time)  # Removed linked_profile