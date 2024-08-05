import tkinter as tk
import glob
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import json
import time
from PIL import Image ,ImageTk
import configparser


from datetime import datetime
from contextlib import contextmanager
import configparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import openpyxl
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait ,Select
from webdriver_manager.chrome import ChromeDriverManager

from test_scenarios import TestScenarioFactory
from custom_data_form import CustomDataForm
from image_comparison import compare_images

class TestApp:

    def configure_driver(self):
        options = Options()
        options.headless = True
        options.add_argument("--disable-search-engine-choice-screen")

        chromedriver_path = ChromeDriverManager().install()
        service = Service(chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=options)

    @contextmanager
    def get_driver(self):
        self.configure_driver()
        try:
            yield self.driver
        finally:
            if self.driver:
                self.driver.quit()

    def __init__(self, root):
        self.root = root
        self.root.title("Automated Testing Application")
        self.root.state('zoomed')

        self.driver = None
        self.screenshots = {}
        self.test_results = []
        self.uploaded_image_path = None

        self.test_var = tk.StringVar()
        self.website_var = tk.StringVar()

        self.create_ui()

    def create_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew")

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=5)
        main_frame.rowconfigure(0, weight=1)

        self.create_report_frame(right_frame)
        self.create_screenshot_frame(right_frame)

    def create_report_frame(self, parent):
        report_frame = ttk.LabelFrame(parent, text="Test Report")
        report_frame.pack(padx=10, pady=10, fill=tk.X, expand=False)

        self.tree = ttk.Treeview(report_frame, columns=("Description", "Status", "Date", "Commit Hash", "Difference Percentage", "Screenshot 1", "Screenshot 2"), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
        self.tree.pack(fill=tk.X, expand=False)

    def create_screenshot_frame(self, parent):
        screenshot_frame = ttk.LabelFrame(parent, text="Screenshots")
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
        time.sleep(2)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        scenario = self.test_var.get()
        if not os.path.exists(f'screenshots/{scenario}'):
            os.makedirs(f'screenshots/{scenario}')

        filename = f"screenshots/{scenario}/{description}_{timestamp}.png"
        self.driver.save_screenshot(filename)

        if scenario not in self.screenshots:
            self.screenshots[scenario] = []
        self.screenshots[scenario].append(filename)

        num_screenshots = len(self.screenshots[scenario])
        column_index = (num_screenshots - 1) % 2
        row_index = (num_screenshots - 1) // 2
        
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
                ssim_index, hist_comparison, pixel_diff_percentage = compare_images(previous_screenshot, current)

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


    def show_test_report(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for result in self.test_results:
            self.tree.insert("", "end", values=(result['description'], result['status'], result['date'], result['commit_hash'], result['difference_percentage'], result['screenshot_1'], result['screenshot_2']))

    def send_email_with_attachments(self, subject, body, to_email, files):
        config_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'config.ini')

        config = configparser.ConfigParser()
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
        excel_file = 'test_report.xlsx'
        temp_file = 'temp_test_report.xlsx'

        try:
            print(f"Attempting to save report with {len(self.test_results)} results")
            df = pd.DataFrame(self.test_results)
            df.to_excel(temp_file, index=False)
            print(f"Temporary file saved: {temp_file}")

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

            workbook.save(excel_file)
            print(f"Final report saved: {excel_file}")

        except Exception as e:
            print(f"Error saving report to Excel: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"Temporary file removed: {temp_file}")
                except Exception as e:
                    print(f"Error removing temporary file: {e}")
    
    def get_custom_scenario_data(self):
        form_data = {}
        dropdown_data = {}

        def submit():
            locator_type = locator_type_entry.get().upper()
            locator_value = locator_value_entry.get()
            input_value = input_value_entry.get()

            if locator_type and locator_value and input_value:
                locator = (getattr(By, locator_type), locator_value)
                form_data[locator] = input_value

            dropdown_locator_type = dropdown_locator_type_entry.get().upper()
            dropdown_locator_value = dropdown_locator_value_entry.get()
            selection_method = selection_method_entry.get().lower()
            option_value = option_value_entry.get()

            if dropdown_locator_type and dropdown_locator_value and selection_method and option_value:
                if selection_method == 'value':
                    dropdown_data = (getattr(By, dropdown_locator_type), dropdown_locator_value, 'value', option_value)
                elif selection_method == 'index':
                    dropdown_data = (getattr(By, dropdown_locator_type), dropdown_locator_value, 'index', int(option_value))

            root.quit()
            root.destroy()

        root = tk.Tk()
        root.title("Custom Scenario Setup")

        tk.Label(root, text="Form Data").grid(row=0, column=0, columnspan=3)

        tk.Label(root, text="Locator Type").grid(row=1, column=0)
        tk.Label(root, text="Locator Value").grid(row=1, column=1)
        tk.Label(root, text="Input Value").grid(row=1, column=2)

        locator_type_entry = tk.Entry(root)
        locator_value_entry = tk.Entry(root)
        input_value_entry = tk.Entry(root)

        locator_type_entry.grid(row=2, column=0)
        locator_value_entry.grid(row=2, column=1)
        input_value_entry.grid(row=2, column=2)

        tk.Label(root, text="Dropdown Data").grid(row=3, column=0, columnspan=4)

        tk.Label(root, text="Locator Type").grid(row=4, column=0)
        tk.Label(root, text="Locator Value").grid(row=4, column=1)
        tk.Label(root, text="Selection Method").grid(row=4, column=2)
        tk.Label(root, text="Option Value/Index").grid(row=4, column=3)

        dropdown_locator_type_entry = tk.Entry(root)
        dropdown_locator_value_entry = tk.Entry(root)
        selection_method_entry = tk.Entry(root)
        option_value_entry = tk.Entry(root)

        dropdown_locator_type_entry.grid(row=5, column=0)
        dropdown_locator_value_entry.grid(row=5, column=1)
        selection_method_entry.grid(row=5, column=2)
        option_value_entry.grid(row=5, column=3)

        tk.Button(root, text="Submit", command=submit).grid(row=6, column=1, columnspan=2)

        root.mainloop()
        
        return form_data, dropdown_data

    def run_custom_scenario(self, data):
        # Implement the logic for the custom scenario using the data collected
        form_data = data.get('form_data')
        dropdown_data = data.get('dropdown_data')
        
        # Example: Fill the form with the provided data
        if form_data:
            self.fill_form(form_data)
        
        # Example: Select from dropdowns with the provided data
        if dropdown_data:
            by, value, method, option_value = dropdown_data
            if method == 'value':
                self.select_from_dropdown_by_value(by, value, option_value)
            elif method == 'index':
                self.select_from_dropdown_by_index(by, value, option_value)

    def save_user_data(self, data):
        with open("user_data.json", 'w') as file:
            json.dump(data, file, indent=4)
        print("Data has been saved to user_data.json")

    def prompt_for_custom_data(self, default_data):
        custom_data_form = CustomDataForm(self.root, default_data)
        self.root.wait_window(custom_data_form)
        return custom_data_form.result if custom_data_form.result else default_data

    def run_test(self, scenario, website, email, data=None):
        self.test_var.set(scenario)
        self.website_var.set(website)
        self.test_results.clear()

        if not website:
            self.handle_test_exception(ValueError("Website URL is required"))
            return

        use_custom_data = messagebox.askyesno("Data Input", "Do you want to enter custom data?")
        if use_custom_data:
            data = self.prompt_for_custom_data(data)
            self.save_user_data({"user_registration": data, "user_login": data})

        self.screenshots.clear()

        with self.get_driver():
            try:
                test_function = TestScenarioFactory.get_scenario(scenario)
                if test_function:
                    test_function(self, data)
                else:
                    raise ValueError(f"Unknown scenario: {scenario}")
            except Exception as e:
                self.handle_test_exception(e)

        if scenario in self.screenshots:
            self.compare_scenario_screenshots(scenario)

        self.show_test_report()
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
        self.delete_old_screenshots()

    def handle_test_exception(self, exception):
            description = f"Error: {str(exception)}"
            self.test_results.append({
                "description": description,
                "status": "Failure",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "commit_hash": "N/A",
                "difference_percentage": "N/A",
                "screenshot_1": "N/A",
                "screenshot_2": "N/A"
            })

