# Protokolist

Protokolist — локальный помощник для расшифровки аудиозаписей совещаний и подготовки материалов для корпоративного протокола.

Первая версия делает главное:

- расшифровывает MP3/WAV/M4A/OGG/FLAC/MP4/WEBM через Faster-Whisper;
- сохраняет результат в TXT;
- сохраняет субтитры SRT;
- сохраняет DOCX;
- создает `*_protocol_prompt.md` — готовый промпт для ChatGPT с участниками и стенограммой.

## Статус проекта

Текущая версия: `0.1.0`.

Это ранняя рабочая версия. Главная цель — стабильно получить текст из записи совещания на Windows-ноутбуке без ручных команд.

## Требования

- Windows 10/11
- Python 3.11 или 3.12
- Интернет при первом запуске, чтобы скачать зависимости и модель Whisper
- 8–16 ГБ RAM достаточно для моделей `small` и `medium`

Для Lenovo IdeaPad Slim 5 14AHP9 / Ryzen 5 8645HS / 16 GB RAM рекомендуемый стартовый режим:

- модель: `small`
- язык: `ru`
- compute type: `int8`

## Установка на Windows

Открой PowerShell или CMD и выполни:

```bat
git clone https://github.com/iGrayf2/Protokolist.git
cd Protokolist
scripts\install_windows.cmd
```

После установки запуск GUI:

```bat
scripts\run_gui.cmd
```

## Быстрый запуск через перетаскивание файла

После установки можно перетащить аудиофайл на:

```text
scripts\transcribe_file.cmd
```

Результаты появятся в папке:

```text
output\
```

## Что получается на выходе

Для файла `meeting.mp3` будут созданы:

```text
output\meeting.txt
output\meeting.srt
output\meeting.docx
output\meeting_protocol_prompt.md
```

Файл `meeting_protocol_prompt.md` можно отправить в ChatGPT для формирования протокола совещания.

## Участники по умолчанию

Список постоянных участников хранится в файле:

```text
participants.txt
```

Его можно редактировать обычным Блокнотом.

## Архитектура

```text
Protokolist/
├── run.py
├── requirements.txt
├── participants.txt
├── scripts/
│   ├── install_windows.cmd
│   ├── run_gui.cmd
│   └── transcribe_file.cmd
└── src/
    └── protokolist/
        ├── app.py
        ├── cli.py
        ├── exporters.py
        ├── protocol_prompt.py
        ├── segments.py
        └── transcriber.py
```

## Дорожная карта

### v0.1

- [x] GUI
- [x] CLI
- [x] Faster-Whisper
- [x] TXT export
- [x] SRT export
- [x] DOCX export
- [x] prompt export for ChatGPT

### v0.2

- [ ] нормальный прогресс по длительности аудио
- [ ] настройка папки вывода
- [ ] сохранение настроек
- [ ] обработка длинных записей стабильными чанками
- [ ] проверка установленного Python и понятные сообщения об ошибках

### v0.3

- [ ] автоматическая сборка `Protokolist.exe`
- [ ] иконка приложения
- [ ] drag and drop в окно
- [ ] история обработанных совещаний

### v0.4

- [ ] диаризация говорящих
- [ ] роли участников
- [ ] словарь терминов предприятия
- [ ] автоподстановка типовых участников

### v0.5

- [ ] генерация протокола через LLM
- [ ] экспорт готового протокола в DOCX/PDF
- [ ] список решений
- [ ] Action Items

## Важное ограничение

Faster-Whisper хорошо распознает речь, но сам по себе не определяет надежно, кто именно говорит. В текущей версии файл `*_protocol_prompt.md` помогает ChatGPT сопоставлять реплики с участниками по контексту. Настоящая диаризация будет добавлена отдельным модулем позже.
