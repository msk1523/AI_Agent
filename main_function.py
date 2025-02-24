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

# Set up logging
logging.basicConfig(filename="job_agent.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)

def clean_job_description(job_description): 
    """Cleans up the job description text.""" 

    soup = BeautifulSoup(job_description, "html.parser")
    text = soup.get_text()

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
        logging.exception(f"Error extracting text from resume: {e}") #log the error
        return None

def search_linkedin_jobs(job_title, job_location, experience_level="All", num_results=5):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    driver_manager = ChromeDriverManager()
    driver_path = driver_manager.install()  # Install and get the path
    logging.debug(f"ChromeDriver path: {driver_path}")  # Log the path

    service = Service(driver_path) 
    driver = webdriver.Chrome(service=service, options=chrome_options) # Ensure ChromeDriver is in your PATH

    search_query = f"{job_title} at {job_location}"
    linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={job_title}&location={job_location}"

    if experience_level != "All":  

         linkedin_url += f"&f_E={experience_level}"


    try:
        driver.get(linkedin_url)
        logging.info(f"Searching LinkedIn with URL: {linkedin_url}")  # log the url

        WebDriverWait(driver, 30).until(
            lambda driver: all(
                len(card.find_element(By.CLASS_NAME, "job-card-container__title").text) > 0
                for card in driver.find_elements(By.CLASS_NAME, "job-card-container")[:num_results] #check only upto num_results
            )
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
    """Retrieves the full job description from the LinkedIn job page."""
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
    """Assesses how well the resume matches the job description using Gemini."""

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
    """Generates a customized cover letter using an LLM."""
# Add chatgpt model
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

def apply_to_job(job_link, cover_letter, resume_path, linkedin_profile_link):
    """Applies to the job using Selenium (simulates user actions)."""

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(linkedin_profile_link)
        driver.get(job_link)

        apply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "jobs-apply-button"))  # example change if wrong

        )
        apply_button.click()

        # Handle the application form (this will be highly variable)
        #  - Fill in text fields
        #  - Upload the resume (using `send_keys` on the file input element)
        #  - Paste the cover letter

        upload_element = driver.find_element(By.ID, "resume-upload-input") #example
        upload_element.send_keys(resume_path)

        cover_letter_textarea = driver.find_element(By.ID, "cover-letter-textarea") #example
        cover_letter_textarea.send_keys(cover_letter)

        submit_button = driver.find_element(By.CLASS_NAME, "final-submit-button") #example
        submit_button.click()

        st.success(f"Successfully applied to {job_link}")

    except Exception as e:
        st.error(f"Error applying to job: {e}")
    finally:
        driver.quit()

def apply_for_jobs(resume_file, job_title, job_location, experience_level, applications_per_day, run_time, linkedin_profile_link):
    """Main function to orchestrate the job application process."""

    st.write(f"Running with configuration: Title={job_title}, Location={job_location}, Experience={experience_level}, Applications/Day={applications_per_day}, Run Time={run_time}")  # debug

    resume_text = extract_resume_text(resume_file)

    if resume_text is None:
        st.error("Failed to extract text from resume.")
        return

    # Save the uploaded resume temporarily
    resume_path = "temp_resume.pdf"  # Temporary file name
    with open(resume_path, "wb") as f:
        f.write(resume_file.read())

    job_data = search_linkedin_jobs(job_title, job_location, experience_level, applications_per_day) 

    job_count = 0  

    for job in job_data:
        if job_count >= applications_per_day:
            st.info(f"Reached application limit for today ({applications_per_day}).")
            break

        job_description = get_job_description(job["link"])
        apply_to_job(job["link"], cover_letter, resume_path, linkedin_profile_link)

        if job_description is not None:
            job_fit_assessment = assess_job_fit(resume_text, job_description, job["title"])
            st.write(f"Job Fit Assessment for {job['title']}: {job_fit_assessment}")

            cover_letter = generate_cover_letter(resume_text, job_description, job["title"], job["company"])
            st.write(f"Cover Letter for {job['title']}:\n{cover_letter}")

            apply_to_job(job["link"], cover_letter, resume_path)

            job_count += 1  # Increment the counter
            time.sleep(15)  

    # Clean up temporary file
    os.remove(resume_path)

# ------------------- User Interface (Streamlit) Code -------------------
st.title("AI Job Application Agent")

st.sidebar.header("Configuration")

job_title = st.sidebar.text_input("Desired Job Title/Keywords:", "Software Engineer, AI Developer")
job_location = st.sidebar.text_input("Desired Job Location:", "Remote, USA")
experience_level = st.sidebar.selectbox("Experience Level:", ["Entry Level", "Mid Level", "Senior Level", "All"])
st.sidebar.header("LinkedIn Configuration")
linkedin_profile_link = st.sidebar.text_input("Your LinkedIn Profile Link:", "") # Added LinkedIn Profile Link input
applications_per_day = st.sidebar.slider("Applications per Day:", 1, 20, 5)  # Min, Max, Default
run_time = st.sidebar.time_input("Time of Day to Run:", datetime.time(9, 0))  # Default 9:00 AM

resume_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

if resume_file is not None:
    st.success("Resume uploaded successfully!")
    # Button to trigger the agent
    if st.button("Start Applying!"): 

     if validate_inputs(resume_file, job_title, job_location):
         st.write("Agent started. Please wait...")
         apply_for_jobs(resume_file, job_title, job_location, experience_level, applications_per_day, run_time, linkedin_profile_link)  # Pass all config options
