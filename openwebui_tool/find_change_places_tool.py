from __future__ import annotations

import os

import requests
from pydantic import Field


class Tools:
    def find_change_places(
        self,
        task: str = Field(..., description="Описание задачи аналитика"),
        repo: str = Field("gp", description="Имя репозитория"),
        branch: str = Field("master", description="Ветка"),
        limit: int = Field(10, description="Количество результатов"),
    ) -> str:
        """
        Найти вероятные места изменения в 1С-репозитории по тексту задачи.
        Возвращает файлы, модули, процедуры и объяснение.
        """

        base_url = os.getenv("ONEC_CODE_SEARCH_API_URL", "http://onec-code-search-api:8000").rstrip("/")
        response = requests.post(
            f"{base_url}/find-change-places",
            json={
                "query": task,
                "repo": repo,
                "branch": branch,
                "limit": limit,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        lines = [f"Задача: {task}", "", "Вероятные места изменения:"]
        for item in data.get("candidates", []):
            lines.append("")
            lines.append(f"{item['rank']}. {item.get('module_name')} / {item.get('symbol_name')}")
            lines.append(f"   Файл: {item.get('path')}")
            lines.append(f"   Строки: {item.get('start_line')}-{item.get('end_line')}")
            lines.append(f"   Score: {item.get('final_score', item.get('score'))}")
            lines.append(f"   GitLab: {item.get('gitlab_url')}")

            reasons = item.get("why") or []
            if reasons:
                lines.append("   Почему:")
                for reason in reasons:
                    lines.append(f"   - {reason}")

        return "\n".join(lines)
