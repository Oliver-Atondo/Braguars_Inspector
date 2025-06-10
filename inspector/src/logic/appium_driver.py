
from appium import webdriver
from appium.options.common.base import AppiumOptions

class AppiumDriver(webdriver.Remote):
    def __init__(self, url: str, capabilities: dict):
        options = AppiumOptions()
        options.load_capabilities(capabilities)
        super().__init__(url, options=options)
