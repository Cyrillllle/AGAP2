from dataclasses import dataclass, field
from datetime import datetime
import threading

from core.fetcher import start_fetch
from core.parser import start_parse
from core.analyzer import start_analyze

@dataclass
class PipelineStats:
    users_added          : int = 0
    users_updated        : int = 0

    cvs_downloaded       : int = 0
    cvs_skipped          : int = 0

    cvs_parsed           : int = 0
    cvs_already_parsed   : int = 0

    cvs_analyzed         : int = 0

    errors               : list[str] = field(default_factory=list)


class PipelineManager:
    def __init__(self):
        self.running     = False
        self.step        = 1
        self.done        = False
        self.progress    = 0.0
        self.message     = ""
        self.error       = ""
        self.stats       = PipelineStats()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
        self.message = "Arrêt demandé…"

    def run(self, selection: str):
        self.running = True
        self.stats = PipelineStats()
        self._stop_event.clear()

        try:
            if self.step == 1 :
                fetch_stats = start_fetch(self, selection=selection, stop_requested=self._stop_event)
                if self._stop_event.is_set():
                    return self._finish("Arrêt pendant le fetch")
                                
            
            if self.step == 4 :
                self.progress = 0.0
                parse_stats = start_parse(self, stop_event=self._stop_event)

                if self._stop_event.is_set():
                    return self._finish("Arrêt pendant le parsing")


            if self.step == 5 :
                analyze_stats = start_analyze(self, stop_event=self._stop_event)

                self._finish("Pipeline terminé avec succès")

        except Exception as e:
            print(e)
            self.stats.errors.append(str(e))
            self._finish("Erreur pendant le pipeline")

        finally:
            print("finally")
            self.running = False
            self.progress = 1.0



    def _set_step(self, progress, message):
        self.progress = progress
        self.message = message

    def _merge_stats(self, partial_stats: dict):
        for key, value in partial_stats.items():
            if hasattr(self.stats, key):
                setattr(self.stats, key, getattr(self.stats, key) + value)

    def _finish(self, message):
        self.message = message
