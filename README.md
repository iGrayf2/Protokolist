# Protokolist

> Ubuntu-first CLI-генератор готового пакета для ChatGPT из длинной записи производственного совещания.

Protokolist не пытается быть обычной программой «аудио → текст». Его главная задача — получить максимально качественный RAW из записи совещания и собрать папку/архив, который можно сразу отправить в ChatGPT.

Проект теперь работает только из командной строки. GUI убран намеренно: длинные записи удобнее обрабатывать через понятный CLI-конвейер с этапами, логами и повторяемым запуском на Ubuntu.

## Рекомендуемое расположение

На рабочей Ubuntu-машине проект лучше держать прямо в домашней папке:

```text
~/Protokolist/
```

Внутри репозитория создаются рабочие папки:

```text
~/Protokolist/
├── input/     # сюда можно класть аудиозаписи
├── output/    # сюда сохраняются пакеты для ChatGPT
├── logs/      # будущие логи
├── models/    # будущие локальные модели/кэш
├── cache/     # временные данные
├── src/
├── scripts/
├── profiles/
├── config/
└── .venv/
```

Папки `input`, `output`, `logs`, `models`, `cache` есть в репозитории только как пустая структура. Реальные записи, результаты, модели и логи не попадают в Git.

## Пользовательский сценарий

```text
Запись совещания на 1 час
   │
   ▼
Protokolist CLI на Ubuntu
   │
   ▼
output/<дата>_<имя_записи>/
   │
   ├── CHATGPT_PACKAGE/
   │   ├── CHATGPT_TASK.md
   │   ├── README.md
   │   ├── meeting_context.json
   │   ├── meeting.raw.json
   │   ├── meeting.raw.txt
   │   ├── meeting.cleaned.txt
   │   └── meeting.cleaned_with_timestamps.txt
   │
   ├── <имя>_chatgpt_package.zip
   │
   └── artifacts/
       ├── prepared_audio.wav
       ├── meeting.raw.json
       ├── meeting.raw.txt
       ├── meeting.cleaned.txt
       ├── meeting.cleaned.srt
       └── meeting.cleaned.docx
```

Дальше пользователь открывает ChatGPT, загружает zip и пишет:

```text
Выполни CHATGPT_TASK.md
```

## Почему Ubuntu и CLI

Проект переводится в Ubuntu-first CLI-режим, потому что дальнейшее развитие будет завязано на инструменты, которые намного проще поддерживать в Linux:

- ffmpeg;
- Faster-Whisper;
- PyTorch/CUDA;
- будущая диаризация;
- локальные LLM;
- Docker;
- systemd/cron;
- автоматическая серверная обработка записей.

CLI удобнее для длинных задач: его можно запускать по SSH, оставлять на ночь, логировать, повторять, автоматизировать через cron/systemd и позже обернуть в серверный режим без переписывания ядра.

## Быстрый старт на Ubuntu

```bash
cd ~
git clone https://github.com/iGrayf2/Protokolist.git
cd Protokolist
chmod +x scripts/*.sh
./scripts/install_ubuntu.sh
```

## Проверка окружения

Перед первой длинной обработкой запусти:

```bash
PYTHONPATH=src .venv/bin/python -m protokolist.cli doctor
```

Команда проверит Python, ffmpeg, зависимости, рабочие папки, профиль, словарь, свободное место и наличие `nvidia-smi`.

## Обработка записи

Положи запись в `input/` и запусти:

```bash
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3
```

То же самое напрямую через Python-модуль:

```bash
PYTHONPATH=src .venv/bin/python -m protokolist.cli input/meeting.mp3
```

Служебный вариант с явной командой тоже поддерживается:

```bash
PYTHONPATH=src .venv/bin/python -m protokolist.cli process input/meeting.mp3
```

Начиная с версии `0.3.0`, перед Whisper по умолчанию создается подготовленный файл `artifacts/prepared_audio.wav`: mono WAV 16 kHz. Исходная запись не изменяется.

Предобработку можно отключить:

```bash
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3 --no-preprocess
```

Подробности: `docs/audio_preprocessing.md`.

Основные параметры:

```bash
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3 \
  --model large-v3 \
  --language ru \
  --device cpu \
  --compute-type int8 \
  --cpu-threads 0 \
  --output-dir output
```

Для текущей рабочей машины с Xeon E5-2699 v3 и GT 710 рекомендуемый режим по умолчанию:

```text
model: large-v3
device: cpu
compute_type: int8
cpu_threads: 0
```

GT 710 не стоит рассматривать как полезную CUDA-карту для этого проекта, поэтому базовая рабочая стратегия — качественное CPU-распознавание.

## Служебные команды

```bash
PYTHONPATH=src .venv/bin/python -m protokolist.cli version
PYTHONPATH=src .venv/bin/python -m protokolist.cli doctor
PYTHONPATH=src .venv/bin/python -m protokolist.cli hardware
```

## Сбор информации о железе Ubuntu

Чтобы собрать отчет по железу машины:

```bash
./scripts/collect_hardware_ubuntu.sh
```

Будет создан файл:

```text
protokolist_hardware.txt
```

Его можно загрузить в ChatGPT для подбора оптимальных настроек модели, потоков, устройства и дальнейшего плана ускорения.

## Что делать после обработки

После завершения открой папку `output/`.

Там будет создана отдельная папка встречи, например:

```text
output/20260708_121500_meeting/
```

Главное, что нужно пользователю:

```text
meeting_chatgpt_package.zip
```

Или папка:

```text
CHATGPT_PACKAGE/
```

Загрузи zip или всю папку в ChatGPT и напиши:

```text
Выполни CHATGPT_TASK.md
```

## Что находится в CHATGPT_PACKAGE

### CHATGPT_TASK.md

Главная инструкция для ChatGPT. В ней описан полный алгоритм:

1. изучить контекст предприятия;
2. построить карту встречи;
3. исправить ошибки распознавания;
4. определить говорящих;
5. сделать осмысленную стенограмму;
6. составить протокол;
7. извлечь решения и задачи;
8. провести контроль качества.

### meeting_context.json

Профиль предприятия и правила обработки:

- участники;
- роли;
- мастера смен;
- производственный контекст;
- термины;
- правила неуверенности.

Важное правило профиля: мастеров смен шесть — Алла, Ольга, Мария, Юлия, Людмила, Светлана, но на одном совещании обычно присутствуют только трое из шести. ChatGPT не должен автоматически считать, что присутствовали все.

### meeting.raw.json

Главный источник правды.

Содержит:

- сырые сегменты Whisper;
- начало и конец каждого сегмента;
- слова с таймкодами;
- вероятности;
- параметры модели;
- язык;
- длительность;
- метаданные.

### meeting.raw.txt

Сырой текст с таймкодами для быстрого просмотра.

### meeting.cleaned.txt

Текст после мягкой словарной очистки.

### meeting.cleaned_with_timestamps.txt

Очищенный текст с полными диапазонами времени.

## Что находится в artifacts

`artifacts/` — это служебная папка для разработчика и ручной проверки.

Там сохраняются:

```text
prepared_audio.wav
meeting.raw.json
meeting.raw.txt
meeting.cleaned.txt
meeting.cleaned.srt
meeting.cleaned.docx
```

Эти файлы не обязательно отправлять в ChatGPT вручную, потому что нужное уже собрано в `CHATGPT_PACKAGE`.

## Качество распознавания

По умолчанию используется режим максимального качества:

```text
model: large-v3
language: ru
device: cpu
compute_type: int8
word_timestamps: true
```

Это медленнее, зато лучше подходит для длинных производственных совещаний.

## Профиль предприятия

Основной профиль находится здесь:

```text
profiles/factory_moydod.json
```

Он хранит:

- контекст предприятия;
- участников и роли;
- мастеров смен;
- термины;
- правила обработки.

## Словарь исправлений

```text
config/dictionary.json
```

Используется:

1. как подсказка для Whisper;
2. как мягкая постобработка после сохранения RAW.

RAW никогда не изменяется. Все исправления выполняются поверх него.

## Архитектура

```text
audio
   │
   ▼
CLI command
   │
   ▼
ffmpeg preprocessing
   │
   ▼
transcriber.py
   │
   ▼
raw_exporters.py
   │
   ▼
cleanup.py
   │
   ▼
artifacts/
   │
   ▼
chatgpt_package.py
   │
   ▼
CHATGPT_PACKAGE + zip
   │
   ▼
ChatGPT
```

## Roadmap

### v0.2

- [x] Faster-Whisper `large-v3`
- [x] word timestamps
- [x] RAW JSON
- [x] cleaned TXT/DOCX/SRT
- [x] профиль предприятия
- [x] пакет для ChatGPT
- [x] zip-архив для загрузки в ChatGPT
- [x] Ubuntu install/run scripts
- [x] рабочие папки `input`, `output`, `logs`, `models`, `cache`
- [x] CLI-only режим вместо GUI
- [x] команда сбора информации о железе
- [x] команда проверки окружения `doctor`
- [x] прямой запуск `protokolist input/meeting.mp3`

### v0.3

- [x] ffmpeg-предобработка: mono WAV 16 kHz
- [ ] нормализация громкости
- [ ] стабильная обработка длинных записей чанками
- [ ] прогресс по длительности аудио
- [ ] настройка output-папки

### v0.4

- [ ] диаризация говорящих
- [ ] автоматическая сборка итогового DOCX
- [ ] история обработанных записей
- [ ] режим серверной обработки папки с аудио

### v0.5

- [ ] автоматический запуск LLM через API
- [ ] генерация готового протокола без ручной загрузки в ChatGPT
- [ ] поддержка локальных LLM

## Главная идея

Protokolist — это не GUI над Whisper.

Это CLI-конвейер подготовки качественного AI-пакета для длинных производственных совещаний: максимум сырой информации, контекст предприятия, правила обработки и готовая инструкция для ChatGPT в одном архиве.
