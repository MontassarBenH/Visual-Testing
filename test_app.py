# Standard library imports
import argparse
import glob
import json
import os
import smtplib
import subprocess
import time
from configparser import ConfigParser
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from tkinter import messagebox
import traceback

# Third-party imports
import cv2
import numpy as np
import openpyxl
import pandas as pd
from PIL import Image, ImageChops, ImageTk
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from skimage.metrics import structural_similarity as ssim
from webdriver_manager.chrome import ChromeDriverManager

# Tkinter imports
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import Toplevel


# Local application imports
from data_loader import load_test_data
from custom_data_form import CustomDataForm
import test_scenarios
from retry import retry




class TestApp:

    def configure_driver(self):
        if not hasattr(self, 'chromedriver_executable'):
            # Install ChromeDriver only once
            chromedriver_path = ChromeDriverManager().install()
            print(f"ChromeDriver installed at: {chromedriver_path}")
            
            chromedriver_dir = os.path.dirname(chromedriver_path)
            
            # Find the actual chromedriver executable
            for file_name in os.listdir(chromedriver_dir):
                if 'chromedriver' in file_name and os.access(os.path.join(chromedriver_dir, file_name), os.X_OK):
                    self.chromedriver_executable = os.path.join(chromedriver_dir, file_name)
                    break
            
            if not self.chromedriver_executable:
                raise FileNotFoundError("Could not find the ChromeDriver executable in the directory.")
            
            print(f"Using ChromeDriver executable at: {self.chromedriver_executable}")
        
        options = Options()
        options.headless = True
        options.add_argument("--disable-search-engine-choice-screen")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        
        service = Service(self.chromedriver_executable)
        
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)
        
        print(f"Chrome version: {self.driver.capabilities['browserVersion']}")
        print(f"ChromeDriver version: {self.driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]}")

    def close_driver(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    def health_check(self):
        url = "https://parabank.parasoft.com/parabank/index.htm"  
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            print(f"Website {url} is accessible")
            return True
        except requests.RequestException as e:
            print(f"Website {url} is not accessible: {e}")
            return False
        
    def clear_browser_data(self):
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("if (window.localStorage) { window.localStorage.clear(); }")
            self.driver.execute_script("if (window.sessionStorage) { window.sessionStorage.clear(); }")
            print("Browser data cleared successfully")
        except Exception as e:
            print(f"Error clearing browser data: {str(e)}")

    def __init__(self, root):
        self.root = root
        self.root.title("Automated Testing Application")
        self.root.state('zoomed')  # Open in fullscreen mode

        self.driver = None
        self.screenshots = {}
        self.test_results = []  # Store test results for the final report
        self.uploaded_image_path = None

        self.test_var = tk.StringVar()
        self.website_var = tk.StringVar()

        self.setup_initial_ui()

    def setup_initial_ui(self):
        self.initial_frame = ttk.Frame(self.root)
        self.initial_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        ttk.Label(self.initial_frame, text="Test Scenario:").grid(row=0, column=0, sticky="w", pady=5)
        self.scenario_var = tk.StringVar()
        self.scenario_combobox = ttk.Combobox(self.initial_frame, textvariable=self.scenario_var)
        self.scenario_combobox['values'] = ('register', 'login', 'open_account', 'overview', 'view_overview', 'visual_test')
        self.scenario_combobox.grid(row=0, column=1, pady=5)

        ttk.Label(self.initial_frame, text="Website URL:").grid(row=1, column=0, sticky="w", pady=5)
        self.website_entry = ttk.Entry(self.initial_frame)
        self.website_entry.grid(row=1, column=1, pady=5)

        ttk.Label(self.initial_frame, text="Email:").grid(row=2, column=0, sticky="w", pady=5)
        self.email_entry = ttk.Entry(self.initial_frame)
        self.email_entry.grid(row=2, column=1, pady=5)

        self.data_choice_var = tk.StringVar(value="default")
        ttk.Radiobutton(self.initial_frame, text="Use Default Data", variable=self.data_choice_var, value="default").grid(row=3, column=0, pady=5)
        ttk.Radiobutton(self.initial_frame, text="Use Custom Data", variable=self.data_choice_var, value="custom").grid(row=3, column=1, pady=5)

        ttk.Button(self.initial_frame, text="Run Test", command=self.start_test).grid(row=4, column=0, columnspan=2, pady=20)

    def start_test(self):
        scenario = self.scenario_var.get()
        website = self.website_entry.get()
        email = self.email_entry.get()
        use_custom_data = self.data_choice_var.get() == "custom"

        if not scenario or not website or not email:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        self.initial_frame.pack_forget()
        self.setup_ui()  

        #data = None
        #if use_custom_data:
            #data = self.get_custom_data(scenario)

        self.run_test(scenario, website, email, use_custom_data)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew")

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=5)
        main_frame.rowconfigure(0, weight=1)

        # Configure report frame
        report_frame = ttk.LabelFrame(right_frame, text="Test Report")
        report_frame.pack(padx=10, pady=10, fill=tk.X, expand=False)

        self.tree = ttk.Treeview(report_frame, columns=("Description", "Status", "Date", "Commit Hash", "Difference Percentage", "Screenshot 1", "Screenshot 2"), show='headings')
        self.tree.heading("Description", text="Description")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Commit Hash", text="Commit Hash")
        self.tree.heading("Difference Percentage", text="Difference Percentage")
        self.tree.heading("Screenshot 1", text="Screenshot 1")
        self.tree.heading("Screenshot 2", text="Screenshot 2")

        self.tree.pack(fill=tk.X, expand=False)

        # Configure screenshot frame below report frame
        screenshot_frame = ttk.LabelFrame(right_frame, text="Screenshots")
        screenshot_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(screenshot_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(screenshot_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

    def find_element(self, by, value):
        return WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((by, value)))


    def click_element(self, by, value):
        elem = self.find_element(by, value)
        elem.click()

    def fill_form(self, form_data):
         for locator, value in form_data.items():
            element = self.find_element(*locator)
            element.clear()
            element.send_keys(value)

    def trans(css_selector):
        return By.CSS_SELECTOR, css_selector
    
    def select_from_dropdown_by_value(self, by, value, option_value):
        dropdown = Select(self.find_element(by, value))
        dropdown.select_by_value(option_value)

    def select_from_dropdown_by_index(self, by, value, index):
        dropdown = Select(self.find_element(by, value))
        dropdown.select_by_index(index)

    def take_screenshot(self, description):
        time.sleep(2)  # Wait for the page to load completely
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        scenario = self.test_var.get()
        if not os.path.exists(f'screenshots/{scenario}'):
            os.makedirs(f'screenshots/{scenario}')

        filename = f"screenshots/{scenario}/{description}_{timestamp}.png"
        self.driver.save_screenshot(filename)

        if scenario not in self.screenshots:
            self.screenshots[scenario] = []
        self.screenshots[scenario].append(filename)

         # Calculate the position in the grid
        num_screenshots = len(self.screenshots[scenario])
        column_index = (num_screenshots - 1) % 2  # 2 images per row
        row_index = (num_screenshots - 1) // 2
        
        # Display the screenshot in the UI canvas
        self.display_screenshot(filename, column_index=column_index, row_index=row_index)

    def compare_scenario_screenshots(self, scenario):
        screenshots_dir = f'screenshots/{scenario}'

        if os.path.exists(screenshots_dir):
            previous_run_files = sorted(
                [f for f in os.listdir(screenshots_dir) if f.endswith('.png')],
                key=lambda x: os.path.getctime(os.path.join(screenshots_dir, x))
            )

            current_run_files = self.screenshots.get(scenario, [])

        # Function to get the closest previous file based on timestamp and description
        def get_closest_previous_file(current_time, current_description, previous_files):
            closest_file = None
            closest_time_diff = float('inf')
            for prev_file in previous_files:
                if current_description in prev_file:
                    prev_time = os.path.getctime(os.path.join(screenshots_dir, prev_file))
                    if prev_time < current_time:
                        time_diff = current_time - prev_time
                        if time_diff < closest_time_diff:
                            closest_time_diff = time_diff
                            closest_file = prev_file
            return closest_file

        for current in current_run_files:
            current_time = os.path.getctime(current)
            current_description = os.path.basename(current).rsplit('_', 1)[0]  # Extract description
            previous = get_closest_previous_file(current_time, current_description, previous_run_files)

            if previous:
                previous_screenshot = os.path.join(screenshots_dir, previous)
                ssim_index, hist_comparison, pixel_diff_percentage = self.compare_images(previous_screenshot, current)

                if ssim_index < 0.99 or hist_comparison < 0.95 or pixel_diff_percentage > 5:
                    self.test_results.append({
                        "description": f"Differences detected in {scenario}: {os.path.basename(previous_screenshot)} vs {os.path.basename(current)}",
                        "status": "Failure",
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "commit_hash": "Master",
                        "difference_percentage": f"{pixel_diff_percentage:.2f}%",
                        "screenshot_1": os.path.basename(previous_screenshot),
                        "screenshot_2": os.path.basename(current)
                    })
                else:
                    self.test_results.append({
                        "description": f"No significant differences detected between {os.path.basename(previous_screenshot)} and {os.path.basename(current)}.",
                        "status": "Success",
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "commit_hash": "Master",
                        "difference_percentage": f"{pixel_diff_percentage:.2f}%",
                        "screenshot_1": os.path.basename(previous_screenshot),
                        "screenshot_2": os.path.basename(current)
                    })

    def delete_old_screenshots(self):
        for scenario, screenshots in self.screenshots.items():
            screenshots_dir = f'screenshots/{scenario}'
            
            # Get all screenshot files for the current scenario
            all_screenshots = sorted(glob.glob(f"{screenshots_dir}/*.png"), key=os.path.getctime)
            
            # Keep only the last 4 screenshots
            if len(all_screenshots) > 4:
                old_screenshots = all_screenshots[:-4]  # All except the last 4
                for screenshot in old_screenshots:
                    os.remove(screenshot)
                    print(f"Deleted old screenshot: {screenshot}")

    def display_screenshot(self, image_path, column_index=0, row_index=0):
        try:
            img = Image.open(image_path)

            if img is None:
                print(f"Failed to load image from {image_path}")
            else:
                print(f"Image loaded successfully from {image_path}")
            
            # Set new dimensions for larger images
            new_width = 600  # Increase width
            width, height = img.size
            aspect_ratio = height / width
            new_height = int(new_width * aspect_ratio)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)

            label = ttk.Label(self.scrollable_frame, image=img_tk)
            label.image = img_tk  # Keep a reference to avoid garbage collection
            label.grid(column=column_index, row=row_index, padx=5, pady=5)  # Use grid layout
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def get_test_data(self, scenario):
        print(f"Entering get_test_data for scenario: {scenario}")
        scenario_mapping = {
            "register": "register",
            "login": "login"
        }
        try:
            print("Attempting to load test data...")
            data = load_test_data("test_data.json")
            print(f"Loaded test data: {data}")

            scenario_key = scenario_mapping.get(scenario, scenario)
            print(f"Attempting to get scenario data for '{scenario_key}'")
            scenario_data = data.get(scenario_key, {})
            if not scenario_data:
                print(f"Warning: No data found for scenario '{scenario_key}'")
            print(f"Loaded data for {scenario}: {scenario_data}")

            print("Displaying messagebox...")
            choice = messagebox.askyesno("Data Source", "Do you want to use pre-defined test data?")
            print(f"User choice: {'Pre-defined' if choice else 'Custom'}")

            if choice:
                return scenario_data
            else:
                return self.get_custom_data(scenario)
        except Exception as e:
            print(f"Error in get_test_data: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            return {}
        finally:
            print("Exiting get_test_data")
        
    def get_custom_data(self, scenario):
        # Define the fields required for each scenario
        fields = {
            "register": [
                "customer.firstName", "customer.lastName", "customer.address.street",
                "customer.address.city", "customer.address.state", "customer.address.zipCode",
                "customer.phoneNumber", "customer.ssn", "customer.username",
                "customer.password", "repeatedPassword"
            ],
            "login": ["username", "password"],
        }

        custom_data = {}
        
        # Create a new top-level window
        custom_data_window = tk.Toplevel(self.root)
        custom_data_window.title(f"Enter Custom Data for {scenario}")
        
        # Create and place entry fields
        entries = {}
        for i, field in enumerate(fields.get(scenario, [])):
            tk.Label(custom_data_window, text=field).grid(row=i, column=0, sticky="e", padx=5, pady=2)
            entry = tk.Entry(custom_data_window)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[field] = entry
    
        def submit_data():
            for field, entry in entries.items():
                    custom_data[field] = entry.get()
            custom_data_window.destroy()
            
        tk.Button(custom_data_window, text="Submit", command=submit_data).grid(row=len(fields.get(scenario, [])), column=0, columnspan=2, pady=10)
            
            # Wait for the window to be closed
        self.root.wait_window(custom_data_window)
            
        return custom_data

    def compare_images(self, img1_path, img2_path):
        # Open and convert images to grayscale
        img1 = Image.open(img1_path).convert('L')
        img2 = Image.open(img2_path).convert('L')

        # Resize img2 if sizes do not match
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        # Convert images to numpy arrays
        img1_np = np.array(img1)
        img2_np = np.array(img2)

        # Calculate SSIM and obtain difference image
        ssim_index, diff = ssim(img1_np, img2_np, full=True)
        print(f"SSIM Index: {ssim_index}")

        # Calculate histogram comparison
        hist1 = cv2.calcHist([img1_np], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2_np], [0], None, [256], [0, 256])
        hist_comparison = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        print(f"Histogram Comparison: {hist_comparison}")

        # Calculate pixel difference percentage
        diff_pixels = np.sum(img1_np != img2_np)
        total_pixels = img1_np.size
        pixel_diff_percentage = (diff_pixels / total_pixels) * 100
        print(f"Pixel Difference Percentage: {pixel_diff_percentage}%")

        # Create and save the difference image
        diff_image = (diff * 255).astype(np.uint8)
        diff_image_path = 'diff_image.png'
        cv2.imwrite(diff_image_path, diff_image)

        # Create and save highlighted image if pixel difference percentage is higher than 20%
        if pixel_diff_percentage > 20:
            # Threshold the difference image
            _, thresholded_diff = cv2.threshold(diff_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

            # Find contours of the differences
            contours, _ = cv2.findContours(thresholded_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Convert the first image to RGB
            img1_color = cv2.cvtColor(img1_np, cv2.COLOR_GRAY2BGR)

            # Draw bounding boxes around the differences
            for contour in contours:
                if cv2.contourArea(contour) > 10:  # Filter out small contours
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(img1_color, (x, y), (x + w, y + h), (0, 0, 255), 2)

            # Save the highlighted image
            highlighted_img1_path = 'highlighted_Diff_img.png'
            cv2.imwrite(highlighted_img1_path, img1_color)

        return ssim_index, hist_comparison, pixel_diff_percentage

    def show_test_report(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for result in self.test_results:
            self.tree.insert("", "end", values=(result['description'], result['status'], result['date'], result['commit_hash'], result['difference_percentage'], result['screenshot_1'], result['screenshot_2']))

    def send_email_with_attachments(self, subject, body, to_email, files):
        config_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'config.ini')

        config = ConfigParser()
        config.read(config_path)
        from_email = config.get('credentials', 'email_address')
        password = config.get('credentials', 'email_password')

        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        body = 'Please find the attached test report and screenshots.'
        msg.attach(MIMEText(body, 'plain'))

        # Attach the Excel report
        filename = "test_report.xlsx"
        attachment = open(filename, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

         # Attach the screenshots
        latest_screenshot_time = 0
        for scenario, files in self.screenshots.items():
            for file_path in files:
                attachment = open(file_path, "rb")
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file_path)}")
                msg.attach(part)


         # Update the latest screenshot time
            screenshot_time = os.path.getmtime(file_path)
            if screenshot_time > latest_screenshot_time:
                latest_screenshot_time = screenshot_time
          
           # Get the current time of the test run
            current_test_time = time.time()

        # Check and attach the highlighted difference image if it exists and is new
        highlighted_img_path = 'highlighted_Diff_img.png'
        if os.path.exists(highlighted_img_path):
            highlighted_img_time = os.path.getmtime(highlighted_img_path)
            if highlighted_img_time >= latest_screenshot_time or highlighted_img_time >= current_test_time:
                with open(highlighted_img_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(highlighted_img_path)}")
                    msg.attach(part)

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(from_email, password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def save_report_to_excel(self):
        # Ensure any existing file is closed
        excel_file = 'test_report.xlsx'

        # Create a temporary file to avoid conflicts
        temp_file = 'temp_test_report.xlsx'

        try:
            # Save the report to a temporary file
            df = pd.DataFrame(self.test_results)
            df.to_excel(temp_file, index=False)
            print(f"Report saved to {temp_file}")

            # Load the workbook and adjust column widths
            workbook = openpyxl.load_workbook(temp_file)
            sheet = workbook.active

            column_widths = {
                'A': 50,  # Description
                'B': 15,  # Status
                'C': 20,  # Date
                'D': 15,  # Commit Hash
                'E': 20,  # Difference Percentage
                'F': 30,  # Screenshot 1
                'G': 30   # Screenshot 2
            }

            for col, width in column_widths.items():
                sheet.column_dimensions[col].width = width

            # Save the workbook with adjusted column widths
            workbook.save(excel_file)
            print(f"Report saved to {excel_file} with adjusted column widths")

        except Exception as e:
            print(f"Error saving report to Excel: {e}")

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @retry(tries=3, delay=2, backoff=2)
    def run_test(self, scenario, website, email, use_custom_data):

        self.test_var.set(scenario)
        self.website_var.set(website)
        self.test_results.clear()

        if not website:
            self.test_results.append({
                "description": "Website Error: Please provide a website URL.",
                "status": "Failure",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "commit_hash": "N/A",
                "difference_percentage": "N/A",
                "screenshot_1": "N/A",
                "screenshot_2": "N/A"
            })
            return

         # Initialize WebSession with a WebDriver instance
        self.configure_driver()  # Set up the WebDriver
        #session = WebSession(self.driver, website)  # Create a WebSession instance
        self.screenshots.clear()

        try:
            #if data is None:
             #data = self.get_test_data(scenario)

            #print(f"Data being used for {scenario}: {data}")  

            if use_custom_data:
                data = self.get_custom_data(scenario)
            else:
                data = load_test_data("test_data.json").get(scenario, {})

            if scenario == "register":
                test_scenarios.test_user_registration(self, data) 
            elif scenario == "login":
                 test_scenarios.test_user_login(self, data)
            elif scenario == "open_account":
                test_scenarios.test_open_account(self)
            elif scenario == "overview":
                test_scenarios.test_account_overview_display(self)
            elif scenario == "view_overview":
                test_scenarios.test_view_account_overview(self)
            elif scenario == "visual_test":
                test_scenarios.run_visual_test(self)
        except NoSuchWindowException:
            self.test_results.append({
                "description": "Error: Browser window was closed unexpectedly.",
                "status": "Failure",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "commit_hash": "N/A",
                "difference_percentage": "N/A",
                "screenshot_1": "N/A",
                "screenshot_2": "N/A"
            })
        except Exception as e:
            self.test_results.append({
                "description": f"Error: {str(e)}",
                "status": "Failure",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "commit_hash": "N/A",
                "difference_percentage": "N/A",
                "screenshot_1": "N/A",
                "screenshot_2": "N/A"
            })
        finally:
            if self.driver:
                self.close_driver()

            if scenario in self.screenshots:
                self.compare_scenario_screenshots(scenario)

            self.show_test_report()

            # Save report to Excel
            self.save_report_to_excel()

            # Prepare the report content for email
            report_content = "Description | Status | Date | Commit Hash | Difference Percentage | Screenshot 1 | Screenshot 2\n"
            report_content += "-" * 80 + "\n"
            for result in self.test_results:
                report_content += f"{result['description']} | {result['status']} | {result['date']} | {result['commit_hash']} | {result['difference_percentage']} | {result['screenshot_1']} | {result['screenshot_2']}\n"

            screenshots = [s for screenshot_list in self.screenshots.values() for s in screenshot_list]
            # Send email with the latest Excel report and screenshots
            self.send_email_with_attachments(
                subject="Automated Test Report",
                body=report_content,
                to_email=email,
                files=["test_report.xlsx"] + screenshots
            )

            # Delete old screenshots
            self.delete_old_screenshots()



def main():
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()