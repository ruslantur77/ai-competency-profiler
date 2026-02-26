# backend/mock_data.py

MOCK_GRAPH = {
    "vacancy": {
        "id": "123456",
        "name": "Data-аналитик по прогнозированию",
        "experience": "1–3 года",
        "key_skills": ["SQL", "Python", "Excel"]
    },
    "categories": [
        {
            "id": "technical_skills",
            "name": "Технические навыки",
            "emoji": "🔧",
            "description": "Инструменты и технологии"
        },
        {
            "id": "analytical_skills",
            "name": "Аналитические навыки",
            "emoji": "📊",
            "description": "Методы анализа данных"
        },
        {
            "id": "domain_knowledge",
            "name": "Доменные знания",
            "emoji": "🏢",
            "description": "Знание предметной области"
        },
        {
            "id": "soft_skills",
            "name": "Soft Skills",
            "emoji": "🤝",
            "description": "Мягкие навыки"
        }
    ],
    "competencies": [
        {
            "id": "comp_1",
            "category_id": "technical_skills",
            "skill": "SQL — аналитические функции, подзапросы, оптимизация",
            "sub_competencies": [
                {
                    "id": "sub_1_1",
                    "name": "Базовые запросы (SELECT, JOIN, GROUP BY)",
                    "level": "beginner",
                    "description": "Умение писать запросы с объединением таблиц и агрегацией данных",
                    "sub_skills": ["INNER/LEFT/RIGHT JOIN", "GROUP BY + HAVING", "WHERE фильтрация"]
                },
                {
                    "id": "sub_1_2",
                    "name": "Оконные функции",
                    "level": "intermediate",
                    "description": "ROW_NUMBER, RANK, LAG/LEAD, скользящие агрегаты",
                    "sub_skills": ["ROW_NUMBER / RANK / DENSE_RANK", "LAG / LEAD", "SUM/AVG OVER (PARTITION BY)"]
                },
                {
                    "id": "sub_1_3",
                    "name": "Оптимизация запросов",
                    "level": "advanced",
                    "description": "Анализ планов выполнения, индексы, партиционирование",
                    "sub_skills": ["EXPLAIN ANALYZE", "Индексы (B-tree, Hash)", "Партиционирование таблиц"]
                }
            ]
        },
        {
            "id": "comp_2",
            "category_id": "technical_skills",
            "skill": "Python для обработки и анализа данных",
            "sub_competencies": [
                {
                    "id": "sub_2_1",
                    "name": "Pandas — работа с DataFrame",
                    "level": "intermediate",
                    "description": "Чтение, фильтрация, группировка, merge датафреймов",
                    "sub_skills": ["read_csv / read_excel", "groupby + agg", "merge / concat", "pivot_table"]
                },
                {
                    "id": "sub_2_2",
                    "name": "Визуализация (Matplotlib, Seaborn)",
                    "level": "beginner",
                    "description": "Построение графиков для анализа данных",
                    "sub_skills": ["Line / Bar / Scatter plots", "Heatmap корреляций", "Subplots"]
                }
            ]
        },
        {
            "id": "comp_3",
            "category_id": "technical_skills",
            "skill": "Excel (PowerPivot-DAX, PowerQuery)",
            "sub_competencies": [
                {
                    "id": "sub_3_1",
                    "name": "Сводные таблицы и формулы",
                    "level": "beginner",
                    "description": "Создание сводных таблиц, ВПР/ГПР, базовые формулы",
                    "sub_skills": ["Сводные таблицы", "ВПР / ИНДЕКС+ПОИСКПОЗ", "Условное форматирование"]
                },
                {
                    "id": "sub_3_2",
                    "name": "Power Query — ETL в Excel",
                    "level": "intermediate",
                    "description": "Загрузка, трансформация и очистка данных",
                    "sub_skills": ["Подключение к источникам", "Трансформации (unpivot, merge)", "Автообновление"]
                },
                {
                    "id": "sub_3_3",
                    "name": "DAX в PowerPivot",
                    "level": "advanced",
                    "description": "Написание мер и вычисляемых столбцов на DAX",
                    "sub_skills": ["CALCULATE / FILTER", "SUMX / AVERAGEX", "Контекст строки и фильтра"]
                }
            ]
        },
        {
            "id": "comp_4",
            "category_id": "analytical_skills",
            "skill": "Анализ показателей товарного запаса",
            "sub_competencies": [
                {
                    "id": "sub_4_1",
                    "name": "Расчёт оборачиваемости запасов",
                    "level": "intermediate",
                    "description": "Inventory Turnover, Days of Supply, средний запас",
                    "sub_skills": ["Формула оборачиваемости", "Дни запаса (DOS)", "ABC-анализ по оборачиваемости"]
                },
                {
                    "id": "sub_4_2",
                    "name": "Анализ упущенных продаж",
                    "level": "advanced",
                    "description": "Выявление и оценка потерь от отсутствия товара на стоке",
                    "sub_skills": ["Stockout rate", "Lost Sales estimation", "Service Level (fill rate)"]
                },
                {
                    "id": "sub_4_3",
                    "name": "Факторный анализ изменений запаса",
                    "level": "intermediate",
                    "description": "Декомпозиция причин роста/снижения запаса",
                    "sub_skills": ["Waterfall-анализ", "Like-for-like vs новинки", "Сезонная коррекция"]
                }
            ]
        },
        {
            "id": "comp_5",
            "category_id": "analytical_skills",
            "skill": "Ad hoc аналитика",
            "sub_competencies": [
                {
                    "id": "sub_5_1",
                    "name": "Формулирование гипотез",
                    "level": "intermediate",
                    "description": "Умение ставить правильные вопросы к данным",
                    "sub_skills": ["Структурирование проблемы", "Определение метрик для проверки"]
                },
                {
                    "id": "sub_5_2",
                    "name": "Быстрый анализ и визуализация",
                    "level": "intermediate",
                    "description": "Оперативное исследование данных и презентация выводов",
                    "sub_skills": ["Exploratory Data Analysis", "Storytelling с данными", "Быстрое прототипирование дашбордов"]
                }
            ]
        },
        {
            "id": "comp_6",
            "category_id": "domain_knowledge",
            "skill": "Коммерческая аналитика в ритейле",
            "sub_competencies": [
                {
                    "id": "sub_6_1",
                    "name": "Метрики ритейла",
                    "level": "intermediate",
                    "description": "Понимание ключевых KPI розничной торговли",
                    "sub_skills": ["Выручка / маржа / LFL", "Средний чек / конверсия", "Sell-through rate"]
                },
                {
                    "id": "sub_6_2",
                    "name": "Управление ассортиментом",
                    "level": "intermediate",
                    "description": "Принципы формирования и ротации ассортимента",
                    "sub_skills": ["ABC/XYZ-анализ", "Категорийный менеджмент", "Lifecycle товара"]
                }
            ]
        },
        {
            "id": "comp_7",
            "category_id": "soft_skills",
            "skill": "Коммуникация и работа в команде",
            "sub_competencies": [
                {
                    "id": "sub_7_1",
                    "name": "Презентация результатов анализа",
                    "level": "intermediate",
                    "description": "Умение доносить выводы до бизнес-заказчиков",
                    "sub_skills": ["Структура презентации", "Data Storytelling", "Адаптация под аудиторию"]
                },
                {
                    "id": "sub_7_2",
                    "name": "Самостоятельность и ответственность",
                    "level": "intermediate",
                    "description": "Готовность брать ответственность за решения",
                    "sub_skills": ["Приоритизация задач", "Инициативность", "Ownership"]
                }
            ]
        }
    ]
}

MOCK_VACANCY_TEXT = """
Привет! Меня зовут Денис, и я коммерческий директор сети «Золотое Яблоко».

Мой департамент отвечает за ассортимент и цены в наших магазинах. Каждую неделю наш ассортимент пополняется сотнями новых интересных продуктов, а общее предложение в сети достигает уже почти 200 тыс наименований.

Мы всегда рады новым участникам команды, которые, как и мы, будут гореть желанием добиваться результатов.

Что нужно делать:
• Анализировать основные показатели товарного запаса (структуру, причины роста и снижения, оборачиваемость, упущенные продажи, наличие на стоке) и динамику продаж
• Собирать и предобрабатывать данные, необходимые для решения аналитических задач
• Решать задачи в проекте DS (DarkStore), включая предобработку данных, автоматизацию регулярной отчетности
• Проводить ad hoc аналитику

Что ждём от кандидата:
• Опыт коммерческой аналитики в ритейле от года
• Уверенный навык работы с SQL — аналитические функции, подзапросы, оптимизация запросов (Clickhouse, PostgreSQL)
• Excel (PowerPivot-DAX, PowerQuery), Python для обработки и анализа данных, визуализация BI, Git
• Умение работать с большими объемами данных
"""