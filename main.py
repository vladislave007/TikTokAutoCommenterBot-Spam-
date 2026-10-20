import requests, random, binascii, os, uuid, time, re, json, sys
from urllib.parse import urlencode
from MedoSigner import Argus, Gorgon, md5, Ladon

#+------------------------------------------------------+
#| Author : L7N                                       |
#| Telegram : t.me/PyL7N                     |
#| Github : https://github.com/is-L7N  |
#+------------------------------------------------------+

class TikTok:
    def __init__(self, sessionid: str) -> None:
        self.sessionid = sessionid
        self.base_url = "https://api22-normal-c-alisg.tiktokv.com"
        self.headers = {
            'User-Agent': "com.zhiliaoapp.musically.gp/380602 (Linux; U; Android 12; uk_UA; SO-51A; Build/58.2.B.0.520;tt-ok/3.12.13.32-ul)",
            'Cookie': f"sessionid={sessionid}"
        }
        self.params = {
            'iid': str(random.randint(1, 10**19)),
            'openudid': str(binascii.hexlify(os.urandom(8)).decode()),
            'cdid': str(uuid.uuid4()),
            'device_id': str(random.randint(1, 10**19)),
            'region': "UA",
            'aid': "1340",
        }

    def _sign(self, params, payload: str = None, sec_device_id: str = "", aid: int = 567753,
              license_id: int = 1611921764, sdk_version_str: str = "2.3.1.i18n",
              sdk_version: int = 2, platform: int = 19, unix: int = None):

        x_ss_stub = md5(payload.encode('utf-8')).hexdigest() if payload else None
        if not unix:
            unix = int(time.time())
        return Gorgon(params, unix, payload, self.headers.get("Cookie")).get_value() | {
            "x-ladon": Ladon.encrypt(unix, license_id, aid),
            "x-argus": Argus.get_sign(
                params,
                x_ss_stub,
                unix,
                platform=platform,
                aid=aid,
                license_id=license_id,
                sec_device_id=sec_device_id,
                sdk_version=sdk_version_str,
                sdk_version_int=sdk_version,
            ),
        }

    def get_video(self) -> list:
        # 1. Main FYP (For You) feed
        try:
            url = f"{self.base_url}/aweme/v1/feed/"
            params = self.params.copy()
            params.update({
                'count': '20',
                'type': '0',
                'version_name': '38.6.2'
            })
            headers = self.headers.copy()
            signature = self._sign(urlencode(params), payload="")
            headers.update({
                'x-argus': signature["x-argus"],
                'x-gorgon': signature["x-gorgon"],
                'x-khronos': signature["x-khronos"],
                'x-ladon': signature["x-ladon"],
            })
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                aweme_ids = [str(item.get('aweme_id')) for item in data.get('aweme_list', []) if item.get('aweme_id')]
                if aweme_ids:
                    return list(set(aweme_ids))
        except Exception:
            pass

        # 2. Fallback to relation maf list
        try:
            url = f"{self.base_url}/tiktok/user/relation/maf/list/v1"
            params = self.params.copy()
            params.update({
                'scene': "15",
                'count': "20",
                'version_name': "38.6.2"
            })
            headers = self.headers.copy()
            signature = self._sign(urlencode(params), payload="")
            headers.update({
                'x-argus': signature["x-argus"],
                'x-gorgon': signature["x-gorgon"],
                'x-khronos': signature["x-khronos"],
                'x-ladon': signature["x-ladon"],
            })
            response = requests.get(url, params=params, headers=headers, timeout=10).text
            aweme_ids = re.findall(r'"aweme_id":"(\d+)"', response)
            return list(set(aweme_ids))
        except Exception:
            return []

    def get_comments(self, aweme_id: str) -> list:
        url = f"{self.base_url}/lite/v1/comment/list/"
        params = self.params.copy()
        params.update({
            'aweme_id': str(aweme_id),
            'count': '20',
            'cursor': '0',
            'version_name': '38.6.2'
        })
        headers = self.headers.copy()
        signature = self._sign(urlencode(params), payload="")
        headers.update({
            'x-argus': signature["x-argus"],
            'x-gorgon': signature["x-gorgon"],
            'x-khronos': signature["x-khronos"],
            'x-ladon': signature["x-ladon"],
        })
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                comments = data.get("comments", [])
                return [{'cid': str(c.get('cid')), 'user': c.get('user', {}).get('nickname', 'User'), 'text': c.get('text', '')} for c in comments if c.get('cid')]
        except Exception:
            pass
        return []

    def send(self, comment: str, aweme_id: int, reply_id: str = None) -> bool:
        url = f"{self.base_url}/lite/v2/comment/publication/"
        params = self.params.copy()
        headers = self.headers.copy()
        params.update({
            'version_name': "38.6.2",
        })

        data = {
            'aweme_id': int(aweme_id),
            'text': str(comment),
        }
        if reply_id:
            data['reply_id'] = str(reply_id)

        signature = self._sign(urlencode(params), urlencode(data))
        headers.update({
            'x-argus': signature["x-argus"],
            'x-gorgon': signature["x-gorgon"],
            'x-khronos': signature["x-khronos"],
            'x-ladon': signature["x-ladon"],
        })

        try:
            response = requests.post(url, params=params, data=data, headers=headers).json()
            status_msg = response.get("status_msg", "")
            if status_msg == "Comment sent successfully":
                return True
            elif "too fast" in status_msg or "Spam" in status_msg:
                return "Spam"
            elif status_msg:
                return status_msg
            else:
                return False            
        except Exception as e:
            return str(e)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    info = [
        "Author : L7N 🇮🇶",
        "Telegram : t.me/PyL7N",
        "Github : https://github.com/is-L7N"
    ]

    width = max(len(line) for line in info) + 4
    border = "+" + "-" * (width - 2) + "+"
    
    print(border)
    for line in info:
        print("| " + line.ljust(width - 3) + " |") 
    print(border)
    
    saved_session = ""
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
                saved_session = cfg.get("sessionid", "")
        except Exception:
            pass

    prompt_session = f"\nEnter your TikTok Sessionid (press Enter to use saved) : " if saved_session else "\nEnter your TikTok Sessionid : "
    sessionid = input(prompt_session).strip()
    if not sessionid and saved_session:
        sessionid = saved_session

    if sessionid:
        try:
            with open("config.json", "w", encoding="utf-8") as cf:
                json.dump({"sessionid": sessionid}, cf, indent=4)
        except Exception:
            pass

    tiktok = TikTok(sessionid)

    if not os.path.exists("comments.json"):
        with open("comments.json", "w", encoding="utf-8") as f:
            json.dump({"UA": [], "EN": [], "RU": [], "AR": []}, f, indent=4, ensure_ascii=False)

    with open("comments.json", "r", encoding="utf-8") as f:
        com = json.load(f)

    available_langs = " / ".join(com.keys())
    default_lang = "RU" if "RU" in com else ("UA" if "UA" in com else list(com.keys())[0])
    lang = input(f"\nChoose comment language ({available_langs}) [Default: {default_lang}] : ").strip().upper()
    if not lang:
        lang = default_lang
    comments = com.get(lang, [])

    if not comments:
        try:
            num = int(input(f"\nNo comments found for '{lang}'. How many comments do you want to add? : "))
            for i in range(num):
                c = input(f"Comment {i+1}: ")
                comments.append(c)
            com[lang] = comments
            with open("comments.json", "w", encoding="utf-8") as f:
                json.dump(com, f, indent=4, ensure_ascii=False)
        except Exception:
            print("\nInvalid input, using default English comment.")
            comments = ["Great video! 🔥"]

    print("\nSelect Commenting Mode:")
    print("  [1] Mixed (Replies to people + Video comments) - RECOMMENDED")
    print("  [2] Only replies to people (Push notification to user)")
    print("  [3] Only video comments")
    mode = input("\nChoose mode [Default: 1] : ").strip()
    if mode not in ["1", "2", "3"]:
        mode = "1"

    mode_names = {"1": "Mixed (Replies + Video)", "2": "Replies Only", "3": "Video Comments Only"}
    print(f"\n[+] Loaded {len(comments)} comment(s) for [{lang}]. Mode: {mode_names[mode]}")
    print("[*] Press Ctrl+C at any time to stop.\n")

    while True:
        videos = tiktok.get_video()
        if videos:
            print(f"[*] Found {len(videos)} video(s) in feed...")
            for vid in videos:
                comment = random.choice(comments)
                
                do_reply = False
                target_c = None
                
                if mode in ["1", "2"]:
                    existing_comments = tiktok.get_comments(vid)
                    if existing_comments:
                        if mode == "2" or random.random() < 0.7:  # 70% reply in mixed mode
                            do_reply = True
                            target_c = random.choice(existing_comments)
                    elif mode == "2":
                        continue

                if do_reply and target_c:
                    send = tiktok.send(comment, vid, reply_id=target_c['cid'])
                    user_label = target_c['user'][:15]
                    if send is True:
                        print(f"[+] Replied to @{user_label}: '{comment}'")
                    elif send == "Spam":
                        print("\n[!] TikTok Spam Limit: commenting too fast.")
                        print("[*] Pausing for 60s cooldown so TikTok restriction expires...")
                        time.sleep(60)
                        break
                    else:
                        err_detail = f" [TikTok: {send}]" if isinstance(send, str) else ""
                        print(f"[-] Reply failed to @{user_label}{err_detail}")
                else:
                    send = tiktok.send(comment, vid)
                    if send is True:
                        print(f"[+] Commented video {vid}: '{comment}'")
                    elif send == "Spam":
                        print("\n[!] TikTok Spam Limit: commenting too fast.")
                        print("[*] Pausing for 60s cooldown so TikTok restriction expires...")
                        time.sleep(60)
                        break
                    else:
                        err_detail = f" [TikTok: {send}]" if isinstance(send, str) else ""
                        print(f"[-] Comment failed on {vid}{err_detail}")

                time.sleep(random.randint(5, 8))
        else:
            print("[-] No videos returned (check your sessionid or feed). Retrying in 5s...")
            time.sleep(5)
        time.sleep(2)
