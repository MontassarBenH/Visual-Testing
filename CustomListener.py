from selenium.webdriver.support.events import AbstractEventListener


class CustomListener(AbstractEventListener):
        def __init__(self):
            self.actions = []

        def before_click(self, element, driver):
            selector = self.get_css_selector(element, driver)
            self.actions.append({"type": "click", "selector": selector})

        def before_change_value_of(self, element, driver):
            selector = self.get_css_selector(element, driver)
            self.actions.append({"type": "input", "selector": selector, "value": element.get_attribute("value")})

        def get_css_selector(self, element, driver):
            return driver.execute_script("""
                var path = [];
                var element = arguments[0];
                while (element.parentNode) {
                    var siblings = element.parentNode.childNodes;
                    var index = 0;
                    for (var i = 0; i < siblings.length; i++) {
                        var sibling = siblings[i];
                        if (sibling === element) {
                            path.unshift(element.tagName.toLowerCase() + ':nth-child(' + (index + 1) + ')');
                            break;
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            index++;
                        }
                    }
                    element = element.parentNode;
                }
                return path.join(' > ');
            """, element)