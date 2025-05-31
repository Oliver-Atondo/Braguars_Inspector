import sys
from PySide6.QtWidgets import QApplication
from gui import MainWindow

if __name__ == "__main__":
    capabilities = {
        "cap1": {
            "platformName": "iOS",
            "platformVersion": "18.4",
            "deviceName": "iPhone14ProMax",
            "automationName": "XCUITest",
            "udid": "00008110-0005554A1460401E",
            "includeSafariInWebviews": True,
            "newCommandTimeout": 3600,
            "connectHardwareKeyboard": True,
            "showXcodeLog": True
        },
        "caps2": {
            "platformName": "ANDROID",
            "automationName": "uiautomator2",
            "deviceName": "Galaxy S21 5G",
            "noReset": True,
            "fullReset": False,
            "newCommandTimeout": 3600
        }
    }

    app = QApplication(sys.argv)
    window = MainWindow()
    window.load(capabilities)
    window.resize(1200, 800)
    window.show()
    app.exec()