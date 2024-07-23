from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException
from selenium import webdriver
import time

def run_visual_test(app):
    try:
        app.driver.get(app.website_var.get())
        time.sleep(2)
        app.take_screenshot("visual_test_initial")

        initial_count_text = app.driver.find_element(By.XPATH, "//div[@class='demo']/h1").text
        initial_count = int(initial_count_text.split()[-2])

        enable_button = app.driver.find_element(By.XPATH, "//button[span='Enable']")
        enable_button.click()
        time.sleep(1)
        app.take_screenshot("visual_test_after_enable")

        updated_count_text = app.driver.find_element(By.XPATH, "//div[@class='demo']/h1").text
        updated_count = int(updated_count_text.split()[-2])

        if updated_count == initial_count + 1:
            print("Visual Test passed: Count incremented correctly after clicking 'Enable'.")
        else:
            print("Visual Test failed: Count did not increment correctly after clicking 'Enable'.")

        disable_button = app.driver.find_element(By.XPATH, "//button[span='Disable']")
        disable_button.click()
        time.sleep(1)
        app.take_screenshot("visual_test_after_disable")
    
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_user_registration(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("register_home_page")

        app.driver.find_element(By.LINK_TEXT, "Register").click()
        app.take_screenshot("register_clicked_register")

        app.driver.find_element(By.ID, "customer.firstName").send_keys("Montassar")
        app.driver.find_element(By.ID, "customer.lastName").send_keys("Ben")
        app.driver.find_element(By.ID, "customer.address.street").send_keys("123 Haupt St")
        app.driver.find_element(By.ID, "customer.address.city").send_keys("Anytown")
        app.driver.find_element(By.ID, "customer.address.state").send_keys("Anystate")
        app.driver.find_element(By.ID, "customer.address.zipCode").send_keys("12345")
        app.driver.find_element(By.ID, "customer.phoneNumber").send_keys("555-1234")
        app.driver.find_element(By.ID, "customer.ssn").send_keys("123-45-6789")
        app.driver.find_element(By.ID, "customer.username").send_keys("Montassar")
        app.driver.find_element(By.ID, "customer.password").send_keys("password")
        app.driver.find_element(By.ID, "repeatedPassword").send_keys("password")
        app.take_screenshot("register_filled_form")

        app.driver.find_element(By.CSS_SELECTOR, "input.button[value='Register']").click()
        app.driver.implicitly_wait(10)
        app.take_screenshot("register_submitted")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_user_login(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("login_home_page")

        app.driver.find_element(By.NAME, "username").send_keys("Montassar")
        app.driver.find_element(By.NAME, "password").send_keys("password")
        app.driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        app.take_screenshot("login_logged_in")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_open_account(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("open_account_home_page")

        test_user_login(app)

        try:
            element = WebDriverWait(app.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Open New Account"))
            )
            element.click()
            app.take_screenshot("open_account_new_account_page")

            WebDriverWait(app.driver, 10).until(
                EC.presence_of_element_located((By.ID, "type"))
            )

            account_type_dropdown = Select(app.driver.find_element(By.ID, "type"))
            try:
                account_type_dropdown.select_by_value("0")
                app.take_screenshot("open_account_selected_type")
            except NoSuchElementException:
                account_type_dropdown.select_by_index(0)
                app.take_screenshot("open_account_selected_type_default")

            WebDriverWait(app.driver, 10).until(
                EC.presence_of_element_located((By.ID, "fromAccountId"))
            )

            account_dropdown = Select(app.driver.find_element(By.ID, "fromAccountId"))
            try:
                account_dropdown.select_by_index(1)
                app.take_screenshot("open_account_selected_account")
            except NoSuchElementException:
                app.take_screenshot("open_account_no_account_option")

            try:
                element = WebDriverWait(app.driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Open New Account']"))
                )
                element.click()
                app.take_screenshot("open_account_opened_success")

                WebDriverWait(app.driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@id='success-message']"))
                )
                app.take_screenshot("open_account_success_message")

            except TimeoutException:
                app.take_screenshot("open_account_button_timeout")

        except TimeoutException:
            app.take_screenshot("open_account_link_timeout")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_account_overview_display(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("overview_home_page")

        test_user_login(app)

        app.driver.find_element(By.LINK_TEXT, "Accounts Overview").click()
        time.sleep(10)
        app.take_screenshot("overview_displayed")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_view_account_overview(app):
    try:
        app.driver.get(app.website_var.get())
        app.take_screenshot("view_overview_home_page")

        test_user_login(app)

        app.driver.find_element(By.LINK_TEXT, "Accounts Overview").click()
        time.sleep(10)
        app.take_screenshot("view_overview_displayed")
    except NoSuchWindowException:
        print("Error: Browser window was closed unexpectedly.")
    except Exception as e:
        print(f"Error: {str(e)}")
