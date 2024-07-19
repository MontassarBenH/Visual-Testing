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
import smtplib
import openpyxl
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from configparser import ConfigParser


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
        self.test_results = []  # Store test results for the final report
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

    def reload_latest_screenshot(self):
        if self.screenshots:
            latest_screenshot_key = list(self.screenshots.keys())[-1]
            latest_screenshot_path = self.screenshots[latest_screenshot_key][-1]
            self.update_screenshot_canvas(latest_screenshot_path)

    def update_and_load_screenshots(self):
        self.load_screenshots_for_test()

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
        
        # Display the screenshot in the UI canvas
        self.display_screenshot(filename)

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

    def update_screenshot_canvas(self, image_path):
        try:
            img = Image.open(image_path)

            if img is None:
                print(f"Failed to load image from {image_path}")
            else:
                print(f"Image loaded successfully from {image_path}")

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            img.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)

            self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=img_tk, anchor=tk.CENTER)
            self.canvas.image = img_tk  # Keep reference to avoid garbage collection
        except Exception as e:
            print(f"Error updating screenshot canvas: {e}")

    def load_screenshots_for_test(self):
        selected_test = self.test_var.get()
        screenshots_dir = f'screenshots/{selected_test}'

        print(f"Loading screenshots for test: {selected_test}")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if os.path.exists(screenshots_dir):
            all_screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith('.png')]
            print(f"Found {len(all_screenshots)} screenshots in directory: {screenshots_dir}")
            for screenshot in all_screenshots:
                screenshot_path = os.path.join(screenshots_dir, screenshot)
                print(f"Loading screenshot: {screenshot_path}")

                img = Image.open(screenshot_path)
                img.thumbnail((self.canvas.winfo_width(), self.canvas.winfo_height()), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)

                label = tk.Label(self.scrollable_frame, image=img_tk)
                label.image = img_tk
                label.pack(padx=5, pady=5)
                
    def display_screenshot(self, image_path):
        try:
            img = Image.open(image_path)

            if img is None:
                print(f"Failed to load image from {image_path}")
            else:
                print(f"Image loaded successfully from {image_path}")
            width, height = img.size
            aspect_ratio = height / width
            new_width = 200
            new_height = int(new_width * aspect_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)

            img_tk = ImageTk.PhotoImage(img)

            label = ttk.Label(self.scrollable_frame, image=img_tk)
            label.image = img_tk  # Keep reference to avoid garbage collection
            label.pack(pady=5)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def compare_images(self, img1_path, img2_path):
        img1 = Image.open(img1_path).convert('L')
        img2 = Image.open(img2_path).convert('L')

        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        img1_np = np.array(img1)
        img2_np = np.array(img2)

        ssim_index, diff = ssim(img1_np, img2_np, full=True)
        print(f"SSIM Index: {ssim_index}")

        diff_image = Image.fromarray((diff * 255).astype(np.uint8))
        diff_image.save('diff_image.png')

        hist1 = cv2.calcHist([img1_np], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2_np], [0], None, [256], [0, 256])
        hist_comparison = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        print(f"Histogram Comparison: {hist_comparison}")

        diff_pixels = np.sum(img1_np != img2_np)
        total_pixels = img1_np.size
        pixel_diff_percentage = (diff_pixels / total_pixels) * 100
        print(f"Pixel Difference Percentage: {pixel_diff_percentage}%")

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
        for scenario, files in self.screenshots.items():
            for file_path in files:
                attachment = open(file_path, "rb")
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file_path)}")
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

    def run_test(self, scenario, website, email):
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
                self.driver.quit()

            if scenario in self.screenshots:
                self.compare_scenario_screenshots(scenario)

            self.load_screenshots_for_test()
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


def main():
    parser = argparse.ArgumentParser(description="Run automated tests for web applications.")
    parser.add_argument("--scenario", required=True, help="Name of the test scenario to run")
    parser.add_argument("--website", required=True, help="Website URL to test")
    parser.add_argument("--email", required=True, help="Email address to send the report")
    args = parser.parse_args()

    root = tk.Tk()
    app = TestApp(root)

    app.run_test(args.scenario, args.website, args.email)

    root.mainloop()


if __name__ == "__main__":
    main()
