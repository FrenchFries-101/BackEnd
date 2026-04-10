# AcademicEnglish Backend

## Overview
This repository contains the FastAPI backend for the AcademicEnglish team project. It provides APIs for multiple modules used by the desktop frontend, including:

- user authentication
- listening practice
- word learning
- forum and replies
- speaking assessment
- ranking / points
- group features
- word game
- pet system
- restaurant recommendation

The main application entry point is `main.py`.

## Tech Stack
- Python
- FastAPI
- SQLAlchemy
- MySQL / PyMySQL
- Pydantic
- faster-whisper
- OpenAI-compatible API client

## Repository Structure
├── main.py                     # Main FastAPI app entry
├── database.py                 # Database engine and session setup
├── Login.py                    # Login and registration APIs
├── listening.py                # Listening module APIs
├── word.py                     # Vocabulary module APIs
├── forum.py                    # Forum APIs
├── speaking.py                 # Speaking scoring APIs
├── ted.py                      # TED practice APIs
├── rank.py                     # Ranking / points APIs
├── group.py                    # Group APIs
├── word_game.py                # Word game APIs
├── pet.py                      # Pet system APIs
├── recommendation/
│   ├── restaurant.py           # Restaurant recommendation APIs
│   └── changsha.py             # Changsha city info APIs
├── tests/                      # Automated tests
├── requirements.txt            # Project dependencies
└── run_backend.bat             # Windows helper script

## Requirements
- Python 3.10+
- pip
- MySQL database access

## Installation
Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```


## Configuration
This project currently reads the database connection directly from `database.py`.

The speaking module also uses environment variables for external service configuration, such as:

```env
QWEN_API_KEY=your_api_key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
WHISPER_MODEL_SIZE=small.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```


## Running the Backend
```bash
uvicorn main:app --reload
```

## Testing
Some test files are included in the repository.

Run all tests:
```bash
pytest
```

Run a specific test file:
```bash
pytest tests/test_word_game_api.py -v
```
