\# Hackathon Radar AI - Backend



FastAPI backend for the Hackathon Radar AI platform.



\## Tech Stack



\- Python 3.13

\- FastAPI

\- Uvicorn

\- Pydantic Settings

\- Pytest

\- HTTPX

\- Docker

\- Docker Compose



\## Project Structure



```text

backend/

├── app/

│   ├── api/

│   │   ├── routes/

│   │   │   └── health.py

│   │   └── router.py

│   ├── core/

│   │   ├── config.py

│   │   ├── exceptions.py

│   │   ├── logging.py

│   │   └── utils.py

│   ├── schemas/

│   │   └── errors.py

│   └── main.py

├── tests/

│   └── test\_api.py

├── .env.example

├── Dockerfile

├── .dockerignore

└── requirements.txt
