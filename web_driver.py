# web_driver.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def configure_driver():
    options = Options()
    options.headless = True
    options.add_argument("--disable-search-engine-choice-screen")
    
    chromedriver_path = ChromeDriverManager().install()
    service = Service(chromedriver_path)
    
    return webdriver.Chrome(service=service, options=options)