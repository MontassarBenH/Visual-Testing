import time
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, TimeoutException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from data_loader import load_test_data



def run_visual_test(app):
    try:
        app.driver.get(app.website_var.get())
        time.sleep(2)
        app.take_screenshot("visual_test_initial.png")

        initial_count_text = app.find_element(By.XPATH, "//div[@class='demo']/h1").text
        initial_count = int(initial_count_text.split()[-2])

        app.click_element(By.XPATH, "//button[span='Enable']")
        time.sleep(1)
        app.take_screenshot("visual_test_after_enable.png")

        updated_count_text = app.find_element(By.XPATH, "//div[@class='demo']/h1").text
        updated_count = int(updated_count_text.split()[-2])

        if updated_count == initial_count + 1:
            print("Visual Test passed: Count incremented correctly after clicking 'Enable'.")
        else:
            print("Visual Test failed: Count did not increment correctly after clicking 'Enable'.")

        app.click_element(By.XPATH, "//button[span='Disable']")
        time.sleep(1)
        app.take_screenshot("visual_test_after_disable.png")
    
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_user_registration(app, data):
    try:
                
        app.driver.get(app.website_var.get())
        app.click_element(By.LINK_TEXT, "Register")
        app.take_screenshot("register_clicked_register.png")

        form_data = {(By.ID, key): value for key, value in data.items()}
        app.fill_form(form_data)
        app.take_screenshot("register_filled_form.png")

        app.click_element(By.CSS_SELECTOR, "input.button[value='Register']")
        time.sleep(10)
        app.take_screenshot("register_submitted.png")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_user_login(app, data):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("login_home_page")

        print(f"Form Data: {data}")  # Debugging line


        form_data = {(By.NAME, key): value for key, value in data.items()}
        app.fill_form(form_data)

        app.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        time.sleep(6)
        app.take_screenshot("login_logged_in.png")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_open_account(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("open_account_home_page")
        test_user_login(app, load_test_data("test_data.json")["user_login"])


        element = WebDriverWait(app.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Open New Account"))
        )
        element.click()
        app.take_screenshot("open_account_new_account_page.png")

        WebDriverWait(app.driver, 10).until(
            EC.presence_of_element_located((By.ID, "type"))
        )

        account_type_dropdown = Select(app.find_element(By.ID, "type"))
        try:
            app.select_from_dropdown_by_value(By.ID, "type", "0")
            app.take_screenshot("open_account_selected_type.png")
        except NoSuchElementException:
            app.select_from_dropdown_by_index(By.ID, "fromAccountId", 1)
            app.take_screenshot("open_account_selected_type_default.png")

        WebDriverWait(app.driver, 10).until(
            EC.presence_of_element_located((By.ID, "fromAccountId"))
        )

        account_dropdown = Select(app.find_element(By.ID, "fromAccountId"))
        try:
            account_dropdown.select_by_index(1)
            app.take_screenshot("open_account_selected_account.png")
        except NoSuchElementException:
            app.take_screenshot("open_account_no_account_option.png")

        try:
            element = WebDriverWait(app.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Open New Account']"))
            )
            element.click()
            app.take_screenshot("open_account_opened_success.png")

            WebDriverWait(app.driver, 2).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@id='success-message']"))
            )
            app.take_screenshot("open_account_success_message.png")

        except TimeoutException:
            app.take_screenshot("open_account_button_timeout.png")
            

    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_account_overview_display(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("overview_home_page")
        test_user_login(app, load_test_data("test_data.json")["user_login"])


        app.click_element(By.LINK_TEXT, "Accounts Overview")
        time.sleep(6)
        app.take_screenshot("overview_displayed.png")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_view_account_overview(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("view_overview_home_page")

        test_user_login(app, load_test_data("test_data.json")["user_login"])

        app.click_element(By.LINK_TEXT, "Accounts Overview")
        time.sleep(6)
        app.take_screenshot("view_overview_displayed.png")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")
