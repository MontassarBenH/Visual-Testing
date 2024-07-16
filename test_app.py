import argparse
import json
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
import cv2
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

        self.test_var = tk.StringVar()
        self.website_var = tk.StringVar()

        self.setup_ui()

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

        report_frame = ttk.LabelFrame(left_frame, text="Test Report")
        report_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.report_text = tk.Text(report_frame, wrap=tk.WORD)
        self.report_text.pack(fill=tk.BOTH, expand=True)

        screenshot_frame = ttk.LabelFrame(right_frame, text="Screenshots")
        screenshot_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(screenshot_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(screenshot_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)


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
        # Define the directory where the screenshots for the given scenario are stored
        screenshots_dir = f'screenshots/{scenario}'

        # Check if the screenshots directory exists
        if os.path.exists(screenshots_dir):
            # Get the list of all PNG files in the screenshots directory, sorted by creation time
            previous_run_files = sorted(
                [f for f in os.listdir(screenshots_dir) if f.endswith('.png')],
                key=lambda x: os.path.getctime(os.path.join(screenshots_dir, x))
            )

            # Get the list of screenshots taken during the current run for the given scenario
            current_run_files = self.screenshots.get(scenario, [])

            # Iterate through pairs of current run screenshots and previous run screenshots
            for current, previous in zip(current_run_files, previous_run_files):
                # Get the full path of the previous screenshot
                previous_screenshot = os.path.join(screenshots_dir, previous)
                
                # Compare the current screenshot with the previous one
                ssim_index, hist_comparison, pixel_diff_percentage = self.compare_images(previous_screenshot, current)

            # Check if the Structural Similarity Index (SSIM) is below 0.99, indicating significant differences
            if ssim_index < 0.99 or hist_comparison < 0.95 or pixel_diff_percentage > 5:
                # If differences are detected based on any of the three metrics
                self.test_messages.append(f"Differences detected in {scenario}: {os.path.basename(previous_screenshot)} vs {os.path.basename(current)}")
            else:
                # If no significant differences are detected based on all three metrics
                self.test_messages.append(f"No significant differences detected between {os.path.basename(previous_screenshot)} and {os.path.basename(current)}.")




    def update_screenshot_canvas(self, image_path):
        img = Image.open(image_path)

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        img.thumbnail((canvas_width, canvas_height), Image.LANCZOS)

        img_tk = ImageTk.PhotoImage(img)

        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=img_tk, anchor=tk.CENTER)
        self.canvas.image = img_tk

    def load_screenshots_for_test(self):
        selected_test = self.test_var.get()
        screenshots_dir = f'screenshots/{selected_test}'

        print(f"Loading screenshots for test: {selected_test}")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if os.path.exists(screenshots_dir):
            all_screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
            print(f"Found {len(all_screenshots)} screenshots in directory: {screenshots_dir}")

            if all_screenshots:
                all_screenshots.sort(key=lambda x: os.path.getctime(os.path.join(screenshots_dir, x)))
                for screenshot in all_screenshots:
                    screenshot_path = os.path.join(screenshots_dir, screenshot)
                    print(f"Displaying screenshot: {screenshot_path}")
                    self.display_screenshot(screenshot_path)
            else:
                self.test_messages.append(f"No screenshots found for test: {selected_test}")
                self.show_test_report()
        else:
            self.test_messages.append("Screenshots directory does not exist")
            self.show_test_report()

    def display_screenshot(self, image_path):
        try:
            img = Image.open(image_path)
            img.thumbnail((600, 600), Image.LANCZOS)  # Resize image to fit within the canvas width

            img_tk = ImageTk.PhotoImage(img)

            label = ttk.Label(self.scrollable_frame, image=img_tk)
            label.image = img_tk  # Keep a reference to avoid garbage collection
            label.pack(padx=5, pady=5)

            print(f"Displayed image: {image_path}")
        except Exception as e:
            print(f"Error displaying image {image_path}: {e}")

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def compare_images(self, img1_path, img2_path):
        # Open and convert images to grayscale
        img1 = Image.open(img1_path).convert('L')
        img2 = Image.open(img2_path).convert('L')

        # Resize images to the same size if they are not already
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        # Convert images to numpy arrays
        img1_np = np.array(img1)
        img2_np = np.array(img2)

        # Structural Similarity Index (SSIM)
        ssim_index, diff = ssim(img1_np, img2_np, full=True)
        print(f"SSIM Index: {ssim_index}")

        # Save the difference image
        diff_image = Image.fromarray((diff * 255).astype(np.uint8))
        diff_image.save('diff_image.png')

        # Histogram Comparison
        hist1 = cv2.calcHist([img1_np], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2_np], [0], None, [256], [0, 256])
        hist_comparison = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        print(f"Histogram Comparison: {hist_comparison}")

        # Pixel-wise Comparison
        diff_pixels = np.sum(img1_np != img2_np)
        total_pixels = img1_np.size
        pixel_diff_percentage = (diff_pixels / total_pixels) * 100
        print(f"Pixel Difference Percentage: {pixel_diff_percentage}%")

        return ssim_index, hist_comparison, pixel_diff_percentage

    

    def show_test_report(self):
        report_content = "\n".join(self.test_messages)
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(tk.END, report_content)

    def run_test(self, scenario, website):
        self.test_var.set(scenario)
        self.website_var.set(website)
        self.test_messages.clear()

        if not website:
            self.test_messages.append("Website Error: Please provide a website URL.")
            return

        self.configure_driver()
        self.screenshots.clear()

        try:
            if scenario == "register":
                test_scenarios.test_user_registration(self)
            elif scenario == "login":
                test_scenarios.test_user_login(self)
            elif scenario == "open_account":
                test_scenarios.test_open_account(self)
            elif scenario == "overview":
                test_scenarios.test_account_overview_display(self)
            elif scenario == "view_overview":
                test_scenarios.test_view_account_overview(self)
            elif scenario == "visual_test":
                test_scenarios.run_visual_test(self)
        except NoSuchWindowException:
            self.test_messages.append("Error: Browser window was closed unexpectedly.")
        except Exception as e:
            self.test_messages.append(f"Error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

            if scenario in self.screenshots:
                self.compare_scenario_screenshots(scenario)
            self.load_screenshots_for_test()
            self.show_test_report()


def main():
    parser = argparse.ArgumentParser(description="Run automated tests for web applications.")
    parser.add_argument("--scenario", required=True, help="Name of the test scenario to run")
    parser.add_argument("--website", required=True, help="Website URL to test")
    args = parser.parse_args()

    root = tk.Tk()
    app = TestApp(root)

    app.run_test(args.scenario, args.website)

    root.mainloop()


if __name__ == "__main__":
    main()

