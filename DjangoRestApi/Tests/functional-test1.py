from selenium import webdriver
import time
browser = webdriver.Chrome(executable_path='./chromedriver')
time.sleep(3)
browser.get('http://127.0.0.1:5000/')
assert 'Django' in browser.title
browser.quit()