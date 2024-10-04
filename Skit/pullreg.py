from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from functions import key_mapping

def get_reg_data(regnum):
    url = f'https://biluppgifter.se/fordon/{regnum}'

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=options)
    driver.get(url)

    element = driver.find_element(By.CLASS_NAME, "css-47sehv")
    element.click()

    cardata = carspec(driver)
    
    driver.quit()
    return(cardata)
    
def carspec(data):
    car = data.find_elements(By.CSS_SELECTOR, ".list-data.enlarge li")
    data = {}
    for carelem in car:
        label = carelem.find_element(By.CLASS_NAME, "label").text
        value = carelem.find_element(By.CLASS_NAME, "value").text
        data[label] = value

    mapping = key_mapping()

    cardata = {}

    for key,value in mapping.items():
        if key in data:
            cardata[value] = data[key]
        else:
            cardata[value] = None
    return cardata
