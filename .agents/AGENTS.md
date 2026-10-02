# Agent Rules

- **Docker Execution**: NEVER start Docker containers manually using commands like `docker-compose up`, `docker compose up`, `docker build`, or `make up`. The user's system has limited resources and doing so causes severe CPU and RAM spikes leading to Out-Of-Memory (OOM) crashes, taking down the entire IDE and other applications. The user will manually start containers when needed.
- **Database Migrations**: DO NOT create new numbered migration files (`000002_*`, `000003_*`). Until the first official release, all DDL schema changes must be added directly into the initial `000001_*.sql` migration file for the corresponding service.
- **Investigation vs Modification (Изучение и сверка с кодом)**:
  Когда пользователь говорит «изучить», «сверить с кодом», «проверить» — это означает **только проверку, аудит и сравнение** (убедиться, есть ли на самом деле ошибки или расхождения в коде).
  - Это **НЕ означает**, что нужно сразу редактировать файлы, компилировать код или делать деплой.
  - **Любые изменения в коде запрещены** до тех пор, пока не будет составлен подробный пошаговый план реализации (`implementation_plan.md`) и пользователь не даст на него явное согласие.
  - Сначала только анализ, факты и выводы. Только после отдельного согласования плана — переход к коду.

