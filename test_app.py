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
import test_scenarios

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
        self.screenshots = {}
        self.test_messages = []  # Store messages for the final report
        self.uploaded_image_path = None

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        website_frame = ttk.LabelFrame(left_frame, text="Choose Website to Test")
        website_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.website_var = tk.StringVar()
        self.website_var.set("https://parabank.parasoft.com/parabank/index.htm")
        self.website_var.trace('w', self.update_test_scenarios)

        ttk.Label(website_frame, text="Select a website:").pack(pady=(10, 5))
        ttk.Radiobutton(website_frame, text="ParaBank", variable=self.website_var,
                        value="https://parabank.parasoft.com/parabank/index.htm").pack(anchor=tk.W)
        ttk.Radiobutton(website_frame, text="Demo App", variable=self.website_var,
                        value="http://localhost:3000/").pack(anchor=tk.W)
        self.other_website_entry = ttk.Entry(website_frame, width=50)
        self.other_website_entry.pack(pady=(0, 10))

        self.test_frame = ttk.LabelFrame(left_frame, text="Choose Test Scenario")
        self.test_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.test_var = tk.StringVar()
        self.update_test_scenarios()

        ttk.Button(left_frame, text="Run Test", command=self.run_test).pack(pady=10)
        ttk.Button(left_frame, text="Upload Image for Comparison", command=self.upload_image).pack(pady=10)

        report_frame = ttk.LabelFrame(left_frame, text="Test Report")
        report_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.report_text = tk.Text(report_frame, wrap=tk.WORD)
        self.report_text.pack(fill=tk.BOTH, expand=True)

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
        
        self.canvas.bind("<Configure>", lambda e: self.reload_latest_screenshot())

    def upload_image(self):
        self.uploaded_image_path = filedialog.askopenfilename(
            title="Select Image for Comparison",
            filetypes=(("PNG files", ".png"), ("All files", ".*"))
        )
        if self.uploaded_image_path:
            self.test_messages.append(f"Uploaded image for comparison: {self.uploaded_image_path}")

    def reload_latest_screenshot(self):
        if self.screenshots:
            latest_screenshot_key = list(self.screenshots.keys())[-1]
            latest_screenshot_path = self.screenshots[latest_screenshot_key][-1]
            self.update_screenshot_canvas(latest_screenshot_path)

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
                            value=value, command=self.update_and_load_screenshots).pack(anchor=tk.W)
            
    def update_and_load_screenshots(self):
        self.update_test_scenarios()
        self.load_screenshots_for_test()

    def take_screenshot(self, description):
        time.sleep(2)  # Wait for the page to load completely
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        scenario = self.test_var.get()
        if not os.path.exists(f'screenshots/{scenario}'):
            os.makedirs(f'screenshots/{scenario}')
        
        filename = f"screenshots/{scenario}/{description}.png"
        self.driver.save_screenshot(filename)
        
        if scenario not in self.screenshots:
            self.screenshots[scenario] = []
        self.screenshots[scenario].append(filename)

    def compare_scenario_screenshots(self, scenario):
        screenshots_dir = f'screenshots/{scenario}'
        if os.path.exists(screenshots_dir):
            previous_run_files = sorted([f for f in os.listdir(screenshots_dir) if f.endswith('.png')], key=lambda x: os.path.getctime(os.path.join(screenshots_dir, x)))
            current_run_files = self.screenshots.get(scenario, [])

            for current, previous in zip(current_run_files, previous_run_files):
                previous_screenshot = os.path.join(screenshots_dir, previous)
                ssim_index = self.compare_images(previous_screenshot, current)
                if ssim_index < 0.99:
                    self.test_messages.append(f"Differences detected in {scenario}: {os.path.basename(previous_screenshot)} vs {os.path.basename(current)}")
                else:
                    self.test_messages.append(f"No significant differences detected between {os.path.basename(previous_screenshot)} and {os.path.basename(current)}.")

    def update_screenshot_canvas(self, image_path):
        img = Image.open(image_path)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=img_tk, anchor=tk.CENTER)
        self.canvas.image = img_tk

    def load_screenshots_for_test(self):
        selected_test = self.test_var.get()
        screenshots_dir = f'screenshots/{selected_test}'
        
        self.canvas.delete("all")
        
        if os.path.exists(screenshots_dir):
            all_screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
            
            if all_screenshots:
                all_screenshots.sort(key=lambda x: os.path.getctime(os.path.join(screenshots_dir, x)), reverse=True)
                latest_screenshot = all_screenshots[0]
                self.update_screenshot_canvas(os.path.join(screenshots_dir, latest_screenshot))
            else:
                self.test_messages.append(f"No screenshots found for test: {selected_test}")
                self.show_test_report()
        else:
            self.test_messages.append("Screenshots directory does not exist")
            self.show_test_report()

    def compare_images(self, img1_path, img2_path):
        img1 = Image.open(img1_path).convert('L')
        img2 = Image.open(img2_path).convert('L')
        
        # Crop images to the same size if needed 
        img1_cropped = img1.crop((50, 50, img1.width - 50, img1.height - 50))
        img2_cropped = img2.crop((50, 50, img2.width - 50, img2.height - 50))
        
        img1_np = np.array(img1_cropped)
        img2_np = np.array(img2_cropped)
        
        ssim_index, diff = ssim(img1_np, img2_np, full=True)
        diff_image = Image.fromarray((diff * 255).astype(np.uint8))
        diff_image.save('diff_image.png')
        
        return ssim_index
    
    def show_test_report(self):
        report_content = "\n".join(self.test_messages)
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(tk.END, report_content)

    def run_test(self):
        selected_test = self.test_var.get()
        self.test_messages.clear()

        if not self.website_var.get() or (self.website_var.get() == "" and not self.other_website_entry.get()):
            self.test_messages.append("Website Error: Please provide a website URL.")
            return

        if self.website_var.get() == "":
            self.website_var.set(self.other_website_entry.get())

        self.configure_driver()
        self.screenshots.clear()

        try:
            if selected_test == "register":
                test_scenarios.test_user_registration(self)
            elif selected_test == "login":
                test_scenarios.test_user_login(self)
            elif selected_test == "open_account":
                test_scenarios.test_open_account(self)
            elif selected_test == "overview":
                test_scenarios.test_account_overview_display(self)
            elif selected_test == "view_overview":
                test_scenarios.test_view_account_overview(self)
            elif selected_test == "visual_test":
                test_scenarios.run_visual_test(self)
        except NoSuchWindowException:
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            self.test_messages.append(f"Error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

            if selected_test in self.screenshots:
                self.compare_scenario_screenshots(selected_test)
            self.show_test_report()
