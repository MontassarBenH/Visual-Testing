# configure_driver.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.events import EventFiringWebDriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os

class configure_driver:
    def __init__(self):
        self.driver = None
        self.chromedriver_executable = None

    def configure_driver(self):
        if not hasattr(self, 'chromedriver_executable') or self.chromedriver_executable is None:
            chromedriver_path = ChromeDriverManager().install()
            chromedriver_dir = os.path.dirname(chromedriver_path)

            for file_name in os.listdir(chromedriver_dir):
                if 'chromedriver' in file_name and os.access(os.path.join(chromedriver_dir, file_name), os.X_OK):
                    self.chromedriver_executable = os.path.join(chromedriver_dir, file_name)
                    break
            
            if not self.chromedriver_executable:
                raise FileNotFoundError("Could not find the ChromeDriver executable in the directory.")
        
        options = Options()
        options.headless = True
        options.add_argument("--disable-search-engine-choice-screen")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        
        service = Service(self.chromedriver_executable)
        self.driver = webdriver.Chrome(service=service, options=options)
        print(f"WebDriver initialized: {self.driver is not None}")
        
    def close_driver(self):
        if self.driver:
            self.driver.quit()
