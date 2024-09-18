# Supabase
import os
from supabase import create_client, Client

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time

# Set up the WebDriver service
service = Service(executable_path="chromedriver")
driver = webdriver.Chrome(service=service)

starts_from = 1001 

main_url = "https://presidencycollege.linways.com/ams/student/login"
pending_profile_url = "https://presidencycollege.linways.com/ams/student/mandatory-pending-tasks"

presidency = [
    # {"year": 24, "course": 'bca', "semeser": 1, "end_limit": 1311},
    {"year": 23, "course": 'bca', "semeser": 3, "end_limit": 1267},
    {"year": 22, "course": 'bca', "semeser": 5, "end_limit": 1197},
]

# Supabase config
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def format_name_to_filename(name: str) -> str:
    # Replace spaces with hyphens and add the ".png" extension
    formatted_name = name.replace(" ", "-") + ".png"
    return formatted_name

try:
    for year in presidency:
        # Ensure range includes the end_limit
        for i in range(starts_from, year['end_limit'], 1):
            driver.get(main_url)
            time.sleep(2)
            current_url = driver.current_url

            if current_url != main_url:
                try:
                    # Wait until the profile dropdown is visible
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'profile-dropdown'))
                    )

                    logout_parent_el = driver.find_element(By.CLASS_NAME, 'profile-dropdown')
                    driver.execute_script("arguments[0].style.display = 'block'", logout_parent_el)
                    logout_el = logout_parent_el.find_element(By.XPATH, ".//a[contains(text(), 'Logout')]")
                    logout_el.click()
                except Exception as e:
                    print(f"An error occurred: {e}")
                    driver.quit()
                    continue

            # Wait until login button is visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'loginBtn'))
            )

            # Determine evaluated course and register number
            evaluated_course = 'C' if year['course'] == 'bca' else 'DefaultValue'
            evaluated_register_number = "{}{}0{}".format(year['year'], evaluated_course, i)

            try:
                # Locate elements 
                username = driver.find_element(By.ID, "username")
                password = driver.find_element(By.ID, "password")
                login_btn = driver.find_element(By.ID, "loginBtn")

                # Clear and set input values
                username.clear()
                password.clear()
                username.send_keys(evaluated_register_number)
                password.send_keys(evaluated_register_number)
                login_btn.click()

                # Wait for login to complete
                time.sleep(4)

                # Find and print image element source
                try:
                    time.sleep(4)
                    
                    # Student Name
                    name_parent = driver.find_element(By.CLASS_NAME, 'profile-dropdown')
                    driver.execute_script("arguments[0].style.display = 'block'", name_parent)
                    student_name = driver.find_element(By.CSS_SELECTOR, ".dropdown-item b").text

                    image_element = driver.find_element(By.CLASS_NAME, "thumbnail-wrapper.d32.circular.inline img")
                    image_url = image_element.get_attribute("src")
                    driver.get(image_url)
                    time.sleep(2)

                    image_element_from_url = driver.find_element(By.TAG_NAME, 'img')
                    screenshot_filename = f"image_{i+1}.png"
                    image_element_from_url.screenshot(screenshot_filename)

                    driver.get(main_url)

                    # Supabase table insertion for student data
                    try:
                        # Format the filename
                        filename = format_name_to_filename(student_name)

                        # Open the screenshot file and upload it
                        with open(screenshot_filename, 'rb') as f:
                            supabase.storage.from_("students").upload(
                                path=filename,
                                file=f,
                                file_options={"content-type": "image/png"}
                            )
                        print(f"File uploaded successfully as {filename}")

                        # Clean up the local file
                        os.remove(screenshot_filename)
                        
                        image_url = "https://hsnxhaebiajbjpbckscs.supabase.co/storage/v1/object/public/students/"+filename
                        
                        response = (
                            supabase.table("Student Data")
                            .insert({"profile_image": image_url, "name": student_name})
                            .execute()
                        )
                        print(i, student_name)
                        # Check if the response contains errors
                        if response.status_code != 200:
                            print(f"Failed to insert data into Supabase: {response.json()}")

                    except FileNotFoundError:
                        print(f"Error: The file {screenshot_filename} was not found.")
                    except Exception as e:
                        print(f"An error occurred with Supabase request: {e}")

                except NoSuchElementException as e:
                    print(f"Image element not found: {e}")
                    driver.find_element(By.CLASS_NAME, 'pull-right').click()
                    WebDriverWait(driver, 10).until(
                       EC.presence_of_element_located((By.ID, 'loginBtn')))
                    continue
                except Exception as e:
                    print(f"Error finding image element: {e}")
                    continue

            except NoSuchElementException as e:
                print(f"Login element not found: {e}")
                continue
            except TimeoutException as e:
                print(f"Timed out while waiting: {e}")
                continue
            except Exception as e:
                print(f"An error occurred during login: {e}")
                continue

finally:
    driver.quit()  # Close the browser once all operations are complete
