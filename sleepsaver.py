from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from random import randint, choice
from time import sleep
from datetime import datetime, timedelta
from pathlib import Path
import json
import requests
import platform
import sys


# returns current time in XXXX format (no delimiter, int)
def current_time():
    _current_time = str(datetime.now().time())[:5]
    _current_time = int(_current_time.replace(":", ""))
    return _current_time


# returns current time in XX:XX format
def log_time():
    _current_time = str(datetime.now().time())[:5]
    return _current_time


# calculate schedule's expiration date
def expiration_date():
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday())
    nearest_saturday = last_monday + timedelta(days=5)
    timestamp = nearest_saturday.replace(hour=23, minute=59)
    return str(timestamp)[:-10]


# returns a true or false if the datetime has passed already
def expired(timestamp_):
    timestamp_ = datetime.strptime(timestamp_, "%Y-%m-%d %H:%M")
    if timestamp_ <= datetime.now():
        return True
    else:
        return False


# getting directory's absolute path in case it does not match CWD
path = Path(__file__).parent.absolute()

# Parsing config data, performing the initial checks
c_path = path / "config.json"
if not c_path.is_file():
    print("config.json not found, exiting")
    sys.exit()
else:
    with open(c_path, "r") as open_file:
        config = json.load(open_file)

# loading up fillers
f_path = path / "fillers.json"
if not f_path.is_file():
    fillers = {}
else:
    with open(f_path, "r") as open_file:
        fillers = json.load(open_file)

# parsing schedule for today
s_path = path / "schedule.json"

if (not s_path.is_file()) or "schedule_expiration_date" not in config or expired(config["schedule_expiration_date"]):
    print("schedule.json not found or expired, attempting download")

    try:
        if int(config["subgroup"]) == 0:
            response = requests.get(url=f"{config['schedule_provider_url']}?groupID={config['group_id']}")
        elif int(config["subgroup"]) > 0:
            response = requests.get(
                url=f"{config['schedule_provider_url']}?groupID={config['group_id']}&subgroup={int(config['subgroup']) - 1}"
                                    )
        else:
            print("Subgroup parameter in config is invalid")
            raise ValueError

        schedule = response.json()

        try:
            if schedule["status"] == 500:
                print(f"Provider returned error: {schedule['message']}. Wrong group id?")
                raise ValueError
        except ValueError:
            sys.exit()
        except TypeError:
            pass

        with open(s_path, "w") as file:
            json.dump(schedule, file, indent=4, ensure_ascii=False)

        config["schedule_expiration_date"] = expiration_date()
        with open(c_path, "w") as file:
            json.dump(config, file, indent=4, ensure_ascii=False)

        print("Success!\n")

    except ValueError:
        sys.exit()

    except:
        print(f"Error. Response status code: {response.status_code}. \
        Provider's website might be down, try again in a few minutes.")
        sys.exit()

else:
    with open(s_path, "r") as file:
        schedule = json.load(file)

# parsing date choice from args or from console
try:
    _choice = int(sys.argv[1])
    if not 0 <= _choice <= 1:
        raise ValueError
except:
    print("The desired date was not provided as an argument or the provided option is invalid.")
    print("Which schedule to use?\n\n[0] Today's\n[1] Tomorrow's")
    while True:
        _choice = int(input("Enter a number: "))
        if _choice == 0 or _choice == 1:
            break
        else:
            print("Error: Impossible option, try again.")
    print()

# limiting schedule only to today's one
dow = (datetime.now().weekday() + _choice)

if dow == 6:
    print("You're trying to setup the Sleepsaver to work on Sunday, exiting.")
    sys.exit()
elif dow == 7:
    dow = 0

schedule = schedule[dow]

# checking for blanks in the schedule, attempting to fill in automatically or prompting the user
fillers_modified = False

for i in range(len(schedule)):
    if schedule[i]["course_link"] == "none":
        if schedule[i]["name"] in fillers:
            schedule[i]["course_link"] = fillers[schedule[i]["name"]]
        else:
            print(f"Course link for lesson {schedule[i]['name']} was not provided in the schedule.")
            fillers[schedule[i]["name"]] = input("Please fill it in manually: ")
            schedule[i]["course_link"] = fillers[schedule[i]["name"]]
            fillers_modified = True
            print("Link saved for the next time.")

# saving modified fillers
if fillers_modified:
    with open(f_path, "w") as file:
        json.dump(fillers, file, indent=4, ensure_ascii=False)

# initializing variation related variables
approx_wait_time = config["approx_wait_time"]
variation = round(approx_wait_time * 0.25)

# parsing start and end times for today from the schedule
start_time = int(schedule[0]["start_time"])
end_time = int(schedule[-1]["end_time"])

# begin the cycle
print(f"Sleepsaver started at {str(datetime.now().time())[:5]}, have a rest.")

# wait until lessons start
while True:
    if end_time < current_time() or current_time() < start_time:
        sleep(randint(60, 120))
    else:
        break

# getting platform
config["platform"] = platform.system()

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
    sys.exit()

# log into the moodle account 1 min before lessons start
driver.get(config["base_url"])

while True:
    print(f"{log_time()}: Attempting to log in")
    login_field = driver.find_element_by_id("inputName")
    password_field = driver.find_element_by_id("inputPassword")
    login_field.send_keys(config["login"])
    sleep(2)
    password_field.send_keys(config["password"])
    sleep(1)
    password_field.send_keys(Keys.RETURN)

    sleep(5)
    try:
        error_msg = driver.find_element_by_xpath('//*[@id="yui_3_17_2_1_1601932417085_35"]')
        print(f"{log_time()}: Something went wrong while logging in. Trying again.")
        pass
    except:
        print(f"{log_time()}: Logged in successfully!")
        sleep(randint(5, 10))
        break

# keep looping until lessons are over
for i in range(len(schedule)):
    lesson = schedule[i]

    # skipping lessons which are already over
    if not int(lesson["start_time"]) < current_time() <= int(lesson["end_time"]):
        continue

    # open course
    print(f"{log_time()}: Lesson {lesson['name']} begins, opening course.")
    try:
        driver.get(lesson["course_link"])
    except KeyError:
        print("Error: course link field is empty!")

    sleep(randint(5, 10))
    # refresh periodically until lesson is over
    while True:
        if not int(lesson["start_time"]) < current_time() <= int(lesson["end_time"]):
            break
        wait_time = approx_wait_time + randint(variation * -1, variation)
        print(f"{log_time()}: Refreshing in {wait_time} seconds.")
        sleep(wait_time)

        driver.refresh()
        sleep(2)

        # trying to  simulate some sort of human activity
        html = driver.find_element_by_tag_name('html')
        html.send_keys(Keys.HOME)

        for j in range(1, randint(2, 6)):
            if choice([True, False]):
                html.send_keys(Keys.PAGE_DOWN)
            else:
                html.send_keys(Keys.PAGE_UP)
            sleep(1)

        print(f"{log_time()}: Page has just been refreshed.")

    # waiting for a break to end
    print(f"{log_time()}: Break now. Waiting for the next lesson to begin.")
    try:
        while int(lesson["end_time"]) <= current_time() <= int(schedule[i + 1]["start_time"]):
            sleep(randint(30, 60))
    except IndexError:
        break

# quit browser and exit
driver.quit()
print(f"Sleepsaver stopped at {str(datetime.now().time())[:5]}. Lessons are over. Press enter to exit.")
input()
