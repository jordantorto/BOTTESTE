import time
import configparser
from datetime import datetime
from bot.core.http.navigator import Browser
from bot.core.http.hcaptcha import hcaptcha_solver

config = configparser.ConfigParser()
config.read('settings/config.ini', encoding="utf-8")

host = config.get("server", "host")
port = config.getint("server", "port")
site_key = config.get("hcaptcha", "site_key")

URL_BASE = "https://blaze.com"
URL_SERVER = f"http://{host}:{port}"
URL_HCAPTCHA_API = "http://104.152.186.57:63098"
VERSION_API = "0.0.1-professional"

class BlazeClientAPI(Browser):

    def __init__(self, username=None, password=None):
        super().__init__()
        self.proxies = None
        self.token = None
        self.hcaptcha_token = None
        self.is_logged = False
        self.wallet_id = None
        self.username = username
        self.password = password
        self.set_headers()
        self.headers = self.get_headers()

    def authorization(self, token=None):
        if token:
            self.token = token
            self.is_logged = True
        else:
            return self.auth()
        return True, "Token em execução..."

    def auth(self):
        data = {
            "username": self.username,
            "password": self.password
        }
        timestamp = int(time.time() * 1000)
        self.headers["x-captcha-response"] = self.hcaptcha_token or self.get_captcha_token()
        self.headers["referer"] = f"{URL_BASE}/pt/?modal=auth&tab=login"
        self.response = self.send_request("PUT",
                                          f"{URL_BASE}/api/auth/password?analyticSessionID={timestamp}",
                                          json=data,
                                          headers=self.headers)
        if not self.response.json().get("error"):
            self.token = self.response.json()["access_token"]
            self.is_logged = True
        return self.response.json()

    def reconnect(self):
        return self.auth()

    def hcaptcha_response(self):
        print("Using Anticaptcha System !!!")
        self.headers = self.get_headers()
        self.response = self.send_request("GET",
                                          f"{URL_HCAPTCHA_API}/hcaptcha/token",
                                          headers=self.headers,
                                          timeout=15)
        if self.response:
            return self.response.json().get("x-captcha-response")
        return None

    def get_captcha_token(self):
        site_url = f"{URL_BASE}/api/auth/password"
        response_result = self.hcaptcha_response()
        if not response_result:
            response_result = hcaptcha_solver(site_url, site_key)
        return response_result

    def get_profile(self):
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("GET",
                                          f"{URL_BASE}/api/users/me",
                                          headers=self.headers)
        if not self.response.json().get("error"):
            self.is_logged = True
        return self.response.json()

    def get_balance(self):
        self.headers["referer"] = f"{URL_BASE}/pt/games/double"
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("GET",
                                          f"{URL_BASE}/api/wallets",
                                          headers=self.headers)
        if self.response.status_code == 502:
            self.reconnect()
            return self.get_balance()
        try:
            data = self.response.json()[0]
            self.wallet_id = data["id"]
            return data
        except Exception as e:
            return {}

    def get_user_info(self):
        result_dict = {}
        balance = self.get_balance()
        user_info = self.get_profile()
        result_dict["username"] = user_info["username"]
        result_dict["balance"] = balance["balance"]
        result_dict["wallet_id"] = balance["id"]
        result_dict["tax_id"] = user_info["tax_id"]
        return result_dict

    def get_result(self, game):
        self.headers = self.get_headers()
        result = self.get_current(game)
        if not result:
            self.response = self.send_request("GET",
                                              f"{URL_SERVER}/api/v1/{game}/result",
                                              headers=self.headers)
        return self.response.json()

    def get_status(self, game):
        self.response = self.get_result(game)
        if self.response:
            return self.response.get("status")
        return {"status": "unknown"}

    def get_message(self):
        error = "Erro, aposta não concluída!!!"
        success = "Operação realizada com sucesso!!!"
        return success if self.response else error

    def double_bets(self, color, amount):
        data = {
            "amount": amount,
            "currency_type": "BRL",
            "color": 1 if color == "vermelho" else 2 if color == "preto" else 0,
            "free_bet": False,
            "wallet_id": self.wallet_id
        }
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("POST",
                                          f"{URL_BASE}/api/roulette_bets",
                                          json=data,
                                          headers=self.headers)
        result_dict = {
            "result": True if self.response else False,
            "object": self.response.json(),
            "message": self.get_message()
        }
        return result_dict

    def crash_bets(self, amount, cashout=2):
        data = {
            "amount": amount,
            "type": "BRL",
            "auto_cashout_at": cashout,
            "wallet_id": self.wallet_id
        }
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("POST",
                                          f"{URL_BASE}/api/crash/round/enter",
                                          json=data,
                                          headers=self.headers)
        result_dict = {
            "result": True if self.response else False,
            "object": self.response.json(),
            "message": self.get_message()
        }
        return result_dict

    def crash_cashout(self):
        data = {}
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("POST",
                                          f"{URL_BASE}/api/crash/round/cashout",
                                          json=data,
                                          headers=self.headers)
        result_dict = {
            "result": True if self.response else False,
            "object": self.response.json(),
            "message": self.get_message()
        }
        return result_dict

    async def awaiting_double(self, verbose=True):
        while True:
            try:
                self.response = self.get_result("double")
                if verbose:
                    print(f'\rSTATUS: {self.response["status"]}', end="")
                if self.response["color"] is not None and self.response["roll"] is not None:
                    return self.response
            except Exception as e:
                pass
            time.sleep(0.1)

    async def awaiting_crash(self, verbose=True):
        while True:
            try:
                self.response = self.get_result("crash")
                if verbose:
                    print(f'\rSTATUS: {self.response["status"]}', end="")
                if self.response["crash_point"] is not None:
                    return self.response
            except Exception as e:
                pass
            time.sleep(0.1)

    async def get_double(self):
        result_dict = None
        data = await self.awaiting_double(verbose=False)
        if data:
            result_dict = {
                "roll": data["roll"],
                "color": data["color"]
            }
        return result_dict

    async def get_crash(self):
        result_dict = None
        data = await self.awaiting_crash(verbose=False)
        if data:
            result_dict = {
                "point": data["crash_point"],
            }
        return result_dict

    def get_last_doubles(self):
        self.headers["referer"] = f"{URL_BASE}/pt/games/double"
        self.response = self.send_request("GET",
                                          f"{URL_BASE}/api/roulette_games/recent",
                                          proxies=self.proxies,
                                          headers=self.headers)
        if self.response:
            result = {
                "items": [
                    {"color": "branco" if i["color"] == 0 else "vermelho" if i["color"] == 1 else "preto",
                     "value": i["roll"], "created_date": datetime.strptime(
                        i["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
                     } for i in self.response.json()]}
            return result
        return False

    def get_last_crashs(self):
        self.headers["referer"] = f"{URL_BASE}/pt/games/crash"
        self.response = self.send_request("GET",
                                          f"{URL_BASE}/api/crash_games/recent",
                                          proxies=self.proxies,
                                          headers=self.headers)
        if self.response:
            result = {
                "items": [{"color": "preto" if float(i["crash_point"]) < 2 else "verde", "point": i["crash_point"]}
                          for i in self.response.json()]}
            return result
        return False

    def get_current(self, game="double"):
        self.headers = self.get_headers()
        url_path = "roulette"
        if game == "crash":
            url_path = "crash"
        self.response = self.send_request("GET",
                                          f"{URL_BASE}/api/{url_path}_games/current",
                                          proxies=self.proxies,
                                          headers=self.headers)
        if self.response:
            return self.response
        return None

    def get_history(self, game="double", pages=1):
        self.headers = self.get_headers()
        url_path = "roulette"
        if game == "crash":
            url_path = "crash"
        payload = {
            "page": pages
        }
        self.response = self.send_request("GET",
                                          f"{URL_BASE}/api/{url_path}_games/history",
                                          params=payload,
                                          proxies=self.proxies,
                                          headers=self.headers)
        return self.response.json()
