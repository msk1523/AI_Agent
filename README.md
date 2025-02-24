# AI Job Application Agent

This project automates the job application process using AI, allowing you to efficiently search for jobs, assess your fit, generate cover letters, and (attempt to) submit applications.

## Overview

The AI Job Application Agent is a Python-based tool that leverages web scraping, natural language processing, and large language models to streamline the job search process. It automates the following steps:

*   **Job Discovery:** Searches for relevant job postings based on your criteria.
*   **Resume and Job Description Analysis:** Assesses your fit for a role based on your resume and the job description.
*   **Cover Letter Generation:** Creates personalized cover letters tailored to specific jobs.
*   **Application Submission:** (Attempts to) Automates the filling and submission of online applications.

**For a detailed explanation of the project's architecture, concepts, and tech stack, please read the [Medium blog post](https://medium.com/@mskmss1516/building-an-ai-powered-job-application-agent-automating-your-job-search-with-python-e6beab1862d4).**

## Tech Stack

*   Python
*   Streamlit
*   Selenium
*   PDFMiner.six
*   Langchain
*   Google Gemini
*   OpenAI GPT-3.5 Turbo
*   `webdriver_manager`
*   Beautiful Soup
*   Dotenv
*   Logging

## Prerequisites

*   Python 3.7+
*   A Google Gemini API key (configured as a Streamlit secret `GEMINI_API_KEY`).
*   An OpenAI API key (configured as an environment variable or another secure method).
*   Chrome browser installed.

## Installation

1.  Clone the repository:

    ```bash
    git clone <your_repository_url>
    cd <your_repository_directory>
    ```

2.  Create a virtual environment (recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```
    (If `requirements.txt` doesn't exist, create it and add the package names listed in the Tech Stack section)

4.  Create a `.env` file in the root directory and add your OpenAI API key:

    ```
    OPENAI_API_KEY=YOUR_OPENAI_API_KEY
    ```

    (Alternatively, configure your OpenAI API key through your system's environment variables.)

5. Configure your Gemini API key as a Streamlit secret, follow the instructions in the Streamlit documentation or create a file called `secrets.toml` in the same directory as your Streamlit app and put the following inside:
    ```toml
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
    ```

## Usage

1.  Run the Streamlit application:

    ```bash
    streamlit run main_function.py
    ```

2.  Open the application in your web browser (usually at `http://localhost:8501`).

3.  Configure the job search criteria (job title, location, experience level, etc.).

4.  Upload your resume (PDF).

5.  Enter your LinkedIn Profile Link.

6.  Click the "Start Applying!" button.

## Important Considerations

*   **LinkedIn's Terms of Service:** Automating LinkedIn interactions may violate their terms of service. Proceed with caution and be aware of the potential risks to your account.
*   **CAPTCHA Handling:** The application does not currently handle CAPTCHAs. You may need to implement a CAPTCHA solving service if you encounter them.
*   **Two-Factor Authentication:** Automating login with two-factor authentication is not supported.
*   **Selenium Configuration:** You may need to configure Selenium and ChromeDriver correctly for your operating system. The project uses `webdriver_manager` to handle this automatically, but you might need to specify the ChromeDriver path manually if you encounter issues. See previous responses for troubleshooting `GetHandleVerifier` errors.
*   **Application Form Variability:** The application submission process is highly dependent on the structure of the online job application forms. It may not work correctly for all websites.
*   **Ethical Considerations:** Avoid submitting a large number of untargeted applications. Focus on jobs that genuinely match your qualifications.
*   **Disclaimer:** Automated login may cause the bot to be flagged

## Disclaimer

This project is for educational and experimental purposes only. Use it at your own risk. The authors are not responsible for any consequences resulting from the use of this software.

## Contributing

Contributions are welcome! Please submit a pull request with your proposed changes.