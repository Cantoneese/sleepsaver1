from selenium import webdriver
from time import sleep
from pathlib import Path
import json
import platform

# getting directory's absolute path in case it does not match CWD
path = Path(__file__).parent.absolute()

# Parsing config data, performing the initial checks
c_path = path / "config.json"
if not c_path.is_file():
    print("config.json not found, exiting")
    exit()
else:
    with open(c_path, "r") as open_file:
        config = json.load(open_file)

# getting platform
config["platform"] = platform.system()
print(f"Detected platform: {config['platform']}")

# initializing proper webdriver
if config["platform"] == "Linux":
    d_path = path / "linux_drivers"
    log_path = d_path / "geckodriver.log"
    d_path = d_path / "geckodriver"
    print(f"Attempting to initialize webdriver binary:\n{d_path}\n")
    driver = webdriver.Firefox(executable_path=d_path, service_log_path=log_path)

elif config["platform"] == "Windows":
    d_path = path / "windows_drivers" / "chromedriver.exe"
    print(f"Attempting to initialize webdriver binary:\n{d_path}\n")
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options, executable_path=d_path)

else:
    print("Error: Unsupported OS, exiting")
    exit()

# performing test run
driver.get("https://google.com")
sleep(5)
driver.quit()
print("\nTest run was successful!")
