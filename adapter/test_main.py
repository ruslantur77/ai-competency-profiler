#!/usr/bin/env python3
"""
Скрипт для ручной проверки работы адаптера.
Запуск: python test_adapter.py

Что делает:
1. Проверяет здоровье адаптера
2. Запускает синк (получает прогресс из LMS → сохраняет в БД)
3. Показывает что получилось в БД
4. Показывает статус отправки в webhook
"""

import asyncio
import httpx

ADAPTER_URL = "http://localhost:8001"


async def check_health(client: httpx.AsyncClient) -> bool:
    """Шаг 1: проверяем что адаптер живой."""
    print("\n=== 1. Health check ===")
    try:
        r = await client.get(f"{ADAPTER_URL}/api/health")
        print(f"Статус: {r.status_code} | {r.json()}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Адаптер недоступен: {e}")
        return False


async def check_status(client: httpx.AsyncClient) -> None:
    """Шаг 2: текущая статистика до синка."""
    print("\n=== 2. Статистика ДО синка ===")
    r = await client.get(f"{ADAPTER_URL}/api/status")
    data = r.json()
    stats = data.get("db_stats", {})
    print(f"  pending : {stats.get('pending', 0)}")
    print(f"  sent    : {stats.get('sent', 0)}")
    print(f"  failed  : {stats.get('failed', 0)}")
    print(f"  dlq     : {stats.get('dlq', 0)}")
    print(f"  last_sync: {stats.get('last_sync', 'никогда')}")


async def run_sync(client: httpx.AsyncClient) -> None:
    """Шаг 3: запускаем синк и ждём завершения."""
    print("\n=== 3. Запуск синка ===")
    r = await client.post(f"{ADAPTER_URL}/api/sync-now")
    print(f"Ответ: {r.status_code} | {r.json()}")

    # Синк работает в фоне — ждём немного
    print("Ждём 10 секунд пока синк завершится...")
    for i in range(10, 0, -1):
        print(f"  {i}...", end="\r")
        await asyncio.sleep(1)
    print("  Готово!     ")


async def check_events(client: httpx.AsyncClient) -> None:
    """Шаг 4: смотрим что появилось в БД."""
    print("\n=== 4. События в БД после синка ===")
    r = await client.get(f"{ADAPTER_URL}/api/debug/events", params={"limit": 10})
    data = r.json()
    print(f"Всего событий в выборке: {data.get('count', 0)}")

    for event in data.get("events", []):
        print(
            f"\n  event_id     : {event.get('event_id')}"
            f"\n  task_ext_id  : {event.get('task_external_id')}"
            f"\n  vacancy_id   : {event.get('vacancy_id')}"
            f"\n  user_id      : {event.get('lms_user_id')}"
            f"\n  type         : {event.get('task_type')}"
            f"\n  passed/total : {event.get('passed')}/{event.get('total')}"
            f"\n  send_status  : {event.get('send_status')}"
            f"\n  last_error   : {event.get('last_error')}"
            f"\n  {'-' * 40}"
        )


async def check_status_after(client: httpx.AsyncClient) -> None:
    """Шаг 5: статистика после синка."""
    print("\n=== 5. Статистика ПОСЛЕ синка ===")
    r = await client.get(f"{ADAPTER_URL}/api/status")
    data = r.json()
    stats = data.get("db_stats", {})
    print(f"  pending : {stats.get('pending', 0)}")
    print(f"  sent    : {stats.get('sent', 0)}")
    print(f"  failed  : {stats.get('failed', 0)}")
    print(f"  dlq     : {stats.get('dlq', 0)}")
    print(f"  last_sync: {stats.get('last_sync')}")

    # Итоговый вывод
    print("\n=== Итог ===")
    sent = stats.get("sent", 0)
    pending = stats.get("pending", 0)
    failed = stats.get("failed", 0)
    dlq = stats.get("dlq", 0)

    if sent > 0:
        print(f"✅ Отправлено в webhook: {sent} событий")
    if pending > 0:
        print(
            f"⏳ Pending (таск ещё не синкнут Airflow): {pending} событий"
            f"\n   → Запусти Airflow DAG task_sync и повтори тест"
        )
    if failed > 0:
        print(f"⚠️  Failed (будет retry): {failed} событий")
    if dlq > 0:
        print(
            f"❌ DLQ (застряли): {dlq} событий"
            f"\n   → Проверь BACKEND_WEBHOOK_SECRET и доступность бэкенда"
            f"\n   → Для повтора: POST {ADAPTER_URL}/api/dlq/requeue"
        )
    if sent == 0 and pending == 0 and failed == 0 and dlq == 0:
        print("🤔 Событий нет совсем — проверь SOURCE_COURSE_IDS и COURSE_VACANCY_MAP в .env")


async def check_external_tasks(client: httpx.AsyncClient) -> None:
    """Шаг 6: проверяем GET /external/tasks — northbound API для бэкенда."""
    print("\n=== 6. Проверка GET /external/tasks (northbound API) ===")
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    r = await client.get(
        f"{ADAPTER_URL}/external/tasks",
        params={"start": start, "end": end, "force": "true"},
    )
    print(f"Статус: {r.status_code}")

    if r.status_code == 200:
        tasks = r.json()
        print(f"Задач получено: {len(tasks)}")
        for task in tasks[:5]:  # показываем первые 5
            print(
                f"\n  external_id : {task.get('external_id')}"
                f"\n  title       : {task.get('title')}"
                f"\n  type        : {task.get('type')}"
                f"\n  tags        : {task.get('tags')}"
            )
        if len(tasks) > 5:
            print(f"\n  ... и ещё {len(tasks) - 5} задач")
    else:
        print(f"❌ Ошибка: {r.text[:300]}")


async def main():
    print("=" * 50)
    print("  Проверка адаптера")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health
        ok = await check_health(client)
        if not ok:
            print("\n❌ Адаптер не отвечает. Запусти его: python main.py")
            return

        # 2. Статистика до
        await check_status(client)

        # 3. Синк
        await run_sync(client)

        # 4. События в БД
        await check_events(client)

        # 5. Статистика после
        await check_status_after(client)

        # 6. Northbound API
        await check_external_tasks(client)

    print("\n" + "=" * 50)
    print("  Проверка завершена")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())