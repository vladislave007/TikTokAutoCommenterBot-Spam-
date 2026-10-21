import requests, random, binascii, os, uuid, time, re, json, sys
from urllib.parse import urlencode
from MedoSigner import Argus, Gorgon, md5, Ladon


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

    def warm_up(self) -> bool:
        """Simulate organic human behavior: fetch feed, watch a video, and like it."""
        try:
            url = f"{self.base_url}/aweme/v1/feed/"
            params = self.params.copy()
            params.update({'count': '6', 'type': '0', 'version_name': '38.6.2'})
            headers = self.headers.copy()
            sig = self._sign(urlencode(params), payload="")
            headers.update({
                'x-argus': sig["x-argus"],
                'x-gorgon': sig["x-gorgon"],
                'x-khronos': sig["x-khronos"],
                'x-ladon': sig["x-ladon"],
            })
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                items = r.json().get('aweme_list', [])
                if items:
                    v_item = random.choice(items)
                    v_id = str(v_item.get('aweme_id'))
                    # Simulate human watch time
                    time.sleep(random.randint(2, 4))
                    # Like the video to build account karma
                    digg_url = f"{self.base_url}/aweme/v1/commit/item/digg/"
                    digg_params = self.params.copy()
                    digg_params.update({'aweme_id': v_id, 'type': '1', 'version_name': '38.6.2'})
                    digg_sig = self._sign(urlencode(digg_params), payload="")
                    digg_headers = self.headers.copy()
                    digg_headers.update({
                        'x-argus': digg_sig["x-argus"],
                        'x-gorgon': digg_sig["x-gorgon"],
                        'x-khronos': digg_sig["x-khronos"],
                        'x-ladon': digg_sig["x-ladon"],
                    })
                    requests.post(digg_url, params=digg_params, headers=digg_headers, timeout=6)
                    return True
        except Exception:
            pass
        return False

    def get_video(self, min_comments: int = 15) -> list:
        # 1. Main FYP (For You) feed
        try:
            url = f"{self.base_url}/aweme/v1/feed/"
            params = self.params.copy()
            params.update({
                'count': '25',
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
                videos = []
                for item in data.get('aweme_list', []):
                    aweme_id = str(item.get('aweme_id', ''))
                    if not aweme_id:
                        continue
                    stats = item.get('statistics', {})
                    c_count = int(stats.get('comment_count', 0))
                    digg_count = int(stats.get('digg_count', 0))
                    if c_count >= min_comments:
                        videos.append({
                            'id': aweme_id,
                            'comment_count': c_count,
                            'digg_count': digg_count
                        })
                # Sort by comments count descending so we target viral videos first
                videos.sort(key=lambda x: x['comment_count'], reverse=True)
                if videos:
                    return [v['id'] for v in videos]
                
                # Fallback to any available videos if feed has low comments
                fallback_ids = [str(item['aweme_id']) for item in data.get('aweme_list', []) if item.get('aweme_id')]
                if fallback_ids:
                    return list(dict.fromkeys(fallback_ids))
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
            return list(dict.fromkeys(aweme_ids))
        except Exception:
            return []

    def get_comments(self, aweme_id: str, max_count: int = 50) -> list:
        all_comments = []
        cursor = "0"
        seen_cids = set()
        
        while len(all_comments) < max_count:
            count = min(20, max_count - len(all_comments))
            url = f"{self.base_url}/lite/v1/comment/list/"
            params = self.params.copy()
            params.update({
                'aweme_id': str(aweme_id),
                'count': str(count),
                'cursor': str(cursor),
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
                    if not comments:
                        break
                    for c in comments:
                        cid = str(c.get('cid'))
                        if cid and cid not in seen_cids:
                            seen_cids.add(cid)
                            user_name = c.get('user', {}).get('nickname', 'User')
                            all_comments.append({
                                'cid': cid,
                                'user': user_name,
                                'text': c.get('text', '')
                            })
                    if not data.get("has_more") or len(all_comments) >= max_count:
                        break
                    cursor = str(data.get("cursor", len(all_comments)))
                else:
                    break
            except Exception:
                break
        return all_comments

    def send(self, comment: str, aweme_id: int, reply_id: str = None) -> dict:
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
            response = requests.post(url, params=params, data=data, headers=headers, timeout=10).json()
            status_msg = response.get("status_msg", "")
            comment_obj = response.get("comment", {})
            status = comment_obj.get("status")
            cid = comment_obj.get("cid")

            if status_msg == "Comment sent successfully":
                return {"success": True, "status": status, "cid": cid, "msg": status_msg}
            elif "too fast" in status_msg or "Spam" in status_msg:
                return {"success": False, "status": "spam", "msg": status_msg}
            elif status_msg:
                return {"success": False, "status": "error", "msg": status_msg}
            else:
                return {"success": False, "status": "error", "msg": "No response"}
        except Exception as e:
            return {"success": False, "status": "error", "msg": str(e)}


def spin(template: str, target_user: str = None) -> str:
    """
    Recursively resolves {option1|option2|...} Spintax syntax
    and organically injects @{target_user} into the comment.
    Produces thousands of unique, natural human-like variations.
    """
    pattern = re.compile(r'\{([^{}]+)\}')
    text = template
    for _ in range(5):
        if not pattern.search(text):
            break
        text = pattern.sub(lambda m: random.choice(m.group(1).split('|')), text)

    if target_user:
        clean_user = re.sub(r'[@\s]+', '', target_user).strip()
        if clean_user:
            text = text.replace("@{user}", f"@{clean_user}").replace("{user}", clean_user)
        else:
            text = text.replace("@{user}", "").replace("{user}", "")
    else:
        text = text.replace("@{user}", "").replace("{user}", "")

    # Clean whitespace
    return re.sub(r'\s+', ' ', text).strip()


class Account:
    def __init__(self, sessionid: str, index: int) -> None:
        self.sessionid = sessionid
        self.index = index
        self.label = f"Acc #{index} (...{sessionid[-6:]})" if len(sessionid) >= 6 else f"Acc #{index}"
        self.tiktok = TikTok(sessionid)
        self.cooldown_until = 0
        self.sent_count = 0
        self.fail_count = 0

    @property
    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    @property
    def cooldown_remaining(self) -> int:
        return max(0, int(self.cooldown_until - time.time()))

    def trigger_cooldown(self, seconds: int = 600) -> None:
        self.cooldown_until = time.time() + seconds


class AccountPool:
    def __init__(self, sessions: list) -> None:
        self.accounts = [Account(s, i + 1) for i, s in enumerate(sessions)]
        self.current_idx = 0

    def get_next_available(self) -> Account:
        if not self.accounts:
            return None

        # Check in round-robin order
        for _ in range(len(self.accounts)):
            acc = self.accounts[self.current_idx % len(self.accounts)]
            self.current_idx = (self.current_idx + 1) % len(self.accounts)
            if acc.is_available:
                return acc

        # All accounts are currently on cooldown
        shortest_acc = min(self.accounts, key=lambda a: a.cooldown_remaining)
        wait_time = shortest_acc.cooldown_remaining
        print(f"\n[!] All {len(self.accounts)} account(s) are currently resting.")
        print(f"[*] Shortest cooldown is {shortest_acc.label} ({wait_time}s remaining). Waiting...")
        time.sleep(wait_time + 1)
        return shortest_acc

    def print_summary(self) -> None:
        print(f"\n[+] Loaded {len(self.accounts)} TikTok Account(s) into Carousel:")
        for acc in self.accounts:
            status = "Ready" if acc.is_available else f"Cooldown ({acc.cooldown_remaining}s)"
            print(f"    • {acc.label} - Status: {status}")
        print("")


def load_accounts() -> list:
    sessions = []
    # 1. Load from accounts.txt
    if os.path.exists("accounts.txt"):
        try:
            with open("accounts.txt", "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith("#") and s not in sessions:
                        sessions.append(s)
        except Exception:
            pass

    # 2. Fallback to config.json
    if not sessions and os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
                if isinstance(cfg.get("sessions"), list):
                    sessions = [s.strip() for s in cfg["sessions"] if s.strip()]
                elif cfg.get("sessionid"):
                    sessions = [cfg["sessionid"].strip()]
        except Exception:
            pass

    # 3. Prompt user if still empty
    if not sessions:
        user_in = input("\nEnter your TikTok Session ID (or multiple separated by commas) : ").strip()
        if user_in:
            for part in user_in.split(","):
                part = part.strip()
                if part and part not in sessions:
                    sessions.append(part)

    # Save to accounts.txt and config.json
    if sessions:
        try:
            with open("accounts.txt", "w", encoding="utf-8") as f:
                f.write("# TikTok Session IDs (one per line)\n\n")
                for s in sessions:
                    f.write(s + "\n")
            with open("config.json", "w", encoding="utf-8") as cf:
                json.dump({"sessions": sessions, "sessionid": sessions[0]}, cf, indent=4)
        except Exception:
            pass

    return sessions


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("\n[+] TikTok Multi-Account Carousel & Auto-Commenter")
    
    sessions = load_accounts()
    if not sessions:
        print("[-] No valid session IDs provided. Exiting.")
        sys.exit(1)

    pool = AccountPool(sessions)
    warm_choice = input("Запустить быстрый прогрев аккаунтов (лайки/просмотр ленты для роста доверия)? (y/n) [По умолчанию: y] : ").strip().lower()
    if warm_choice != "n":
        print("\n[*] Запускаю прогрев аккаунтов (имитация живого пользователя)...")
        for acc in pool.accounts:
            ok = acc.tiktok.warm_up()
            print(f"    • {acc.label}: {'Прогрет успешно (лайк + лента) 👍' if ok else 'Лента проверена'}")
            time.sleep(1)
        print("[+] Прогрев завершен! Аккаунты готовы к работе.\n")

    if not os.path.exists("comments.json"):
        with open("comments.json", "w", encoding="utf-8") as f:
            json.dump({"UA": [], "EN": [], "RU": []}, f, indent=4, ensure_ascii=False)

    with open("comments.json", "r", encoding="utf-8") as f:
        com = json.load(f)

    available_langs = " / ".join(com.keys())
    default_lang = "RU" if "RU" in com else ("UA" if "UA" in com else list(com.keys())[0])
    lang = input(f"Choose comment language ({available_langs}) [Default: {default_lang}] : ").strip().upper()
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

    max_replies_per_video = 30
    if mode in ["1", "2"]:
        print("\nСколько ответов оставлять под одним популярным видео?")
        print("  (Рекомендуется: 15-30 ответов, аккаунты сменяются по очереди)")
        r_in = input("Количество ответов на видео [По умолчанию: 25] : ").strip()
        if r_in.isdigit() and int(r_in) > 0:
            max_replies_per_video = min(100, int(r_in))
        else:
            max_replies_per_video = 25

    mode_names = {
        "1": f"Mixed (до {max_replies_per_video} ответов + коммент под видео)",
        "2": f"Replies Only (до {max_replies_per_video} ответов на видео)",
        "3": "Video Comments Only"
    }
    print(f"\n[+] Загружено {len(comments)} Spintax-шаблонов для [{lang}]. Режим: {mode_names[mode]}")
    print(f"[*] Лимит ответов на видео: {max_replies_per_video} | Карусель активна ({len(pool.accounts)} акк).")
    print("[*] Безопасные интервалы: 18-30 сек между ответами (защита от теневого бана).")
    print("[*] Нажмите Ctrl+C в любой момент для остановки.\n")

    while True:
        acc_for_feed = pool.get_next_available()
        videos = acc_for_feed.tiktok.get_video(min_comments=10)
        if videos:
            print(f"\n[*] Найдено {len(videos)} активных видео в ленте рекомендаций...")
            for v_idx, vid in enumerate(videos, 1):
                if mode in ["1", "2"]:
                    worker_init = pool.get_next_available()
                    existing_comments = worker_init.tiktok.get_comments(vid, max_count=max_replies_per_video)
                    
                    if existing_comments:
                        print(f"\n[*] [Видео {v_idx}/{len(videos)}] (ID: {vid}): Найдено {len(existing_comments)} комментариев. Запускаю карусель ответов...")
                        for c_idx, target_c in enumerate(existing_comments, 1):
                            raw_template = random.choice(comments)
                            comment = spin(raw_template, target_c.get('user', ''))
                            worker = pool.get_next_available()
                            
                            res = worker.tiktok.send(comment, vid, reply_id=target_c['cid'])
                            try:
                                user_label = target_c['user'][:15]
                            except Exception:
                                user_label = "User"
                                
                            if res.get("success"):
                                worker.sent_count += 1
                                c_status = res.get("status")
                                if c_status == 1:
                                    status_badge = "[✓ ВИДЕН ВСЕМ]"
                                elif c_status == 2:
                                    status_badge = "[~ Теневая проверка]"
                                else:
                                    status_badge = "[✓ Отправлен]"
                                print(f"[+] [{worker.label}] {status_badge} Ответил @{user_label}: '{comment}' ({c_idx}/{len(existing_comments)}) [Всего: {worker.sent_count}]")
                            elif res.get("status") == "spam":
                                print(f"\n[!] [{worker.label}] Лимит спама от TikTok! Отдых 15 мин...")
                                worker.trigger_cooldown(900)
                                if any(a.is_available for a in pool.accounts):
                                    print(f"[*] Мгновенно переключаюсь на следующий аккаунт...")
                                continue
                            else:
                                worker.fail_count += 1
                                err_msg = res.get("msg", "Unknown")
                                print(f"[-] [{worker.label}] Ошибка ответа @{user_label}: {err_msg}")
                            
                            delay = random.randint(18, 28) if len(pool.accounts) > 1 else random.randint(25, 40)
                            time.sleep(delay)
                            
                        # If in mixed mode, optionally leave 1 direct comment on video
                        if mode == "1" and random.random() < 0.4:
                            worker = pool.get_next_available()
                            comment = spin(random.choice(comments), None)
                            res = worker.tiktok.send(comment, vid)
                            if res.get("success"):
                                worker.sent_count += 1
                                print(f"[+] [{worker.label}] Комментарий к видео {vid}: '{comment}'")
                            time.sleep(random.randint(15, 25))
                    else:
                        if mode == "2":
                            print(f"[-] [Видео {v_idx}/{len(videos)}] Нет комментариев для ответов, перехожу дальше...")
                            continue
                        else:
                            # Mode 1 fallback to video comment
                            worker = pool.get_next_available()
                            comment = spin(random.choice(comments), None)
                            res = worker.tiktok.send(comment, vid)
                            if res.get("success"):
                                worker.sent_count += 1
                                print(f"[+] [{worker.label}] Комментарий к видео {vid}: '{comment}'")
                            time.sleep(random.randint(18, 28))
                else:
                    # Mode 3: Video Comments Only
                    comment = spin(random.choice(comments), None)
                    worker = pool.get_next_available()
                    res = worker.tiktok.send(comment, vid)
                    if res.get("success"):
                        worker.sent_count += 1
                        print(f"[+] [{worker.label}] Прокомментировал видео {vid}: '{comment}' (Всего: {worker.sent_count})")
                    elif res.get("status") == "spam":
                        print(f"\n[!] [{worker.label}] Лимит спама! Отдых 15 мин...")
                        worker.trigger_cooldown(900)
                        continue
                    else:
                        worker.fail_count += 1
                        print(f"[-] [{worker.label}] Ошибка коммента на {vid}: {res.get('msg')}")
                    
                    delay = random.randint(18, 28) if len(pool.accounts) > 1 else random.randint(25, 40)
                    time.sleep(delay)
                
                # Human pause between videos (simulating watching next video)
                pause = random.randint(20, 35)
                print(f"[*] Пауза просмотра ленты: {pause}с перед следующим видео...")
                time.sleep(pause)
        else:
            print("[-] No videos returned (check account sessions or feed). Retrying in 10s...")
            time.sleep(10)
        time.sleep(3)

