import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from driver import configure_driver  
from PIL import Image, ImageChops
import imagehash


class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automated Testing Application")
        self.root.state('zoomed')  # Open in fullscreen mode

        self.driver = None
        self.screenshots = []
        self.test_messages = []  # Store messages for the final report

        self.setup_ui()

    def setup_ui(self):
        website_frame = ttk.LabelFrame(self.root, text="Choose Website to Test")
        website_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.website_var = tk.StringVar()
        self.website_var.set("https://parabank.parasoft.com/parabank/index.htm")

        ttk.Label(website_frame, text="Select a website:").pack(pady=(10, 5))
        ttk.Radiobutton(website_frame, text="ParaBank", variable=self.website_var,
                        value="https://parabank.parasoft.com/parabank/index.htm").pack(anchor=tk.W)
        ttk.Radiobutton(website_frame, text="Other", variable=self.website_var,
                        value="").pack(anchor=tk.W)
        self.other_website_entry = ttk.Entry(website_frame, width=50)
        self.other_website_entry.pack(pady=(0, 10))

        test_frame = ttk.LabelFrame(self.root, text="Choose Test Scenario")
        test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.test_var = tk.StringVar()
        self.test_var.set("open_account")

        ttk.Label(test_frame, text="Select a test scenario:").pack(pady=(10, 5))
        ttk.Radiobutton(test_frame, text="User Registration", variable=self.test_var,
                        value="register", command=self.load_last_screenshot).pack(anchor=tk.W)
        ttk.Radiobutton(test_frame, text="User Login", variable=self.test_var,
                        value="login", command=self.load_last_screenshot).pack(anchor=tk.W)
        ttk.Radiobutton(test_frame, text="Open New Account", variable=self.test_var,
                        value="open_account", command=self.load_last_screenshot).pack(anchor=tk.W)
        ttk.Radiobutton(test_frame, text="Account Overview Display", variable=self.test_var,
                        value="overview", command=self.load_last_screenshot).pack(anchor=tk.W)
        ttk.Radiobutton(test_frame, text="View Account Overview", variable=self.test_var,
                        value="view_overview", command=self.load_last_screenshot).pack(anchor=tk.W)

        screenshot_frame = ttk.LabelFrame(self.root, text="Screenshots")
        screenshot_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(screenshot_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(screenshot_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        ttk.Button(self.root, text="Run Test", command=self.run_test).pack(pady=10)

    def configure_driver(self):
        options = Options()
        options.headless = True
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def take_screenshot(self, description):
        if not os.path.exists('screenshots'):
            os.makedirs('screenshots')

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"screenshots/{description}_{timestamp}.png"
        self.driver.save_screenshot(filename)
        self.screenshots.append(filename)
        self.update_screenshot_canvas(filename)

        # Compare with the previous screenshot with a similar description pattern
        if len(self.screenshots) > 1:
            current_screenshot = self.screenshots[-1]
            current_time = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
            
            # Look for the previous screenshot with the same description pattern
            similar_screenshot = None
            for prev_screenshot in reversed(self.screenshots[:-1]):
                prev_timestamp = os.path.basename(prev_screenshot).split('_')[-1][:-4]  # Extract timestamp part
                prev_time = datetime.strptime(prev_timestamp, "%Y%m%d-%H%M%S")
                
                # Compare if the descriptions match and if the previous timestamp is earlier
                if description in prev_screenshot and prev_time < current_time:
                    similar_screenshot = prev_screenshot
                    break
            
            # Perform comparison if a similar screenshot is found
            if similar_screenshot:
                difference = self.compare_images_hash(similar_screenshot, current_screenshot)
                if difference:
                    self.test_messages.append(f"Differences detected between {os.path.basename(similar_screenshot)} and {os.path.basename(current_screenshot)}.")
                else:
                    self.test_messages.append(f"No differences detected between {os.path.basename(similar_screenshot)} and {os.path.basename(current_screenshot)}.")
            else:
                self.test_messages.append(f"No previous screenshot found for comparison with {os.path.basename(current_screenshot)}.")

    def update_screenshot_canvas(self, image_path):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        img = tk.PhotoImage(file=image_path)
        label = tk.Label(self.scrollable_frame, image=img)
        label.image = img
        label.pack()

    def load_last_screenshot(self):
        selected_test = self.test_var.get()
        screenshots_dir = 'screenshots'
        if os.path.exists(screenshots_dir):
            screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
            test_screenshots = [f for f in screenshots if f.startswith(selected_test)]
            if test_screenshots:
                latest_screenshot = max(test_screenshots, key=lambda x: os.path.getctime(os.path.join(screenshots_dir, x)))
                self.update_screenshot_canvas(os.path.join(screenshots_dir, latest_screenshot))
            else:
                self.test_messages.append(f"No screenshots found for test: {selected_test}")
        else:
            self.test_messages.append("Screenshots directory does not exist")

   

    def test_user_registration(self):
        self.driver.get(self.website_var.get())
        self.take_screenshot("register_opened_home_page")

        self.driver.find_element(By.LINK_TEXT, "Register").click()
        self.take_screenshot("register_clicked_register")

        self.driver.find_element(By.ID, "customer.firstName").send_keys("John")
        self.driver.find_element(By.ID, "customer.lastName").send_keys("Doe")
        self.driver.find_element(By.ID, "customer.address.street").send_keys("123 Main St")
        self.driver.find_element(By.ID, "customer.address.city").send_keys("Anytown")
        self.driver.find_element(By.ID, "customer.address.state").send_keys("Anystate")
        self.driver.find_element(By.ID, "customer.address.zipCode").send_keys("12345")
        self.driver.find_element(By.ID, "customer.phoneNumber").send_keys("555-1234")
        self.driver.find_element(By.ID, "customer.ssn").send_keys("123-45-6789")
        self.driver.find_element(By.ID, "customer.username").send_keys("johndoe")
        self.driver.find_element(By.ID, "customer.password").send_keys("password")
        self.driver.find_element(By.ID, "repeatedPassword").send_keys("password")
        self.take_screenshot("register_filled_registration_form")

        self.driver.find_element(By.CSS_SELECTOR, "input.button[value='Register']").click()
        self.driver.implicitly_wait(10)
        self.take_screenshot("register_submitted_registration")

    def test_user_login(self):
        self.driver.get(self.website_var.get())
        self.take_screenshot("login_opened_home_page")

        self.driver.find_element(By.NAME, "username").send_keys("johndoe")
        self.driver.find_element(By.NAME, "password").send_keys("password")
        self.driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        self.take_screenshot("login_logged_in")

    def test_open_account(self):
        self.driver.get(self.website_var.get())
        self.take_screenshot("open_account_opened_home_page")

        self.test_user_login()

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Open New Account"))
            )
            element.click()
            self.take_screenshot("open_account_opened_new_account_page")

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "type"))
            )

            account_type_dropdown = Select(self.driver.find_element(By.ID, "type"))
            try:
                account_type_dropdown.select_by_value("0")
                self.take_screenshot("open_account_selected_account_type")
            except NoSuchElementException:
                account_type_dropdown.select_by_index(0)
                self.take_screenshot("open_account_selected_account_type_default")

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "fromAccountId"))
            )

            account_dropdown = Select(self.driver.find_element(By.ID, "fromAccountId"))
            try:
                account_dropdown.select_by_index(1)
                self.take_screenshot("open_account_selected_account")
            except NoSuchElementException:
                self.take_screenshot("open_account_account_option_not_found")

            try:
                element = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Open New Account']"))
                )
                element.click()
                self.take_screenshot("open_account_clicked_open_new_account")

                WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@id='success-message']"))
                )
                self.take_screenshot("open_account_account_opened_successfully")

            except TimeoutException:
                self.take_screenshot("open_account_button_timeout")
                self.test_messages.append("Timeout Error: Failed to open a new account.")

        except TimeoutException:
            self.take_screenshot("open_account_link_timeout")
            self.test_messages.append("Timeout Error: Failed to find 'Open New Account' link or button within 10 seconds.")

    def test_account_overview_display(self):
        self.driver.get(self.website_var.get())
        self.take_screenshot("overview_opened_home_page")

        self.test_user_login()

        self.driver.find_element(By.LINK_TEXT, "Accounts Overview").click()
        time.sleep(10)
        self.take_screenshot("overview_opened_accounts_overview")

    def test_view_account_overview(self):
        self.driver.get(self.website_var.get())
        self.take_screenshot("view_overview_opened_home_page")

        self.test_user_login()

        self.driver.find_element(By.LINK_TEXT, "Accounts Overview").click()
        time.sleep(10)
        self.take_screenshot("view_overview_view_account_overview")

    def run_test(self):
        selected_test = self.test_var.get()

        if not self.website_var.get() or (self.website_var.get() == "" and not self.other_website_entry.get()):
            self.test_messages.append("Website Error: Please provide a website URL.")
            return

        if self.website_var.get() == "":
            self.website_var.set(self.other_website_entry.get())

        self.configure_driver()

        if selected_test == "register":
            self.test_user_registration()
        elif selected_test == "login":
            self.test_user_login()
        elif selected_test == "open_account":
            self.test_open_account()
        elif selected_test == "overview":
            self.test_account_overview_display()
        elif selected_test == "view_overview":
            self.test_view_account_overview()

        if self.driver:
            self.driver.quit()

        self.load_last_screenshot()
        self.show_test_report()

    def show_test_report(self):
        report_window = tk.Toplevel(self.root)
        report_window.title("Test Report")
        report_window.geometry("600x400")

        report_text = tk.Text(report_window, wrap=tk.WORD)
        report_text.pack(fill=tk.BOTH, expand=True)

        report_content = "\n".join(self.test_messages)
        report_text.insert(tk.END, report_content)

