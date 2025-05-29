import json
import uuid
from lxml import etree

class AppiumRecorder:
    def __init__(self):
        self.click_records = []
        self.step_counter = 1
        self.recordingOn = False

    def setRecordingOn(self, state):
        self.recordingOn = state

    def record_dual_step(self, ios_elem, android_elem, ios_img_b64, android_img_b64):
        record = {
            "stepNumber": self.step_counter,
            "iOS_ids": generate_ios_locators(ios_elem),
            "android_ids": generate_android_locators(android_elem),
            "iOS_img_base64": ios_img_b64,
            "android_img_base64": android_img_b64
        }

        self.click_records.append(record)
        self.step_counter += 1
        print(json.dumps(self.click_records, indent=4, ensure_ascii=False))

    def get_click_records_json(self):
        return json.dumps(self.click_records, indent=4, ensure_ascii=False)

    def save_to_file(self, filepath="recording.json"):
        with open(filepath, 'w') as json_file:
            json.dump(self.click_records, json_file, indent=4)
            print("SI LLEGO")

def generate_ios_locators(elem):
    name = elem.attrib.get("name", "")
    label = elem.attrib.get("label", "")
    type_ = elem.attrib.get("type", "")
    return {
        "accessibility id": name or label,
        "-ios class chain": build_ios_class_chain(elem),
        "-ios predicate string": build_ios_predicate_string(elem),
        "xpath": build_xpath_from_hierarchy(elem, 'iOS')
    }

def generate_android_locators(elem):
    resource_id = elem.attrib.get("resource-id", "")

    return {
        "resource-id": resource_id,
        "-android uiautomator": build_android_ui_automator(elem),
        "xpath": build_xpath_from_hierarchy(elem, 'android')
    }

def build_xpath_from_hierarchy(elem, platform="iOS"):
    parts = []

    while elem is not None:
        tag = elem.tag
        attrib = elem.attrib

        predicate = ""
        if platform.lower() == "ios":
            if "name" in attrib and attrib["name"].strip():
                predicate = f"[@name='{attrib['name']}']"
                parts.insert(0, f"{tag}{predicate}")
                break
            elif "label" in attrib and attrib["label"].strip():
                predicate = f"[@label='{attrib['label']}']"
                parts.insert(0, f"{tag}{predicate}")
                break
        elif platform.lower() == "android":
            if "resource-id" in attrib and attrib["resource-id"].strip():
                predicate = f"[@resource-id='{attrib['resource-id']}']"
                parts.insert(0, f"{tag}{predicate}")
                break
            elif "text" in attrib and attrib["text"].strip():
                predicate = f"[@text='{attrib['text']}']"
                parts.insert(0, f"{tag}{predicate}")
                break

        parts.insert(0, tag)
        elem = elem.getparent()

    xpath = "//" + "/".join(parts)
    return xpath

def build_ios_predicate_string(elem):
    attrib = elem.attrib
    if "name" in attrib and attrib["name"].strip():
        return f"name == '{attrib['name'].strip()}'"
    elif "label" in attrib and attrib["label"].strip():
        return f"label == '{attrib['label'].strip()}'"
    elif "value" in attrib and attrib["value"].strip():
        return f"value == '{attrib['value'].strip()}'"
    else:
        return None

def build_ios_class_chain(elem):
    tag = elem.tag
    name = elem.attrib.get("name", "").strip()
    label = elem.attrib.get("label", "").strip()

    if name:
        return f"**/{tag}[`name == '{name}'`]"
    elif label:
        return f"**/{tag}[`label == '{label}'`]"
    else:
        return f"**/{tag}"

def build_android_ui_automator(elem):
    attrib = elem.attrib
    if "resource-id" in attrib and attrib["resource-id"].strip():
        return f'new UiSelector().resourceId("{attrib["resource-id"].strip()}")'
    elif "text" in attrib and attrib["text"].strip():
        return f'new UiSelector().text("{attrib["text"].strip()}")'
    elif "class" in attrib and attrib["class"].strip():
        return f'new UiSelector().className("{attrib["class"].strip()}")'
    else:
        return None
    
