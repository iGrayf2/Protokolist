from __future__ import annotations

import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cleanup import cleanup_segments
from .exporters import write_docx, write_srt, write_txt
from .protocol_prompt import write_protocol_prompt
from .transcriber import transcribe_audio


class ProtokolistApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Protokolist")
        self.geometry("760x520")
        self.minsize(700, 460)

        self.audio_path = tk.StringVar()
        self.model_size = tk.StringVar(value="small")
        self.language = tk.StringVar(value="ru")
        self.status = tk.StringVar(value="Ready")
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.after(200, self._poll_log_queue)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.LabelFrame(root, text="Audio file", padding=10)
        file_frame.pack(fill=tk.X)

        entry = ttk.Entry(file_frame, textvariable=self.audio_path)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(file_frame, text="Browse", command=self._select_audio).pack(side=tk.LEFT)

        options = ttk.LabelFrame(root, text="Settings", padding=10)
        options.pack(fill=tk.X, pady=12)

        ttk.Label(options, text="Model:").grid(row=0, column=0, sticky="w")
        model_box = ttk.Combobox(
            options,
            textvariable=self.model_size,
            values=["tiny", "base", "small", "medium", "large-v3"],
            width=14,
            state="readonly",
        )
        model_box.grid(row=0, column=1, sticky="w", padx=(8, 24))

        ttk.Label(options, text="Language:").grid(row=0, column=2, sticky="w")
        ttk.Entry(options, textvariable=self.language, width=8).grid(row=0, column=3, sticky="w", padx=(8, 24))

        ttk.Button(options, text="Transcribe", command=self._start_transcription).grid(row=0, column=4, sticky="e")
        options.columnconfigure(5, weight=1)

        ttk.Label(root, textvariable=self.status).pack(fill=tk.X)

        log_frame = ttk.LabelFrame(root, text="Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.log_text = tk.Text(log_frame, height=16, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _select_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="Select audio or video file",
            filetypes=[
                ("Audio/video", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.webm *.mkv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.audio_path.set(path)

    def _append_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.status.set(message)

    def _poll_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(message)
        self.after(200, self._poll_log_queue)

    def _log_from_worker(self, message: str) -> None:
        self.log_queue.put(message)

    def _start_transcription(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Protokolist", "Transcription is already running")
            return

        audio = Path(self.audio_path.get().strip())
        if not audio.exists():
            messagebox.showerror("Protokolist", "Select an existing audio file")
            return

        self.log_text.delete("1.0", tk.END)
        self.worker = threading.Thread(target=self._run_transcription, args=(audio,), daemon=True)
        self.worker.start()

    def _run_transcription(self, audio: Path) -> None:
        try:
            output_dir = Path.cwd() / "output"
            segments = transcribe_audio(
                audio_path=audio,
                output_dir=output_dir,
                model_size=self.model_size.get(),
                language=self.language.get().strip() or "ru",
                compute_type="int8",
                progress=self._log_from_worker,
            )

            self._log_from_worker("Applying transcript cleanup dictionary...")
            segments = cleanup_segments(segments)

            stem = audio.stem
            files = [
                write_txt(segments, output_dir / f"{stem}.txt"),
                write_srt(segments, output_dir / f"{stem}.srt"),
                write_docx(segments, output_dir / f"{stem}.docx"),
                write_protocol_prompt(segments, output_dir / f"{stem}_protocol_prompt.md"),
            ]
            self._log_from_worker("Files created:")
            for file in files:
                self._log_from_worker(str(file.resolve()))
            self._log_from_worker("Finished")
        except Exception as exc:  # noqa: BLE001 - GUI must show any crash clearly.
            self._log_from_worker(f"ERROR: {exc}")


def main() -> None:
    app = ProtokolistApp()
    app.mainloop()
