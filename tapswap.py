import requests
import urllib.parse
import json
import time
import random
import cloudscraper
import sys
import js2py

from bs4 import BeautifulSoup
from BypassTLS import BypassTLSv1_3

class TapSwap:
    def __init__(self, url: str, chq_bypass, auto_upgrade:bool, max_charge_level:int, max_energy_level:int, max_tap_level:int):
        if auto_upgrade:
            self.max_charge_level = max_charge_level
            self.max_energy_level = max_energy_level
            self.max_tap_level = max_tap_level
        else:
            self.max_charge_level = 1
            self.max_energy_level = 1
            self.max_tap_level = 1
        
        self.webappurl = url
        self.init_data = urllib.parse.unquote(url).split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
        self.x_cv = "617"
        self.access_token = ""
        self.chq_bypass = chq_bypass
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,fa;q=0.8",
            "content-type": "application/json",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13; iPhone 15 Pro Max) AppleWebKit/533.2 (KHTML, like Gecko) Version/122.0 Mobile/15E148 Safari/533.2"
        }
        self.headers_requests = self.headers.copy()
        self.headers_requests.update({
            "Authorization": f"Bearer {self.access_token}",
            "x-cv": self.x_cv,
            "X-App": "tapswap_server",
            "x-bot": "no",
        })

        self.session = requests.Session()
        self.session.mount("https://", BypassTLSv1_3())
        
        self.prepare_prerequisites()
        
        
    def prepare_prerequisites(self):
        uph = self.update_headers()
        if uph == False:
            print("[!] We ran into trouble with the updates to the headers! 🚫 The script is stopping.")
            sys.exit()
        
        atk = self.get_auth_token()
        if atk == False:
            print("[!] We ran into trouble with the get auth token! 🚫 The script is stopping.")
            sys.exit()
    
    def extract_chq_result(self, chq):
        return self.chq_bypass(chq)

    def get_auth_token(self):
        payload = {
            "init_data": self.init_data,
            "referrer": ""
        }
        
        maxtries = 5

        while maxtries >= 0:
            try:
                
                response = self.session.post(
                    'https://api.tapswap.ai/api/account/login',
                    headers=self.headers,
                    data=json.dumps(payload)
                ).json()
                
                if 'wait_s' in response:
                    sleep_time = response["wait_s"]
                    if sleep_time > 70:
                        maxtries += 1
                        continue
                    time.sleep(sleep_time/10)
                    continue
                
                if 'chq' in response:
                    chq_result = self.extract_chq_result(response['chq'])
                    payload['chr'] = chq_result
                    
                    print("[~] ByPass CHQ:  ", chq_result)
                    response = requests.post(
                        'https://api.tapswap.ai/api/account/login',
                        headers=self.headers,
                        data=json.dumps(payload)
                    ).json()
                    
                if not 'access_token' in response:
                    print('[!] There is no access_token in response')
                    continue
                        
                    
                
                self.client_id = response['player']['id']
                self.headers_requests['Authorization'] = f"Bearer {response['access_token']}"
                self.balance = response['player']['shares']
                energy_level = response['player']['energy_level']
                charge_level = response['player']['charge_level']
                self._time_to_recharge = (energy_level*500) / charge_level
                
                try:
                    self.check_update(response)
                except Exception as e:
                    print('[!] Error in upgrade: ', e)
                    
                return response['access_token']
            except Exception as e:
                print("[!] Error in auth:", e)
                time.sleep(3)
            finally:
                maxtries -=1
        
        return False

    def update_headers(self):
        maxtries = 5

        while maxtries >= 0:
            try:
                headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                }

                session = requests.Session()
                session.mount("https://", BypassTLSv1_3())
                session.headers = headers
                scraper = cloudscraper.create_scraper(sess=session)
                
                headers_json = scraper.get(f'https://poeai.click/tapswap/headers.json').json()
                
                if 'dont_run_code' in headers_json:
                    continue
                
                self.headers.update(headers_json['login'])
                self.headers_requests.update(headers_json['send_tap'])

                
                print(self.headers_requests)
                
                return self.headers_requests

            except Exception as e:
                print("[!] Error in update headers:", e)
                time.sleep(3)
                

            finally:
                maxtries -= 1
        
        return False
    
    def check_update(self, response):
        charge_level = response['player']['charge_level']
        energy_level = response['player']['energy_level']
        tap_level    = response['player']['tap_level']
        shares       = response['player']['shares']

        if charge_level < self.max_charge_level:
            price = 0
            while shares >= price:
                for item in response['conf']['charge_levels']:
                    if item['rate'] == charge_level + 1:
                        price = item['price']
                
                if price > shares or charge_level >= self.max_charge_level:
                    break
                
                print('[+] Updating Charge Level')
                self.upgrade_boost('charge')

                shares       -= price
                charge_level += 1
        
        if energy_level < self.max_energy_level:
            price = 0
            while shares >= price:
                for item in response['conf']['energy_levels']:
                    if item['limit'] == (energy_level + 1)*500:
                        price = item['price']
                
                if price > shares or energy_level >= self.max_energy_level:
                    break
                
                print('[+] Updating energy')
                self.upgrade_boost('energy')

                shares       -= price
                energy_level += 1
        
        if tap_level < self.max_tap_level:
            price = 0
            while shares >= price:
                for item in response['conf']['tap_levels']:
                    if item['rate'] == tap_level + 1:
                        price = item['price']
                
                if price > shares or tap_level >= self.max_tap_level:
                    break
                
                print('[+] Updating taps')
                self.upgrade_boost('tap')

                shares    -= price
                tap_level += 1
            
    def tap_stats(self):
        response = self.session.get(
            'https://api.tapswap.ai/api/stat',
            headers=self.headers_requests,
        ).json()
        return response
    
    def upgrade_boost(self, boost_type: str = "energy"):
        payload = {"type": boost_type}
        response = self.session.post(
            'https://api.tapswap.ai/api/player/upgrade',
            headers=self.headers_requests,
            json=payload
        ).json()
        return response
    
    def apply_boost(self, boost_type: str = "energy"):
        payload = {"type": boost_type}
        response = self.session.post(
            'https://api.tapswap.ai/api/player/apply_boost',
            headers=self.headers_requests,
            json=payload
        ).json()
        return response

    def submit_taps(self, taps: int = 1):
        
        o = int(time.time() * 1000)     
           
        result = o * self.client_id
        result = result * self.client_id
        result = result / self.client_id
        result = result % self.client_id
        result = result % self.client_id
        
        content_id = int(result)
        
        payload = {"taps": taps, "time": o}
        
        self.headers_requests['Content-Id'] = str(content_id)

        while True:
            try:
                response = self.session.post(
                    'https://api.tapswap.ai/api/player/submit_taps',
                    headers=self.headers_requests,
                    json=payload
                ).json()
                return response
            except Exception as e:
                print("[!] Error in Tapping:", e)
                time.sleep(1)
    
    def sleep_time(self, num_clicks):
        
        time_to_sleep = 0
        
        for _ in range(num_clicks):
            time_to_sleep += random.uniform(0.1, 0.7)
        
        return time_to_sleep
    
    def click_turbo(self):
        xtap = self.submit_taps(random.randint(60, 70))
        for boost in xtap['player']['boost']:
            if boost['type'] == 'turbo' and boost['end'] > time.time():
                for i in range(random.randint(3, 7)):
                    
                    taps = random.randint(84, 86)
                    
                    sleepTime = self.sleep_time(taps)
                    print(f'[~] Sleeping {sleepTime/6} for next tap.')
                    time.sleep(sleepTime/6)
                    
                    print(f'[+] Turbo: {taps} ...')
                    xtap = self.submit_taps(taps)
                    shares = xtap['player']['shares']
                    
                    print(f'[+] Balance : {shares}')
                    self.balance = shares
                if boost['cnt'] > 0:
                    print('[+] Activing Turbo ...')
                    self.apply_boost("turbo")
                    self.click_turbo()
    
    def click_all(self):
        
        self.prepare_prerequisites()
        
        
        xtap = self.submit_taps(random.randint(1, 10))
        energy = xtap['player']['energy']
        tap_level = xtap['player']['tap_level']
        energy_level = xtap['player']['energy_level']
        charge_level = xtap['player']['charge_level']
        shares = xtap['player']['shares']
        
        while energy > tap_level*3:
            maxClicks = min([round(energy/tap_level)-1, random.randint(66, 84)])
            if maxClicks > 1:
                sleepTime = self.sleep_time(maxClicks)
                print(f'[~] Sleeping {sleepTime} for next tap.')
                time.sleep(sleepTime)
                xtap = self.submit_taps(maxClicks)
                energy = xtap['player']['energy']
                tap_level = xtap['player']['tap_level']
                shares = xtap['player']['shares']
                print(f'[+] Balance : {shares}')
                self.balance = shares
            else:
                break
        
        for boost in xtap['player']['boost']:
            if boost['type'] == 'energy' and boost['cnt'] > 0:
                print('[+] Activing Full Tank ...')
                self.apply_boost()
                self.click_all()
            
            if boost['type'] == 'turbo' and boost['cnt'] > 0:
                print('[+] Activing Turbo ...')
                self.apply_boost("turbo")
                self.click_turbo()
        
        time_to_recharge = ((energy_level*500)-energy) / charge_level
        return time_to_recharge
    
    def shares(self):
        return self.balance
    
    def time_to_recharge(self):
        return self._time_to_recharge + random.randint(60*2, 60*12)

