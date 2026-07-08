# Запуск через tmux

`tmux` нужен для длинной обработки записей: можно запустить Protokolist, закрыть SSH/консоль и потом вернуться к тому же процессу.

## Установка

```bash
sudo apt install -y tmux
```

## Запуск обработки в tmux

Создать отдельную сессию:

```bash
tmux new -s protokolist
```

Внутри открывшейся сессии запустить обработку:

```bash
cd ~/Protokolist
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3
```

## Отключиться, не останавливая обработку

Нажать последовательно:

```text
Ctrl+B
D
```

После этого окно терминала можно закрывать. Процесс продолжит работать внутри `tmux`.

## Вернуться к обработке

```bash
tmux attach -t protokolist
```

## Посмотреть список сессий

```bash
tmux ls
```

## Закрыть сессию после завершения

Когда обработка закончилась, внутри tmux можно написать:

```bash
exit
```

или нажать `Ctrl+D`.

## Короткая памятка

```bash
sudo apt install -y tmux
cd ~/Protokolist
tmux new -s protokolist
./scripts/transcribe_file_ubuntu.sh input/meeting.mp3
```

Отключиться: `Ctrl+B`, потом `D`.

Вернуться:

```bash
tmux attach -t protokolist
```
