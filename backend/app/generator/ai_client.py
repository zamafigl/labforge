import json
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")


def generate_cpp_solution(task: str, variant_id: int, student: dict) -> dict:
    if AI_PROVIDER == "ollama":
        return _generate_with_ollama(task, variant_id, student)

    return _fallback_solution(
        task=task,
        variant_id=variant_id,
        student=student,
        reason=f"Unsupported AI_PROVIDER: {AI_PROVIDER}",
    )


def _generate_with_ollama(task: str, variant_id: int, student: dict) -> dict:
    prompt = _build_prompt(task, variant_id, student)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2500,
                },
            },
            timeout=240,
        )

        if response.status_code != 200:
            return _fallback_solution(
                task=task,
                variant_id=variant_id,
                student=student,
                reason=f"Ollama HTTP {response.status_code}: {response.text}",
            )

        raw_text = response.json().get("response", "")
        parsed = _extract_json(raw_text)

        result = {
            "main_cpp": _to_text(parsed.get("main_cpp")),
            "readme_md": _to_text(parsed.get("readme_md")),
            "report_typ": _to_text(parsed.get("report_typ")),
        }

        if not _is_valid_result(result):
            return _fallback_solution(
                task=task,
                variant_id=variant_id,
                student=student,
                reason="Ollama returned invalid or incomplete JSON",
            )

        return result

    except requests.Timeout:
        return _fallback_solution(
            task=task,
            variant_id=variant_id,
            student=student,
            reason="Ollama request timeout",
        )

    except requests.RequestException as error:
        return _fallback_solution(
            task=task,
            variant_id=variant_id,
            student=student,
            reason=f"Ollama request error: {error}",
        )

    except Exception as error:
        return _fallback_solution(
            task=task,
            variant_id=variant_id,
            student=student,
            reason=f"Unexpected AI error: {error}",
        )


def _build_prompt(task: str, variant_id: int, student: dict) -> str:
    return f"""
Ты генератор лабораторных работ по C++.

Верни только валидный JSON.
Не используй markdown.
Не пиши текст до JSON.
Не пиши текст после JSON.

Структура ответа строго такая:

{{
  "main_cpp": "полный C++17 код",
  "readme_md": "README.md на русском",
  "report_typ": "Typst отчёт на русском"
}}

Данные:
Вариант: {variant_id}
Задание: {task}
Студент: {student.get("name", "")}
Группа: {student.get("group", "")}

Требования к main_cpp:
- полный рабочий C++17 код;
- использовать iostream и vector;
- не использовать using namespace std;
- считать n;
- считать n целых чисел;
- посчитать количество элементов, которые больше предыдущего;
- вывести только результат;
- код должен компилироваться командой: g++ -std=c++17 src/main.cpp -o lab.

Требования к readme_md:
- название лабораторной;
- студент, группа, вариант;
- задание;
- сборка;
- запуск;
- пример входных данных;
- пример вывода.

Требования к report_typ:
- простой Typst-документ;
- заголовок;
- студент, группа, вариант;
- задание;
- описание алгоритма;
- вывод.
""".strip()


def _extract_json(raw_text: str) -> dict[str, Any]:
    if not raw_text:
        return {}

    text = raw_text.strip()

    candidates = [
        text,
        text.replace("```json", "").replace("```JSON", "").replace("```", "").strip(),
    ]

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.append(match.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    return {}


def _to_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _is_valid_result(result: dict) -> bool:
    required_fields = ["main_cpp", "readme_md", "report_typ"]

    for field in required_fields:
        value = result.get(field)

        if not isinstance(value, str):
            return False

        if len(value.strip()) < 20:
            return False

    return True


def _fallback_solution(task: str, variant_id: int, student: dict, reason: str) -> dict:
    return {
        "main_cpp": _fallback_cpp(),
        "readme_md": _fallback_readme(task, variant_id, student, reason),
        "report_typ": _fallback_report(task, variant_id, student, reason),
    }


def _fallback_cpp() -> str:
    return """#include <iostream>
#include <vector>

int main() {
    int n;
    std::cin >> n;

    std::vector<int> values(n);

    for (int i = 0; i < n; ++i) {
        std::cin >> values[i];
    }

    int count = 0;

    for (int i = 1; i < n; ++i) {
        if (values[i] > values[i - 1]) {
            ++count;
        }
    }

    std::cout << count << std::endl;

    return 0;
}
"""


def _fallback_readme(task: str, variant_id: int, student: dict, reason: str) -> str:
    return f"""# Лабораторная работа

Студент: {student.get("name", "")}
Группа: {student.get("group", "")}
Вариант: {variant_id}

## Задание

{task}

## Сборка

```bash
g++ -std=c++17 src/main.cpp -o lab
```

## Запуск

```bash
./lab
```

## Пример входных данных

```text
5
1 3 2 5 4
```

## Пример вывода

```text
2
```

## AI status

Использован fallback-режим.

Причина:

```text
{reason}
```
"""


def _fallback_report(task: str, variant_id: int, student: dict, reason: str) -> str:
    return f"""= Лабораторная работа

Студент: {student.get("name", "")}
Группа: {student.get("group", "")}
Вариант: {variant_id}

== Задание

{task}

== Описание алгоритма

Программа считывает количество элементов массива, затем считывает сами элементы.

После этого выполняется проход по массиву, начиная со второго элемента.

Если текущий элемент больше предыдущего, счётчик увеличивается на единицу.

== Текст программы

Код программы находится в файле `src/main.cpp`.

== Вывод

В ходе выполнения лабораторной работы была разработана программа на языке C++, которая подсчитывает количество элементов массива, значение которых превышает значение предыдущего элемента.

== AI status

Использован fallback-режим.

Причина: {reason}
"""