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

В RAW metadata поле `audio_path` показывает связку исходника и подготовленного WAV:

```text
input/meeting.mp3 -> output/.../artifacts/prepared_audio.wav
```

Предобработку можно отключить:

```bash
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3 --no-preprocess
```

Подробности: `docs/audio_preprocessing.md`.

## Запуск долгой обработки через tmux

Если закрыть обычное окно терминала или SSH-сессию, запущенная обработка может остановиться. Для длинных записей лучше запускать Protokolist внутри `tmux`.

Установить `tmux`:

```bash
sudo apt install -y tmux
```

Создать отдельную сессию:

```bash
cd ~/Protokolist
tmux new -s protokolist
```

Внутри открывшейся сессии запустить обработку:

```bash
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3
```

Отключиться от сессии, не останавливая обработку:

```text
Ctrl+B
D
```

Вернуться обратно:

```bash
tmux attach -t protokolist
```

Полная памятка: `docs/tmux.md`.

## Основные параметры

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

Чтобы собрать отчет по железе машины:

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

- убрать GUI и Windows-first подход;
- закрепить Ubuntu-first CLI;
- сохранять RAW JSON/TXT;
- собирать ChatGPT-пакет;
- добавить профиль предприятия;
- добавить словарь терминов.

### v0.3

- ffmpeg-предобработка аудио;
- более устойчивые настройки Faster-Whisper;
- улучшенные экспортные артефакты;
- документация по запуску длинных задач через tmux.

### v0.4+

- диаризация;
- локальная LLM-обработка;
- серверный режим;
- автоматическая обработка папки `input/`;
- web/API-обертка.
