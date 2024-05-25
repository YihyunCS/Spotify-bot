import subprocess
import time
import os
import json
import websocket
import random
from colorama import init, Fore
from fake_useragent import UserAgent
from faker import Faker

def load_config(config_path="config.json"):
    with open(config_path, 'r') as file:
        return json.load(file)

def load_proxies(proxy_file="proxies.txt"):
    with open(proxy_file, 'r') as file:
        proxies = file.read().splitlines()
    return proxies

def launch_chrome(config, proxy=None):
    chrome_path = config['chrome_path']
    use_proxies = config['use_proxies']

    if not os.path.exists(chrome_path):
        raise FileNotFoundError("Could not find the specified Chrome executable. Make sure it's installed and the path is correct.")

    command = [
        chrome_path,
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-gpu",
        "--disable-software-rasterizer",
    ]

    if use_proxies.lower() == 'y' and proxy:
        command.append(f"--proxy-server={proxy}")

    process = subprocess.Popen(command)
    time.sleep(5)  # Give Chrome time to start and open the debugging port
    return process

def get_websocket_debugger_url():
    import urllib.request

    url = "http://localhost:9222/json"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        if not data:
            raise Exception("No WebSocket debugger URL found")
        websocket_url = data[0]['webSocketDebuggerUrl']
        return websocket_url

def send_command(ws, method, params={}):
    message_id = 1
    message = json.dumps({"id": message_id, "method": method, "params": params})
    ws.send(message)
    response = ws.recv()
    return json.loads(response)

def execute_script(ws, script):
    send_command(ws, "Runtime.evaluate", {"expression": script})

def navigate_to_url(ws, url):
    send_command(ws, "Page.navigate", {"url": url})
    time.sleep(5)  # Adjust as needed based on network speed

def click_element(ws, xpath):
    script = f"""
    (function() {{
        var element = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (element) {{
            element.click();
        }}
    }})();
    """
    execute_script(ws, script)

def type_text(ws, xpath, text):
    # Focus on the element
    script = f"""
    (function() {{
        var element = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (element) {{
            element.focus();
        }}
    }})();
    """
    execute_script(ws, script)

    # Type each character as a key event
    for char in text:
        send_command(ws, "Input.dispatchKeyEvent", {
            "type": "char",
            "text": char,
            "unmodifiedText": char
        })
        time.sleep(0.05)  # Small delay between keystrokes

def clear_cookies(ws):
    send_command(ws, "Network.clearBrowserCookies")

def check_for_proxy_error(ws):
    response = send_command(ws, "Runtime.evaluate", {
        "expression": "document.body.innerText.includes('ERR_NO_SUPPORTED_PROXIES')"
    })
    return response.get("result", {}).get("value", False)

def main():
    init(autoreset=True)  # Initialize colorama
    config = load_config()
    ua = UserAgent()
    fake = Faker()
    count = 0

    # Load proxies if required
    proxies = load_proxies() if config['use_proxies'].lower() == 'y' else []

    while True:
        user_agent = ua.random  # Switch user agent after each process
        random_email = f"s{''.join(random.choices('0123456789', k=25))}@everstreams.pro"

        # Select a proxy if needed
        proxy = random.choice(proxies) if proxies else None

        chrome_process = launch_chrome(config, proxy)
        ws = None

        try:
            websocket_url = get_websocket_debugger_url()
            ws = websocket.create_connection(websocket_url)

            # Set the user agent
            send_command(ws, "Network.setUserAgentOverride", {"userAgent": user_agent})

            # Spoof navigator properties and other detection techniques
            script = f"""
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => false
                }});
                Object.defineProperty(navigator, 'languages', {{
                    get: () => ['en-US', 'en']
                }});
                Object.defineProperty(navigator, 'platform', {{
                    get: () => 'Win32'  // Spoof the platform to Windows
                }});
                Object.defineProperty(navigator, 'userAgent', {{
                    get: () => '{user_agent}'
                }});
                Object.defineProperty(navigator, 'plugins', {{
                    get: () => [1, 2, 3]
                }});
                Object.defineProperty(window, 'chrome', {{
                    get: () => {{}}
                }});
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => 8
                }});
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => 4
                }});

                // Canvas spoofing
                const toDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function() {{
                    const context = this.getContext('2d');
                    context.fillStyle = 'rgb(255, 255, 255)';
                    context.fillRect(0, 0, this.width, this.height);
                    return toDataURL.apply(this, arguments);
                }};

                const getImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function() {{
                    const result = getImageData.apply(this, arguments);
                    for (let i = 0; i < result.data.length; i += 4) {{
                        result.data[i] = result.data[i] ^ 255;     // XOR with white
                        result.data[i + 1] = result.data[i + 1] ^ 255;
                        result.data[i + 2] = result.data[i + 2] ^ 255;
                    }}
                    return result;
                }};

                // WebGL spoofing
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37446) return 'Intel Inc.';
                    if (parameter === 37447) return 'Intel Iris OpenGL Engine';
                    return getParameter.apply(this, arguments);
                }};

                // Audio spoofing
                const getChannelData = AudioBuffer.prototype.getChannelData;
                AudioBuffer.prototype.getChannelData = function() {{
                    const data = getChannelData.apply(this, arguments);
                    for (let i = 0; i < data.length; i++) {{
                        data[i] = data[i] ^ 255;  // XOR with white noise
                    }}
                    return data;
                }};

                Object.defineProperty(window, 'outerWidth', {{
                    get: () => window.innerWidth
                }});
                Object.defineProperty(window, 'outerHeight', {{
                    get: () => window.innerHeight
                }});

                // Additional spoofing for better evasion
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) =>
                    parameters.name === 'notifications' ? Promise.resolve({{ state: 'denied' }}) : originalQuery(parameters);

                const originalGetBattery = navigator.getBattery;
                navigator.getBattery = () => Promise.resolve({{
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                }});

                const originalGetGamepads = navigator.getGamepads;
                navigator.getGamepads = () => [null, null, null, null];

                const originalGetVRDisplays = navigator.getVRDisplays;
                navigator.getVRDisplays = () => Promise.resolve([]);

                // WebRTC IP Leak Prevention
                const originalRTCPeerConnection = window.RTCPeerConnection;
                window.RTCPeerConnection = function(config) {{
                    if (config && config.iceServers) {{
                        config.iceServers = config.iceServers.filter(server => {{
                            if (server.urls) {{
                                if (typeof server.urls === 'string') {{
                                    return !server.urls.includes('stun:') && !server.urls.includes('turn:');
                                }} else if (Array.isArray(server.urls)) {{
                                    server.urls = server.urls.filter(url => !url.includes('stun:') && !url.includes('turn:'));
                                    return server.urls.length > 0;
                                }}
                            }}
                            return false;
                        }});
                    }}
                    return new originalRTCPeerConnection(config);
                }};
                window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
            """
            send_command(ws, "Page.addScriptToEvaluateOnNewDocument", {"source": script})

            # Navigate to the Spotify signup page and perform actions
            navigate_to_url(ws, "https://www.spotify.com/signup")

            # Check for proxy error
            if check_for_proxy_error(ws):
                raise Exception("ERR_NO_SUPPORTED_PROXIES")

            # Enter random email
            type_text(ws, "/html/body/div[1]/main/main/section/div/form/div/div/div/div[2]/input", random_email)
            time.sleep(1)
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/button/span[1]")

            # Wait for page to load and enter password
            type_text(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[2]/div/div[2]/div[1]/input", "Mario2005!")
            time.sleep(1)
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/div[2]/button/span[1]")

            # Wait for page to load and enter name
            name = fake.name()
            type_text(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div/2/div/section/div[3]/div[1]/div[2]/input", name)

            # Enter random date of birth
            day = random.randint(1, 28)
            type_text(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[3]/div[2]/div[2]/div/input[1]", str(day))
            execute_script(ws, f"""
            (function() {{
                var select = document.evaluate('/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[3]/div[2]/div[2]/div/div/select', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (select) {{
                    select.value = '10';
                    select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }})();
            """)
            year = random.randint(1990, 2005)
            type_text(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[3]/div[2]/div[2]/div[1]/input[2]", str(year))

            # Select gender and click sign up
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[3]/fieldset/div/div/div[2]/label/span[2]")
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/div[2]/button/span[1]")

            # Wait for page to load and select preferences
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[4]/div[1]/div/div/label/span[2]")
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/div[1]/div[2]/div/section/div[4]/div[3]/div/div/label/span[1]")
            time.sleep(1)
            click_element(ws, "/html/body/div[1]/main/main/section/div/form/div[2]/button/span[1]")

            # Wait and go to a specific album page
            time.sleep(10)
            navigate_to_url(ws, "https://open.spotify.com/album/2rcpu1m9gwH5BDqw40AC4D")
            time.sleep(5)  # Adjust as needed based on network speed

            # Play the album
            click_element(ws, "/html/body/div[4]/div/div[2]/div[3]/div[1]/div[2]/div[2]/div[2]/main/section/div[3]/div[2]/div/div/div[1]/button")

            # Wait a random time between 44 and 65 seconds before restarting the process
            time.sleep(random.randint(44, 65))

            # Clear cookies after the process
            clear_cookies(ws)

            count += 1
            if count % 5 == 0:
                print(Fore.RED + "switch")
                input("Press 'y' to continue: ")
                chrome_process.terminate()
                time.sleep(5)  # Adjust as needed

        except Exception as e:
            print(f"An error occurred: {e}")
            if "ERR_NO_SUPPORTED_PROXIES" in str(e):
                print(Fore.YELLOW + "Switching proxy due to ERR_NO_SUPPORTED_PROXIES")
                if ws:
                    ws.close()
                if chrome_process:
                    chrome_process.terminate()
                continue

        finally:
            if ws:
                ws.close()
            if chrome_process:
                chrome_process.terminate()

if __name__ == "__main__":
    main()
