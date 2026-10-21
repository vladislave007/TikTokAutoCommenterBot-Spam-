import os
import random
import sys
import time

from config import load_accounts, load_comments, save_accounts
from logger import logger
from pool import AccountPool, AccountState
from spintax import spin


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(" [+] TikTok Multi-Account Carousel & Auto-Commenter")
    print("=" * 65)

    # 1. Load accounts
    sessions = load_accounts()
    if not sessions:
        user_in = input("\nEnter your TikTok Session ID (or multiple separated by commas) : ").strip()
        if user_in:
            for part in user_in.split(","):
                part = part.strip()
                if part and part not in sessions:
                    sessions.append(part)
            save_accounts(sessions)

    if not sessions:
        logger.critical("No valid session IDs provided. Exiting.")
        sys.exit(1)

    pool = AccountPool(sessions)
    pool.validate_all()
    pool.print_summary()

    if not pool.active_accounts:
        logger.critical("Ни один аккаунт не прошел проверку авторизации. Проверьте sessionid в accounts.txt!")
        sys.exit(1)

    # 2. Optional warm-up
    warm_choice = input("Запустить быстрый прогрев аккаунтов (лайки/просмотр ленты для роста доверия)? (y/n) [По умолчанию: y] : ").strip().lower()
    if warm_choice != "n":
        print("\n[*] Запускаю прогрев аккаунтов (имитация живого пользователя)...")
        for acc in pool.active_accounts:
            ok = acc.client.warm_up()
            res_str = "Прогрет успешно (лайк + лента) 👍" if ok else "Лента проверена"
            print(f"    • {acc.label}: {res_str}")
            time.sleep(1)
        print("[+] Прогрев завершен! Аккаунты готовы к работе.\n")

    # 3. Load Spintax comments
    comments_db = load_comments()
    available_langs = " / ".join(comments_db.keys())
    default_lang = "RU" if "RU" in comments_db else ("UA" if "UA" in comments_db else list(comments_db.keys())[0])
    
    lang = input(f"Choose comment language ({available_langs}) [Default: {default_lang}] : ").strip().upper()
    if not lang:
        lang = default_lang
    templates = comments_db.get(lang, [])

    if not templates:
        logger.warning(f"No comments found for '{lang}'. Adding default template.")
        templates = ["{хаха|ору|жесть} {в точку|жиза|согласен} 😂"]

    # 4. Select Mode
    print("\nSelect Commenting Mode:")
    print("  [1] Mixed (Replies to people + Video comments) - RECOMMENDED")
    print("  [2] Only replies to people (Push notification to user)")
    print("  [3] Only video comments")
    mode = input("\nChoose mode [Default: 1] : ").strip()
    if mode not in ["1", "2", "3"]:
        mode = "1"

    max_replies_per_video = 25
    if mode in ["1", "2"]:
        print("\nСколько ответов оставлять под одним популярным видео?")
        print("  (Рекомендуется: 15-30 ответов, аккаунты сменяются по очереди)")
        r_in = input("Количество ответов на видео [По умолчанию: 25] : ").strip()
        if r_in.isdigit() and int(r_in) > 0:
            max_replies_per_video = min(100, int(r_in))

    mode_names = {
        "1": f"Mixed (до {max_replies_per_video} ответов + коммент под видео)",
        "2": f"Replies Only (до {max_replies_per_video} ответов на видео)",
        "3": "Video Comments Only"
    }

    print(f"\n[+] Загружено {len(templates)} Spintax-шаблонов для [{lang}]. Режим: {mode_names[mode]}")
    print(f"[*] Лимит ответов на видео: {max_replies_per_video} | Карусель активна ({len(pool.active_accounts)} акк).")
    print("[*] Безопасные интервалы: 18-28 сек между ответами (защита от теневого бана).")
    print("[*] Логи пишутся в консоль и в файл 'bot.log'.")
    print("[*] Нажмите Ctrl+C в любой момент для остановки.\n")

    # 5. Main Commenting Loop
    while True:
        acc_for_feed = pool.get_next_available()
        if not acc_for_feed:
            logger.critical("No accounts available. Exiting loop.")
            break

        videos = acc_for_feed.client.get_feed(count=25, min_comments=10)
        if videos:
            print(f"\n[*] Найдено {len(videos)} активных видео в ленте рекомендаций...")
            for v_idx, vid in enumerate(videos, 1):
                if mode in ["1", "2"]:
                    worker_init = pool.get_next_available()
                    if not worker_init:
                        break
                    existing_comments = worker_init.client.get_comments(vid, max_count=max_replies_per_video)

                    if existing_comments:
                        print(f"\n[*] [Видео {v_idx}/{len(videos)}] (ID: {vid}): Найдено {len(existing_comments)} комментариев. Запускаю карусель ответов...")
                        for c_idx, target_c in enumerate(existing_comments, 1):
                            raw_template = random.choice(templates)
                            comment = spin(raw_template, target_c.get('user', ''))
                            worker = pool.get_next_available()
                            if not worker:
                                break

                            res = worker.client.post_comment(int(vid), comment, reply_id=target_c.get('cid'))
                            user_label = str(target_c.get('user', 'User'))[:15]

                            if res.get("success"):
                                worker.sent_count += 1
                                c_status = res.get("status")
                                if c_status == 1:
                                    worker.public_count += 1
                                    badge = "[✓ ВИДЕН ВСЕМ]"
                                elif c_status == 2:
                                    worker.shadow_count += 1
                                    badge = "[~ Теневая проверка]"
                                else:
                                    badge = "[✓ Отправлен]"
                                print(f"[+] [{worker.label}] {badge} Ответил @{user_label}: '{comment}' ({c_idx}/{len(existing_comments)}) [Всего: {worker.sent_count}]")

                            elif res.get("error_type") == "spam":
                                print(f"\n[!] [{worker.label}] Лимит спама от TikTok! Отдых 15 мин...")
                                worker.trigger_cooldown(900, reason="Spam limit")
                                if pool.active_accounts:
                                    print(f"[*] Мгновенно переключаюсь на следующий аккаунт...")
                                continue

                            elif res.get("error_type") == "auth":
                                print(f"\n[!] [{worker.label}] Сессия недействительна! Отключаю аккаунт...")
                                worker.mark_invalid(res.get("msg", "Session expired"))
                                continue

                            else:
                                worker.fail_count += 1
                                err_msg = res.get("msg", "Unknown")
                                print(f"[-] [{worker.label}] Ошибка ответа @{user_label}: {err_msg}")

                            delay = random.randint(18, 28) if len(pool.active_accounts) > 1 else random.randint(25, 40)
                            time.sleep(delay)

                        # Mode 1: optionally leave 1 direct comment on the video
                        if mode == "1" and random.random() < 0.4:
                            worker = pool.get_next_available()
                            if worker:
                                comment = spin(random.choice(templates), None)
                                res = worker.client.post_comment(int(vid), comment)
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
                            if worker:
                                comment = spin(random.choice(templates), None)
                                res = worker.client.post_comment(int(vid), comment)
                                if res.get("success"):
                                    worker.sent_count += 1
                                    print(f"[+] [{worker.label}] Комментарий к видео {vid}: '{comment}'")
                                time.sleep(random.randint(18, 28))
                else:
                    # Mode 3: Video Comments Only
                    worker = pool.get_next_available()
                    if not worker:
                        break
                    comment = spin(random.choice(templates), None)
                    res = worker.client.post_comment(int(vid), comment)

                    if res.get("success"):
                        worker.sent_count += 1
                        print(f"[+] [{worker.label}] Прокомментировал видео {vid}: '{comment}' (Всего: {worker.sent_count})")
                    elif res.get("error_type") == "spam":
                        print(f"\n[!] [{worker.label}] Лимит спама! Отдых 15 мин...")
                        worker.trigger_cooldown(900, reason="Spam limit")
                        continue
                    elif res.get("error_type") == "auth":
                        worker.mark_invalid(res.get("msg", "Session expired"))
                        continue
                    else:
                        worker.fail_count += 1
                        print(f"[-] [{worker.label}] Ошибка коммента на {vid}: {res.get('msg')}")

                    delay = random.randint(18, 28) if len(pool.active_accounts) > 1 else random.randint(25, 40)
                    time.sleep(delay)

                # Human pause between videos (simulating watching next video)
                pause = random.randint(20, 35)
                print(f"[*] Пауза просмотра ленты: {pause}с перед следующим видео...")
                time.sleep(pause)
        else:
            logger.warning("No videos returned from feed. Retrying in 10s...")
            time.sleep(10)
        time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Остановлено пользователем (Ctrl+C). До свидания!")
        sys.exit(0)
