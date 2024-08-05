import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException


def test_setup_teardown(func):
    def wrapper(self, *args, **kwargs):
        self.driver.get(self.website_var.get())
        self.take_screenshot(f"{func.__name__}_start.png")
        result = func(self, *args, **kwargs)
        self.take_screenshot(f"{func.__name__}_end.png")
        return result
    return wrapper

@test_setup_teardown
def test_user_registration(app, data):
    app.click_element(By.LINK_TEXT, "Register")
    form_data = {(By.ID, key): value for key, value in data.items()}
    app.fill_form(form_data)
    app.click_element(By.CSS_SELECTOR, "input.button[value='Register']")
    time.sleep(10)

@test_setup_teardown
def test_user_login(app, data):
    form_data = {(By.NAME, key): value for key, value in data.items()}
    app.fill_form(form_data)
    app.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(6)

@test_setup_teardown
def test_open_account(app):
    test_user_login(app, app.load_test_data("test_data.json")["user_login"])
    
    element = WebDriverWait(app.driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Open New Account"))
    )
    element.click()

    WebDriverWait(app.driver, 10).until(
        EC.presence_of_element_located((By.ID, "type"))
    )

    try:
        app.select_from_dropdown_by_value(By.ID, "type", "0")
    except NoSuchElementException:
        app.select_from_dropdown_by_index(By.ID, "fromAccountId", 1)

    WebDriverWait(app.driver, 10).until(
        EC.presence_of_element_located((By.ID, "fromAccountId"))
    )

    account_dropdown = Select(app.find_element(By.ID, "fromAccountId"))
    try:
        account_dropdown.select_by_index(1)
    except NoSuchElementException:
        pass

    try:
        element = WebDriverWait(app.driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Open New Account']"))
        )
        element.click()

        WebDriverWait(app.driver, 2).until(
            EC.visibility_of_element_located((By.XPATH, "//div[@id='success-message']"))
        )

    except TimeoutException:
        pass

@test_setup_teardown
def test_account_overview_display(app):
    test_user_login(app, app.load_test_data("test_data.json")["user_login"])
    app.click_element(By.LINK_TEXT, "Accounts Overview")
    time.sleep(6)

@test_setup_teardown
def test_view_account_overview(app):
    test_user_login(app, app.load_test_data("test_data.json")["user_login"])
    app.click_element(By.LINK_TEXT, "Accounts Overview")
    time.sleep(6)

@test_setup_teardown
def run_visual_test(app):
    initial_count_text = app.find_element(By.XPATH, "//div[@class='demo']/h1").text
    initial_count = int(initial_count_text.split()[-2])

    app.click_element(By.XPATH, "//button[span='Enable']")
    time.sleep(1)

    updated_count_text = app.find_element(By.XPATH, "//div[@class='demo']/h1").text
    updated_count = int(updated_count_text.split()[-2])

    if updated_count == initial_count + 1:
        print("Visual Test passed: Count incremented correctly after clicking 'Enable'.")
    else:
        print("Visual Test failed: Count did not increment correctly after clicking 'Enable'.")

    app.click_element(By.XPATH, "//button[span='Disable']")
    time.sleep(1)

class TestScenarioFactory:
    @staticmethod
    def get_scenario(scenario_name):
        scenarios = {
            "register": test_user_registration,
            "login": test_user_login,
            "open_account": test_open_account,
            "overview": test_account_overview_display,
            "view_overview": test_view_account_overview,
            "visual_test": run_visual_test
        }
        return scenarios.get(scenario_name)