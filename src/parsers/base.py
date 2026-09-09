from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.models.events import NormalizedEvent, ParseStatus


class ParserStats(BaseModel):
    total_lines: int = 0
    parsed_count: int = 0
    partially_parsed_count: int = 0
    unparsed_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return ((self.parsed_count + self.partially_parsed_count) / self.total_lines) * 100.0


class BaseLogParser(ABC):
    def __init__(self):
        self.stats = ParserStats()

    @abstractmethod
    def parse_line(self, line: str, default_node_id: str = "unknown-node") -> Optional[NormalizedEvent]:
        pass

    def parse_lines(self, lines: List[str], default_node_id: str = "unknown-node") -> List[NormalizedEvent]:
        events = []
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            self.stats.total_lines += 1
            event = self.parse_line(line_str, default_node_id)
            if event:
                if event.parse_status == ParseStatus.PARSED:
                    self.stats.parsed_count += 1
                elif event.parse_status == ParseStatus.PARTIALLY_PARSED:
                    self.stats.partially_parsed_count += 1
                else:
                    self.stats.unparsed_count += 1
                events.append(event)
            else:
                self.stats.unparsed_count += 1
        return events
