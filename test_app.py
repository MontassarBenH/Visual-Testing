import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException
from PIL import Image, ImageChops, ImageTk
from skimage.metrics import structural_similarity as ssim
import numpy as np

class TestApp:

    def configure_driver(self):
        options = Options()
        options.headless = True
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def __init__(self, root):
        self.root = root
        self.root.title("Automated Testing Application")
        self.root.state('zoomed')  # Open in fullscreen mode

        self.driver = None
        self.screenshots = []
        self.test_messages = []  # Store messages for the final report
        self.uploaded_image_path = None

        self.setup_ui()

    def setup_ui(self):
        # Main layout frames
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Website selection UI
        website_frame = ttk.LabelFrame(left_frame, text="Choose Website to Test")
        website_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.website_var = tk.StringVar()
        self.website_var.set("https://parabank.parasoft.com/parabank/index.htm")
        self.website_var.trace('w', self.update_test_scenarios)

        ttk.Label(website_frame, text="Select a website:").pack(pady=(10, 5))
        ttk.Radiobutton(website_frame, text="ParaBank", variable=self.website_var,
                        value="https://parabank.parasoft.com/parabank/index.htm").pack(anchor=tk.W)
        ttk.Radiobutton(website_frame, text="Demo App", variable=self.website_var,
                        value="http://localhost:3000/").pack(anchor=tk.W)  # Replace with actual path
        self.other_website_entry = ttk.Entry(website_frame, width=50)
        self.other_website_entry.pack(pady=(0, 10))

        # Test scenarios UI
        self.test_frame = ttk.LabelFrame(left_frame, text="Choose Test Scenario")
        self.test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.test_var = tk.StringVar()
        self.update_test_scenarios()

        # Run test button
        ttk.Button(left_frame, text="Run Test", command=self.run_test).pack(pady=10)

        # Upload image button
        ttk.Button(left_frame, text="Upload Image for Comparison", command=self.upload_image).pack(pady=10)

        # Test report UI
        report_frame = ttk.LabelFrame(left_frame, text="Test Report")
        report_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.report_text = tk.Text(report_frame, wrap=tk.WORD)
        self.report_text.pack(fill=tk.BOTH, expand=True)

        # Screenshots UI
        screenshot_frame = ttk.LabelFrame(right_frame, text="Screenshots")
        screenshot_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(screenshot_frame, width=800)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(screenshot_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind the <Configure> event to resize images when the canvas is resized
        self.canvas.bind("<Configure>", lambda e: self.reload_latest_screenshot())

    def upload_image(self):
        self.uploaded_image_path = filedialog.askopenfilename(
            title="Select Image for Comparison",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*"))
        )
        if self.uploaded_image_path:
            self.test_messages.append(f"Uploaded image for comparison: {self.uploaded_image_path}")

    def reload_latest_screenshot(self):
        if self.screenshots:
            self.update_screenshot_canvas(self.screenshots[-1])

    def update_test_scenarios(self, *args):
        for widget in self.test_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.test_frame, text="Select a test scenario:").pack(pady=(10, 5))
        
        if self.website_var.get() == "https://parabank.parasoft.com/parabank/index.htm":
            scenarios = [
                ("Scenario 1: User Registration", "register"),
                ("Scenario 2: User Login", "login"),
                ("Scenario 3: Open New Account", "open_account"),
                ("Scenario 4: Account Overview Display", "overview"),
                ("Scenario 5: View Account Overview", "view_overview")
            ]
        else:
            scenarios = [
                ("Scenario 1: Visual Test", "visual_test")
            ]

        for text, value in scenarios:
            ttk.Radiobutton(self.test_frame, text=text, variable=self.test_var,
                            value=value, command=self.load_screenshots_for_test).pack(anchor=tk.W)

    

    def take_screenshot(self, description):
        # Check if the 'screenshots' directory exists, if not, create it
        if not os.path.exists('screenshots'):
            os.makedirs('screenshots')

        # Generate a timestamp for the screenshot filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        # Create the filename using the description and timestamp
        filename = f"screenshots/{description}_{timestamp}.png"
        # Save the screenshot using the driver
        self.driver.save_screenshot(filename)
        
        # Compare with the previous screenshot if it exists
        if self.screenshots:
            previous_screenshot = self.screenshots[-1]
            current_screenshot = filename
            difference = self.compare_images(previous_screenshot, current_screenshot)
            if difference < 0.99:  
                self.test_messages.append(f"Differences detected between {os.path.basename(previous_screenshot)} and {os.path.basename(current_screenshot)}.")
                self.screenshots.append(filename)
            else:
                # Override the previous screenshot if there are no significant differences
                os.remove(previous_screenshot)
                self.screenshots[-1] = filename
                self.test_messages.append(f"No significant differences detected. Overriding {os.path.basename(previous_screenshot)} with {os.path.basename(current_screenshot)}.")
        else:
            self.screenshots.append(filename)
        
        # Update the screenshot canvas with the new screenshot
        self.update_screenshot_canvas(filename)

    def update_screenshot_canvas(self, image_path):
        # Open the image from the provided path using PIL (Pillow)
        img = Image.open(image_path)
        
        # Get the current width and height of the canvas widget
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Resize the image to fit within the canvas while maintaining aspect ratio
        img.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
        
        # Convert the PIL image to a format that can be used in Tkinter (ImageTk.PhotoImage)
        img_tk = ImageTk.PhotoImage(img)

        # Clear any previous images or drawings on the canvas
        self.canvas.delete("all")
        
        # Draw the image on the canvas, centered both horizontally and vertically
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=img_tk, anchor=tk.CENTER)
        
        
        # Keep a reference to the image to prevent it from being garbage collected
        self.canvas.image = img_tk

    def load_screenshots_for_test(self):
        selected_test = self.test_var.get()  # Get the currently selected test scenario
        screenshots_dir = 'screenshots'  # Define the directory where screenshots are stored
        
        # Clear any existing widgets in the scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Check if the screenshots directory exists
        if os.path.exists(screenshots_dir):
            # List all PNG files in the screenshots directory
            screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
            # Filter the screenshots to include only those that start with the selected test scenario
            test_screenshots = [f for f in screenshots if f.startswith(selected_test)]
            
            if test_screenshots:
                # Group screenshots by their base name (excluding timestamp)
                grouped_screenshots = {}
                for screenshot in test_screenshots:
                    base_name = '_'.join(screenshot.split('_')[:-1])
                    if base_name not in grouped_screenshots:
                        grouped_screenshots[base_name] = []
                    grouped_screenshots[base_name].append(screenshot)
                
                # Sort the groups by the creation time of the latest screenshot in each group
                sorted_groups = sorted(grouped_screenshots.values(), key=lambda group: max(os.path.getctime(os.path.join(screenshots_dir, s)) for s in group))
                # Get the latest group of screenshots
                latest_screenshots = sorted_groups[-1]
                
                # Display each screenshot in the latest group
                for screenshot in latest_screenshots:
                    self.update_screenshot_canvas(os.path.join(screenshots_dir, screenshot))
                    self.test_messages.append(f"Loaded screenshot: {screenshot}")
            else:
                # If no screenshots are found for the selected test, add a message
                self.test_messages.append(f"No screenshots found for test: {selected_test}")
        else:
            # If the screenshots directory does not exist, add a message
            self.test_messages.append("Screenshots directory does not exist")

    def compare_images(self, img1_path, img2_path):
        # Open and convert images to grayscale
        img1 = Image.open(img1_path).convert('L')
        img2 = Image.open(img2_path).convert('L')
        
        # Convert images to NumPy arrays
        img1_np = np.array(img1)
        img2_np = np.array(img2)
        
        # Compute the Structural Similarity Index (SSIM) and get the difference map
        ssim_index, diff = ssim(img1_np, img2_np, full=True)
        
        # Convert the difference map array back to an image
        diff_image = Image.fromarray((diff * 255).astype(np.uint8))
        
        # Save the difference image to a file 
        diff_image.save('diff_image.png')
        
        # Return the SSIM index, which indicates the similarity between the images
        return ssim_index
    
    def show_test_report(self):
        # Join all the test messages into a single string with newline separators
        report_content = "\n".join(self.test_messages)
        # Clear the current content of the report text widget
        self.report_text.delete(1.0, tk.END)
        # Insert the test report content into the report text widget
        self.report_text.insert(tk.END, report_content)
    
    def run_visual_test(self):
            try:
                # Navigate to the selected website
                self.driver.get(self.website_var.get())
                time.sleep(2)  # Wait for the page to fully load

                # Get the initial count from the text inside the specified element
                initial_count_text = self.driver.find_element(By.XPATH, "//div[@class='demo']/h1").text
                # Extract the count value, assuming it is the second to last word in the text
                initial_count = int(initial_count_text.split()[-2])
                # Take a screenshot of the initial count state
                self.take_screenshot("visual_test_initial_count")

                # Find the "Enable" button by its XPath and click it
                enable_button = self.driver.find_element(By.XPATH, "//button[span='Enable']")
                enable_button.click()
                time.sleep(1)  # Wait for the count to update
                # Take a screenshot after clicking the "Enable" button
                self.take_screenshot("visual_test_after_enable")

                # Get the updated count from the text inside the specified element
                updated_count_text = self.driver.find_element(By.XPATH, "//div[@class='demo']/h1").text
                # Extract the updated count value, assuming it is the second to last word in the text
                updated_count = int(updated_count_text.split()[-2])

                # Check if the count has incremented correctly
                if updated_count == initial_count + 1:
                    self.test_messages.append("Visual Test passed: Count incremented correctly after clicking 'Enable'.")
                else:
                    self.test_messages.append("Visual Test failed: Count did not increment correctly after clicking 'Enable'.")

                # Find the "Disable" button by its XPath and click it
                disable_button = self.driver.find_element(By.XPATH, "//button[span='Disable']")
                disable_button.click()
                time.sleep(1)  # Wait for the effect of the click
                # Take a screenshot after clicking the "Disable" button
                self.take_screenshot("visual_test_after_disable")
            
            # Handle the case where the browser window is unexpectedly closed
            except NoSuchWindowException:
                self.test_messages.append("Error: Browser window was closed unexpectedly.")
            # Catch any other exceptions that may occur and log the error message
            except Exception as e:
                self.test_messages.append(f"Error: {str(e)}")

    def test_user_registration(self):
        try:
            # Open the website specified in the UI
            self.driver.get(self.website_var.get())
            # Take a screenshot of the home page
            self.take_screenshot("register_opened_home_page")

            # Click on the "Register" link
            self.driver.find_element(By.LINK_TEXT, "Register").click()
            # Take a screenshot after clicking the register link

            self.take_screenshot("register_clicked_register")

            # Fill in the registration form fields
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
            # Take a screenshot after filling in the registration form
            self.take_screenshot("register_filled_registration_form")

            # Click on the "Register" button to submit the form
            self.driver.find_element(By.CSS_SELECTOR, "input.button[value='Register']").click()
            # Implicitly wait for up to 10 seconds for elements to be available
            self.driver.implicitly_wait(10)
            # Take a screenshot after submitting the registration form
            self.take_screenshot("register_submitted_registration")
        except NoSuchWindowException:
            # Append an error message if the browser window was closed unexpectedly
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            # Append any other exceptions that occur during the process
            self.test_messages.append(f"Error: {str(e)}")

    def test_user_login(self):
        try:
            self.driver.get(self.website_var.get())
            self.take_screenshot("login_opened_home_page")

            self.driver.find_element(By.NAME, "username").send_keys("johndoe")
            self.driver.find_element(By.NAME, "password").send_keys("password")
            self.driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
            self.take_screenshot("login_logged_in")
        except NoSuchWindowException:
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            self.test_messages.append(f"Error: {str(e)}")

    def test_open_account(self):
        try:
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
        except NoSuchWindowException:
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            self.test_messages.append(f"Error: {str(e)}")

    def test_account_overview_display(self):
        try:
            self.driver.get(self.website_var.get())
            self.take_screenshot("overview_opened_home_page")

            self.test_user_login()

            self.driver.find_element(By.LINK_TEXT, "Accounts Overview").click()
            time.sleep(10)
            self.take_screenshot("overview_opened_accounts_overview")
        except NoSuchWindowException:
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            self.test_messages.append(f"Error: {str(e)}")

    def test_view_account_overview(self):
        try:
            self.driver.get(self.website_var.get())
            self.take_screenshot("view_overview_opened_home_page")

            self.test_user_login()

            self.driver.find_element(By.LINK_TEXT, "Accounts Overview").click()
            time.sleep(10)
            self.take_screenshot("view_overview_view_account_overview")
        except NoSuchWindowException:
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            self.test_messages.append(f"Error: {str(e)}")

    def run_test(self):
            selected_test = self.test_var.get()

            # Clear the test messages at the beginning of each test run
            self.test_messages.clear()

            # Check if a website URL is provided
            if not self.website_var.get() or (self.website_var.get() == "" and not self.other_website_entry.get()):
                self.test_messages.append("Website Error: Please provide a website URL.")
                return

            # If no URL is selected from the options, use the URL entered in the other website entry
            if self.website_var.get() == "":
                self.website_var.set(self.other_website_entry.get())

            # Configure the WebDriver
            self.configure_driver()

            # Clear the list of previous screenshots
            self.screenshots.clear()

            try:
                # Run the test based on the selected scenario
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
                elif selected_test == "visual_test":
                    self.run_visual_test()
            except NoSuchWindowException:
                    # Append an error message if the browser window was closed unexpectedly
                    self.test_messages.append("Error: Browser window was closed unexpectedly.")
            except Exception as e:
                    # Append any other exceptions that occur during the process
                    self.test_messages.append(f"Error: {str(e)}")
            finally:
                    # Quit the WebDriver to close the browser window
                    if self.driver:
                        self.driver.quit()

                    # Load the screenshots taken during the test
                    self.load_screenshots_for_test()
                    # Display the test report
                    self.show_test_report()
                    
                    # Compare the uploaded image with the latest screenshot, if an image was uploaded
                    if self.uploaded_image_path and self.screenshots:
                        latest_screenshot = self.screenshots[-1]
                        difference = self.compare_images(self.uploaded_image_path, latest_screenshot)
                        if difference < 0.99:  
                            self.test_messages.append(f"Differences detected between uploaded image and {os.path.basename(latest_screenshot)}.")
                        else:
                            self.test_messages.append(f"No significant differences detected between uploaded image and {os.path.basename(latest_screenshot)}.")
                        self.show_test_report()
